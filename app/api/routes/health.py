"""Liveness and readiness probes."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.dependencies import get_health_service
from app.schemas.health import HealthResponse, ReadinessResponse
from app.services.health_service import HealthService

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Liveness: the process is up. Deliberately checks nothing else."""
    return HealthResponse(service=get_settings().SERVICE_NAME)


@router.get("/ready", response_model=ReadinessResponse, responses={503: {"model": ReadinessResponse}})
def ready(service: HealthService = Depends(get_health_service)) -> JSONResponse:
    """Readiness: models loaded and the vector database reachable."""
    report = service.readiness()
    body = ReadinessResponse(
        status="ready" if report.ready else "not_ready",
        service=get_settings().SERVICE_NAME,
        checks=report.checks,
    )
    return JSONResponse(status_code=200 if report.ready else 503, content=body.model_dump())
