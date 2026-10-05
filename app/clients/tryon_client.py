"""Virtual try-on client for the Leffa Hugging Face Space (Gradio API).

The only module that knows the Space's endpoint and inputs. It runs one
try-on, reporting progress through a callback as the Space moves the job
along, and returns the generated image bytes. Callers get a
DependencyUnavailableError on failure -- never a raw Gradio error.
"""

from __future__ import annotations

import logging
import mimetypes
import shutil
import tempfile
import threading
import time
from concurrent.futures import CancelledError
from pathlib import Path
from typing import Callable, Optional

from app.core.exceptions import DependencyUnavailableError
from app.domain.tryon import UPPER_BODY, TryOnStage

logger = logging.getLogger(__name__)

DEPENDENCY = "tryon"
LEFFA_ENDPOINT = "/leffa_predict_vt"
POLL_INTERVAL_SECONDS = 0.5
# Retries per connection when it is reset while being opened (with backoff
# 0.5s, 1s, 2s...). Six keeps the odds of a failed try-on tiny even when
# ~40% of connections to *.hf.space get reset.
CONNECT_RETRIES = 6

UNREACHABLE = "The try-on service is unreachable right now. Please try again shortly."

# (stage, queue position when waiting for the GPU) -> None
StatusCallback = Callable[[TryOnStage, Optional[int]], None]

_retries_installed = False
_retries_lock = threading.Lock()


def _retry_dropped_connections() -> None:
    """Make every httpx connection retry when it is reset while being opened.

    One try-on opens about six connections (config, two uploads, queue join,
    status stream, result download), and gradio_client makes them through
    module-level httpx calls that take no transport option. A connection
    reset on any of them (WinError 10054, common on some networks) used to
    fail the whole try-on. httpx can retry, but only via its transport, so we
    default `retries` on the transport classes.

    Safe for every request, including POSTs: httpx only retries while
    connecting (TCP + TLS handshake), before any request data is sent.
    Process-wide, so other httpx users (e.g. the Groq client) benefit too;
    a caller that passes `retries` explicitly keeps its own value.
    """
    global _retries_installed
    with _retries_lock:
        if _retries_installed:
            return
        import httpx

        for transport in (httpx.HTTPTransport, httpx.AsyncHTTPTransport):
            original_init = transport.__init__

            def __init__(self, *args, _original_init=original_init, **kwargs):
                kwargs.setdefault("retries", CONNECT_RETRIES)
                _original_init(self, *args, **kwargs)

            transport.__init__ = __init__
        _retries_installed = True


class TryOnClient:
    def __init__(self, space: str, token: str = "", timeout_seconds: float = 180.0, connect_attempts: int = 3) -> None:
        self.space = space
        self._token = token or None
        self.timeout_seconds = timeout_seconds
        self.connect_attempts = max(1, connect_attempts)
        self._client = None
        self._lock = threading.Lock()
        _retry_dropped_connections()

    def generate(
        self,
        person_image: bytes,
        garment_image_url: str,
        garment_type: str,
        on_status: StatusCallback = lambda stage, position: None,
    ) -> tuple[bytes, str]:
        """Dress the person (JPEG bytes) in the garment. Returns (image bytes, mime type)."""
        from gradio_client import handle_file  # deferred: heavy import, only needed for try-on

        with tempfile.TemporaryDirectory(prefix="tryon_") as tmp:
            person_path = Path(tmp) / "person.jpg"
            person_path.write_bytes(person_image)

            on_status(TryOnStage.UPLOADING, None)
            try:
                job = self._connect().submit(
                    src_image_path=handle_file(str(person_path)),
                    ref_image_path=handle_file(garment_image_url),
                    ref_acceleration=False,
                    step=30,
                    scale=2.5,
                    seed=42,
                    # Leffa has two checkpoints: VITON-HD (tops only) and DressCode (all types).
                    vt_model_type="viton_hd" if garment_type == UPPER_BODY else "dress_code",
                    vt_garment_type=garment_type,
                    vt_repaint=False,
                    api_name=LEFFA_ENDPOINT,
                )
                outputs = self._wait(job, on_status)
            except DependencyUnavailableError:
                raise
            except Exception as exc:  # noqa: BLE001 -- Gradio, network and quota errors
                self._client = None  # reconnect next time; the Space may have restarted
                raise DependencyUnavailableError(DEPENDENCY, _friendly_error(exc)) from exc

        return _read_and_delete(outputs)

    def _wait(self, job, on_status: StatusCallback):
        from gradio_client.utils import Status

        deadline = time.monotonic() + self.timeout_seconds
        last: tuple = ()
        while not job.done():
            if time.monotonic() > deadline:
                job.cancel()
                raise DependencyUnavailableError(DEPENDENCY, "The try-on took too long. Please try again.")
            status = job.status()
            if status.code in (Status.JOINING_QUEUE, Status.IN_QUEUE, Status.QUEUE_FULL):
                update = (TryOnStage.WAITING_FOR_GPU, (status.rank + 1) if status.rank is not None else None)
            elif status.code in (Status.PROCESSING, Status.ITERATING, Status.PROGRESS):
                update = (TryOnStage.GENERATING, None)
            elif status.code == Status.FINISHED:
                update = (TryOnStage.FINISHING, None)  # result is being downloaded
            else:
                update = ()
            if update and update != last:
                on_status(*update)
                last = update
            time.sleep(POLL_INTERVAL_SECONDS)
        on_status(TryOnStage.FINISHING, None)
        return job.result()

    def _connect(self):
        """The Gradio client, created once. Creating it fetches the Space's
        config, which fails on connection resets -- so retry."""
        from gradio_client import Client

        with self._lock:
            if self._client is not None:
                return self._client
            for attempt in range(1, self.connect_attempts + 1):
                try:
                    self._client = Client(self.space, token=self._token, verbose=False)
                    return self._client
                except Exception as exc:  # noqa: BLE001
                    logger.warning("Connecting to Space %s failed (attempt %d): %s", self.space, attempt, exc)
                    if attempt == self.connect_attempts:
                        raise DependencyUnavailableError(DEPENDENCY, UNREACHABLE) from exc
                    time.sleep(attempt)
        raise AssertionError("unreachable")


def _read_and_delete(outputs) -> tuple[bytes, str]:
    """Read the generated image; delete every downloaded output (they include
    the person's mask, which we never keep)."""
    image_path = Path(outputs[0])
    try:
        data = image_path.read_bytes()
    finally:
        for path in outputs:
            if path:
                shutil.rmtree(Path(path).parent, ignore_errors=True)
    mime = mimetypes.guess_type(image_path.name)[0] or "image/webp"
    return data, mime


def _is_network_error(exc: BaseException) -> bool:
    """A dropped connection, anywhere in the exception chain. gradio_client
    surfaces a dropped status stream as a cancelled job."""
    import httpx

    while exc is not None:
        if isinstance(exc, (httpx.TransportError, ConnectionError, CancelledError)):
            return True
        exc = exc.__cause__ or exc.__context__
    return False


def _friendly_error(exc: Exception) -> str:
    text = str(exc).lower()
    if "quota" in text or "runs limit" in text:
        return "The free GPU quota for try-on is used up for now. Please try again later."
    if "queue" in text and "full" in text:
        return "The try-on service is very busy. Please try again in a minute."
    logger.warning("Try-on failed: %r", exc)
    if _is_network_error(exc):
        return UNREACHABLE
    return "The try-on couldn't be generated. Please try again with a different photo."
