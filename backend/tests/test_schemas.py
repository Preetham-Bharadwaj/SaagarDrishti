"""Tests for typed request and response schemas."""

from datetime import datetime, timezone
import pytest
from pydantic import ValidationError
from app.schemas.common import GeoCoordinate
from app.schemas.marine import OceanographicObservation
from app.schemas.pfz import PFZAdvisoryItem, PFZAdvisoryPayload


def test_valid_geo_coordinate():
    """Ensure valid coordinates pass schema validation."""
    coord = GeoCoordinate(latitude=13.35, longitude=74.70)
    assert coord.latitude == 13.35
    assert coord.longitude == 74.70


def test_invalid_geo_coordinate():
    """Ensure invalid latitude or longitude raises ValidationError."""
    with pytest.raises(ValidationError):
        GeoCoordinate(latitude=95.0, longitude=74.0)

    with pytest.raises(ValidationError):
        GeoCoordinate(latitude=13.0, longitude=200.0)


def test_pfz_advisory_payload_schema():
    """Ensure PFZ advisory payload validates required structure."""
    now = datetime.now(timezone.utc)
    item = PFZAdvisoryItem(
        item_id="PFZ-KA-001",
        coordinate=GeoCoordinate(latitude=13.35, longitude=74.70),
        landing_center="Malpe",
        direction_bearing_deg=270.0,
        distance_km=25.0,
        depth_m=40.0,
    )
    payload = PFZAdvisoryPayload(
        advisory_id="ADV-2026-10-01",
        source="INCOIS",
        region="Karnataka Coast",
        issued_at=now,
        valid_from=now,
        valid_to=now,
        items=[item],
    )
    assert payload.advisory_id == "ADV-2026-10-01"
    assert len(payload.items) == 1
    assert payload.items[0].landing_center == "Malpe"


def test_marine_observation_schema():
    """Ensure OceanographicObservation validates correctly."""
    obs = OceanographicObservation(
        coordinate=GeoCoordinate(latitude=14.81, longitude=74.12),
        timestamp=datetime.now(timezone.utc),
        sea_surface_temperature_c=28.5,
        chlorophyll_mg_m3=1.2,
        significant_wave_height_m=1.5,
        wind_speed_m_s=5.4,
        data_source="INCOIS",
    )
    assert obs.sea_surface_temperature_c == 28.5
    assert obs.data_source == "INCOIS"
