"""Response shape shared by every error the API returns."""

from __future__ import annotations

from pydantic import BaseModel


class ErrorResponse(BaseModel):
    # "detail" matches FastAPI's own error key, which the frontend reads.
    detail: str
    code: str
    request_id: str
