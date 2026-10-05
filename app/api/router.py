"""Mounts every route under /api."""

from fastapi import APIRouter

from app.api.routes import health, search, tryon

api_router = APIRouter(prefix="/api")
api_router.include_router(health.router)
api_router.include_router(search.router)
api_router.include_router(tryon.router)
