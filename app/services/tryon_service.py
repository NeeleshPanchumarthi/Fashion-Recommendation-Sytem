"""Use case: virtual try-on of a catalog product on the user's photo.

A try-on takes 20-60s, so it runs as a background job: start() validates the
request, prepares the photo and returns a job at once; the client polls get()
and shows the job's stage as progress. Jobs live in memory only -- a restart
drops them -- and expire after a TTL.

Privacy: the person photo is never written anywhere we keep. It is held in
memory until the job runs, then dropped; the result expires with the job.
"""

from __future__ import annotations

import io
import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Optional
from urllib.parse import urlparse

from PIL import Image, ImageOps, UnidentifiedImageError

from app.clients.tryon_client import TryOnClient
from app.core.exceptions import AppError, InvalidRequestError, NotFoundError, TooManyRequestsError
from app.domain.tryon import GARMENT_TYPES, TryOnJob, TryOnStage

logger = logging.getLogger(__name__)

# Leffa works at 768x1024. A photo of any other shape gets letterboxed with
# white bars, which shrinks the person and blurs the result.
MODEL_SIZE = (768, 1024)
MIN_PHOTO_SIDE = 256

# Garment images are fetched by the model service, so only accept catalog
# image hosts -- never an arbitrary URL from the client.
ALLOWED_GARMENT_HOSTS = ("media-amazon.com", "images-amazon.com", "ssl-images-amazon.com")


def prepare_person_photo(data: bytes) -> bytes:
    """Upright, centre-crop to 3:4 portrait, resize to the model size, re-encode
    as JPEG (which also drops EXIF metadata such as GPS location)."""
    try:
        image = Image.open(io.BytesIO(data))
        image = ImageOps.exif_transpose(image).convert("RGB")  # phone photos store rotation in EXIF
    except (UnidentifiedImageError, OSError) as exc:
        raise InvalidRequestError("That file isn't a readable image. Please upload a JPEG, PNG or WebP photo.") from exc

    width, height = image.size
    if min(width, height) < MIN_PHOTO_SIDE:
        raise InvalidRequestError("That photo is too small. Please use one at least 256 pixels wide.")

    target_ratio = MODEL_SIZE[0] / MODEL_SIZE[1]
    if width / height > target_ratio:
        # Too wide (e.g. landscape): keep full height, cut the sides equally.
        crop_w = round(height * target_ratio)
        left = (width - crop_w) // 2
        image = image.crop((left, 0, left + crop_w, height))
    else:
        # Too tall: keep full width, cut from the bottom so the head stays in frame.
        image = image.crop((0, 0, width, round(width / target_ratio)))

    out = io.BytesIO()
    image.resize(MODEL_SIZE, Image.Resampling.LANCZOS).save(out, format="JPEG", quality=95)
    return out.getvalue()


def validate_garment_url(url: str) -> str:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if parsed.scheme != "https" or not any(host == h or host.endswith("." + h) for h in ALLOWED_GARMENT_HOSTS):
        raise InvalidRequestError("The garment image must be a catalog product image.")
    return url


class TryOnService:
    def __init__(
        self,
        client: TryOnClient,
        max_active_jobs: int = 4,
        job_ttl_seconds: float = 900.0,
        max_upload_bytes: int = 10 * 1024 * 1024,
        workers: int = 2,
    ) -> None:
        self._client = client
        self.max_active_jobs = max_active_jobs
        self.job_ttl_seconds = job_ttl_seconds
        self.max_upload_bytes = max_upload_bytes
        self._jobs: dict[str, TryOnJob] = {}
        self._lock = threading.Lock()
        self._executor = ThreadPoolExecutor(max_workers=workers, thread_name_prefix="tryon")

    def start(self, person_photo: bytes, garment_image_url: str, garment_type: str) -> TryOnJob:
        if garment_type not in GARMENT_TYPES:
            raise InvalidRequestError(f"This product can't be tried on (garment type '{garment_type}').")
        if not person_photo:
            raise InvalidRequestError("Please upload a photo of yourself.")
        if len(person_photo) > self.max_upload_bytes:
            raise InvalidRequestError(f"That photo is too large. The limit is {self.max_upload_bytes // (1024 * 1024)} MB.")
        validate_garment_url(garment_image_url)
        prepared = prepare_person_photo(person_photo)

        job = TryOnJob(garment_type=garment_type)
        with self._lock:
            self._expire_old_jobs()
            active = sum(1 for j in self._jobs.values() if not j.finished)
            if active >= self.max_active_jobs:
                raise TooManyRequestsError("Lots of people are trying things on right now. Please try again in a minute.")
            self._jobs[job.job_id] = job

        self._executor.submit(self._run, job, prepared, garment_image_url)
        logger.info("Try-on job %s started (%s)", job.job_id, garment_type)
        return job

    def get(self, job_id: str) -> TryOnJob:
        with self._lock:
            self._expire_old_jobs()
            job = self._jobs.get(job_id)
        if job is None:
            raise NotFoundError("That try-on has expired or doesn't exist. Please start a new one.")
        return job

    def shutdown(self) -> None:
        self._executor.shutdown(wait=False, cancel_futures=True)

    def _run(self, job: TryOnJob, person_photo: bytes, garment_image_url: str) -> None:
        def on_status(stage: TryOnStage, queue_position: Optional[int]) -> None:
            job.stage, job.queue_position = stage, queue_position

        try:
            job.result_image, job.result_mime_type = self._client.generate(
                person_photo, garment_image_url, job.garment_type, on_status
            )
            job.stage = TryOnStage.DONE
            logger.info("Try-on job %s done in %.0fs", job.job_id, job.elapsed_seconds)
        except AppError as exc:
            job.error, job.stage = exc.message, TryOnStage.FAILED
            logger.warning("Try-on job %s failed: %s", job.job_id, exc.message)
        except Exception:  # noqa: BLE001 -- a worker thread must never die silently
            job.error, job.stage = "Something went wrong while generating the try-on.", TryOnStage.FAILED
            logger.exception("Try-on job %s crashed", job.job_id)
        finally:
            job.queue_position = None
            job.finished_at = time.monotonic()

    def _expire_old_jobs(self) -> None:
        now = time.monotonic()
        expired = [jid for jid, j in self._jobs.items() if now - j.created_at > self.job_ttl_seconds]
        for jid in expired:
            del self._jobs[jid]
