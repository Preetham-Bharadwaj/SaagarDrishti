"""Common and reusable Pydantic schemas."""

from datetime import datetime, timezone
from typing import Generic, Optional, TypeVar
from pydantic import BaseModel, Field

T = TypeVar("T")


class HealthCheckResponse(BaseModel):
    """Standard health check status schema."""

    status: str = Field(default="ok", description="Operational status of the API")
    app_name: str = Field(..., description="Name of the application")
    version: str = Field(..., description="Application version")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), description="UTC timestamp of the check"
    )


class GeoCoordinate(BaseModel):
    """Geographic coordinate representation."""

    latitude: float = Field(..., ge=-90.0, le=90.0, description="Latitude in decimal degrees")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="Longitude in decimal degrees")


class GeoBoundingBox(BaseModel):
    """Geographic bounding box for region queries."""

    min_latitude: float = Field(..., ge=-90.0, le=90.0, description="Southernmost latitude boundary")
    max_latitude: float = Field(..., ge=-90.0, le=90.0, description="Northernmost latitude boundary")
    min_longitude: float = Field(..., ge=-180.0, le=180.0, description="Westernmost longitude boundary")
    max_longitude: float = Field(..., ge=-180.0, le=180.0, description="Easternmost longitude boundary")


class APIResponse(BaseModel, Generic[T]):
    """Standard envelope for API responses."""

    success: bool = True
    message: Optional[str] = None
    data: Optional[T] = None
