"""Data source availability API endpoint."""

from typing import List
from fastapi import APIRouter
from app.schemas.query import SourceAvailabilityReport
from app.services.data_availability import check_marine_data_availability

router = APIRouter(tags=["Data Sources"])


@router.get("/data-sources", response_model=List[SourceAvailabilityReport])
async def get_data_source_status() -> List[SourceAvailabilityReport]:
    """Return the operational availability status of all tracked upstream marine data sources.

    Includes INCOIS WFS layers, INCOIS WebGIS, and IMD marine weather,
    with timestamps, validity windows, known limitations, and audit notes.
    """
    return check_marine_data_availability()
