"""Geospatial helper utilities and boundaries for the Karnataka coast."""

import math
from typing import Optional, Tuple
from app.schemas.common import GeoBoundingBox, GeoCoordinate

# Approximate bounding box for Karnataka coastal waters and Exclusive Economic Zone (EEZ)
# Latitude: ~12.7°N (Mangalore / border with Kerala) to ~15.0°N (Karwar / border with Goa)
# Longitude: ~73.0°E (Offshore maritime area) to ~75.2°E (Inshore coastline)
KARNATAKA_COASTAL_BBOX = GeoBoundingBox(
    min_latitude=12.5,
    max_latitude=15.2,
    min_longitude=73.0,
    max_longitude=75.3,
)

# Major fishing ports and landing centers along Karnataka coast
KARNATAKA_LANDING_CENTERS = {
    "Karwar": GeoCoordinate(latitude=14.8135, longitude=74.1298),
    "Tadri": GeoCoordinate(latitude=14.5262, longitude=74.3496),
    "Honnavar": GeoCoordinate(latitude=14.2800, longitude=74.4444),
    "Bhatkal": GeoCoordinate(latitude=13.9780, longitude=74.5510),
    "Gangolli": GeoCoordinate(latitude=13.6394, longitude=74.6750),
    "Malpe": GeoCoordinate(latitude=13.3525, longitude=74.7042),
    "Mangalore": GeoCoordinate(latitude=12.8698, longitude=74.8430),
}


def is_within_karnataka_coast(coord: GeoCoordinate) -> bool:
    """Check if a coordinate falls within the Karnataka marine boundary box.

    Args:
        coord: GeoCoordinate with latitude and longitude.

    Returns:
        bool: True if coordinate is inside the Karnataka coastal bounding box.
    """
    return (
        KARNATAKA_COASTAL_BBOX.min_latitude <= coord.latitude <= KARNATAKA_COASTAL_BBOX.max_latitude
        and KARNATAKA_COASTAL_BBOX.min_longitude <= coord.longitude <= KARNATAKA_COASTAL_BBOX.max_longitude
    )


def haversine_distance_km(coord1: GeoCoordinate, coord2: GeoCoordinate) -> float:
    """Calculate the great-circle distance between two geographic points in kilometers.

    Args:
        coord1: First GeoCoordinate.
        coord2: Second GeoCoordinate.

    Returns:
        float: Distance in kilometers.
    """
    earth_radius_km = 6371.0

    lat1_rad = math.radians(coord1.latitude)
    lat2_rad = math.radians(coord2.latitude)
    dlat = math.radians(coord2.latitude - coord1.latitude)
    dlon = math.radians(coord2.longitude - coord1.longitude)

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return round(earth_radius_km * c, 2)


def dms_to_decimal_degrees(
    deg: float, minutes: float, seconds: float, direction: str
) -> float:
    """Convert Degrees, Minutes, Seconds (DMS) to Decimal Degrees (DD).

    Args:
        deg: Degrees value.
        minutes: Minutes value.
        seconds: Seconds value.
        direction: Compass direction ('N', 'S', 'E', 'W').

    Returns:
        float: Decimal degrees rounded to 5 decimal places (~1.1 meter precision).
    """
    decimal = float(deg) + float(minutes) / 60.0 + float(seconds) / 3600.0
    if direction.strip().upper() in ("S", "W"):
        decimal = -decimal
    return round(decimal, 5)


def parse_dms_string(dms_str: str) -> float:
    """Parse a DMS string like '13 1 11 N' or '74 39 50 E' to decimal degrees.

    Args:
        dms_str: String formatted with degree, minute, second and direction suffix.

    Returns:
        float: Decimal degree equivalent.

    Raises:
        ValueError: If string format cannot be parsed.
    """
    cleaned = dms_str.replace("°", " ").replace("'", " ").replace('"', " ").strip()
    parts = cleaned.split()
    if len(parts) < 4:
        raise ValueError(f"Cannot parse DMS string '{dms_str}'. Expected 4 components: deg min sec dir.")
    deg = float(parts[0])
    minutes = float(parts[1])
    seconds = float(parts[2])
    direction = parts[3].upper()
    return dms_to_decimal_degrees(deg, minutes, seconds, direction)


def find_landing_center_coordinate(text_or_name: str) -> Optional[Tuple[str, GeoCoordinate]]:
    """Lookup a Karnataka landing center coordinate by name or substring.

    Args:
        text_or_name: Name or text containing a landing center name.

    Returns:
        Optional[Tuple[str, GeoCoordinate]]: (Canonical name, coordinate) or None.
    """
    if not text_or_name:
        return None
    query_lower = text_or_name.strip().lower()
    for port_name, coord in KARNATAKA_LANDING_CENTERS.items():
        if port_name.lower() in query_lower:
            return port_name, coord
    return None


def resolve_karnataka_coordinate(
    user_location: Optional[GeoCoordinate] = None,
    departure_port: Optional[str] = None,
    query_text: Optional[str] = None,
) -> Tuple[GeoCoordinate, str]:
    """Resolve a target geographic coordinate along the Karnataka coast.

    Priority order:
    1. Explicit user_location coordinate
    2. departure_port lookup in KARNATAKA_LANDING_CENTERS
    3. Landing center name mentioned in query_text
    4. Default central Karnataka coastal reference point (Malpe: 13.3525°N, 74.7042°E)

    Returns:
        Tuple[GeoCoordinate, str]: (Resolved coordinate, location description label)
    """
    if user_location is not None:
        return user_location, f"user GPS coordinate ({user_location.latitude:.4f}°N, {user_location.longitude:.4f}°E)"

    if departure_port:
        match = find_landing_center_coordinate(departure_port)
        if match:
            port_name, coord = match
            return coord, f"{port_name} landing center ({coord.latitude:.4f}°N, {coord.longitude:.4f}°E)"

    if query_text:
        match = find_landing_center_coordinate(query_text)
        if match:
            port_name, coord = match
            return coord, f"{port_name} landing center ({coord.latitude:.4f}°N, {coord.longitude:.4f}°E)"

    # Default to Malpe, central Karnataka coast
    default_coord = KARNATAKA_LANDING_CENTERS["Malpe"]
    return default_coord, f"central Karnataka coast (Malpe reference: {default_coord.latitude:.4f}°N, {default_coord.longitude:.4f}°E)"

