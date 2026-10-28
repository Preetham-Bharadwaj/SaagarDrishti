"""Tests for geospatial utilities and Karnataka coastline boundaries."""

from app.geo.coordinates import (
    KARNATAKA_LANDING_CENTERS,
    haversine_distance_km,
    is_within_karnataka_coast,
)
from app.schemas.common import GeoCoordinate


def test_landing_centers_within_karnataka_bounds():
    """Ensure all predefined Karnataka landing centers fall inside Karnataka bbox."""
    for name, center in KARNATAKA_LANDING_CENTERS.items():
        assert is_within_karnataka_coast(center), f"{name} expected inside Karnataka coastal bounds"


def test_out_of_bounds_coordinates():
    """Ensure coordinates far from Karnataka are rejected by boundary check."""
    # Delhi coordinate
    delhi = GeoCoordinate(latitude=28.6139, longitude=77.2090)
    assert not is_within_karnataka_coast(delhi)

    # Bay of Bengal coordinate
    bay_of_bengal = GeoCoordinate(latitude=13.0827, longitude=80.2707)
    assert not is_within_karnataka_coast(bay_of_bengal)


def test_haversine_distance():
    """Ensure haversine distance calculates reasonable distance between Malpe and Mangalore."""
    malpe = KARNATAKA_LANDING_CENTERS["Malpe"]
    mangalore = KARNATAKA_LANDING_CENTERS["Mangalore"]
    dist = haversine_distance_km(malpe, mangalore)
    # Distance between Malpe and Mangalore is ~55-65 km as the crow flies
    assert 50.0 <= dist <= 70.0
