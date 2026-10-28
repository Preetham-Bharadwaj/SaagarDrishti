"""Pydantic schemas for Potential Fishing Zone (PFZ) advisories."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field
from app.schemas.common import GeoCoordinate


class PFZAdvisoryItem(BaseModel):
    """Individual PFZ advisory hotspot or zone point from INCOIS records."""

    item_id: str = Field(..., description="Unique identifier for the advisory hotspot (e.g., LC_UNIQUE_ code or feature ID)")
    coordinate: GeoCoordinate = Field(..., description="Target PFZ hotspot coordinates (decimal degrees)")
    landing_center: str = Field(..., description="Associated landing center (e.g., Karwar, Malpe, Mangalore, Belekeri)")
    landing_center_coordinate: Optional[GeoCoordinate] = Field(
        None, description="Coordinates of the origin fish landing center"
    )
    district: Optional[str] = Field(None, description="Coastal district (e.g., Dakshina Kannada, Udupi, Uttara Kannada)")
    direction_bearing_deg: Optional[float] = Field(
        None, ge=0.0, le=360.0, description="Direction / bearing from landing center in degrees (0-360)"
    )
    direction_compass: Optional[str] = Field(
        None, description="Compass cardinal/intercardinal direction (e.g., W, NW, SW, WSW)"
    )
    distance_km: Optional[float] = Field(
        None, ge=0.0, description="Nominal distance from landing center in kilometers"
    )
    distance_range_km: Optional[Tuple[float, float]] = Field(
        None, description="Distance range (from_km, to_km) from landing center"
    )
    depth_m: Optional[float] = Field(
        None, ge=0.0, description="Nominal ocean depth at the zone in meters"
    )
    depth_range_m: Optional[Tuple[float, float]] = Field(
        None, description="Bathymetric depth range (from_m, to_m) in meters"
    )
    status: Optional[str] = Field(
        default="YES", description="Advisory activation status (e.g., 'YES' for active hotspot, 'NO' for nil)"
    )
    raw_properties: Optional[Dict[str, Any]] = Field(
        default=None, description="Preserved verbatim source attributes from INCOIS"
    )


class PFZAdvisoryPayload(BaseModel):
    """Complete incoming PFZ advisory document for ingestion and validation."""

    advisory_id: str = Field(..., description="Official advisory identification code (e.g., FORECAST_I)")
    source: str = Field(default="INCOIS", description="Data provider or dissemination source")
    source_url: Optional[str] = Field(
        None, description="Verified upstream source URL from which advisory was fetched or downloaded"
    )
    region: str = Field(default="Karnataka Coast", description="Coastal sector or state")
    sector_id: Optional[str] = Field(default="SEC004", description="INCOIS sector code (e.g., SEC004 for Karnataka)")
    retrieved_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp when data was fetched or loaded into SaagarDrishti",
    )
    issued_at: Optional[datetime] = Field(
        None, description="Timestamp when the advisory was published or updated by provider"
    )
    valid_from: Optional[datetime] = Field(None, description="Start of advisory validity period")
    valid_to: Optional[datetime] = Field(None, description="End of advisory validity period")
    quality_limitations: List[str] = Field(
        default_factory=list,
        description="Data-quality constraints (e.g., satellite cloud occlusion, current-driven drift)",
    )
    items: List[PFZAdvisoryItem] = Field(default_factory=list, description="List of advisory zones/hotspots")


class PFZValidationResult(BaseModel):
    """Validation report summary for an ingested PFZ advisory."""

    advisory_id: str
    is_valid: bool
    is_expired: bool = False
    total_items: int
    valid_items_count: int
    duplicate_items_count: int = 0
    errors: List[str] = Field(default_factory=list, description="Fatal validation issues preventing ingestion")
    warnings: List[str] = Field(default_factory=list, description="Non-fatal warnings (e.g., boundary alerts, expired data)")
    data_quality_notes: List[str] = Field(default_factory=list, description="Operational notes on provider limitations")
