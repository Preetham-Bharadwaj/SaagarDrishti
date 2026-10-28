"""Unit tests for PFZ advisory ingestion and validation service."""

from datetime import datetime, timedelta, timezone
from pathlib import Path
from app.schemas.common import GeoCoordinate
from app.schemas.pfz import PFZAdvisoryItem, PFZAdvisoryPayload
from app.services.pfz_ingestion import PFZIngestionService

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "incois_karnataka_sample.json"


def test_valid_active_pfz_ingestion():
    """Ensure a properly structured active Karnataka PFZ payload passes validation."""
    now = datetime.now(timezone.utc)
    payload = PFZAdvisoryPayload(
        advisory_id="PFZ-TEST-001",
        source="INCOIS",
        region="Karnataka Coast",
        issued_at=now,
        valid_from=now,
        valid_to=now + timedelta(days=2),
        items=[
            PFZAdvisoryItem(
                item_id="HOTSPOT-1",
                coordinate=GeoCoordinate(latitude=13.35, longitude=74.70),
                landing_center="Malpe",
                direction_bearing_deg=280.0,
                distance_km=15.0,
                depth_m=35.0,
            )
        ],
    )
    result = PFZIngestionService.validate_advisory(payload, as_of=now)
    assert result.is_valid is True
    assert result.is_expired is False
    assert result.total_items == 1
    assert result.valid_items_count == 1
    assert result.duplicate_items_count == 0
    assert len(result.errors) == 0


def test_missing_dates_pfz_ingestion():
    """Ensure payload with missing valid_from or valid_to fails validation."""
    now = datetime.now(timezone.utc)
    payload = PFZAdvisoryPayload(
        advisory_id="PFZ-TEST-NODATE",
        source="INCOIS",
        region="Karnataka Coast",
        issued_at=now,
        valid_from=None,
        valid_to=None,
        items=[
            PFZAdvisoryItem(
                item_id="HOTSPOT-1",
                coordinate=GeoCoordinate(latitude=13.35, longitude=74.70),
                landing_center="Malpe",
            )
        ],
    )
    result = PFZIngestionService.validate_advisory(payload)
    assert result.is_valid is False
    assert any("Missing advisory validity timeline" in err for err in result.errors)


def test_invalid_timeline_pfz_ingestion():
    """Ensure payload where valid_to <= valid_from fails validation."""
    now = datetime.now(timezone.utc)
    payload = PFZAdvisoryPayload(
        advisory_id="PFZ-TEST-TIMELINE",
        source="INCOIS",
        region="Karnataka Coast",
        issued_at=now,
        valid_from=now + timedelta(days=1),
        valid_to=now,  # Invalid: valid_to is earlier than valid_from
        items=[
            PFZAdvisoryItem(
                item_id="HOTSPOT-2",
                coordinate=GeoCoordinate(latitude=14.81, longitude=74.12),
                landing_center="Karwar",
            )
        ],
    )
    result = PFZIngestionService.validate_advisory(payload)
    assert result.is_valid is False
    assert any("strictly after" in err for err in result.errors)


def test_expired_advisory_detection():
    """Ensure expired advisory is flagged with is_expired=True and warning."""
    now = datetime.now(timezone.utc)
    past_date = now - timedelta(days=10)
    payload = PFZAdvisoryPayload(
        advisory_id="PFZ-TEST-EXPIRED",
        source="INCOIS",
        region="Karnataka Coast",
        issued_at=past_date,
        valid_from=past_date,
        valid_to=past_date + timedelta(days=1),  # Expired 9 days ago
        items=[
            PFZAdvisoryItem(
                item_id="HOTSPOT-EXPIRED",
                coordinate=GeoCoordinate(latitude=14.81, longitude=74.12),
                landing_center="Karwar",
            )
        ],
    )
    result = PFZIngestionService.validate_advisory(payload, as_of=now)
    assert result.is_valid is True  # Schema is valid
    assert result.is_expired is True  # But timeline has expired
    assert any("expired" in warn.lower() for warn in result.warnings)


def test_duplicate_records_detection():
    """Ensure duplicate item_id or duplicate target from landing center is detected."""
    now = datetime.now(timezone.utc)
    payload = PFZAdvisoryPayload(
        advisory_id="PFZ-TEST-DUPLICATES",
        source="INCOIS",
        region="Karnataka Coast",
        issued_at=now,
        valid_from=now,
        valid_to=now + timedelta(days=1),
        items=[
            PFZAdvisoryItem(
                item_id="ITEM-DUP-1",
                coordinate=GeoCoordinate(latitude=13.35, longitude=74.70),
                landing_center="Malpe",
                direction_bearing_deg=270.0,
                distance_km=20.0,
            ),
            # Duplicate item_id
            PFZAdvisoryItem(
                item_id="ITEM-DUP-1",
                coordinate=GeoCoordinate(latitude=13.35, longitude=74.70),
                landing_center="Malpe",
                direction_bearing_deg=270.0,
                distance_km=20.0,
            ),
            # Duplicate target signature
            PFZAdvisoryItem(
                item_id="ITEM-DIFF-ID",
                coordinate=GeoCoordinate(latitude=13.35, longitude=74.70),
                landing_center="Malpe",
                direction_bearing_deg=270.0,
                distance_km=20.0,
            ),
        ],
    )
    result = PFZIngestionService.validate_advisory(payload, as_of=now)
    assert result.duplicate_items_count == 2
    assert any("Duplicate advisory record detected" in warn for warn in result.warnings)


def test_out_of_bounds_coordinate_warning():
    """Ensure coordinates outside Karnataka coast produce a warning, not a fatal crash."""
    now = datetime.now(timezone.utc)
    payload = PFZAdvisoryPayload(
        advisory_id="PFZ-TEST-OOB",
        source="INCOIS",
        region="Karnataka Coast",
        issued_at=now,
        valid_from=now,
        valid_to=now + timedelta(days=1),
        items=[
            PFZAdvisoryItem(
                item_id="HOTSPOT-CHENNAI",
                coordinate=GeoCoordinate(latitude=13.08, longitude=80.27),  # East coast (Chennai)
                landing_center="Non-Karnataka Center",
            )
        ],
    )
    result = PFZIngestionService.validate_advisory(payload, as_of=now)
    assert result.is_valid is True
    assert any("outside expected Karnataka coastal" in warn for warn in result.warnings)


def test_empty_items_pfz_ingestion():
    """Ensure payload with no advisory items fails validation."""
    now = datetime.now(timezone.utc)
    payload = PFZAdvisoryPayload(
        advisory_id="PFZ-TEST-EMPTY",
        source="INCOIS",
        region="Karnataka Coast",
        issued_at=now,
        valid_from=now,
        valid_to=now + timedelta(days=1),
        items=[],
    )
    result = PFZIngestionService.validate_advisory(payload, as_of=now)
    assert result.is_valid is False
    assert any("no advisory items" in err for err in result.errors)


def test_ingest_from_real_fixture_file():
    """Ensure file ingestion helper processes the real INCOIS fixture file correctly."""
    # Test with as_of set to the historical validity date so it passes active check
    historical_date = datetime(2024, 4, 27, 20, 0, tzinfo=timezone.utc)
    payload, result = PFZIngestionService.ingest_from_file(FIXTURE_PATH, as_of=historical_date)

    assert payload.advisory_id == "INCOIS-PFZ-KA-32599"
    assert len(payload.items) == 3
    assert result.is_valid is True
    assert result.is_expired is False
    assert result.total_items == 3
    assert result.valid_items_count == 3
    assert result.duplicate_items_count == 0
    assert len(result.errors) == 0
    assert len(result.data_quality_notes) > 0
