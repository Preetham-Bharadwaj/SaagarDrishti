"""INCOIS Potential Fishing Zone (PFZ) GeoJSON API endpoint.

Serves current-day Karnataka PFZ advisory polylines fetched live from the
INCOIS GeoServer WFS (PFZ_Automation:pfzlines layer).  Each feature is
validated for geographic bounds and temporal currency before being forwarded
to the frontend map.
"""

from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(tags=["PFZ"])

# INCOIS WFS endpoint – no authentication required
_INCOIS_PFZ_WFS = (
    "https://incois.gov.in/geoserver/PFZ_Automation/ows"
    "?service=WFS&version=1.1.0&request=GetFeature"
    "&typeName=PFZ_Automation:pfzlines&outputFormat=application/json"
)

# Karnataka approximate bounding box (degrees)
_KA_LAT_MIN, _KA_LAT_MAX = 11.5, 16.5
_KA_LON_MIN, _KA_LON_MAX = 73.0, 76.0

# Max age tolerance in days (PFZ advisories refresh daily)
_MAX_AGE_DAYS = 3


class PFZLayer(BaseModel):
    """Metadata for the PFZ GeoJSON response."""

    source: str = "INCOIS WFS – PFZ_Automation:pfzlines"
    source_url: str = _INCOIS_PFZ_WFS.split("?")[0]
    retrieved_at: str
    julian_day: Optional[int] = Field(None, description="Julian day of the advisory features")
    year: Optional[int] = Field(None, description="Year of the advisory features")
    is_current: bool = Field(False, description="True when features belong to today's advisory")
    feature_count: int = 0
    chl_count: int = Field(0, description="Number of chlorophyll-based PFZ lines")
    sst_count: int = Field(0, description="Number of SST-based PFZ lines")
    validation_notes: List[str] = Field(default_factory=list)


class PFZGeoJSONResponse(BaseModel):
    """GeoJSON FeatureCollection of Karnataka PFZ lines with audit metadata."""

    type: str = "FeatureCollection"
    features: List[Dict[str, Any]] = Field(default_factory=list)
    metadata: PFZLayer


def _is_in_karnataka_bounds(coordinates: List[Any]) -> bool:
    """Check that all coordinate vertices are within the Karnataka bounding box."""
    for line in coordinates:
        for pt in line:
            lon, lat = pt[0], pt[1]
            if not (_KA_LAT_MIN <= lat <= _KA_LAT_MAX and _KA_LON_MIN <= lon <= _KA_LON_MAX):
                return False
    return True


def _julian_to_date(julian_day: int, year: int) -> Optional[datetime]:
    """Convert Julian day + year to a UTC datetime (midnight)."""
    try:
        return datetime(year, 1, 1, tzinfo=timezone.utc) + __import__("datetime").timedelta(
            days=julian_day - 1
        )
    except Exception:
        return None


@router.get("/pfz/geojson", response_model=PFZGeoJSONResponse)
async def get_pfz_geojson() -> PFZGeoJSONResponse:
    """Retrieve current-day Karnataka PFZ advisory lines from INCOIS WFS.

    Fetches the full ``pfzlines`` layer, filters to Karnataka features,
    validates geometry bounds and temporal currency, and returns a clean
    GeoJSON FeatureCollection ready for direct Leaflet rendering.

    Returns:
        PFZGeoJSONResponse: GeoJSON FeatureCollection with audit metadata.

    Raises:
        HTTPException 502: If the INCOIS WFS endpoint is unreachable.
        HTTPException 204: If no valid Karnataka features are found.
    """
    now = datetime.now(timezone.utc)
    today_julian = now.timetuple().tm_yday
    today_year = now.year
    retrieved_at = now.isoformat()
    validation_notes: List[str] = []

    # ------------------------------------------------------------------ #
    # 1.  Fetch raw WFS GeoJSON from INCOIS                                #
    # ------------------------------------------------------------------ #
    try:
        async with httpx.AsyncClient(timeout=20.0, verify=False) as client:
            resp = await client.get(_INCOIS_PFZ_WFS)
            resp.raise_for_status()
            raw = resp.json()
    except httpx.HTTPError as exc:
        logger.error("Failed to reach INCOIS WFS: %s", exc)
        raise HTTPException(
            status_code=502,
            detail=f"INCOIS WFS unreachable: {exc}",
        )

    all_features: List[Dict[str, Any]] = raw.get("features", [])
    logger.info("INCOIS WFS returned %d total PFZ features", len(all_features))

    # ------------------------------------------------------------------ #
    # 2.  Filter to Karnataka features                                     #
    # ------------------------------------------------------------------ #
    ka_features = [
        f for f in all_features if f.get("properties", {}).get("State_Name") == "KARNATAKA"
    ]
    logger.info("Karnataka PFZ features: %d", len(ka_features))

    if not ka_features:
        validation_notes.append(
            "No Karnataka features found in the INCOIS pfzlines layer for today."
        )
        return PFZGeoJSONResponse(
            features=[],
            metadata=PFZLayer(
                retrieved_at=retrieved_at,
                julian_day=today_julian,
                year=today_year,
                is_current=False,
                feature_count=0,
                validation_notes=validation_notes,
            ),
        )

    # ------------------------------------------------------------------ #
    # 3.  Temporal validation                                              #
    # ------------------------------------------------------------------ #
    sample_props = ka_features[0].get("properties", {})
    feature_julian: Optional[int] = None
    feature_year: Optional[int] = None
    is_current = False

    try:
        feature_julian = int(sample_props.get("Julian_day", 0))
        feature_year = int(sample_props.get("Year", 0))
        day_delta = abs(today_julian - feature_julian) if feature_year == today_year else 999
        is_current = day_delta <= _MAX_AGE_DAYS
        if not is_current:
            validation_notes.append(
                f"PFZ advisory is {day_delta} days old (Julian {feature_julian}/{feature_year}). "
                f"Displaying but marking as potentially stale."
            )
    except (TypeError, ValueError):
        validation_notes.append("Could not parse Julian_day/Year from INCOIS properties.")

    # ------------------------------------------------------------------ #
    # 4.  Geometry validation and feature enrichment                       #
    # ------------------------------------------------------------------ #
    valid_features: List[Dict[str, Any]] = []
    chl_count = 0
    sst_count = 0
    skipped_oob = 0

    for feat in ka_features:
        props = feat.get("properties", {})
        geom = feat.get("geometry", {})
        coords = geom.get("coordinates", [])
        category = str(props.get("Category", "unknown")).lower()
        uid = props.get("UID", "")

        # Bounds check
        if not _is_in_karnataka_bounds(coords):
            skipped_oob += 1
            logger.warning("PFZ feature UID=%s failed bounds check – skipped", uid)
            continue

        # Enrich properties with human-readable metadata for the popup
        enriched_props = {
            **props,
            "pfz_category_label": "Chlorophyll-a Front" if category == "chl" else "SST Thermal Front",
            "pfz_category": category,
            "julian_day": feature_julian,
            "year": feature_year,
            "is_current": is_current,
            "advisory_date": (
                _julian_to_date(feature_julian, feature_year).strftime("%d %b %Y")
                if feature_julian and feature_year
                else "Unknown"
            ),
            "data_source": "INCOIS WFS – pfzlines (official advisory)",
        }

        valid_features.append({**feat, "properties": enriched_props})

        if category == "chl":
            chl_count += 1
        elif category == "sst":
            sst_count += 1

    if skipped_oob:
        validation_notes.append(
            f"{skipped_oob} feature(s) skipped – coordinates outside Karnataka bounds."
        )

    if not valid_features:
        validation_notes.append(
            "All Karnataka features failed geometric bounds validation."
        )

    logger.info(
        "PFZ GeoJSON response: %d valid features (chl=%d, sst=%d), current=%s",
        len(valid_features),
        chl_count,
        sst_count,
        is_current,
    )

    return PFZGeoJSONResponse(
        features=valid_features,
        metadata=PFZLayer(
            retrieved_at=retrieved_at,
            julian_day=feature_julian,
            year=feature_year,
            is_current=is_current,
            feature_count=len(valid_features),
            chl_count=chl_count,
            sst_count=sst_count,
            validation_notes=validation_notes,
        ),
    )
