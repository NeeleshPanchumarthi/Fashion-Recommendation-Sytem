import io
import time

import pytest
from PIL import Image

from app.core.exceptions import InvalidRequestError, NotFoundError, TooManyRequestsError
from app.domain.tryon import TryOnStage
from app.services.tryon_service import MODEL_SIZE, TryOnService, prepare_person_photo, validate_garment_url
from tests.fakes import FakeTryOnClient

GARMENT = "https://m.media-amazon.com/images/I/41NVNs6JKxL._AC_.jpg"


def photo(width=1200, height=800, fmt="JPEG") -> bytes:
    out = io.BytesIO()
    Image.new("RGB", (width, height), (200, 180, 160)).save(out, format=fmt)
    return out.getvalue()


def wait_until_finished(service, job_id, timeout=5.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        job = service.get(job_id)
        if job.finished:
            return job
        time.sleep(0.01)
    raise AssertionError("job did not finish")


@pytest.mark.parametrize("size", [(1200, 800), (600, 1400), (768, 1024)])
def test_photo_is_cropped_to_model_portrait_size(size):
    prepared = Image.open(io.BytesIO(prepare_person_photo(photo(*size))))
    assert prepared.size == MODEL_SIZE
    assert prepared.format == "JPEG"


def test_png_photos_are_accepted():
    assert Image.open(io.BytesIO(prepare_person_photo(photo(fmt="PNG")))).size == MODEL_SIZE


@pytest.mark.parametrize("data", [b"not an image", photo(100, 120)])
def test_unreadable_or_tiny_photos_are_rejected(data):
    with pytest.raises(InvalidRequestError):
        prepare_person_photo(data)


@pytest.mark.parametrize(
    "url",
    [
        "http://m.media-amazon.com/images/I/x.jpg",          # not https
        "https://evil.example.com/x.jpg",
        "https://m.media-amazon.com.evil.com/x.jpg",         # lookalike host
        "https://127.0.0.1/x.jpg",
    ],
)
def test_only_catalog_image_urls_are_allowed(url):
    with pytest.raises(InvalidRequestError):
        validate_garment_url(url)


def test_catalog_image_url_is_allowed():
    assert validate_garment_url(GARMENT) == GARMENT


def test_job_runs_to_done_with_the_prepared_photo():
    client = FakeTryOnClient()
    service = TryOnService(client)
    job = service.start(photo(), GARMENT, "upper_body")

    done = wait_until_finished(service, job.job_id)
    assert done.stage == TryOnStage.DONE
    assert done.result_image == b"fake-image"
    sent_photo, sent_url, sent_type = client.calls[0]
    assert Image.open(io.BytesIO(sent_photo)).size == MODEL_SIZE
    assert (sent_url, sent_type) == (GARMENT, "upper_body")


def test_failed_job_carries_a_user_facing_error():
    service = TryOnService(FakeTryOnClient(fail=True))
    job = service.start(photo(), GARMENT, "dresses")

    failed = wait_until_finished(service, job.job_id)
    assert failed.stage == TryOnStage.FAILED
    assert "quota" in failed.error
    assert failed.result_image is None


def test_unsupported_garment_type_is_rejected():
    with pytest.raises(InvalidRequestError):
        TryOnService(FakeTryOnClient()).start(photo(), GARMENT, "shoes")


def test_oversized_upload_is_rejected():
    with pytest.raises(InvalidRequestError):
        TryOnService(FakeTryOnClient(), max_upload_bytes=100).start(photo(), GARMENT, "upper_body")


def test_too_many_active_jobs_is_rejected():
    service = TryOnService(FakeTryOnClient(), max_active_jobs=0)
    with pytest.raises(TooManyRequestsError):
        service.start(photo(), GARMENT, "upper_body")


def test_expired_and_unknown_jobs_are_not_found():
    service = TryOnService(FakeTryOnClient(), job_ttl_seconds=-1)  # already expired
    job = service.start(photo(), GARMENT, "upper_body")
    with pytest.raises(NotFoundError):
        service.get(job.job_id)
    with pytest.raises(NotFoundError):
        service.get("nope")
