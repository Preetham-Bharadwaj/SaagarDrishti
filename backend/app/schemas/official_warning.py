"""Typed schemas for official government marine weather bulletins and warnings.

Covers statutory warnings issued by official authorities:
- India Meteorological Department (IMD) / Cyclone Warning Centre (CWC)
- Indian National Centre for Ocean Information Services (INCOIS)
- Department of Fisheries, Government of Karnataka (DFO)

These statutory warnings represent authoritative regulatory safety notices and
must strictly supersede prototype numerical model guidance.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class OfficialWarningSeverity(str, Enum):
    """Standardized severity classification for official government marine alerts."""

    NO_WARNING = "no_warning"           # Normal conditions, no alert issued
    ADVISORY = "advisory"               # Be aware; caution advised for small craft
    WARNING = "warning"                 # Hazardous conditions; fishers advised not to venture
    SEVERE_WARNING = "severe_warning"   # Extremely dangerous; port operations suspended


class OfficialMarineWarning(BaseModel):
    """Structured record of an official government marine bulletin or warning."""

    bulletin_id: str = Field(..., description="Unique official bulletin or report ID")
    issuing_authority: str = Field(
        ...,
        description="Official government body (e.g. 'India Meteorological Department (IMD) - CWC Thiruvananthapuram')",
    )
    issued_at: datetime = Field(..., description="Timestamp when bulletin was officially issued")
    valid_from: datetime = Field(..., description="Start of warning validity period")
    valid_to: datetime = Field(..., description="End of warning validity period")
    coastal_zone: str = Field("Karnataka Coast", description="Geographic zone covered by advisory")
    severity: OfficialWarningSeverity = Field(
        OfficialWarningSeverity.NO_WARNING, description="Severity of official alert"
    )
    warning_type: str = Field(
        "Fishermen Warning",
        description="Category: Fishermen Warning, Squally Weather, High Wave Alert, Port Warning, etc.",
    )
    warning_text: str = Field(..., description="Verbatim or summary alert text from the bulletin")
    wind_speed_knots_min: Optional[float] = Field(None, description="Minimum expected wind speed in knots")
    wind_speed_knots_max: Optional[float] = Field(None, description="Maximum expected wind speed/gust in knots")
    fishermen_advised_not_to_venture: bool = Field(
        False, description="Explicit life-safety flag: true if fishers are instructed not to venture out"
    )
    source_document: str = Field(..., description="Original filename, bulletin URL, or reference")
    ingested_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def is_currently_active(self) -> bool:
        """Check if this official warning is currently in effect."""
        now = datetime.now(timezone.utc)
        vt = self.valid_to if self.valid_to.tzinfo else self.valid_to.replace(tzinfo=timezone.utc)
        vf = self.valid_from if self.valid_from.tzinfo else self.valid_from.replace(tzinfo=timezone.utc)
        return vf <= now <= vt


class OfficialBulletinPayload(BaseModel):
    """Container payload for ingested official bulletins."""

    source: str = "IMD Coastal / Marine Warning"
    bulletins: List[OfficialMarineWarning] = Field(default_factory=list)
    notes: List[str] = Field(default_factory=list)
