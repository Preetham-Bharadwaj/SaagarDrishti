"""Health and system status API endpoints."""

from fastapi import APIRouter
from app import __version__
from app.core.config import settings
from app.schemas.common import HealthCheckResponse

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthCheckResponse)
async def check_health() -> HealthCheckResponse:
    """Return health status, application name, and version."""
    return HealthCheckResponse(
        status="ok",
        app_name=settings.APP_NAME,
        version=__version__,
    )
