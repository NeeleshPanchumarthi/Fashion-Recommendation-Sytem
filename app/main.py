"""FastAPI application entry point (uvicorn app.main:app)."""

from __future__ import annotations

import logging
import time
import uuid
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.core.config import Settings, get_settings
from app.core.exceptions import AppError
from app.core.logging import configure_logging, request_id_var
from app.dependencies import ServiceContainer, build_container
from app.schemas.common import ErrorResponse

logger = logging.getLogger(__name__)

REQUEST_ID_HEADER = "X-Request-ID"


def _error(status_code: int, code: str, message: str) -> JSONResponse:
    body = ErrorResponse(detail=message, code=code, request_id=request_id_var.get())
    return JSONResponse(status_code=status_code, content=body.model_dump())


def create_app(settings: Optional[Settings] = None, container: Optional[ServiceContainer] = None) -> FastAPI:
    """Build the app. Tests pass a container of fakes; production builds the
    real one at startup."""
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        configure_logging(settings.SERVICE_NAME, settings.LOG_LEVEL)
        app.state.container = container or build_container(settings)
        if container is None and settings.WARM_MODELS_ON_STARTUP:
            started = time.perf_counter()
            try:
                app.state.container.warm()
                logger.info("Models loaded in %.1fs", time.perf_counter() - started)
            except Exception:  # noqa: BLE001 -- start anyway; /ready reports not ready
                logger.exception("Model warm-up failed")
        logger.info("%s started", settings.SERVICE_NAME)
        yield
        logger.info("%s stopped", settings.SERVICE_NAME)

    app = FastAPI(
        title="Fashion Search Service",
        description="Semantic fashion product search: query understanding, vector retrieval and reranking.",
        version="1.0.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=settings.CORS_ORIGIN_REGEX,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=[REQUEST_ID_HEADER],
    )

    @app.middleware("http")
    async def request_context(request: Request, call_next):
        request_id = request.headers.get(REQUEST_ID_HEADER) or uuid.uuid4().hex[:12]
        token = request_id_var.set(request_id)
        started = time.perf_counter()
        try:
            try:
                response = await call_next(request)
            except Exception:  # noqa: BLE001 -- last-resort handler: never leak a stack trace
                logger.exception("Unhandled error on %s %s", request.method, request.url.path)
                response = _error(500, "internal_error", "Internal server error.")
            response.headers[REQUEST_ID_HEADER] = request_id
            logger.info(
                "%s %s -> %d (%.0f ms)",
                request.method, request.url.path, response.status_code, (time.perf_counter() - started) * 1000,
            )
            return response
        finally:
            request_id_var.reset(token)

    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        level = logging.WARNING if exc.status_code < 500 else logging.ERROR
        logger.log(level, "%s on %s: %s", exc.code, request.url.path, exc.message)
        return _error(exc.status_code, exc.code, exc.message)

    app.include_router(api_router)
    return app


app = create_app()
