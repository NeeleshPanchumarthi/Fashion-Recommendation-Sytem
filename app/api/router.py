"""Mounts every API version under /api."""

from fastapi import APIRouter

from app.api.v1 import health, search

api_router = APIRouter(prefix="/api")

v1 = APIRouter(prefix="/v1")
v1.include_router(health.router)
v1.include_router(search.router)

api_router.include_router(v1)
