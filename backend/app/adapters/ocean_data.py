"""Copernicus Marine Data Store adapter for oceanographic observations and Level-4 SST.

Source specifications
---------------------
Product ID : SST_GLO_SST_L4_NRT_OBSERVATIONS_010_001
Dataset ID : cmems_SST_GLO_SST_L4_NRT_OBSERVATIONS_010_001
Title      : Global Ocean OSTIA Sea Surface Temperature and Sea Ice Analysis
Provider   : UK Met Office / Copernicus Marine Service (CMEMS)
Category   : L4_SATELLITE_ANALYSIS (gap-free optimal interpolation of multi-sensor
             satellite infrared/microwave + in-situ assimilated data)
Resolution : 0.05° × 0.05° (~5.5 km grid spacing)
Cadence    : Daily foundation SST (issued ~06:00 UTC for previous day)
Coverage   : Global ocean, including Arabian Sea and Karnataka coast (12.5°N - 15.2°N)
Format     : NetCDF-4 (CF-1.4 compliant)
Access     : Requires user registration at data.marine.copernicus.eu; authenticated
             Keycloak/CAS tokens via auth.marine.copernicus.eu.

ECOLOGICAL & SAFETY GOVERNANCE
-------------------------------
SST is a physical oceanographic parameter. Thermal fronts and gradients indicate
oceanographic processes such as coastal upwelling or current boundaries.
SST ALONE DOES NOT PROVE FISH ABUNDANCE, CATCH YIELD, OR NAVIGATION SAFETY.
Operational guidance must always defer to official multi-parameter advisories
(e.g., INCOIS PFZ) and official statutory IMD weather warnings.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import httpx
import numpy as np

from app.adapters.base import BaseMarineDataAdapter
from app.geo.coordinates import KARNATAKA_COASTAL_BBOX, haversine_distance_km
from app.schemas.common import GeoBoundingBox, GeoCoordinate
from app.schemas.ocean_analytics import (
    OceanAnalyticsPayload,
    OceanAreaSummary,
    OceanGridPoint,
    OceanProductCategory,
    OceanProductMetadata,
    OceanVariableType,
)

try:
    from app.core.config import settings
except ImportError:
    settings = None

logger = logging.getLogger(__name__)

COPERNICUS_PRODUCT_ID = "SST_GLO_SST_L4_NRT_OBSERVATIONS_010_001"
COPERNICUS_DATASET_ID = "cmems_SST_GLO_SST_L4_NRT_OBSERVATIONS_010_001"
COPERNICUS_AUTH_ENDPOINT = "https://auth.marine.copernicus.eu"
COPERNICUS_TOKEN_ENDPOINT = "https://auth.marine.copernicus.eu/realms/MIS/protocol/openid-connect/token"
COPERNICUS_DATA_ENDPOINT = "https://data.marine.copernicus.eu"
COPERNICUS_WMTS_ENDPOINT = "https://wmts.marine.copernicus.eu/teroWmts"
COPERNICUS_WMTS_LAYER = "SST_GLO_SST_L4_NRT_OBSERVATIONS_010_001/METOFFICE-GLO-SST-L4-NRT-OBS-SST-V2/analysed_sst"
COPERNICUS_CLIENT_ID = "toolbox"
COPERNICUS_SCOPE = "openid profile email"


class OceanDataAdapter(BaseMarineDataAdapter):
    """Adapter for Copernicus Marine Data Store oceanographic datasets."""

    def __init__(
        self,
        username: Optional[str] = None,
        password: Optional[str] = None,
        base_url: Optional[str] = None,
    ) -> None:
        self.username = (
            username
            or os.getenv("COPERNICUSMARINE_SERVICE_USERNAME")
            or (getattr(settings, "COPERNICUSMARINE_SERVICE_USERNAME", None) if settings else None)
        )
        self.password = (
            password
            or os.getenv("COPERNICUSMARINE_SERVICE_PASSWORD")
            or (getattr(settings, "COPERNICUSMARINE_SERVICE_PASSWORD", None) if settings else None)
        )
        resolved_url = (base_url or COPERNICUS_DATA_ENDPOINT).rstrip("/")
        super().__init__(source_name="Copernicus Marine Data Store", base_url=resolved_url)

    def has_credentials(self) -> bool:
        """Check if Copernicus Marine credentials are configured."""
        return bool(self.username and self.password)

    def validate_connection(self) -> bool:
        """Validate adapter connectivity configuration."""
        return bool(self.base_url)

    async def fetch_feed(
        self,
        endpoint: str = "",
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Fetch feed implementation adhering to BaseMarineDataAdapter."""
        full_url = f"{self.base_url}{endpoint}"
        async with httpx.AsyncClient(timeout=15.0) as client:
            headers = {"User-Agent": "SaagarDrishti-Marine-Analytics/1.0"}
            response = await client.get(full_url, params=params, headers=headers)
            response.raise_for_status()
            return response.json()

    @staticmethod
    def kelvin_to_celsius(kelvin: Optional[float]) -> Optional[float]:
        """Convert temperature from Kelvin to Celsius rounded to 2 decimal places.

        Formula: T(°C) = T(K) - 273.15
        """
        if kelvin is None:
            return None
        return round(float(kelvin) - 273.15, 2)

    def parse_local_sample(self, file_path: Path) -> OceanAnalyticsPayload:
        """Parse an explicitly labelled local Copernicus sample file into typed payload.

        Args:
            file_path: Path to the JSON fixture or exported slice file.

        Returns:
            OceanAnalyticsPayload: Fully validated and structured oceanographic dataset.

        Raises:
            FileNotFoundError: If fixture file does not exist.
            ValueError: If JSON is invalid or missing required keys.
        """
        if not file_path.exists():
            raise FileNotFoundError(f"Copernicus ocean sample file does not exist: {file_path}")

        with file_path.open("r", encoding="utf-8-sig") as f:
            data = json.load(f)

        raw_meta = data.get("metadata", {})
        raw_prov = data.get("_provenance", {})
        cov_bbox = raw_meta.get("coverage_bbox", {})
        bbox = GeoBoundingBox(
            min_latitude=float(cov_bbox.get("min_latitude", KARNATAKA_COASTAL_BBOX.min_latitude)),
            max_latitude=float(cov_bbox.get("max_latitude", KARNATAKA_COASTAL_BBOX.max_latitude)),
            min_longitude=float(cov_bbox.get("min_longitude", KARNATAKA_COASTAL_BBOX.min_longitude)),
            max_longitude=float(cov_bbox.get("max_longitude", KARNATAKA_COASTAL_BBOX.max_longitude)),
        )

        obs_ts_str = raw_meta.get("observation_timestamp", "2026-10-25T12:00:00Z")
        try:
            obs_dt = datetime.fromisoformat(obs_ts_str.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            obs_dt = datetime.now(timezone.utc)

        # Staleness audit (> 72 hours)
        now_utc = datetime.now(timezone.utc)
        age_hours = (now_utc - obs_dt).total_seconds() / 3600.0
        is_stale = age_hours > 72.0

        fixture_type = raw_meta.get("fixture_type") or raw_prov.get("fixture_type", "MANUALLY_PREPARED_TEST_FIXTURE")
        is_real_download = bool(raw_meta.get("is_real_download", False))
        provenance_audit = raw_meta.get("provenance_audit") or raw_prov.get("provenance_audit")

        metadata = OceanProductMetadata(
            product_id=str(raw_meta.get("product_id", COPERNICUS_PRODUCT_ID)),
            dataset_id=str(raw_meta.get("dataset_id", COPERNICUS_DATASET_ID)),
            production_center=str(raw_meta.get("production_center", "UK Met Office / Copernicus Marine Service (CMEMS)")),
            product_category=OceanProductCategory.L4_SATELLITE_ANALYSIS,
            spatial_resolution_deg=float(raw_meta.get("spatial_resolution_deg", 0.05)),
            temporal_resolution=str(raw_meta.get("temporal_resolution", "daily")),
            data_format=str(raw_meta.get("data_format", "NetCDF-4")),
            usage_terms=str(raw_meta.get("usage_terms", "Copernicus Open Access (CC-BY 4.0)")),
            access_requirement=str(
                raw_meta.get("access_requirement", "Copernicus Marine Data Store account (auth.marine.copernicus.eu)")
            ),
            fixture_type=fixture_type,
            is_real_download=is_real_download,
            provenance_audit=provenance_audit,
            is_stale=is_stale,
            retrieved_at=now_utc,
            observation_timestamp=obs_dt,
            coverage_bbox=bbox,
        )

        raw_cells = data.get("grid_cells", [])
        grid_points: List[OceanGridPoint] = []

        for cell in raw_cells:
            lat = float(cell["latitude"])
            lon = float(cell["longitude"])
            sst_k = cell.get("analysed_sst_k")
            err_k = cell.get("analysis_error_k")
            mask = cell.get("mask", 1)

            # Mask: 1=sea, 2=land
            is_land = mask == 2 or sst_k is None

            # Physical validity checks: Earth ocean SST roughly 271.15K (-2°C) to 315.15K (+42°C)
            is_invalid = False
            if sst_k is not None:
                if sst_k < 260.0 or sst_k > 325.0:
                    is_invalid = True
            if err_k is not None and err_k < 0.0:
                err_k = None

            if is_invalid:
                sst_c = None
                quality_flag = 3  # invalid/missing
            elif is_land:
                sst_c = None
                quality_flag = 2  # land masked
            else:
                sst_c = self.kelvin_to_celsius(sst_k)
                quality_flag = 0  # nominal good

            pt = OceanGridPoint(
                coordinate=GeoCoordinate(latitude=lat, longitude=lon),
                variable=OceanVariableType.SST,
                value_raw=sst_k,
                value_si=sst_c,
                units="degC",
                analysis_error=err_k if not is_invalid else None,
                is_land_masked=is_land,
                quality_flag=quality_flag,
            )
            grid_points.append(pt)

        obs_date_str = obs_dt.strftime("%Y-%m-%d")
        summary = self.compute_area_summary(
            grid_points, bbox, obs_date_str, observation_timestamp=obs_dt
        )

        prov_notes = [
            f"Fixture Provenance: {fixture_type} (Real Download: {is_real_download}).",
            provenance_audit or "Manually prepared synthetic test slice constructed according to OSTIA L4 specifications.",
            f"Coverage: {bbox.min_latitude}°N-{bbox.max_latitude}°N, {bbox.min_longitude}°E-{bbox.max_longitude}°E.",
            "Foundation SST: free of diurnal daytime warming.",
        ]
        if is_stale:
            prov_notes.append(
                f"STALENESS WARNING: Observation timestamp ({obs_ts_str}) is older than 72 hours. "
                "Data represents historical analysis and must not be treated as real-time sea conditions."
            )

        return OceanAnalyticsPayload(
            metadata=metadata,
            grid_points=grid_points,
            area_summary=summary,
            provenance_notes=prov_notes,
            is_live_retrieval=is_real_download,
        )

    def compute_area_summary(
        self,
        points: List[OceanGridPoint],
        bbox: GeoBoundingBox,
        observation_date: str,
        observation_timestamp: Optional[datetime] = None,
        max_neighbor_distance_km: float = 40.0,
        thermal_front_threshold_c_per_km: float = 0.05,
    ) -> OceanAreaSummary:
        """Compute deterministic spatial and statistical summaries for bounded ocean grid cells.

        Distinguishes:
        - Macro-regional SST Range: max(T) - min(T) across the entire bounded region.
        - Local Spatial Gradient: |T_A - T_B| / d between neighboring valid sea cells
          (accounting for distance and land barriers).

        Args:
            points: List of grid points to summarize.
            bbox: Bounding box region for the summary.
            observation_date: Observation date string (YYYY-MM-DD).
            observation_timestamp: UTC datetime of observation (used for staleness check).
            max_neighbor_distance_km: Maximum great-circle distance between two cells to be
                treated as spatial neighbors (default: 40.0 km).
            thermal_front_threshold_c_per_km: Gradient threshold in °C/km to detect a
                physical thermal front (default: 0.05 °C/km).

        Returns:
            OceanAreaSummary: Statistically normalized summary.
        """
        valid_points = [
            p for p in points
            if not p.is_land_masked and p.value_si is not None and p.quality_flag != 3
        ]
        land_points = [p for p in points if p.is_land_masked or p.quality_flag == 2]
        missing_count = sum(
            1 for p in points
            if not p.is_land_masked and (p.value_si is None or p.quality_flag == 3)
        )
        land_count = len(land_points)
        valid_count = len(valid_points)

        gradient_notes: List[str] = []
        thermal_front = False

        # Staleness check
        is_stale = False
        if observation_timestamp is not None:
            age_hours = (datetime.now(timezone.utc) - observation_timestamp).total_seconds() / 3600.0
            if age_hours > 72.0:
                is_stale = True
                gradient_notes.append(
                    f"STALENESS WARNING: Observation timestamp ({observation_date}) is older than 72 hours. "
                    "Data represents historical analysis."
                )

        if valid_count > 0:
            celsius_vals = [p.value_si for p in valid_points if p.value_si is not None]
            mean_val = round(float(np.mean(celsius_vals)), 2)
            min_val = round(float(np.min(celsius_vals)), 2)
            max_val = round(float(np.max(celsius_vals)), 2)
            std_val = round(float(np.std(celsius_vals)), 2)
            regional_range = round(max_val - min_val, 2)

            errors = [p.analysis_error for p in valid_points if p.analysis_error is not None]
            mean_err = round(float(np.mean(errors)), 3) if errors else None

            gradient_notes.append(
                f"Regional SST range across valid sea cells: {min_val:.2f}°C to {max_val:.2f}°C "
                f"(spread: {regional_range:.2f}°C across region). Note: Regional range is a macro-scale "
                "spread, not a localized spatial gradient."
            )

            # Spatial gradient computation between neighboring valid sea cells
            gradients: List[float] = []
            for i in range(len(valid_points)):
                for j in range(i + 1, len(valid_points)):
                    p1 = valid_points[i]
                    p2 = valid_points[j]
                    if p1.value_si is None or p2.value_si is None:
                        continue

                    dist_km = haversine_distance_km(p1.coordinate, p2.coordinate)
                    if not (0.5 <= dist_km <= max_neighbor_distance_km):
                        continue

                    # Land barrier check: verify if an intervening land point blocks the direct path
                    is_blocked = False
                    for lp in land_points:
                        d1 = haversine_distance_km(p1.coordinate, lp.coordinate)
                        d2 = haversine_distance_km(lp.coordinate, p2.coordinate)
                        if (d1 + d2) <= dist_km * 1.15 and min(d1, d2) >= 0.5:
                            is_blocked = True
                            break

                    if not is_blocked:
                        delta_t = abs(p1.value_si - p2.value_si)
                        grad = round(delta_t / dist_km, 4)
                        gradients.append(grad)

            evaluated_pairs_count = len(gradients)
            if gradients:
                max_gradient = round(float(max(gradients)), 4)
                mean_gradient = round(float(np.mean(gradients)), 4)
                gradient_notes.append(
                    f"Evaluated {evaluated_pairs_count} neighboring sea-cell pairs (neighbor radius <= "
                    f"{max_neighbor_distance_km:.1f} km, accounting for land barriers). "
                    f"Max local spatial gradient: {max_gradient:.4f} °C/km, mean gradient: {mean_gradient:.4f} °C/km "
                    f"(thermal front threshold: {thermal_front_threshold_c_per_km:.4f} °C/km)."
                )

                if max_gradient >= thermal_front_threshold_c_per_km:
                    thermal_front = True
                    gradient_notes.append(
                        f"Significant local thermal front detected (max gradient {max_gradient:.4f} °C/km >= "
                        f"{thermal_front_threshold_c_per_km:.4f} °C/km). Indicates localized thermal boundary."
                    )
                else:
                    gradient_notes.append(
                        f"No significant local thermal front detected (max gradient {max_gradient:.4f} °C/km < "
                        f"{thermal_front_threshold_c_per_km:.4f} °C/km)."
                    )
            else:
                max_gradient = None
                mean_gradient = None
                if valid_count > 1:
                    gradient_notes.append(
                        f"No neighboring sea-cell pairs found within {max_neighbor_distance_km:.1f} km distance threshold "
                        "(cells are either isolated, separated by land barriers, or too distant for local gradient analysis)."
                    )
        else:
            mean_val = min_val = max_val = std_val = regional_range = mean_err = None
            max_gradient = mean_gradient = None
            evaluated_pairs_count = 0
            gradient_notes.append("No valid ocean cells found within the specified boundary.")

        return OceanAreaSummary(
            variable=OceanVariableType.SST,
            bounding_box=bbox,
            observation_date=observation_date,
            mean_value=mean_val,
            min_value=min_val,
            max_value=max_val,
            std_dev=std_val,
            mean_error=mean_err,
            valid_cell_count=valid_count,
            land_masked_cell_count=land_count,
            missing_cell_count=missing_count,
            regional_range_celsius=regional_range,
            max_spatial_gradient_c_per_km=max_gradient,
            mean_spatial_gradient_c_per_km=mean_gradient,
            evaluated_neighbor_pairs_count=evaluated_pairs_count,
            thermal_front_threshold_c_per_km=thermal_front_threshold_c_per_km,
            thermal_front_detected=thermal_front,
            is_stale=is_stale,
            gradient_notes=gradient_notes,
        )

    async def fetch_live_subset(
        self,
        bbox: Optional[GeoBoundingBox] = None,
        date_str: Optional[str] = None,
    ) -> Tuple[Optional[OceanAnalyticsPayload], Dict[str, Any]]:
        """Attempt live retrieval or report exact credential blocker for Copernicus Marine Store.

        Args:
            bbox: Target bounding box (default: Karnataka coastal waters).
            date_str: Target observation date (YYYY-MM-DD).

        Returns:
            Tuple[Optional[OceanAnalyticsPayload], Dict[str, Any]]:
            (Payload if successful, telemetry dict with status, blocker details, and HTTP codes).
        """
        target_bbox = bbox or KARNATAKA_COASTAL_BBOX
        telemetry: Dict[str, Any] = {
            "product_id": COPERNICUS_PRODUCT_ID,
            "target_bbox": {
                "min_lat": target_bbox.min_latitude,
                "max_lat": target_bbox.max_latitude,
                "min_lon": target_bbox.min_longitude,
                "max_lon": target_bbox.max_longitude,
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # 1. Check credentials
        if not self.has_credentials():
            logger.info("Copernicus Marine live retrieval blocked: credentials not configured in environment.")
            telemetry.update({
                "status": "CREDENTIALS_REQUIRED",
                "http_status": 401,
                "blocker_reason": (
                    "Copernicus Marine Data Store requires registered user authentication. "
                    "Environment variables 'COPERNICUSMARINE_SERVICE_USERNAME' and "
                    "'COPERNICUSMARINE_SERVICE_PASSWORD' are not set. "
                    "Register for free at https://data.marine.copernicus.eu/."
                ),
                "auth_endpoint": COPERNICUS_AUTH_ENDPOINT,
                "data_store_endpoint": COPERNICUS_DATA_ENDPOINT,
            })
            return None, telemetry

        # 2. Live authentication attempt
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                auth_resp = await client.post(
                    COPERNICUS_TOKEN_ENDPOINT,
                    data={
                        "client_id": COPERNICUS_CLIENT_ID,
                        "grant_type": "password",
                        "username": self.username,
                        "password": self.password,
                        "scope": COPERNICUS_SCOPE,
                    },
                )
                telemetry["http_status"] = auth_resp.status_code
                if auth_resp.status_code != 200:
                    telemetry.update({
                        "status": "AUTHENTICATION_FAILED",
                        "blocker_reason": f"Copernicus auth returned HTTP {auth_resp.status_code}: {auth_resp.text[:200]}",
                    })
                    return None, telemetry

                token_data = auth_resp.json()
                telemetry["status"] = "AUTHENTICATED"
                telemetry["token_type"] = token_data.get("token_type")
                telemetry["expires_in"] = token_data.get("expires_in")
                access_token = token_data.get("access_token")

                if not access_token:
                    telemetry["status"] = "AUTHENTICATION_FAILED"
                    telemetry["blocker_reason"] = "No access_token found in authentication response."
                    return None, telemetry

                # 3. Live data query via Copernicus WMTS GetFeatureInfo for Karnataka coastal points
                try:
                    headers = {"Authorization": f"Bearer {access_token}"}
                    sample_coords = [
                        (14.80, 73.80, "Offshore Karwar"),
                        (14.80, 74.05, "Coastal Karwar"),
                        (14.30, 74.20, "Coastal Honnavar"),
                        (13.90, 74.30, "Coastal Bhatkal"),
                        (13.35, 74.50, "Offshore Malpe"),
                        (12.85, 74.60, "Offshore Mangalore"),
                        (12.85, 74.75, "Coastal Mangalore"),
                        (12.85, 75.20, "Onshore Mangalore (Land)"),
                    ]

                    active_coords = [
                        (lat, lon, desc) for lat, lon, desc in sample_coords
                        if (target_bbox.min_latitude <= lat <= target_bbox.max_latitude and
                            target_bbox.min_longitude <= lon <= target_bbox.max_longitude)
                    ]
                    if not active_coords:
                        active_coords = sample_coords

                    grid_points: List[OceanGridPoint] = []
                    target_time = f"{date_str}T00:00:00.000Z" if date_str else "2026-10-25T00:00:00.000Z"

                    for lat, lon, desc in active_coords:
                        tilerow = int((90.0 - lat) / 45.0)
                        tilecol = int((lon + 180.0) / 45.0)
                        top_lat = 90.0 - tilerow * 45.0
                        left_lon = -180.0 + tilecol * 45.0
                        j = max(0, min(255, int(((top_lat - lat) / 45.0) * 256.0)))
                        i = max(0, min(255, int(((lon - left_lon) / 45.0) * 256.0)))

                        gfi_params = {
                            "service": "WMTS",
                            "request": "GetFeatureInfo",
                            "version": "1.0.0",
                            "layer": COPERNICUS_WMTS_LAYER,
                            "style": "cmap:thermal",
                            "format": "image/png",
                            "infoformat": "application/json",
                            "tilematrixset": "EPSG:4326",
                            "tilematrix": "2",
                            "tilerow": str(tilerow),
                            "tilecol": str(tilecol),
                            "i": str(i),
                            "j": str(j),
                            "time": target_time,
                        }

                        gfi_resp = await client.get(
                            COPERNICUS_WMTS_ENDPOINT,
                            params=gfi_params,
                            headers=headers,
                            timeout=10.0,
                        )

                        if gfi_resp.status_code == 200:
                            gfi_json = gfi_resp.json()
                            features = gfi_json.get("features", [])
                            if features:
                                props = features[0].get("properties", {})
                                val_k = props.get("value")
                                is_land = (val_k is None)
                                val_c = self.kelvin_to_celsius(val_k) if not is_land else None

                                grid_points.append(
                                    OceanGridPoint(
                                        coordinate=GeoCoordinate(latitude=lat, longitude=lon),
                                        variable=OceanVariableType.SST,
                                        value_raw=val_k,
                                        value_si=val_c,
                                        units="degC",
                                        analysis_error=0.35 if not is_land else None,
                                        is_land_masked=is_land,
                                        quality_flag=2 if is_land else 0,
                                    )
                                )

                    if grid_points:
                        obs_date_str = target_time[:10]
                        try:
                            obs_dt = datetime.fromisoformat(target_time.replace("Z", "+00:00"))
                        except Exception:
                            obs_dt = datetime.now(timezone.utc)

                        summary = self.compute_area_summary(
                            grid_points, target_bbox, obs_date_str, observation_timestamp=obs_dt
                        )

                        masked_user = (
                            f"{self.username[:2]}***{self.username[-2:]}"
                            if len(self.username) > 4
                            else "***"
                        )
                        metadata = OceanProductMetadata(
                            product_id=COPERNICUS_PRODUCT_ID,
                            dataset_id=COPERNICUS_DATASET_ID,
                            production_center="UK Met Office / Copernicus Marine Service (CMEMS)",
                            product_category=OceanProductCategory.L4_SATELLITE_ANALYSIS,
                            spatial_resolution_deg=0.05,
                            temporal_resolution="daily",
                            data_format="NetCDF-4 / WMTS OGC Service",
                            usage_terms="Copernicus Open Access (CC-BY 4.0)",
                            access_requirement="Copernicus Marine Data Store account (auth.marine.copernicus.eu)",
                            fixture_type="LIVE_DOWNLOADED_PRODUCT",
                            is_real_download=True,
                            provenance_audit=(
                                "Verified live retrieval via Copernicus Marine OpenID Connect authentication "
                                "and WMTS GetFeatureInfo data service."
                            ),
                            is_stale=summary.is_stale,
                            retrieved_at=datetime.now(timezone.utc),
                            observation_timestamp=obs_dt,
                            coverage_bbox=target_bbox,
                        )

                        payload = OceanAnalyticsPayload(
                            metadata=metadata,
                            grid_points=grid_points,
                            area_summary=summary,
                            provenance_notes=[
                                "Live data retrieved directly from Copernicus Marine Data Store (WMTS).",
                                f"Authenticated as user {masked_user}.",
                                f"Coverage: {target_bbox.min_latitude}°N-{target_bbox.max_latitude}°N, {target_bbox.min_longitude}°E-{target_bbox.max_longitude}°E.",
                                "Foundation SST: free of diurnal daytime warming.",
                            ],
                            is_live_retrieval=True,
                        )

                        telemetry["status"] = "SUCCESS"
                        telemetry["live_features_retrieved"] = len(grid_points)
                        return payload, telemetry

                except Exception as query_exc:
                    logger.info("Authenticated successfully, but live data query encountered: %s", query_exc)
                    telemetry["query_error"] = str(query_exc)
                    return None, telemetry

                return None, telemetry

        except Exception as exc:  # noqa: BLE001
            telemetry.update({
                "status": "CONNECTION_ERROR",
                "http_status": 0,
                "blocker_reason": f"Connection to Copernicus auth endpoint failed: {exc}",
            })
            return None, telemetry
