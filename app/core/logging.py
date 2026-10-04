"""Centralized logging: one format for the API and the worker.

Every record carries the service name and the current request ID (set by
the API middleware; "-" outside a request, e.g. in the worker), so a single
request can be followed across modules.
"""

from __future__ import annotations

import logging
import sys
from contextvars import ContextVar

request_id_var: ContextVar[str] = ContextVar("request_id", default="-")

LOG_FORMAT = "%(asctime)s %(levelname)-7s [%(service)s] [req=%(request_id)s] %(name)s: %(message)s"

# Libraries that log every HTTP call or download at INFO.
_NOISY_LOGGERS = ("httpx", "httpcore", "urllib3", "sentence_transformers", "huggingface_hub", "pinecone")


class _ContextFilter(logging.Filter):
    def __init__(self, service: str) -> None:
        super().__init__()
        self.service = service

    def filter(self, record: logging.LogRecord) -> bool:
        record.service = self.service
        record.request_id = request_id_var.get()
        return True


def configure_logging(service: str, level: str = "INFO") -> None:
    """Configure the root logger once per process. Safe to call again."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(LOG_FORMAT))
    handler.addFilter(_ContextFilter(service))

    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(level.upper())

    for name in _NOISY_LOGGERS:
        logging.getLogger(name).setLevel(logging.WARNING)
    # Let uvicorn's own loggers go through the same handler and format.
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logging.getLogger(name).handlers[:] = []
        logging.getLogger(name).propagate = True
