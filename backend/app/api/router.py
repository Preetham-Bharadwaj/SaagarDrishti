"""Top-level API router combining versioned sub-routers."""

from fastapi import APIRouter
from app.api.v1 import data_sources, health, query, pfz

api_router = APIRouter()
api_router.include_router(health.router, prefix="/v1")
api_router.include_router(query.router, prefix="/v1")
api_router.include_router(data_sources.router, prefix="/v1")
api_router.include_router(pfz.router, prefix="/v1")
