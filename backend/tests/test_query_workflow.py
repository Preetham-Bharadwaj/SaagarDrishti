"""Tests for the end-to-end marine query workflow engine and API endpoints."""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from app.adapters.ocean_data import OceanDataAdapter
from app.main import app
from app.schemas.common import GeoCoordinate
from app.schemas.ocean_analytics import (
    OceanAnalyticsPayload,
    OceanAreaSummary,
    OceanGridPoint,
    OceanProductCategory,
    OceanProductMetadata,
    OceanSSTResult,
    OceanVariableType,
)
from app.schemas.pfz import PFZAdvisoryItem, PFZAdvisoryPayload
from app.schemas.query import (
    DataStatus,
    MarineQueryRequest,
    QueryIntent,
    QueryWorkflowStatus,
    SourceAvailabilityReport,
)
from app.services.query_workflow import QueryWorkflowEngine
from app.geo.coordinates import KARNATAKA_COASTAL_BBOX

client = TestClient(app)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_expired_payload() -> PFZAdvisoryPayload:
    """Return an advisory payload whose validity window expired in April 2024."""
    return PFZAdvisoryPayload(
        advisory_id="INCOIS-PFZ-KA-32599",
        source="INCOIS",
        source_url="https://incois.gov.in/geoserver/...",
        region="Karnataka Coast",
        sector_id="SEC004",
        retrieved_at=datetime.now(timezone.utc),
        issued_at=datetime(2024, 4, 27, 18, 30, tzinfo=timezone.utc),
        valid_from=datetime(2024, 4, 27, 18, 30, tzinfo=timezone.utc),
        valid_to=datetime(2024, 4, 28, 18, 30, tzinfo=timezone.utc),
        quality_limitations=[],
        items=[
            PFZAdvisoryItem(
                item_id="KA0302a",
                coordinate=GeoCoordinate(latitude=13.019, longitude=74.664),
                landing_center="Suratakal Pt",
                landing_center_coordinate=GeoCoordinate(latitude=13.0, longitude=74.79),
                status="YES",
                distance_km=14.5,
                direction_bearing_deg=279.0,
                depth_m=25.5,
            )
        ],
    )


def _make_current_payload() -> PFZAdvisoryPayload:
    """Return an advisory payload with a future valid_to (simulating a live advisory)."""
    return PFZAdvisoryPayload(
        advisory_id="INCOIS-PFZ-KA-99999",
        source="INCOIS",
        source_url="https://incois.gov.in/geoserver/...",
        region="Karnataka Coast",
        sector_id="SEC004",
        retrieved_at=datetime.now(timezone.utc),
        issued_at=datetime(2099, 1, 1, 0, 0, tzinfo=timezone.utc),
        valid_from=datetime(2099, 1, 1, 0, 0, tzinfo=timezone.utc),
        valid_to=datetime(2099, 1, 2, 0, 0, tzinfo=timezone.utc),
        quality_limitations=[],
        items=[
            PFZAdvisoryItem(
                item_id="KA0302a",
                coordinate=GeoCoordinate(latitude=13.019, longitude=74.664),
                landing_center="Suratakal Pt",
                landing_center_coordinate=GeoCoordinate(latitude=13.0, longitude=74.79),
                status="YES",
                distance_km=14.5,
                direction_bearing_deg=279.0,
                depth_m=25.5,
            )
        ],
    )


def _mock_current_sources():
    """Return source availability list where PFZ vector lines is CURRENT."""
    return [
        SourceAvailabilityReport(
            source_name="INCOIS GeoServer WFS (Landing Centers Reference Layer)",
            source_url="https://incois.gov.in/...",
            status=DataStatus.EXPIRED,
            notes="Historical snapshot.",
        ),
        SourceAvailabilityReport(
            source_name="INCOIS GeoServer WFS (PFZ Vector Lines)",
            source_url="https://incois.gov.in/...",
            status=DataStatus.CURRENT,
            notes="Live PFZ lines available.",
        ),
        SourceAvailabilityReport(
            source_name="INCOIS WebGIS DataProcess (Tabular Advisory Backend)",
            source_url="https://incois.gov.in/...",
            status=DataStatus.EXPIRED,
            notes="Expired.",
        ),
        SourceAvailabilityReport(
            source_name="IMD Marine & Coastal Weather Hazard Bulletin",
            source_url="https://mausam.imd.gov.in/",
            status=DataStatus.NOT_VERIFIED,
            notes="Not yet integrated.",
        ),
    ]


# ---------------------------------------------------------------------------
# Query planner intent classification
# ---------------------------------------------------------------------------

def test_classify_pfz_intent():
    from app.agents.planner import QueryPlanner
    assert QueryPlanner.classify_intent("where can I fish near Malpe today") == QueryIntent.NEAREST_PFZ
    assert QueryPlanner.classify_intent("show me the nearest PFZ") == QueryIntent.NEAREST_PFZ
    assert QueryPlanner.classify_intent("tuna hotspot near Karwar") == QueryIntent.NEAREST_PFZ


def test_classify_hazard_intent():
    from app.agents.planner import QueryPlanner
    assert QueryPlanner.classify_intent("is it safe to go to sea?") == QueryIntent.WEATHER_HAZARD
    assert QueryPlanner.classify_intent("cyclone warning today") == QueryIntent.WEATHER_HAZARD
    assert QueryPlanner.classify_intent("wave height forecast") == QueryIntent.WEATHER_HAZARD


def test_classify_conditions_intent():
    from app.agents.planner import QueryPlanner
    assert QueryPlanner.classify_intent("what is the SST near Mangalore?") == QueryIntent.MARINE_CONDITIONS
    assert QueryPlanner.classify_intent("chlorophyll levels today") == QueryIntent.MARINE_CONDITIONS


def test_classify_general_intent():
    from app.agents.planner import QueryPlanner
    assert QueryPlanner.classify_intent("tell me about Karnataka fisheries") == QueryIntent.GENERAL_MARINE_INFORMATION


# ---------------------------------------------------------------------------
# Workflow: DATA_UNAVAILABLE when PFZ lines source is not CURRENT
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_nearest_pfz_data_unavailable_when_source_not_current():
    """Expired data source => workflow must return DATA_UNAVAILABLE, not a PFZ result."""
    engine = QueryWorkflowEngine()
    request = MarineQueryRequest(
        query="nearest PFZ from Malpe",
        user_location=GeoCoordinate(latitude=13.36, longitude=74.7),
    )

    # Patch: use real expired payload + default sources (PFZ lines = UNAVAILABLE in real audit)
    response = await engine.run(request)

    assert response.intent == QueryIntent.NEAREST_PFZ
    assert response.status == QueryWorkflowStatus.DATA_UNAVAILABLE
    assert response.candidate_pfz is None
    assert not response.evidence_audit.passed
    # Landing center guard must be noted but NOT trigger lc_mistaken flag
    assert not response.evidence_audit.is_landing_center_mistaken_for_pfz


# ---------------------------------------------------------------------------
# Workflow: SUCCESS with distance when source is CURRENT (mocked)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_nearest_pfz_success_when_source_current_and_location_given():
    """When PFZ source is CURRENT and unexpired payload exists, return candidate."""
    engine = QueryWorkflowEngine()
    request = MarineQueryRequest(
        query="nearest fishing zone",
        user_location=GeoCoordinate(latitude=13.36, longitude=74.7),
    )
    current_payload = _make_current_payload()
    current_sources = _mock_current_sources()
    mock_validation = MagicMock()
    mock_validation.errors = []

    with (
        patch(
            "app.services.query_workflow.check_marine_data_availability",
            return_value=current_sources,
        ),
        patch(
            "app.services.query_workflow.PFZIngestionService.ingest_from_adapter",
            new_callable=AsyncMock,
            return_value=(current_payload, mock_validation),
        ),
    ):
        response = await engine.run(request)

    assert response.intent == QueryIntent.NEAREST_PFZ
    assert response.status == QueryWorkflowStatus.SUCCESS
    assert response.candidate_pfz is not None
    assert response.candidate_pfz.distance_km > 0
    assert response.evidence_audit.passed
    assert not response.evidence_audit.is_expired


# ---------------------------------------------------------------------------
# Workflow: LOCATION_REQUIRED when source CURRENT but no user_location
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_nearest_pfz_location_required_without_coordinates():
    engine = QueryWorkflowEngine()
    request = MarineQueryRequest(query="nearest PFZ")  # no user_location
    current_payload = _make_current_payload()
    current_sources = _mock_current_sources()
    mock_validation = MagicMock()
    mock_validation.errors = []

    with (
        patch(
            "app.services.query_workflow.check_marine_data_availability",
            return_value=current_sources,
        ),
        patch(
            "app.services.query_workflow.PFZIngestionService.ingest_from_adapter",
            new_callable=AsyncMock,
            return_value=(current_payload, mock_validation),
        ),
    ):
        response = await engine.run(request)

    assert response.intent == QueryIntent.NEAREST_PFZ
    assert response.status == QueryWorkflowStatus.LOCATION_REQUIRED
    assert response.candidate_pfz is None


# ---------------------------------------------------------------------------
# Workflow: Expired advisory is rejected even with CURRENT source
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_expired_advisory_rejected_even_when_source_current():
    engine = QueryWorkflowEngine()
    request = MarineQueryRequest(
        query="PFZ near Udupi",
        user_location=GeoCoordinate(latitude=13.36, longitude=74.7),
    )
    expired_payload = _make_expired_payload()
    current_sources = _mock_current_sources()
    mock_validation = MagicMock()
    mock_validation.errors = []

    with (
        patch(
            "app.services.query_workflow.check_marine_data_availability",
            return_value=current_sources,
        ),
        patch(
            "app.services.query_workflow.PFZIngestionService.ingest_from_adapter",
            new_callable=AsyncMock,
            return_value=(expired_payload, mock_validation),
        ),
    ):
        response = await engine.run(request)

    assert response.status == QueryWorkflowStatus.DATA_UNAVAILABLE
    assert response.evidence_audit.is_expired
    assert response.candidate_pfz is None


# ---------------------------------------------------------------------------
# Workflow: Marine conditions, weather hazard, general
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_marine_conditions_returns_unavailable_when_credentials_missing():
    """When OceanDataAdapter has no credentials, marine-conditions returns DATA_UNAVAILABLE."""
    mock_adapter = MagicMock(spec=OceanDataAdapter)
    mock_adapter.fetch_live_subset = AsyncMock(return_value=(
        None,
        {
            "status": "CREDENTIALS_REQUIRED",
            "http_status": 401,
            "blocker_reason": (
                "Copernicus Marine Data Store requires registered user authentication. "
                "Environment variables 'COPERNICUSMARINE_SERVICE_USERNAME' and "
                "'COPERNICUSMARINE_SERVICE_PASSWORD' are not set."
            ),
            "auth_endpoint": "https://auth.marine.copernicus.eu",
            "data_store_endpoint": "https://data.marine.copernicus.eu",
        },
    ))
    engine = QueryWorkflowEngine(ocean_data_adapter=mock_adapter)
    request = MarineQueryRequest(query="what is the SST near Karnataka?")
    response = await engine.run(request)
    assert response.intent == QueryIntent.MARINE_CONDITIONS
    assert response.status == QueryWorkflowStatus.DATA_UNAVAILABLE
    assert response.ocean_sst is None
    assert not response.evidence_audit.passed
    assert any("CREDENTIALS_REQUIRED" not in r or "Copernicus" in r
               for r in response.evidence_audit.rejection_reasons)


@pytest.mark.asyncio
async def test_weather_hazard_returns_success_with_marine_hazard():
    engine = QueryWorkflowEngine()
    request = MarineQueryRequest(query="wave height forecast for Malpe coast")
    response = await engine.run(request)
    assert response.intent == QueryIntent.WEATHER_HAZARD
    assert response.status == QueryWorkflowStatus.SUCCESS
    assert response.marine_hazard is not None
    assert response.marine_hazard.source == "Open-Meteo Marine API"
    assert response.evidence_audit.passed
    assert "IMD" in response.answer


@pytest.mark.asyncio
async def test_weather_hazard_returns_unavailable_on_adapter_error():
    mock_adapter = MagicMock()
    mock_adapter.fetch_karnataka_marine_forecast = AsyncMock(
        side_effect=RuntimeError("Simulated network outage")
    )
    engine = QueryWorkflowEngine(open_meteo_adapter=mock_adapter)
    request = MarineQueryRequest(query="is there a storm warning today?")
    response = await engine.run(request)
    assert response.intent == QueryIntent.WEATHER_HAZARD
    assert response.status == QueryWorkflowStatus.DATA_UNAVAILABLE
    assert not response.evidence_audit.passed
    assert any("Simulated network outage" in r for r in response.evidence_audit.rejection_reasons)
    assert "IMD" in response.answer


@pytest.mark.asyncio
async def test_weather_hazard_resolves_named_landing_center():
    engine = QueryWorkflowEngine()
    request = MarineQueryRequest(query="sea condition near Karwar")
    response = await engine.run(request)
    assert response.intent == QueryIntent.WEATHER_HAZARD
    assert response.status == QueryWorkflowStatus.SUCCESS
    assert "Karwar" in response.answer


@pytest.mark.asyncio
async def test_general_intent_returns_success():
    engine = QueryWorkflowEngine()
    request = MarineQueryRequest(query="tell me about Karnataka landing centers")
    response = await engine.run(request)
    assert response.intent == QueryIntent.GENERAL_MARINE_INFORMATION
    assert response.status == QueryWorkflowStatus.SUCCESS
    assert "Karnataka" in response.answer


# ---------------------------------------------------------------------------
# API endpoint: /api/v1/query (HTTP integration)
# ---------------------------------------------------------------------------

def test_query_endpoint_general_marine():
    payload = {"query": "tell me about Karnataka fisheries"}
    resp = client.post("/api/v1/query", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["intent"] == "general_marine_information"
    assert data["status"] == "SUCCESS"
    assert isinstance(data["sources_checked"], list)
    assert isinstance(data["tools_used"], list)
    assert "classify_intent" in data["tools_used"]


def test_query_endpoint_weather_hazard():
    payload = {"query": "wave height forecast for Karnataka coast"}
    resp = client.post("/api/v1/query", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["intent"] == "weather_hazard"
    assert data["status"] == "SUCCESS"
    assert data["marine_hazard"] is not None
    assert "wave_height_m" in data["marine_hazard"]["forecast_hours"][0]
    assert data["candidate_pfz"] is None



def test_query_endpoint_marine_conditions():
    """Marine conditions endpoint returns 200 with marine_conditions intent.

    Status is SUCCESS when credentials are configured, DATA_UNAVAILABLE otherwise.
    Both outcomes are valid; we only assert HTTP 200 and correct intent.
    """
    payload = {"query": "SST near Mangalore"}
    resp = client.post("/api/v1/query", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["intent"] == "marine_conditions"
    assert data["status"] in ("SUCCESS", "DATA_UNAVAILABLE")


def test_query_endpoint_nearest_pfz_no_location():
    """PFZ query without live data + no user location => DATA_UNAVAILABLE."""
    payload = {"query": "nearest fishing zone"}
    resp = client.post("/api/v1/query", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["intent"] == "nearest_pfz"
    # Real live data is not current, so DATA_UNAVAILABLE expected
    assert data["status"] == "DATA_UNAVAILABLE"
    assert data["candidate_pfz"] is None


def test_query_endpoint_missing_query_field():
    """Request without required 'query' field must return 422."""
    resp = client.post("/api/v1/query", json={"user_location": {"latitude": 13.0, "longitude": 74.0}})
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# API endpoint: /api/v1/data-sources
# ---------------------------------------------------------------------------

def test_data_sources_endpoint_returns_list():
    resp = client.get("/api/v1/data-sources")
    assert resp.status_code == 200
    sources = resp.json()
    assert isinstance(sources, list)
    assert len(sources) >= 5

    source_names = [s["source_name"] for s in sources]
    assert any("PFZ Vector Lines" in n for n in source_names)
    assert any("Landing Centers" in n for n in source_names)
    assert any("Open-Meteo" in n for n in source_names)
    assert any("IMD" in n for n in source_names)


def test_data_sources_have_required_fields():
    resp = client.get("/api/v1/data-sources")
    assert resp.status_code == 200
    for source in resp.json():
        assert "source_name" in source
        assert "source_url" in source
        assert "status" in source
        assert "notes" in source
        assert "limitations" in source


# ---------------------------------------------------------------------------
# Marine Conditions: live SST workflow tests
# ---------------------------------------------------------------------------

def _make_live_sst_payload(is_stale: bool = False) -> OceanAnalyticsPayload:
    """Build a synthetic OceanAnalyticsPayload that mimics a successful live retrieval."""
    now = datetime.now(timezone.utc)
    from datetime import timedelta
    obs_dt = now - timedelta(hours=200 if is_stale else 12)

    metadata = OceanProductMetadata(
        product_id="SST_GLO_SST_L4_NRT_OBSERVATIONS_010_001",
        dataset_id="METOFFICE-GLO-SST-L4-NRT-OBS-SST-V2",
        production_center="UK Met Office / Copernicus Marine Service (CMEMS)",
        product_category=OceanProductCategory.L4_SATELLITE_ANALYSIS,
        spatial_resolution_deg=0.05,
        temporal_resolution="daily",
        data_format="NetCDF-4 / WMTS OGC Service",
        usage_terms="Copernicus Open Access (CC-BY 4.0)",
        access_requirement="Copernicus Marine Data Store account",
        fixture_type="LIVE_DOWNLOADED_PRODUCT",
        is_real_download=True,
        provenance_audit="Mocked live retrieval for unit testing.",
        is_stale=is_stale,
        retrieved_at=now,
        observation_timestamp=obs_dt,
        coverage_bbox=KARNATAKA_COASTAL_BBOX,
    )

    grid_points = [
        OceanGridPoint(
            coordinate=GeoCoordinate(latitude=14.80, longitude=73.80),
            variable=OceanVariableType.SST,
            value_raw=303.35,
            value_si=30.20,
            units="degC",
            analysis_error=0.35,
            is_land_masked=False,
            quality_flag=0,
        ),
        OceanGridPoint(
            coordinate=GeoCoordinate(latitude=12.85, longitude=75.20),
            variable=OceanVariableType.SST,
            value_raw=None,
            value_si=None,
            units="degC",
            is_land_masked=True,
            quality_flag=2,
        ),
    ]

    summary = OceanAreaSummary(
        variable=OceanVariableType.SST,
        bounding_box=KARNATAKA_COASTAL_BBOX,
        observation_date=obs_dt.strftime("%Y-%m-%d"),
        mean_value=30.20,
        min_value=30.20,
        max_value=30.20,
        std_dev=0.0,
        mean_error=0.35,
        valid_cell_count=1,
        land_masked_cell_count=1,
        missing_cell_count=0,
        regional_range_celsius=0.0,
        max_spatial_gradient_c_per_km=None,
        mean_spatial_gradient_c_per_km=None,
        evaluated_neighbor_pairs_count=0,
        thermal_front_threshold_c_per_km=0.05,
        thermal_front_detected=False,
        is_stale=is_stale,
    )

    return OceanAnalyticsPayload(
        metadata=metadata,
        grid_points=grid_points,
        area_summary=summary,
        provenance_notes=["Mocked for unit testing."],
        is_live_retrieval=True,
    )


@pytest.mark.asyncio
async def test_marine_conditions_success_with_live_sst():
    """Successful live SST retrieval returns SUCCESS with populated ocean_sst."""
    live_payload = _make_live_sst_payload(is_stale=False)
    mock_adapter = MagicMock(spec=OceanDataAdapter)
    mock_adapter.fetch_live_subset = AsyncMock(return_value=(
        live_payload,
        {"status": "SUCCESS", "http_status": 200, "live_features_retrieved": 2},
    ))

    engine = QueryWorkflowEngine(ocean_data_adapter=mock_adapter)
    request = MarineQueryRequest(query="what is the sea surface temperature near Karnataka?")
    response = await engine.run(request)

    assert response.intent == QueryIntent.MARINE_CONDITIONS
    assert response.status == QueryWorkflowStatus.SUCCESS
    assert response.ocean_sst is not None
    sst = response.ocean_sst

    # Source identity fields
    assert "Copernicus" in sst.source_name
    assert sst.product_id == "SST_GLO_SST_L4_NRT_OBSERVATIONS_010_001"
    assert sst.dataset_id == "METOFFICE-GLO-SST-L4-NRT-OBS-SST-V2"
    assert sst.product_category == OceanProductCategory.L4_SATELLITE_ANALYSIS
    assert "Met Office" in sst.production_center

    # Temporal provenance
    assert sst.is_live_retrieval is True
    assert sst.is_stale is False
    assert isinstance(sst.observation_timestamp, datetime)
    assert isinstance(sst.retrieved_at, datetime)

    # Spatial coverage — Karnataka coast
    assert sst.coverage_min_lat == KARNATAKA_COASTAL_BBOX.min_latitude
    assert sst.coverage_max_lat == KARNATAKA_COASTAL_BBOX.max_latitude

    # Statistics
    assert sst.valid_cell_count == 1
    assert sst.land_masked_cell_count == 1
    assert sst.mean_sst_celsius == pytest.approx(30.20, abs=0.01)
    assert sst.retrieval_status == "SUCCESS"

    # Mandatory ecological disclaimer
    assert "SST ALONE DOES NOT" in sst.ecological_disclaimer
    assert "SST ALONE DOES NOT" in response.answer

    # Audit
    assert response.evidence_audit.passed is True
    assert not response.evidence_audit.is_expired
    assert "fetch_copernicus_sst_live" in response.evidence_audit.checks_performed


@pytest.mark.asyncio
async def test_marine_conditions_auth_failure():
    """Authentication failure from Copernicus returns DATA_UNAVAILABLE with clear blocker."""
    mock_adapter = MagicMock(spec=OceanDataAdapter)
    mock_adapter.fetch_live_subset = AsyncMock(return_value=(
        None,
        {
            "status": "AUTHENTICATION_FAILED",
            "http_status": 401,
            "blocker_reason": 'Copernicus auth returned HTTP 401: {"error": "invalid_grant"}',
        },
    ))
    engine = QueryWorkflowEngine(ocean_data_adapter=mock_adapter)
    request = MarineQueryRequest(query="SST near Mangalore coast")
    response = await engine.run(request)

    assert response.intent == QueryIntent.MARINE_CONDITIONS
    assert response.status == QueryWorkflowStatus.DATA_UNAVAILABLE
    assert response.ocean_sst is None
    assert not response.evidence_audit.passed
    assert any("authentication failed" in r.lower() or "auth" in r.lower()
               for r in response.evidence_audit.rejection_reasons)
    # Safety critical notices must always be present
    assert any("SST ALONE" in w or "SAFETY" in w for w in response.evidence_audit.warnings)


@pytest.mark.asyncio
async def test_marine_conditions_connection_error():
    """Network failure to Copernicus auth endpoint returns DATA_UNAVAILABLE."""
    mock_adapter = MagicMock(spec=OceanDataAdapter)
    mock_adapter.fetch_live_subset = AsyncMock(return_value=(
        None,
        {
            "status": "CONNECTION_ERROR",
            "http_status": 0,
            "blocker_reason": "Connection to Copernicus auth endpoint failed: Connection timed out",
        },
    ))
    engine = QueryWorkflowEngine(ocean_data_adapter=mock_adapter)
    request = MarineQueryRequest(query="what is the SST near Karwar?")
    response = await engine.run(request)

    assert response.intent == QueryIntent.MARINE_CONDITIONS
    assert response.status == QueryWorkflowStatus.DATA_UNAVAILABLE
    assert response.ocean_sst is None
    assert not response.evidence_audit.passed
    assert any("connection" in r.lower() or "endpoint" in r.lower()
               for r in response.evidence_audit.rejection_reasons)


@pytest.mark.asyncio
async def test_marine_conditions_stale_data_returns_data_unavailable():
    """Stale SST observation (>72 h) must be flagged and returned as DATA_UNAVAILABLE."""
    stale_payload = _make_live_sst_payload(is_stale=True)
    mock_adapter = MagicMock(spec=OceanDataAdapter)
    mock_adapter.fetch_live_subset = AsyncMock(return_value=(
        stale_payload,
        {"status": "SUCCESS", "http_status": 200, "live_features_retrieved": 2},
    ))
    engine = QueryWorkflowEngine(ocean_data_adapter=mock_adapter)
    request = MarineQueryRequest(query="current SST near Honnavar")
    response = await engine.run(request)

    assert response.intent == QueryIntent.MARINE_CONDITIONS
    assert response.status == QueryWorkflowStatus.DATA_UNAVAILABLE
    assert response.ocean_sst is not None
    assert response.ocean_sst.is_stale is True
    assert response.ocean_sst.retrieval_status == "STALE"
    assert response.evidence_audit.is_expired is True
    assert not response.evidence_audit.passed


@pytest.mark.asyncio
async def test_marine_conditions_missing_cells_still_returns_result():
    """A payload with all cells missing still returns a result (not crash) with zero valid cells."""
    now = datetime.now(timezone.utc)
    from datetime import timedelta
    obs_dt = now - timedelta(hours=6)

    metadata = OceanProductMetadata(
        product_id="SST_GLO_SST_L4_NRT_OBSERVATIONS_010_001",
        dataset_id="METOFFICE-GLO-SST-L4-NRT-OBS-SST-V2",
        production_center="UK Met Office / Copernicus Marine Service (CMEMS)",
        product_category=OceanProductCategory.L4_SATELLITE_ANALYSIS,
        spatial_resolution_deg=0.05,
        temporal_resolution="daily",
        data_format="NetCDF-4",
        usage_terms="Copernicus Open Access (CC-BY 4.0)",
        access_requirement="Copernicus Marine Data Store account",
        is_real_download=True,
        is_stale=False,
        retrieved_at=now,
        observation_timestamp=obs_dt,
        coverage_bbox=KARNATAKA_COASTAL_BBOX,
    )
    summary_empty = OceanAreaSummary(
        variable=OceanVariableType.SST,
        bounding_box=KARNATAKA_COASTAL_BBOX,
        observation_date=obs_dt.strftime("%Y-%m-%d"),
        valid_cell_count=0,
        land_masked_cell_count=0,
        missing_cell_count=3,
        is_stale=False,
    )
    empty_payload = OceanAnalyticsPayload(
        metadata=metadata,
        grid_points=[],
        area_summary=summary_empty,
        is_live_retrieval=True,
    )

    mock_adapter = MagicMock(spec=OceanDataAdapter)
    mock_adapter.fetch_live_subset = AsyncMock(return_value=(
        empty_payload,
        {"status": "SUCCESS", "http_status": 200, "live_features_retrieved": 0},
    ))
    engine = QueryWorkflowEngine(ocean_data_adapter=mock_adapter)
    request = MarineQueryRequest(query="sea surface temperature near Karnataka")
    response = await engine.run(request)

    assert response.intent == QueryIntent.MARINE_CONDITIONS
    # With 0 valid cells the handler still runs — status depends on staleness
    assert response.ocean_sst is not None
    assert response.ocean_sst.valid_cell_count == 0
    assert response.ocean_sst.missing_cell_count == 3
    assert response.ocean_sst.mean_sst_celsius is None
    # Disclaimer must always be present
    assert "SST ALONE DOES NOT" in response.ocean_sst.ecological_disclaimer


@pytest.mark.asyncio
async def test_marine_conditions_ocean_sst_fields_complete():
    """Verify all required OceanSSTResult fields are present and correctly typed on success."""
    live_payload = _make_live_sst_payload(is_stale=False)
    mock_adapter = MagicMock(spec=OceanDataAdapter)
    mock_adapter.fetch_live_subset = AsyncMock(return_value=(
        live_payload,
        {"status": "SUCCESS", "http_status": 200},
    ))
    engine = QueryWorkflowEngine(ocean_data_adapter=mock_adapter)
    request = MarineQueryRequest(query="SST near Bhatkal today")
    response = await engine.run(request)

    sst = response.ocean_sst
    assert sst is not None

    # Required identity fields
    assert isinstance(sst.source_name, str) and len(sst.source_name) > 0
    assert isinstance(sst.product_id, str)
    assert isinstance(sst.dataset_id, str)
    assert isinstance(sst.product_category, OceanProductCategory)
    assert sst.product_category == OceanProductCategory.L4_SATELLITE_ANALYSIS

    # Temporal fields
    assert isinstance(sst.observation_timestamp, datetime)
    assert isinstance(sst.retrieved_at, datetime)
    assert isinstance(sst.is_live_retrieval, bool)
    assert isinstance(sst.is_stale, bool)

    # Spatial coverage fields
    assert isinstance(sst.coverage_min_lat, float)
    assert isinstance(sst.coverage_max_lat, float)
    assert isinstance(sst.coverage_min_lon, float)
    assert isinstance(sst.coverage_max_lon, float)
    assert sst.spatial_resolution_deg == pytest.approx(0.05)

    # Retrieval status
    assert sst.retrieval_status == "SUCCESS"

    # Ecological disclaimer always present and non-trivial
    assert isinstance(sst.ecological_disclaimer, str)
    assert len(sst.ecological_disclaimer) > 50
    assert "INCOIS PFZ" in sst.ecological_disclaimer


@pytest.mark.asyncio
async def test_marine_conditions_sst_is_l4_not_forecast():
    """OceanSSTResult must always be labeled L4_SATELLITE_ANALYSIS — not a numerical forecast."""
    live_payload = _make_live_sst_payload()
    mock_adapter = MagicMock(spec=OceanDataAdapter)
    mock_adapter.fetch_live_subset = AsyncMock(return_value=(
        live_payload,
        {"status": "SUCCESS", "http_status": 200},
    ))
    engine = QueryWorkflowEngine(ocean_data_adapter=mock_adapter)
    response = await engine.run(MarineQueryRequest(query="SST update near Karnataka"))

    sst = response.ocean_sst
    assert sst is not None
    assert sst.product_category == OceanProductCategory.L4_SATELLITE_ANALYSIS
    assert sst.product_category != OceanProductCategory.NUMERICAL_MODEL_FORECAST
    assert sst.product_category != OceanProductCategory.IN_SITU_SENSOR
    assert "L4_SATELLITE_ANALYSIS" in response.answer or "Level-4" in response.answer


@pytest.mark.asyncio
async def test_marine_conditions_ecological_disclaimer_always_present():
    """Ecological disclaimer appears in both ocean_sst and answer for both success and failure paths."""
    # Success path
    live_payload = _make_live_sst_payload()
    mock_adapter = MagicMock(spec=OceanDataAdapter)
    mock_adapter.fetch_live_subset = AsyncMock(return_value=(
        live_payload,
        {"status": "SUCCESS", "http_status": 200},
    ))
    engine = QueryWorkflowEngine(ocean_data_adapter=mock_adapter)
    response = await engine.run(MarineQueryRequest(query="SST near Mangalore"))
    assert response.ocean_sst is not None
    assert "SST ALONE DOES NOT" in response.ocean_sst.ecological_disclaimer
    assert "SST ALONE DOES NOT" in response.answer

    # Failure path (credentials missing)
    mock_adapter2 = MagicMock(spec=OceanDataAdapter)
    mock_adapter2.fetch_live_subset = AsyncMock(return_value=(
        None,
        {"status": "CREDENTIALS_REQUIRED", "http_status": 401,
         "blocker_reason": "No credentials",
         "auth_endpoint": "https://auth.marine.copernicus.eu",
         "data_store_endpoint": "https://data.marine.copernicus.eu"},
    ))
    engine2 = QueryWorkflowEngine(ocean_data_adapter=mock_adapter2)
    response2 = await engine2.run(MarineQueryRequest(query="SST near Mangalore"))
    assert response2.ocean_sst is None
    assert any("SST ALONE" in w for w in response2.evidence_audit.warnings)
