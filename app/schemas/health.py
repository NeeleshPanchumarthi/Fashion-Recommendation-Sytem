"""HTTP contracts for the health and readiness endpoints."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    service: str


class ReadinessResponse(BaseModel):
    status: Literal["ready", "not_ready"]
    service: str
    checks: dict[str, dict[str, Any]]
