"""Typed schemas for marine query workflow, planner, evidence validation, and data availability."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.schemas.common import GeoCoordinate
from app.schemas.marine_hazard import MarineHazardForecast
from app.schemas.ocean_analytics import OceanSSTResult
from app.schemas.official_warning import OfficialMarineWarning


class QueryIntent(str, Enum):
    """Categorized intent of a user's marine query."""

    NEAREST_PFZ = "nearest_pfz"
    MARINE_CONDITIONS = "marine_conditions"
    WEATHER_HAZARD = "weather_hazard"
    GENERAL_MARINE_INFORMATION = "general_marine_information"


class DataStatus(str, Enum):
    """Operational availability status of an upstream marine data provider."""

    CURRENT = "current"
    EXPIRED = "expired"
    UNAVAILABLE = "unavailable"
    NOT_VERIFIED = "not_verified"


class QueryWorkflowStatus(str, Enum):
    """Workflow execution status for marine queries."""

    SUCCESS = "SUCCESS"
    DATA_UNAVAILABLE = "DATA_UNAVAILABLE"
    LOCATION_REQUIRED = "LOCATION_REQUIRED"
    EVIDENCE_REJECTED = "EVIDENCE_REJECTED"
    ERROR = "ERROR"


class SourceAvailabilityReport(BaseModel):
    """Report detailing operational status and limitations of a marine data source."""

    source_name: str = Field(..., description="Name of the upstream service or dataset")
    source_url: str = Field(..., description="Access URL or endpoint")
    status: DataStatus = Field(..., description="Operational status: current, expired, unavailable, not_verified")
    latest_verified_timestamp: Optional[datetime] = Field(
        None, description="Timestamp of latest verified record from source"
    )
    validity_window: Optional[str] = Field(None, description="Reported validity range (e.g. valid_from to valid_to)")
    limitations: List[str] = Field(default_factory=list, description="Known operational or data quality limitations")
    notes: str = Field(..., description="Auditor and operational assessment notes")


class MarineQueryRequest(BaseModel):
    """User request payload for marine intelligence query."""

    query: str = Field(..., description="Natural language question or query regarding marine conditions or PFZ")
    user_location: Optional[GeoCoordinate] = Field(
        None, description="Optional current GPS coordinate of the vessel or fisher"
    )
    departure_port: Optional[str] = Field(
        None, description="Optional name of landing center or departure port (e.g., Malpe, Karwar, Mangalore)"
    )


class CandidatePFZResult(BaseModel):
    """Grounded, validated candidate PFZ hotspot with deterministic distance."""

    hotspot_id: str
    coordinate: GeoCoordinate
    distance_km: float = Field(..., description="Deterministic great-circle distance in kilometers from origin")
    bearing_deg: Optional[float] = None
    depth_m: Optional[float] = None
    landing_center: str
    valid_from: Optional[datetime] = None
    valid_to: datetime
    data_source: str


class EvidenceAuditResult(BaseModel):
    """Detailed audit trail validating source evidence before generating answer."""

    passed: bool = Field(..., description="Whether evidence met all domain and safety criteria")
    checks_performed: List[str] = Field(default_factory=list)
    provenance_sources: List[str] = Field(default_factory=list)
    is_landing_center_mistaken_for_pfz: bool = Field(
        default=False, description="Flagged true if a coastal landing center was mistakenly passed as an ocean PFZ"
    )
    is_expired: bool = Field(default=False, description="Flagged true if evidence validity has lapsed")
    sources_disagree: bool = Field(
        default=False, description="Flagged true if official statutory warning and numerical model forecast disagree"
    )
    rejection_reasons: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class MarineQueryResponse(BaseModel):
    """Evidence-grounded response to a marine intelligence query."""

    query: str
    intent: QueryIntent
    status: QueryWorkflowStatus
    answer: str = Field(..., description="Grounded, safety-conscious response explanation")
    candidate_pfz: Optional[CandidatePFZResult] = None
    marine_hazard: Optional[MarineHazardForecast] = Field(
        None, description="Detailed wave and marine hazard forecast if available"
    )
    official_warning: Optional[OfficialMarineWarning] = Field(
        None, description="Active official government bulletin or warning (IMD / DFO) if available"
    )
    ocean_sst: Optional[OceanSSTResult] = Field(
        None,
        description=(
            "Compact Copernicus OSTIA Level-4 foundation SST summary for marine-conditions queries. "
            "None when SST retrieval is blocked, failed, or not attempted. "
            "SST alone DOES NOT prove fish abundance or safe navigation."
        ),
    )
    sources_disagree: bool = Field(
        default=False, description="Flagged true if official statutory warning and numerical model forecast disagree"
    )
    evidence_audit: EvidenceAuditResult
    sources_checked: List[SourceAvailabilityReport] = Field(default_factory=list)
    tools_used: List[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
