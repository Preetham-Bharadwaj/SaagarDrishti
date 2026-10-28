"""Unit tests for the Open-Meteo Marine Weather API adapter.

ALL tests in this file use mocked HTTP responses or the verified fixture file.
No live network requests are made during the unit test run.

Fixture provenance:
  tests/fixtures/open_meteo_marine_karnataka_sample.json
  -- 4-hour slice of authentic live response from 2026-10-26 for Karnataka coast.

For live verification, use:
  python scripts/marine_hazard_smoke_test.py
"""

import json
import pytest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import httpx

from app.adapters.open_meteo_marine import (
    OpenMeteoMarineAdapter,
    classify_hazard_level,
    OPEN_METEO_MARINE_BASE_URL,
    OPEN_METEO_MARINE_ENDPOINT,
    KARNATAKA_MARINE_DEFAULT_LAT,
    KARNATAKA_MARINE_DEFAULT_LON,
)
from app.schemas.marine_hazard import WaveHazardLevel, MarineHazardForecast

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "open_meteo_marine_karnataka_sample.json"


@pytest.fixture(scope="module")
def karnataka_fixture() -> dict:
    """Load the authenticated Open-Meteo fixture from disk."""
    with FIXTURE_PATH.open("r", encoding="utf-8-sig") as f:
        return json.load(f)


# -------------------------------------------------------------------------
# Hazard level classification
# -------------------------------------------------------------------------

class TestClassifyHazardLevel:
    def test_none_returns_unknown(self):
        assert classify_hazard_level(None) == WaveHazardLevel.UNKNOWN

    def test_below_0_5_is_calm(self):
        assert classify_hazard_level(0.0) == WaveHazardLevel.CALM
        assert classify_hazard_level(0.49) == WaveHazardLevel.CALM

    def test_0_5_to_1_25_is_slight(self):
        assert classify_hazard_level(0.5) == WaveHazardLevel.SLIGHT
        assert classify_hazard_level(1.24) == WaveHazardLevel.SLIGHT

    def test_1_25_to_2_5_is_moderate(self):
        assert classify_hazard_level(1.25) == WaveHazardLevel.MODERATE
        assert classify_hazard_level(2.49) == WaveHazardLevel.MODERATE

    def test_2_5_to_4_0_is_rough(self):
        assert classify_hazard_level(2.5) == WaveHazardLevel.ROUGH
        assert classify_hazard_level(4.0) == WaveHazardLevel.ROUGH

    def test_above_4_is_very_rough(self):
        assert classify_hazard_level(4.01) == WaveHazardLevel.VERY_ROUGH
        assert classify_hazard_level(10.0) == WaveHazardLevel.VERY_ROUGH

    def test_fixture_wave_height_0_66_is_slight(self):
        """Wave heights from the live fixture (0.66 m) should classify as SLIGHT."""
        assert classify_hazard_level(0.66) == WaveHazardLevel.SLIGHT


# -------------------------------------------------------------------------
# Adapter construction
# -------------------------------------------------------------------------

class TestOpenMeteoMarineAdapterConstruction:
    def test_default_base_url(self):
        adapter = OpenMeteoMarineAdapter()
        assert adapter.base_url == OPEN_METEO_MARINE_BASE_URL

    def test_custom_base_url_stripped(self):
        adapter = OpenMeteoMarineAdapter(base_url="https://example.com/")
        assert adapter.base_url == "https://example.com"

    def test_source_name(self):
        adapter = OpenMeteoMarineAdapter()
        assert adapter.source_name == "Open-Meteo Marine API"

    def test_validate_connection_true_with_url(self):
        adapter = OpenMeteoMarineAdapter()
        assert adapter.validate_connection() is True

    def test_validate_connection_false_without_url(self):
        adapter = OpenMeteoMarineAdapter()
        adapter.base_url = ""  # Force-clear after construction to test the guard
        assert adapter.validate_connection() is False


# -------------------------------------------------------------------------
# Request parameter construction
# -------------------------------------------------------------------------

class TestBuildRequestParams:
    def test_required_fields_present(self):
        adapter = OpenMeteoMarineAdapter()
        params = adapter.build_request_params(13.36, 74.7)
        assert params["latitude"] == 13.36
        assert params["longitude"] == 74.7
        assert "wave_height" in params["hourly"]
        assert "swell_wave_height" in params["hourly"]
        assert "wave_direction" in params["hourly"]

    def test_forecast_days_clamped_to_7(self):
        adapter = OpenMeteoMarineAdapter()
        params = adapter.build_request_params(13.0, 74.0, forecast_days=100)
        assert params["forecast_days"] == 7

    def test_forecast_days_clamped_to_1(self):
        adapter = OpenMeteoMarineAdapter()
        params = adapter.build_request_params(13.0, 74.0, forecast_days=0)
        assert params["forecast_days"] == 1

    def test_default_timezone_is_kolkata(self):
        adapter = OpenMeteoMarineAdapter()
        params = adapter.build_request_params(13.0, 74.0)
        assert params["timezone"] == "Asia/Kolkata"


# -------------------------------------------------------------------------
# Response parsing - using verified fixture
# -------------------------------------------------------------------------

class TestParseResponseFromFixture:
    def test_fixture_parses_successfully(self, karnataka_fixture):
        adapter = OpenMeteoMarineAdapter()
        # Remove the provenance meta key before parsing
        payload = {k: v for k, v in karnataka_fixture.items() if k != "_fixture_provenance"}
        result = adapter.parse_response(payload, source_url="https://fixture/test")
        assert isinstance(result, MarineHazardForecast)

    def test_fixture_source_fields(self, karnataka_fixture):
        adapter = OpenMeteoMarineAdapter()
        payload = {k: v for k, v in karnataka_fixture.items() if k != "_fixture_provenance"}
        result = adapter.parse_response(payload, source_url="https://fixture/test")
        assert result.source == "Open-Meteo Marine API"
        assert result.source_url == "https://fixture/test"
        assert result.model_label == "ERAssWave"

    def test_fixture_snapped_coordinates(self, karnataka_fixture):
        adapter = OpenMeteoMarineAdapter()
        payload = {k: v for k, v in karnataka_fixture.items() if k != "_fixture_provenance"}
        result = adapter.parse_response(payload)
        assert result.latitude == pytest.approx(13.375, abs=0.01)
        assert result.longitude == pytest.approx(74.708, abs=0.01)

    def test_fixture_timezone_kolkata(self, karnataka_fixture):
        adapter = OpenMeteoMarineAdapter()
        payload = {k: v for k, v in karnataka_fixture.items() if k != "_fixture_provenance"}
        result = adapter.parse_response(payload)
        assert "Kolkata" in result.timezone or "kolkata" in result.timezone.lower()
        assert result.utc_offset_seconds == 19800  # 5h30m = 19800s

    def test_fixture_4_hourly_observations(self, karnataka_fixture):
        adapter = OpenMeteoMarineAdapter()
        payload = {k: v for k, v in karnataka_fixture.items() if k != "_fixture_provenance"}
        result = adapter.parse_response(payload)
        assert len(result.forecast_hours) == 4

    def test_fixture_first_hour_wave_height(self, karnataka_fixture):
        """First hour wave_height from fixture must be 0.66 m as verified live."""
        adapter = OpenMeteoMarineAdapter()
        payload = {k: v for k, v in karnataka_fixture.items() if k != "_fixture_provenance"}
        result = adapter.parse_response(payload)
        first = result.forecast_hours[0]
        assert first.wave_height_m == pytest.approx(0.66, abs=0.001)

    def test_fixture_first_hour_hazard_level_slight(self, karnataka_fixture):
        """0.66 m wave height => SLIGHT hazard for small coastal craft."""
        adapter = OpenMeteoMarineAdapter()
        payload = {k: v for k, v in karnataka_fixture.items() if k != "_fixture_provenance"}
        result = adapter.parse_response(payload)
        assert result.forecast_hours[0].hazard_level == WaveHazardLevel.SLIGHT

    def test_fixture_swell_data_populated(self, karnataka_fixture):
        adapter = OpenMeteoMarineAdapter()
        payload = {k: v for k, v in karnataka_fixture.items() if k != "_fixture_provenance"}
        result = adapter.parse_response(payload)
        first = result.forecast_hours[0]
        assert first.swell_wave_height_m == pytest.approx(0.48, abs=0.001)
        assert first.swell_wave_period_s == pytest.approx(8.9, abs=0.01)
        assert first.swell_wave_direction_deg == pytest.approx(207.0, abs=0.5)

    def test_fixture_wave_direction_populated(self, karnataka_fixture):
        adapter = OpenMeteoMarineAdapter()
        payload = {k: v for k, v in karnataka_fixture.items() if k != "_fixture_provenance"}
        result = adapter.parse_response(payload)
        first = result.forecast_hours[0]
        assert first.wave_direction_deg == pytest.approx(226.0, abs=0.5)

    def test_fixture_peak_hazard_is_slight(self, karnataka_fixture):
        """All hours in fixture have wave_height=0.66 m => peak is SLIGHT."""
        adapter = OpenMeteoMarineAdapter()
        payload = {k: v for k, v in karnataka_fixture.items() if k != "_fixture_provenance"}
        result = adapter.parse_response(payload)
        assert result.peak_hazard_level == WaveHazardLevel.SLIGHT
        assert result.peak_wave_height_m == pytest.approx(0.66, abs=0.001)

    def test_fixture_quality_notes_present(self, karnataka_fixture):
        adapter = OpenMeteoMarineAdapter()
        payload = {k: v for k, v in karnataka_fixture.items() if k != "_fixture_provenance"}
        result = adapter.parse_response(payload)
        assert len(result.data_quality_notes) > 0
        # Safety-critical limitation must be present
        assert any("NWP model" in note for note in result.data_quality_notes)

    def test_safety_disclaimer_present(self, karnataka_fixture):
        """Safety disclaimer must always be attached to every forecast payload."""
        adapter = OpenMeteoMarineAdapter()
        payload = {k: v for k, v in karnataka_fixture.items() if k != "_fixture_provenance"}
        result = adapter.parse_response(payload)
        assert result.safety_disclaimer  # non-empty
        assert "IMD" in result.safety_disclaimer

    def test_retrieved_at_is_utc_aware(self, karnataka_fixture):
        adapter = OpenMeteoMarineAdapter()
        payload = {k: v for k, v in karnataka_fixture.items() if k != "_fixture_provenance"}
        result = adapter.parse_response(payload)
        assert result.retrieved_at.tzinfo is not None


# -------------------------------------------------------------------------
# Mocked HTTP fetch
# -------------------------------------------------------------------------

class TestFetchWithMockedHTTPClient:
    @pytest.mark.asyncio
    async def test_fetch_calls_correct_url(self, karnataka_fixture):
        """Adapter must request the correct Open-Meteo Marine endpoint."""
        payload = {k: v for k, v in karnataka_fixture.items() if k != "_fixture_provenance"}
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = payload
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response

        adapter = OpenMeteoMarineAdapter()
        result = await adapter.fetch_karnataka_marine_forecast(
            latitude=13.36, longitude=74.7, client=mock_client
        )

        assert mock_client.get.called
        call_args = mock_client.get.call_args
        called_url = call_args[0][0]
        assert "marine-api.open-meteo.com" in called_url
        assert "/v1/marine" in called_url

    @pytest.mark.asyncio
    async def test_fetch_returns_typed_forecast(self, karnataka_fixture):
        payload = {k: v for k, v in karnataka_fixture.items() if k != "_fixture_provenance"}
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = payload
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response

        adapter = OpenMeteoMarineAdapter()
        result = await adapter.fetch_karnataka_marine_forecast(
            latitude=13.36, longitude=74.7, client=mock_client
        )
        assert isinstance(result, MarineHazardForecast)
        assert result.peak_hazard_level == WaveHazardLevel.SLIGHT

    @pytest.mark.asyncio
    async def test_fetch_raises_on_non_200(self):
        """Non-2xx response must raise httpx.HTTPError."""
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            message="rate limited", request=MagicMock(), response=mock_response
        )

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response

        adapter = OpenMeteoMarineAdapter()
        with pytest.raises(httpx.HTTPStatusError):
            await adapter.fetch_karnataka_marine_forecast(client=mock_client)


# -------------------------------------------------------------------------
# Edge case: empty / missing data
# -------------------------------------------------------------------------

class TestEdgeCaseParsing:
    def test_empty_hourly_produces_no_observations(self):
        adapter = OpenMeteoMarineAdapter()
        data = {
            "latitude": 13.375,
            "longitude": 74.708,
            "utc_offset_seconds": 19800,
            "timezone": "Asia/Kolkata",
            "hourly": {"time": [], "wave_height": []},
        }
        result = adapter.parse_response(data)
        assert result.forecast_hours == []
        assert result.peak_wave_height_m is None
        assert result.peak_hazard_level == WaveHazardLevel.UNKNOWN
        assert result.current_hour_observation is None

    def test_null_wave_heights_become_none(self):
        adapter = OpenMeteoMarineAdapter()
        data = {
            "latitude": 13.375,
            "longitude": 74.708,
            "utc_offset_seconds": 19800,
            "timezone": "Asia/Kolkata",
            "hourly": {
                "time": ["2026-10-26T00:00"],
                "wave_height": [None],
                "swell_wave_height": [None],
            },
        }
        result = adapter.parse_response(data)
        assert len(result.forecast_hours) == 1
        assert result.forecast_hours[0].wave_height_m is None
        assert result.forecast_hours[0].hazard_level == WaveHazardLevel.UNKNOWN

    def test_rough_seas_classify_correctly(self):
        """Validate that a 3.0 m wave height produces ROUGH level."""
        adapter = OpenMeteoMarineAdapter()
        data = {
            "latitude": 13.375,
            "longitude": 74.708,
            "utc_offset_seconds": 19800,
            "timezone": "Asia/Kolkata",
            "hourly": {
                "time": ["2026-10-26T00:00"],
                "wave_height": [3.0],
                "swell_wave_height": [2.5],
                "wind_wave_height": [1.5],
            },
        }
        result = adapter.parse_response(data)
        assert result.forecast_hours[0].hazard_level == WaveHazardLevel.ROUGH
        assert result.peak_hazard_level == WaveHazardLevel.ROUGH

    def test_very_rough_seas_classify_correctly(self):
        """Validate that a 5.0 m wave height produces VERY_ROUGH level."""
        adapter = OpenMeteoMarineAdapter()
        data = {
            "latitude": 13.375,
            "longitude": 74.708,
            "utc_offset_seconds": 19800,
            "timezone": "Asia/Kolkata",
            "hourly": {
                "time": ["2026-10-26T00:00"],
                "wave_height": [5.0],
            },
        }
        result = adapter.parse_response(data)
        assert result.forecast_hours[0].hazard_level == WaveHazardLevel.VERY_ROUGH
        assert result.peak_hazard_level == WaveHazardLevel.VERY_ROUGH

    def test_safety_disclaimer_always_present_on_empty_response(self):
        """Safety disclaimer must be non-empty even when there is no data."""
        adapter = OpenMeteoMarineAdapter()
        data = {
            "latitude": 13.0, "longitude": 74.0,
            "utc_offset_seconds": 0, "timezone": "UTC",
            "hourly": {"time": [], "wave_height": []},
        }
        result = adapter.parse_response(data)
        assert len(result.safety_disclaimer) > 50
