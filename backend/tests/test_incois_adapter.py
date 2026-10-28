"""Unit tests for INCOIS marine data adapter and GeoJSON parsing."""

import json
from pathlib import Path
import pytest
import httpx

from app.adapters.incois import INCOISAdapter, KARNATAKA_SECTOR_NAME, KARNATAKA_SECTOR_ID
from app.geo.coordinates import dms_to_decimal_degrees, parse_dms_string

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "incois_karnataka_sample.json"


def test_dms_to_decimal_degrees():
    """Verify DMS to DD conversion formula."""
    # 13 deg 1 min 11 sec N -> 13 + 1/60 + 11/3600 = 13.01972
    lat = dms_to_decimal_degrees(13, 1, 11, "N")
    assert lat == 13.01972

    # 74 deg 39 min 50 sec E -> 74 + 39/60 + 50/3600 = 74.66389
    lon = dms_to_decimal_degrees(74, 39, 50, "E")
    assert lon == 74.66389

    # South latitude / West longitude should be negative
    south_lat = dms_to_decimal_degrees(10, 30, 0, "S")
    assert south_lat == -10.5

    west_lon = dms_to_decimal_degrees(45, 15, 0, "W")
    assert west_lon == -45.25


def test_parse_dms_string():
    """Verify parsing of formatted DMS strings."""
    assert parse_dms_string("13 1 11 N") == 13.01972
    assert parse_dms_string("74 39 50 E") == 74.66389
    assert parse_dms_string("14° 41' 43\" N") == 14.69528

    with pytest.raises(ValueError):
        parse_dms_string("invalid string")


def test_adapter_wfs_request_params():
    """Ensure WFS parameters are correctly formatted for Karnataka."""
    adapter = INCOISAdapter()
    params = adapter.get_wfs_request_params(KARNATAKA_SECTOR_NAME)
    assert params["service"] == "WFS"
    assert params["version"] == "1.1.0"
    assert params["request"] == "GetFeature"
    assert params["outputFormat"] == "application/json"
    assert "SECTOR_NAM='KARNATAKA'" in params["CQL_FILTER"]


def test_parse_real_incois_fixture():
    """Verify parsing of actual historical GeoJSON fixture downloaded from INCOIS WFS layer.

    Provenance:
    - Layer: PFZ_LandingCentres:LandingCenters_29Apr2024
    - Downloaded: 2026-10-26 directly from INCOIS GeoServer WFS.
    - Note: Contains historical advisory attributes from 2024-04-27.
    """
    adapter = INCOISAdapter()
    payload = adapter.parse_file(FIXTURE_PATH)

    assert payload.source == "INCOIS"
    assert payload.advisory_id == "INCOIS-PFZ-KA-32599"
    assert payload.region == "Karnataka Coast"
    assert payload.sector_id == KARNATAKA_SECTOR_ID
    assert payload.source_url is not None
    assert len(payload.items) == 3

    # Check First Item: Suratakal Pt
    item1 = payload.items[0]
    assert item1.item_id == "KA0302a"
    assert item1.landing_center == "Suratakal Pt"
    assert item1.district == "Dakshina Kannada"
    assert item1.direction_compass == "NW"
    assert item1.direction_bearing_deg == 279.0
    assert item1.distance_range_km == (12.0, 17.0)
    assert item1.distance_km == 14.5
    assert item1.depth_range_m == (23.0, 28.0)
    assert item1.depth_m == 25.5
    assert item1.status == "YES"
    # Target coordinate verified: Lat 13.01972 N, Lon 74.66389 E
    assert item1.coordinate.latitude == 13.01972
    assert item1.coordinate.longitude == 74.66389

    # Landing center location
    assert item1.landing_center_coordinate is not None
    assert item1.landing_center_coordinate.latitude == 13.0
    assert round(item1.landing_center_coordinate.longitude, 2) == 74.79

    # Check Second Item: Belekeri
    item2 = payload.items[1]
    assert item2.item_id == "KA0104a"
    assert item2.landing_center == "Belekeri"
    assert item2.district == "Uttara Kannada"
    assert item2.direction_compass == "SW"
    assert item2.direction_bearing_deg == 267.0
    assert item2.distance_km == 28.5


@pytest.mark.asyncio
async def test_fetch_with_mock_client():
    """Verify adapter fetch_karnataka_pfz_advisory using mock httpx transport without network."""
    with FIXTURE_PATH.open("r", encoding="utf-8") as f:
        fixture_content = json.load(f)

    # Custom mock transport returning the fixture
    def handler(request: httpx.Request) -> httpx.Response:
        assert "GetFeature" in str(request.url)
        return httpx.Response(200, json=fixture_content)

    mock_transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=mock_transport, base_url="https://incois.gov.in") as mock_client:
        adapter = INCOISAdapter()
        payload = await adapter.fetch_karnataka_pfz_advisory(client=mock_client)
        assert payload.advisory_id == "INCOIS-PFZ-KA-32599"
        assert len(payload.items) == 3
        assert payload.items[0].item_id == "KA0302a"


def test_parse_nonexistent_file():
    """Verify FileNotFoundError on missing file."""
    adapter = INCOISAdapter()
    with pytest.raises(FileNotFoundError):
        adapter.parse_file("nonexistent_path/fake_advisory.json")
