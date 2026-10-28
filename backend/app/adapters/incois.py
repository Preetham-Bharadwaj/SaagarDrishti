"""INCOIS (Indian National Centre for Ocean Information Services) adapter.

Interfaces with official INCOIS Potential Fishing Zone (PFZ) advisory data feeds
for the Karnataka coast, supporting live WFS GeoJSON retrieval and manual file ingestion.
"""

from datetime import datetime, timezone
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import httpx

from app.adapters.base import BaseMarineDataAdapter
from app.core.config import settings
from app.geo.coordinates import dms_to_decimal_degrees
from app.schemas.common import GeoCoordinate
from app.schemas.pfz import PFZAdvisoryItem, PFZAdvisoryPayload

logger = logging.getLogger(__name__)

# Verified operational endpoint details for INCOIS PFZ Landing Center feeds
INCOIS_DEFAULT_BASE_URL = "https://incois.gov.in"
INCOIS_WFS_ENDPOINT = "/geoserver/PFZ_LandingCentres/ows"
INCOIS_WFS_TYPENAME = "PFZ_LandingCentres:LandingCenters_29Apr2024"
KARNATAKA_SECTOR_NAME = "KARNATAKA"
KARNATAKA_SECTOR_ID = "SEC004"

INCOIS_QUALITY_LIMITATIONS = [
    "Advisory hotspots are derived from composite satellite thermal infrared (SST) and ocean color (Chlorophyll-a).",
    "Satellite observations are subject to cloud occlusion, especially during the southwest monsoon.",
    "Dynamic ocean currents and local winds can cause surface feature displacement after 24 hours.",
    "Advisories are suspended during government-mandated seasonal fishing bans and extreme marine weather.",
]


class INCOISAdapter(BaseMarineDataAdapter):
    """Adapter for INCOIS Potential Fishing Zone (PFZ) operational data."""

    def __init__(self, base_url: Optional[str] = None, api_key: Optional[str] = None) -> None:
        resolved_base_url = base_url or settings.INCOIS_API_BASE_URL or INCOIS_DEFAULT_BASE_URL
        super().__init__(
            source_name="INCOIS",
            base_url=resolved_base_url.rstrip("/"),
        )
        self.api_key = api_key or settings.INCOIS_API_KEY

    def validate_connection(self) -> bool:
        """Verify whether base URL is configured.

        Returns:
            bool: True if base URL is non-empty.
        """
        return bool(self.base_url)

    def get_wfs_request_params(self, sector: str = KARNATAKA_SECTOR_NAME) -> Dict[str, str]:
        """Construct standard WFS GetFeature query parameters for the target sector.

        Args:
            sector: Name of the maritime sector (e.g., 'KARNATAKA').

        Returns:
            Dict[str, str]: URL query parameters.
        """
        return {
            "service": "WFS",
            "version": "1.1.0",
            "request": "GetFeature",
            "typeName": INCOIS_WFS_TYPENAME,
            "outputFormat": "application/json",
            "CQL_FILTER": f"SECTOR_NAM='{sector.upper()}'",
        }

    async def fetch_feed(
        self,
        endpoint: str = INCOIS_WFS_ENDPOINT,
        params: Optional[Dict[str, Any]] = None,
        client: Optional[httpx.AsyncClient] = None,
    ) -> Dict[str, Any]:
        """Fetch raw payload from INCOIS via HTTP GET.

        Args:
            endpoint: Relative path to endpoint.
            params: Optional query parameters.
            client: Optional injected httpx AsyncClient for dependency injection or testing.

        Returns:
            Dict[str, Any]: Parsed JSON response.

        Raises:
            httpx.HTTPError: On network or HTTP communication errors.
        """
        full_url = f"{self.base_url}{endpoint}"
        logger.info("Fetching INCOIS feed from %s with params %s", full_url, params)

        if client is not None:
            response = await client.get(full_url, params=params)
            response.raise_for_status()
            return response.json()

        async with httpx.AsyncClient(timeout=15.0) as default_client:
            response = await default_client.get(full_url, params=params)
            response.raise_for_status()
            return response.json()

    async def fetch_karnataka_pfz_advisory(
        self, client: Optional[httpx.AsyncClient] = None
    ) -> PFZAdvisoryPayload:
        """Acquire latest Karnataka PFZ advisory from INCOIS WFS service.

        Args:
            client: Optional injected HTTP client.

        Returns:
            PFZAdvisoryPayload: Structured and typed advisory payload.
        """
        params = self.get_wfs_request_params(KARNATAKA_SECTOR_NAME)
        full_source_url = f"{self.base_url}{INCOIS_WFS_ENDPOINT}?service=WFS&typeName={INCOIS_WFS_TYPENAME}&CQL_FILTER=SECTOR_NAM='{KARNATAKA_SECTOR_NAME}'"

        raw_geojson = await self.fetch_feed(
            endpoint=INCOIS_WFS_ENDPOINT,
            params=params,
            client=client,
        )
        return self.parse_geojson(raw_geojson, source_url=full_source_url)

    def parse_file(self, file_path: Union[str, Path]) -> PFZAdvisoryPayload:
        """Parse an authorized local JSON or GeoJSON file downloaded from INCOIS.

        Args:
            file_path: Path to the local advisory file.

        Returns:
            PFZAdvisoryPayload: Parsed advisory payload.
        """
        path = Path(file_path)
        if not path.is_file():
            raise FileNotFoundError(f"Advisory file does not exist at: {path}")

        with path.open("r", encoding="utf-8") as f:
            raw_data = json.load(f)

        return self.parse_geojson(raw_data, source_url=f"file://{path.resolve()}")

    def parse_geojson(
        self, data: Dict[str, Any], source_url: Optional[str] = None
    ) -> PFZAdvisoryPayload:
        """Parse raw GeoJSON FeatureCollection from INCOIS into typed PFZAdvisoryPayload.

        Args:
            data: Raw GeoJSON dictionary.
            source_url: Upstream origin URL or file path.

        Returns:
            PFZAdvisoryPayload: Standardized advisory payload.
        """
        features = data.get("features", [])
        items: List[PFZAdvisoryItem] = []

        advisory_id = "INCOIS-PFZ-KA-UNKNOWN"
        issued_at: Optional[datetime] = None
        valid_from: Optional[datetime] = None
        valid_to: Optional[datetime] = None

        for idx, feat in enumerate(features):
            props = feat.get("properties", {})

            # Advisory metadata extraction from first available feature
            if idx == 0:
                forecast_id = props.get("FORECAST_I")
                if forecast_id:
                    advisory_id = f"INCOIS-PFZ-KA-{forecast_id}"
                issued_str = props.get("UPDATED_DA") or props.get("FORECAST_D")
                valid_from_str = props.get("FORECAST_D")
                valid_to_str = props.get("VALIDITY_D")

                issued_at = self._parse_iso_date(issued_str)
                valid_from = self._parse_iso_date(valid_from_str)
                valid_to = self._parse_iso_date(valid_to_str)

            # Unique hotspot identifier
            item_id = str(props.get("LC_UNIQUE_") or feat.get("id") or f"PFZ-HOTSPOT-{idx+1}")
            landing_center = str(props.get("LC_NAME") or "Unknown Landing Center").strip()
            district = props.get("DIST_NAME")
            status = str(props.get("STATUS") or "YES").strip().upper()

            # Landing Center Coordinates (from geometry or properties)
            geom_coords = feat.get("geometry", {}).get("coordinates", [])
            lc_coord: Optional[GeoCoordinate] = None
            if geom_coords and len(geom_coords) >= 2:
                lc_coord = GeoCoordinate(longitude=geom_coords[0], latitude=geom_coords[1])
            elif "LONGITUDE" in props and "LATITUDE" in props:
                try:
                    lc_coord = GeoCoordinate(
                        longitude=float(props["LONGITUDE"]), latitude=float(props["LATITUDE"])
                    )
                except (ValueError, TypeError):
                    pass

            # Target PFZ Hotspot Coordinate
            target_coord = self._extract_target_coord(props, lc_coord)
            if target_coord is None:
                # If target coordinate could not be derived, skip item or mark invalid
                continue

            # Direction & Bearings
            bearing = props.get("BEARING")
            direction_bearing_deg: Optional[float] = None
            if bearing is not None:
                try:
                    direction_bearing_deg = float(bearing)
                except (ValueError, TypeError):
                    pass
            direction_compass = props.get("DIRECTION")

            # Distance range
            dist_f = props.get("DISTANCE_F")
            dist_t = props.get("DISTANCE_T")
            distance_range_km: Optional[Tuple[float, float]] = None
            distance_km: Optional[float] = None
            if dist_f is not None and dist_t is not None:
                try:
                    df, dt = float(dist_f), float(dist_t)
                    distance_range_km = (df, dt)
                    distance_km = round((df + dt) / 2.0, 2)
                except (ValueError, TypeError):
                    pass
            elif dist_f is not None:
                try:
                    distance_km = float(dist_f)
                except (ValueError, TypeError):
                    pass

            # Depth range
            depth_f = props.get("DEPTH_FROM")
            depth_t = props.get("DEPTH_TO")
            depth_range_m: Optional[Tuple[float, float]] = None
            depth_m: Optional[float] = None
            if depth_f is not None and depth_t is not None:
                try:
                    df, dt = float(depth_f), float(depth_t)
                    depth_range_m = (df, dt)
                    depth_m = round((df + dt) / 2.0, 2)
                except (ValueError, TypeError):
                    pass
            elif depth_f is not None:
                try:
                    depth_m = float(depth_f)
                except (ValueError, TypeError):
                    pass

            items.append(
                PFZAdvisoryItem(
                    item_id=item_id,
                    coordinate=target_coord,
                    landing_center=landing_center,
                    landing_center_coordinate=lc_coord,
                    district=district,
                    direction_bearing_deg=direction_bearing_deg,
                    direction_compass=direction_compass,
                    distance_km=distance_km,
                    distance_range_km=distance_range_km,
                    depth_m=depth_m,
                    depth_range_m=depth_range_m,
                    status=status,
                    raw_properties=props,
                )
            )

        return PFZAdvisoryPayload(
            advisory_id=advisory_id,
            source=self.source_name,
            source_url=source_url,
            region="Karnataka Coast",
            sector_id=KARNATAKA_SECTOR_ID,
            retrieved_at=datetime.now(timezone.utc),
            issued_at=issued_at,
            valid_from=valid_from,
            valid_to=valid_to,
            quality_limitations=INCOIS_QUALITY_LIMITATIONS,
            items=items,
        )

    def _extract_target_coord(
        self, props: Dict[str, Any], fallback_coord: Optional[GeoCoordinate]
    ) -> Optional[GeoCoordinate]:
        """Extract decimal coordinates from INCOIS DMS properties."""
        has_lat_dms = all(k in props for k in ("LATITUDE_D", "LATITUDE_M", "LATITUDE_S", "LATITUDE_1"))
        has_lon_dms = all(k in props for k in ("LONGITUDE_", "LONGITUDE1", "LONGITUD_1", "LONGITUD_2"))

        if has_lat_dms and has_lon_dms:
            try:
                lat_dd = dms_to_decimal_degrees(
                    props["LATITUDE_D"],
                    props["LATITUDE_M"],
                    props["LATITUDE_S"],
                    str(props["LATITUDE_1"]),
                )
                lon_dd = dms_to_decimal_degrees(
                    props["LONGITUDE_"],
                    props["LONGITUDE1"],
                    props["LONGITUD_1"],
                    str(props["LONGITUD_2"]),
                )
                return GeoCoordinate(latitude=lat_dd, longitude=lon_dd)
            except Exception as e:
                logger.warning("Failed to convert DMS to decimal coordinates: %s", e)

        # Fallback to origin landing center coordinate if target DMS is absent
        return fallback_coord

    @staticmethod
    def _parse_iso_date(date_str: Optional[str]) -> Optional[datetime]:
        """Safely parse ISO 8601 UTC timestamp string from INCOIS."""
        if not date_str:
            return None
        try:
            # Handle ISO ending in 'Z'
            clean = date_str.replace("Z", "+00:00")
            return datetime.fromisoformat(clean)
        except (ValueError, TypeError):
            return None
