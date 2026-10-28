"""Unit tests for Copernicus Ocean Analytics and Sea Surface Temperature (SST).

All tests are strictly offline and independent of network access.
"""

from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.adapters.ocean_data import (
    COPERNICUS_DATASET_ID,
    COPERNICUS_PRODUCT_ID,
    OceanDataAdapter,
)
from app.geo.coordinates import KARNATAKA_COASTAL_BBOX
from app.schemas.common import GeoBoundingBox, GeoCoordinate
from app.schemas.ocean_analytics import (
    OceanAnalyticsPayload,
    OceanAreaSummary,
    OceanGridPoint,
    OceanProductCategory,
    OceanProductMetadata,
    OceanVariableType,
)
from app.schemas.query import DataStatus
from app.services.data_availability import MarineDataAvailabilityService

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "copernicus_sst_karnataka_sample.json"


# ==============================================================================
# 1. FIXTURE PARSING & PROVENANCE AUDIT TESTS
# ==============================================================================


def test_parse_local_sample_metadata_and_fixture_provenance():
    """Verify metadata normalization and explicit fixture provenance auditing."""
    adapter = OceanDataAdapter()
    payload = adapter.parse_local_sample(FIXTURE_PATH)

    assert isinstance(payload, OceanAnalyticsPayload)
    meta = payload.metadata
    assert meta.product_id == COPERNICUS_PRODUCT_ID
    assert meta.dataset_id == COPERNICUS_DATASET_ID
    assert meta.product_category == OceanProductCategory.L4_SATELLITE_ANALYSIS
    assert meta.spatial_resolution_deg == 0.05
    assert meta.temporal_resolution == "daily"
    assert meta.data_format == "NetCDF-4"
    assert "Copernicus Open Access" in meta.usage_terms
    assert "auth.marine.copernicus.eu" in meta.access_requirement

    # Explicit provenance audit: fixture must NOT claim to be a live download
    assert meta.fixture_type == "MANUALLY_PREPARED_TEST_FIXTURE"
    assert meta.is_real_download is False
    assert payload.is_live_retrieval is False
    assert meta.provenance_audit is not None
    assert "Manually prepared" in meta.provenance_audit


def test_parse_local_sample_grid_points():
    """Verify grid point normalization, unit conversion, and land masking."""
    adapter = OceanDataAdapter()
    payload = adapter.parse_local_sample(FIXTURE_PATH)

    points = payload.grid_points
    assert len(points) == 13

    # Check offshore sea point (Karwar offshore)
    sea_point = points[0]
    assert sea_point.coordinate.latitude == 14.80
    assert sea_point.coordinate.longitude == 73.80
    assert sea_point.is_land_masked is False
    assert sea_point.quality_flag == 0
    assert sea_point.value_raw == 301.65
    assert sea_point.value_si == 28.50  # 301.65 - 273.15
    assert sea_point.units == "degC"
    assert sea_point.analysis_error == 0.35

    # Check onshore land-masked point (Mangalore onshore)
    land_point = points[-1]
    assert land_point.coordinate.latitude == 12.85
    assert land_point.coordinate.longitude == 74.88
    assert land_point.is_land_masked is True
    assert land_point.quality_flag == 2
    assert land_point.value_raw is None
    assert land_point.value_si is None


def test_parse_nonexistent_fixture_raises():
    """Verify that parsing a missing fixture file raises FileNotFoundError."""
    adapter = OceanDataAdapter()
    missing_path = Path(__file__).parent / "fixtures" / "nonexistent_sst.json"
    with pytest.raises(FileNotFoundError):
        adapter.parse_local_sample(missing_path)


# ==============================================================================
# 2. CONVERSION & DETERMINISTIC STATISTICAL SUMMARY TESTS
# ==============================================================================


def test_kelvin_to_celsius_conversion():
    """Verify deterministic Kelvin to Celsius conversion formula."""
    assert OceanDataAdapter.kelvin_to_celsius(273.15) == 0.00
    assert OceanDataAdapter.kelvin_to_celsius(300.15) == 27.00
    assert OceanDataAdapter.kelvin_to_celsius(301.65) == 28.50
    assert OceanDataAdapter.kelvin_to_celsius(303.15) == 30.00
    assert OceanDataAdapter.kelvin_to_celsius(None) is None


def test_deterministic_area_summary_from_sample():
    """Verify exact mathematical aggregation and spatial metrics from sample fixture."""
    adapter = OceanDataAdapter()
    payload = adapter.parse_local_sample(FIXTURE_PATH)
    summary = payload.area_summary

    assert summary.valid_cell_count == 10
    assert summary.land_masked_cell_count == 3
    assert summary.missing_cell_count == 0

    assert summary.mean_value == 28.39
    assert summary.min_value == 28.00
    assert summary.max_value == 28.70
    assert summary.std_dev == 0.19
    assert summary.mean_error == 0.338

    # Macro-regional SST range: 28.70 - 28.00 = 0.70 °C across Karnataka
    assert summary.regional_range_celsius == 0.70

    # Local spatial gradient across evaluated adjacent pairs (within 40 km):
    # Evaluates Karwar (26.85 km), Honnavar (37.78 km), and Bhatkal (37.94 km) transect pairs
    assert summary.evaluated_neighbor_pairs_count == 3
    assert summary.max_spatial_gradient_c_per_km == 0.0074
    assert summary.mean_spatial_gradient_c_per_km == 0.0060
    # Since 0.0074 °C/km < 0.05 °C/km threshold, no local front is flagged
    assert summary.thermal_front_detected is False


# ==============================================================================
# 3. REGIONAL RANGE VS. SPATIAL GRADIENT & NEIGHBOR TESTS
# ==============================================================================


def test_regional_range_versus_spatial_gradient():
    """Verify that a large regional temperature range between distant cells does NOT trigger a front."""
    adapter = OceanDataAdapter()
    bbox = KARNATAKA_COASTAL_BBOX

    # Two valid sea cells separated by ~220 km (Karwar to Mangalore) with a 2.0 °C difference
    points = [
        OceanGridPoint(
            coordinate=GeoCoordinate(latitude=14.80, longitude=73.80),
            variable=OceanVariableType.SST,
            value_raw=303.15,
            value_si=30.00,
            units="degC",
            analysis_error=0.35,
            is_land_masked=False,
            quality_flag=0,
        ),
        OceanGridPoint(
            coordinate=GeoCoordinate(latitude=12.85, longitude=74.30),
            variable=OceanVariableType.SST,
            value_raw=301.15,
            value_si=28.00,
            units="degC",
            analysis_error=0.35,
            is_land_masked=False,
            quality_flag=0,
        ),
    ]

    summary = adapter.compute_area_summary(
        points, bbox, "2026-10-25", max_neighbor_distance_km=40.0
    )

    # Regional range is 2.0 °C
    assert summary.regional_range_celsius == 2.00
    # Because distance (220 km) > 40 km, they are not treated as local neighbors
    assert summary.evaluated_neighbor_pairs_count == 0
    assert summary.max_spatial_gradient_c_per_km is None
    assert summary.thermal_front_detected is False


def test_steep_spatial_gradient_triggers_thermal_front():
    """Verify that adjacent sea cells with steep gradient trigger thermal_front_detected."""
    adapter = OceanDataAdapter()
    bbox = KARNATAKA_COASTAL_BBOX

    # Two adjacent grid cells ~5.5 km apart with 0.40 °C difference -> gradient ~0.072 °C/km >= 0.05
    points = [
        OceanGridPoint(
            coordinate=GeoCoordinate(latitude=14.00, longitude=74.00),
            variable=OceanVariableType.SST,
            value_raw=301.15,
            value_si=28.00,
            units="degC",
            analysis_error=0.30,
            is_land_masked=False,
            quality_flag=0,
        ),
        OceanGridPoint(
            coordinate=GeoCoordinate(latitude=14.05, longitude=74.00),
            variable=OceanVariableType.SST,
            value_raw=301.55,
            value_si=28.40,
            units="degC",
            analysis_error=0.30,
            is_land_masked=False,
            quality_flag=0,
        ),
    ]

    summary = adapter.compute_area_summary(
        points, bbox, "2026-10-25", max_neighbor_distance_km=40.0, thermal_front_threshold_c_per_km=0.05
    )

    assert summary.evaluated_neighbor_pairs_count == 1
    assert summary.max_spatial_gradient_c_per_km is not None
    assert summary.max_spatial_gradient_c_per_km >= 0.05
    assert summary.thermal_front_detected is True
    assert any("Significant local thermal front detected" in note for note in summary.gradient_notes)


def test_land_barrier_prevents_gradient_between_sea_cells():
    """Verify that an intervening land-masked point blocks gradient calculation between sea cells."""
    adapter = OceanDataAdapter()
    bbox = KARNATAKA_COASTAL_BBOX

    # Sea Point 1 at (14.00, 74.00), Land Point at (14.00, 74.05), Sea Point 2 at (14.00, 74.10)
    # The direct path from Sea 1 to Sea 2 is blocked by the land point
    points = [
        OceanGridPoint(
            coordinate=GeoCoordinate(latitude=14.00, longitude=74.00),
            variable=OceanVariableType.SST,
            value_raw=301.15,
            value_si=28.00,
            units="degC",
            analysis_error=0.30,
            is_land_masked=False,
            quality_flag=0,
        ),
        OceanGridPoint(
            coordinate=GeoCoordinate(latitude=14.00, longitude=74.05),
            variable=OceanVariableType.SST,
            value_raw=None,
            value_si=None,
            units="degC",
            analysis_error=None,
            is_land_masked=True,
            quality_flag=2,
        ),
        OceanGridPoint(
            coordinate=GeoCoordinate(latitude=14.00, longitude=74.10),
            variable=OceanVariableType.SST,
            value_raw=302.15,
            value_si=29.00,
            units="degC",
            analysis_error=0.30,
            is_land_masked=False,
            quality_flag=0,
        ),
    ]

    summary = adapter.compute_area_summary(
        points, bbox, "2026-10-25", max_neighbor_distance_km=40.0
    )

    # The pair (Sea 1, Sea 2) is blocked by Land Point, so evaluated neighbor pairs count is 0
    assert summary.evaluated_neighbor_pairs_count == 0
    assert summary.max_spatial_gradient_c_per_km is None
    assert summary.thermal_front_detected is False


# ==============================================================================
# 4. PHYSICAL VALUE SANITY & STALENESS AUDITING TESTS
# ==============================================================================


def test_physical_value_sanity_rejects_unphysical_kelvin():
    """Verify that unphysical SST values (< 260 K or > 325 K) are treated as invalid."""
    adapter = OceanDataAdapter()
    bbox = KARNATAKA_COASTAL_BBOX

    points = [
        OceanGridPoint(
            coordinate=GeoCoordinate(latitude=14.00, longitude=74.00),
            variable=OceanVariableType.SST,
            value_raw=150.00,  # Unphysically low Kelvin temperature
            value_si=None,
            units="degC",
            analysis_error=None,
            is_land_masked=False,
            quality_flag=3,  # Invalid
        ),
        OceanGridPoint(
            coordinate=GeoCoordinate(latitude=14.05, longitude=74.00),
            variable=OceanVariableType.SST,
            value_raw=301.15,
            value_si=28.00,
            units="degC",
            analysis_error=0.30,
            is_land_masked=False,
            quality_flag=0,
        ),
    ]

    summary = adapter.compute_area_summary(points, bbox, "2026-10-25")
    assert summary.valid_cell_count == 1
    assert summary.missing_cell_count == 1
    assert summary.mean_value == 28.00


def test_stale_observation_timestamp_flagging():
    """Verify that an observation timestamp older than 72 hours triggers is_stale warning."""
    adapter = OceanDataAdapter()
    bbox = KARNATAKA_COASTAL_BBOX

    old_timestamp = datetime.now(timezone.utc) - timedelta(days=5)  # 120 hours old
    points = [
        OceanGridPoint(
            coordinate=GeoCoordinate(latitude=14.00, longitude=74.00),
            variable=OceanVariableType.SST,
            value_raw=301.15,
            value_si=28.00,
            units="degC",
            analysis_error=0.30,
            is_land_masked=False,
            quality_flag=0,
        )
    ]

    summary = adapter.compute_area_summary(
        points, bbox, old_timestamp.strftime("%Y-%m-%d"), observation_timestamp=old_timestamp
    )
    assert summary.is_stale is True
    assert any("STALENESS WARNING" in note for note in summary.gradient_notes)


# ==============================================================================
# 5. MISSING & ALL-LAND DATA HANDLING TESTS
# ==============================================================================


def test_all_land_cells_handling():
    """Verify that an area with only land cells produces valid summary with None stats."""
    adapter = OceanDataAdapter()
    bbox = KARNATAKA_COASTAL_BBOX
    points = [
        OceanGridPoint(
            coordinate=GeoCoordinate(latitude=14.0, longitude=74.5),
            variable=OceanVariableType.SST,
            value_raw=None,
            value_si=None,
            units="degC",
            analysis_error=None,
            is_land_masked=True,
            quality_flag=2,
        ),
        OceanGridPoint(
            coordinate=GeoCoordinate(latitude=14.1, longitude=74.6),
            variable=OceanVariableType.SST,
            value_raw=None,
            value_si=None,
            units="degC",
            analysis_error=None,
            is_land_masked=True,
            quality_flag=2,
        ),
    ]

    summary = adapter.compute_area_summary(points, bbox, "2026-10-25")
    assert summary.valid_cell_count == 0
    assert summary.land_masked_cell_count == 2
    assert summary.missing_cell_count == 0
    assert summary.mean_value is None
    assert summary.min_value is None
    assert summary.max_value is None
    assert summary.std_dev is None
    assert summary.regional_range_celsius is None
    assert summary.max_spatial_gradient_c_per_km is None
    assert summary.thermal_front_detected is False
    assert any("No valid ocean cells" in note for note in summary.gradient_notes)


def test_missing_data_cells_counting():
    """Verify that unmasked points with null temperature are counted as missing."""
    adapter = OceanDataAdapter()
    bbox = KARNATAKA_COASTAL_BBOX
    points = [
        OceanGridPoint(
            coordinate=GeoCoordinate(latitude=14.0, longitude=74.0),
            variable=OceanVariableType.SST,
            value_raw=None,
            value_si=None,
            units="degC",
            analysis_error=None,
            is_land_masked=False,
            quality_flag=3,
        ),
        OceanGridPoint(
            coordinate=GeoCoordinate(latitude=14.1, longitude=74.1),
            variable=OceanVariableType.SST,
            value_raw=301.15,
            value_si=28.00,
            units="degC",
            analysis_error=0.4,
            is_land_masked=False,
            quality_flag=0,
        ),
    ]

    summary = adapter.compute_area_summary(points, bbox, "2026-10-25")
    assert summary.valid_cell_count == 1
    assert summary.missing_cell_count == 1
    assert summary.land_masked_cell_count == 0
    assert summary.mean_value == 28.00


# ==============================================================================
# 6. ECOLOGICAL & SAFETY GOVERNANCE CONSTRAINTS
# ==============================================================================


def test_mandatory_ecological_disclaimer_present():
    """Ensure every OceanAreaSummary enforces the mandatory ecological disclaimer."""
    adapter = OceanDataAdapter()
    payload = adapter.parse_local_sample(FIXTURE_PATH)
    disclaimer = payload.area_summary.ecological_disclaimer

    assert disclaimer is not None
    assert len(disclaimer) > 50
    assert "SST ALONE DOES NOT PROVE" in disclaimer
    assert "fish abundance" in disclaimer
    assert "INCOIS PFZ" in disclaimer
    assert "IMD" in disclaimer


def test_scientific_distinction_categories():
    """Ensure data product categories explicitly distinguish L4 analyses from forecasts."""
    assert OceanProductCategory.L4_SATELLITE_ANALYSIS != OceanProductCategory.NUMERICAL_MODEL_FORECAST
    assert OceanProductCategory.L4_SATELLITE_ANALYSIS != OceanProductCategory.IN_SITU_SENSOR
    assert OceanProductCategory.L4_SATELLITE_ANALYSIS != OceanProductCategory.L3_SATELLITE_COLLATED


# ==============================================================================
# 7. MOCKED NETWORK & ACCESS BLOCKER TESTS
# ==============================================================================


@pytest.mark.asyncio
async def test_live_probe_blocks_when_credentials_missing(monkeypatch):
    """Verify honest reporting of credential blocker when username/password are not set."""
    monkeypatch.delenv("COPERNICUSMARINE_SERVICE_USERNAME", raising=False)
    monkeypatch.delenv("COPERNICUSMARINE_SERVICE_PASSWORD", raising=False)
    from app.core import config
    if config.settings:
        monkeypatch.setattr(config.settings, "COPERNICUSMARINE_SERVICE_USERNAME", None)
        monkeypatch.setattr(config.settings, "COPERNICUSMARINE_SERVICE_PASSWORD", None)

    adapter = OceanDataAdapter(username=None, password=None)
    assert adapter.has_credentials() is False

    payload, telemetry = await adapter.fetch_live_subset()
    assert payload is None
    assert telemetry["status"] == "CREDENTIALS_REQUIRED"
    assert telemetry["http_status"] == 401
    assert "COPERNICUSMARINE_SERVICE_USERNAME" in telemetry["blocker_reason"]
    assert "auth.marine.copernicus.eu" in telemetry["auth_endpoint"]


@pytest.mark.asyncio
async def test_live_probe_mocked_auth_failure():
    """Verify handling of rejected credentials from Copernicus authentication service."""
    adapter = OceanDataAdapter(username="test_user", password="bad_password")
    assert adapter.has_credentials() is True

    mock_resp = MagicMock()
    mock_resp.status_code = 401
    mock_resp.text = '{"error": "invalid_grant", "error_description": "Invalid user credentials"}'

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp):
        payload, telemetry = await adapter.fetch_live_subset()
        assert payload is None
        assert telemetry["status"] == "AUTHENTICATION_FAILED"
        assert telemetry["http_status"] == 401
        assert "Invalid user credentials" in telemetry["blocker_reason"]


@pytest.mark.asyncio
async def test_live_probe_mocked_connection_error():
    """Verify handling of network timeout or DNS failure to Copernicus auth endpoint."""
    adapter = OceanDataAdapter(username="test_user", password="secret_password")

    with patch("httpx.AsyncClient.post", side_effect=Exception("Connection timed out")):
        payload, telemetry = await adapter.fetch_live_subset()
        assert payload is None
        assert telemetry["status"] == "CONNECTION_ERROR"
        assert telemetry["http_status"] == 0
        assert "Connection timed out" in telemetry["blocker_reason"]


@pytest.mark.asyncio
async def test_live_probe_mocked_auth_success():
    """Verify authenticated session returns token and parses live data successfully."""
    adapter = OceanDataAdapter(username="test_user", password="valid_password")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "access_token": "mocked_jwt_token",
        "token_type": "Bearer",
        "expires_in": 3600,
    }

    mock_gfi_resp = MagicMock()
    mock_gfi_resp.status_code = 200
    mock_gfi_resp.json.return_value = {
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [74.5, 13.35]},
                "properties": {"value": 303.15},  # 30.0 °C
            }
        ]
    }

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp), \
         patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_gfi_resp):
        payload, telemetry = await adapter.fetch_live_subset()
        assert telemetry["status"] == "SUCCESS"
        assert telemetry["http_status"] == 200
        assert telemetry["token_type"] == "Bearer"
        assert payload is not None
        assert payload.is_live_retrieval is True
        assert len(payload.grid_points) > 0
        assert payload.grid_points[0].value_si == 30.00


# ==============================================================================
# 8. DATA AVAILABILITY SERVICE INTEGRATION
# ==============================================================================


def test_copernicus_included_in_data_availability_service():
    """Verify Copernicus Marine Store is included in upstream source availability auditing."""
    reports = MarineDataAvailabilityService.get_sources_availability_report()
    copernicus_report = next((r for r in reports if "Copernicus" in r.source_name), None)

    assert copernicus_report is not None
    assert copernicus_report.status == DataStatus.NOT_VERIFIED
    assert "SST_GLO_SST_L4_NRT_OBSERVATIONS_010_001" in copernicus_report.limitations[0]
    assert any("SST data alone must never be used" in lim for lim in copernicus_report.limitations)
