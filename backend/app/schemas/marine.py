"""Pydantic schemas for oceanographic and marine observation datasets."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from app.schemas.common import GeoCoordinate


class OceanographicObservation(BaseModel):
    """Schema representing physical and biological ocean parameters at a location."""

    coordinate: GeoCoordinate
    timestamp: datetime = Field(..., description="Observation timestamp")
    sea_surface_temperature_c: Optional[float] = Field(
        None, description="Sea Surface Temperature (SST) in Celsius"
    )
    chlorophyll_mg_m3: Optional[float] = Field(
        None, ge=0.0, description="Chlorophyll-a concentration in mg/m^3"
    )
    significant_wave_height_m: Optional[float] = Field(
        None, ge=0.0, description="Significant wave height in meters"
    )
    wind_speed_m_s: Optional[float] = Field(
        None, ge=0.0, description="Wind speed in meters per second"
    )
    data_source: str = Field(..., description="Source origin (e.g., INCOIS, Satellite, Buoy)")
