"""Comprehensive validation tests for marine hazard, official warning integration,
threshold boundaries, stale/missing data governance, and source discrepancies.
"""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.adapters.open_meteo_marine import OpenMeteoMarineAdapter, classify_hazard_level
from app.main import app
from app.schemas.common import GeoCoordinate
from app.schemas.marine_hazard import (
    HourlyMarineForecastStep,
    MarineHazardForecast,
    WaveHazardLevel,
)
from app.schemas.official_warning import (
    OfficialMarineWarning,
    OfficialWarningSeverity,
)
from app.schemas.query import (
    DataStatus,
    MarineQueryRequest,
    QueryIntent,
    QueryWorkflowStatus,
)
from app.services.data_availability import check_marine_data_availability
from app.services.official_warning_service import OfficialWarningService
from app.services.query_workflow import QueryWorkflowEngine

client = TestClient(app)

FIXTURE_DIR = Path(__file__).parent / "fixtures"
IMD_SAMPLE_PATH = FIXTURE_DIR / "official_imd_bulletin_sample.json"


@pytest.fixture(autouse=True)
def cleanup_active_warning():
    """Ensure in-memory active warning is cleared before and after each test."""
    OfficialWarningService.clear_active_warning()
    yield
    OfficialWarningService.clear_active_warning()


# ---------------------------------------------------------------------------
# 1. Classification Threshold Boundaries (Douglas / WMO Scale)
# ---------------------------------------------------------------------------

def test_threshold_boundary_calm_and_slight():
    assert classify_hazard_level(0.0) == WaveHazardLevel.CALM
    assert classify_hazard_level(0.49) == WaveHazardLevel.CALM
    assert classify_hazard_level(0.50) == WaveHazardLevel.SLIGHT
    assert classify_hazard_level(1.24) == WaveHazardLevel.SLIGHT


def test_threshold_boundary_moderate_and_rough():
    assert classify_hazard_level(1.25) == WaveHazardLevel.MODERATE
    assert classify_hazard_level(2.49) == WaveHazardLevel.MODERATE
    assert classify_hazard_level(2.50) == WaveHazardLevel.ROUGH
    assert classify_hazard_level(3.99) == WaveHazardLevel.ROUGH
    assert classify_hazard_level(4.00) == WaveHazardLevel.ROUGH


def test_threshold_boundary_very_rough():
    assert classify_hazard_level(4.01) == WaveHazardLevel.VERY_ROUGH
    assert classify_hazard_level(7.50) == WaveHazardLevel.VERY_ROUGH


def test_threshold_none_or_missing_returns_unknown():
    assert classify_hazard_level(None) == WaveHazardLevel.UNKNOWN


# ---------------------------------------------------------------------------
# 2. Timezone Handling & Missing Offset Fallback
# ---------------------------------------------------------------------------

def test_timezone_missing_offset_falls_back_to_kolkata():
    adapter = OpenMeteoMarineAdapter()
    raw = {
        "latitude": 13.36,
        "longitude": 74.70,
        "timezone": "Asia/Kolkata",
        # utc_offset_seconds deliberately omitted
        "hourly": {
            "time": ["2026-10-26T12:00"],
            "wave_height": [1.0],
        },
    }
    forecast = adapter.parse_response(raw)
    assert forecast.utc_offset_seconds == 19800  # IST fallback
    assert forecast.grid_resolution_km == 9.0


def test_timezone_invalid_offset_falls_back_gracefully():
    adapter = OpenMeteoMarineAdapter()
    raw = {
        "latitude": 13.36,
        "longitude": 74.70,
        "timezone": "Asia/Kolkata",
        "utc_offset_seconds": "invalid_offset",
        "hourly": {
            "time": ["2026-10-26T12:00"],
            "wave_height": [1.0],
        },
    }
    forecast = adapter.parse_response(raw)
    assert forecast.utc_offset_seconds == 19800


# ---------------------------------------------------------------------------
# 3. Missing Data Governance: Never Claim Safe
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_all_wave_heights_null_sets_data_unavailable():
    adapter = OpenMeteoMarineAdapter()
    raw = {
        "latitude": 13.36,
        "longitude": 74.70,
        "timezone": "Asia/Kolkata",
        "utc_offset_seconds": 19800,
        "hourly": {
            "time": ["2026-10-26T12:00", "2026-10-26T13:00"],
            "wave_height": [None, None],
        },
    }
    forecast = adapter.parse_response(raw)
    assert not forecast.is_data_available
    assert forecast.peak_wave_height_m is None
    assert forecast.peak_hazard_level == WaveHazardLevel.UNKNOWN

    # Run through workflow engine
    mock_adapter = MagicMock()
    mock_adapter.fetch_karnataka_marine_forecast = AsyncMock(return_value=forecast)
    engine = QueryWorkflowEngine(open_meteo_adapter=mock_adapter)

    request = MarineQueryRequest(query="wave height near Malpe")
    resp = await engine.run(request)

    assert resp.status == QueryWorkflowStatus.DATA_UNAVAILABLE
    assert not resp.evidence_audit.passed
    assert any("no valid numeric wave height" in r for r in resp.evidence_audit.rejection_reasons)
    # Must NOT claim conditions are safe
    assert "safe" not in resp.answer.lower() or "not mean sea conditions are calm or safe" in resp.answer.lower()


# ---------------------------------------------------------------------------
# 4. Stale Forecast Governance: Lapsed Time Steps
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_stale_forecast_triggers_data_unavailable():
    adapter = OpenMeteoMarineAdapter()
    # Forecast from 2020 (far in the past)
    raw = {
        "latitude": 13.36,
        "longitude": 74.70,
        "timezone": "Asia/Kolkata",
        "utc_offset_seconds": 19800,
        "hourly": {
            "time": ["2020-01-01T00:00", "2020-01-01T01:00"],
            "wave_height": [0.4],
        },
    }
    forecast = adapter.parse_response(raw)
    assert forecast.is_stale

    mock_adapter = MagicMock()
    mock_adapter.fetch_karnataka_marine_forecast = AsyncMock(return_value=forecast)
    engine = QueryWorkflowEngine(open_meteo_adapter=mock_adapter)

    request = MarineQueryRequest(query="sea condition at Mangalore")
    resp = await engine.run(request)

    assert resp.status == QueryWorkflowStatus.DATA_UNAVAILABLE
    assert resp.evidence_audit.is_expired
    assert not resp.evidence_audit.passed
    assert any("lapsed" in r for r in resp.evidence_audit.rejection_reasons)


# ---------------------------------------------------------------------------
# 5. Upstream Service Unavailable (Network Outage / HTTP 500)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_upstream_outage_fails_safely():
    mock_adapter = MagicMock()
    mock_adapter.fetch_karnataka_marine_forecast = AsyncMock(
        side_effect=ConnectionError("Could not resolve host marine-api.open-meteo.com")
    )
    engine = QueryWorkflowEngine(open_meteo_adapter=mock_adapter)

    request = MarineQueryRequest(query="wave hazard Karwar")
    resp = await engine.run(request)

    assert resp.status == QueryWorkflowStatus.DATA_UNAVAILABLE
    assert not resp.evidence_audit.passed
    assert "MISSING FORECAST DATA DOES NOT IMPLY" in resp.answer.upper()
    assert "mausam.imd.gov.in" in resp.answer


# ---------------------------------------------------------------------------
# 6. Official IMD Warning Ingestion & Validation
# ---------------------------------------------------------------------------

def test_ingest_sample_imd_bulletin():
    warning, errors = OfficialWarningService.ingest_from_file(IMD_SAMPLE_PATH)
    assert not errors
    assert warning is not None
    assert warning.bulletin_id == "IMD-CWC-THIRU-20261026-FW01"
    assert warning.severity == OfficialWarningSeverity.WARNING
    assert warning.fishermen_advised_not_to_venture
    assert OfficialWarningService.get_active_warning() is not None


def test_ingest_invalid_timeline_rejected():
    invalid_data = {
        "bulletin_id": "TEST-01",
        "issuing_authority": "IMD",
        "issued_at": "2026-10-26T12:00:00Z",
        "valid_from": "2026-10-26T12:00:00Z",
        "valid_to": "2026-10-26T10:00:00Z",  # valid_to BEFORE valid_from
        "warning_text": "High wind alert",
        "source_document": "IMD test bulletin",
    }
    warning, errors = OfficialWarningService.parse_and_validate_dict(invalid_data)
    assert warning is None
    assert any("Invalid timeline" in e for e in errors)


def test_ingest_missing_required_fields_rejected():
    invalid_data = {
        "bulletin_id": "TEST-02",
        # Missing issuing_authority and warning_text
    }
    warning, errors = OfficialWarningService.parse_and_validate_dict(invalid_data)
    assert warning is None
    assert len(errors) >= 2


# ---------------------------------------------------------------------------
# 7. Conflicting Information & Statutory Override
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_sources_disagree_statutory_override():
    """When model says Slight (0.65m) but official IMD bulletin says WARNING,
    the system must flag discrepancy and defer strictly to the official warning."""
    # 1. Ingest official warning advising fishers NOT to venture
    warning, errors = OfficialWarningService.ingest_from_file(IMD_SAMPLE_PATH)
    assert warning is not None

    # 2. Simulate model returning low/calm waves (0.65 m -> SLIGHT)
    now = datetime.now(timezone.utc)
    mock_forecast = MarineHazardForecast(
        source="Open-Meteo Marine API",
        source_url="https://marine-api.open-meteo.com/v1/marine?...",
        retrieved_at=now,
        model_label="ERAssWave",
        latitude=13.375,
        longitude=74.708,
        grid_resolution_km=9.0,
        timezone="Asia/Kolkata",
        utc_offset_seconds=19800,
        forecast_hours=[
            HourlyMarineForecastStep(
                time_local=(now + timedelta(hours=1)).isoformat(),
                wave_height_m=0.65,
                hazard_level=WaveHazardLevel.SLIGHT,
            )
        ],
        current_hour_observation=HourlyMarineForecastStep(
            time_local=(now + timedelta(hours=1)).isoformat(),
            wave_height_m=0.65,
            hazard_level=WaveHazardLevel.SLIGHT,
        ),
        forecast_valid_time=(now + timedelta(hours=1)).isoformat(),
        is_stale=False,
        is_data_available=True,
        peak_wave_height_m=0.65,
        peak_hazard_level=WaveHazardLevel.SLIGHT,
    )

    mock_adapter = MagicMock()
    mock_adapter.fetch_karnataka_marine_forecast = AsyncMock(return_value=mock_forecast)
    engine = QueryWorkflowEngine(open_meteo_adapter=mock_adapter)

    request = MarineQueryRequest(query="is it safe to fish near Malpe today?")
    resp = await engine.run(request)

    assert resp.status == QueryWorkflowStatus.SUCCESS
    assert resp.sources_disagree
    assert resp.evidence_audit.sources_disagree
    assert resp.official_warning is not None
    assert resp.marine_hazard is not None

    # Verify that the answer explicitly highlights the discrepancy and statutory override
    assert "DISCREPANCY DETECTED" in resp.answer
    assert "STATUTORY OVERRIDE" in resp.answer
    assert "NOT to venture into sea" in resp.answer


# ---------------------------------------------------------------------------
# 8. Data Sources Availability Endpoint Reflects Ingested Warning
# ---------------------------------------------------------------------------

def test_data_sources_reflects_active_warning():
    # Before ingestion
    reports_before = check_marine_data_availability()
    imd_before = next(r for r in reports_before if "IMD" in r.source_name)
    assert imd_before.status == DataStatus.NOT_VERIFIED

    # Ingest official bulletin
    OfficialWarningService.ingest_from_file(IMD_SAMPLE_PATH)

    # After ingestion
    reports_after = check_marine_data_availability()
    imd_after = next(r for r in reports_after if "IMD" in r.source_name)
    assert imd_after.status == DataStatus.CURRENT
    assert imd_after.latest_verified_timestamp is not None
    assert "WARNING" in imd_after.notes
