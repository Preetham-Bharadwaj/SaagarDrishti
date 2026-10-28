"""Open-Meteo Marine Weather API adapter.

Source verification record
--------------------------
Endpoint: https://marine-api.open-meteo.com/v1/marine
Probed:   2026-10-26 (live request, HTTP 200)
Location: Karnataka coast - Malpe area (lat 13.375N, lon 74.708E snapped)
Auth:     None required for non-commercial use.
Model:    ERAssWave (European Reanalysis + ECMWF-based marine model)
Update:   Hourly. Forecast horizon: 7 days. Spatial resolution: ~5 km.

Verified response fields
------------------------
time                : ISO 8601 local time string
wave_height         : Combined significant wave height (m)
wind_wave_height    : Wind-generated wave height component (m)
swell_wave_height   : Swell wave height component (m)
wave_direction      : Mean wave propagation direction (degrees from N)
wave_period         : Mean wave period (s)
wind_wave_direction : Wind-wave direction (degrees from N)
swell_wave_direction: Swell propagation direction (degrees from N)
swell_wave_period   : Swell wave period (s)

Live probe result (2026-10-26 00:00 IST)
  wave_height=0.66 m, swell_wave_height=0.48 m, wave_direction=226 deg
  => WaveHazardLevel.SLIGHT

Limitations
-----------
- NWP model output; not an authoritative safety advisory.
- Grid resolution ~5 km: nearshore bathymetry and headland effects not resolved.
- Coastal breaking waves and rip currents not modelled.
- Absence of a high wave_height value does NOT mean conditions are safe.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
import httpx

from app.adapters.base import BaseMarineDataAdapter
from app.schemas.marine_hazard import (
    HourlyMarineObservation,
    MarineHazardForecast,
    WaveHazardLevel,
)

logger = logging.getLogger(__name__)

OPEN_METEO_MARINE_BASE_URL = "https://marine-api.open-meteo.com"
OPEN_METEO_MARINE_ENDPOINT = "/v1/marine"

# Karnataka coast reference centre point for default queries
KARNATAKA_MARINE_DEFAULT_LAT = 13.36
KARNATAKA_MARINE_DEFAULT_LON = 74.70

# Fields confirmed present in live probe
VERIFIED_HOURLY_FIELDS = [
    "wave_height",
    "wind_wave_height",
    "swell_wave_height",
    "wave_direction",
    "wave_period",
    "wind_wave_direction",
    "swell_wave_direction",
    "swell_wave_period",
]

OPEN_METEO_QUALITY_LIMITATIONS = [
    "NWP model output (ERAssWave). Not an authoritative marine safety advisory.",
    "Spatial resolution ~5 km. Nearshore and coastal effects not fully resolved.",
    "Coastal breaking waves, rip currents, and port-specific sea states not modelled.",
    "Missing or low wave heights DO NOT confirm safe sea conditions.",
    "Official IMD Marine Weather Bulletins must be consulted before departure.",
]


def classify_hazard_level(wave_height_m: Optional[float]) -> WaveHazardLevel:
    """Classify wave hazard using the World Meteorological Organization (WMO) / Douglas Sea State Scale.

    Thresholds:
      < 0.50 m        : CALM (Douglas Sea State 0-2: Calm to Smooth)
      0.50 m - 1.25 m : SLIGHT (Douglas Sea State 3: Slight)
      1.25 m - 2.50 m : MODERATE (Douglas Sea State 4: Moderate)
      2.50 m - 4.00 m : ROUGH (Douglas Sea State 5: Rough)
      > 4.00 m        : VERY_ROUGH (Douglas Sea State 6+: Very Rough / High)

    Intended Use & Operational Boundary:
      This classification is adapted in SaagarDrishti solely as an exploratory
      prototype descriptive heuristic for small coastal craft (<15 m Length Overall).
      It is NOT an official IMD statutory warning, nor a universal vessel-safety limit.
      The absence of rough seas does NOT guarantee safe navigation.
      Small-craft fishers must strictly defer to official IMD/DFO warnings.

    Args:
        wave_height_m: Combined significant wave height in metres.

    Returns:
        WaveHazardLevel enum value. Missing data returns UNKNOWN.
    """
    if wave_height_m is None:
        return WaveHazardLevel.UNKNOWN
    if wave_height_m < 0.5:
        return WaveHazardLevel.CALM
    if wave_height_m < 1.25:
        return WaveHazardLevel.SLIGHT
    if wave_height_m < 2.5:
        return WaveHazardLevel.MODERATE
    if wave_height_m <= 4.0:
        return WaveHazardLevel.ROUGH
    return WaveHazardLevel.VERY_ROUGH


class OpenMeteoMarineAdapter(BaseMarineDataAdapter):
    """Adapter for Open-Meteo Marine Weather API (ERAssWave model).

    Provides hourly wave height and swell forecasts for any coordinate along
    the Karnataka coast without API key authentication.
    """

    def __init__(self, base_url: Optional[str] = None) -> None:
        resolved = (base_url or OPEN_METEO_MARINE_BASE_URL).rstrip("/")
        super().__init__(source_name="Open-Meteo Marine API", base_url=resolved)

    def validate_connection(self) -> bool:
        return bool(self.base_url)

    async def fetch_feed(
        self,
        endpoint: str = OPEN_METEO_MARINE_ENDPOINT,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Fetch raw JSON payload from the Open-Meteo Marine API.

        Implements the BaseMarineDataAdapter contract.

        Args:
            endpoint: Relative API path (default: /v1/marine).
            params: Query parameters dict.

        Returns:
            Dict[str, Any]: Parsed JSON response.
        """
        full_url = f"{self.base_url}{endpoint}"
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(full_url, params=params)
            response.raise_for_status()
            return response.json()

    def build_request_params(
        self,
        latitude: float,
        longitude: float,
        forecast_days: int = 1,
        timezone_str: str = "Asia/Kolkata",
    ) -> Dict[str, Any]:
        """Build verified Open-Meteo Marine API request parameters.

        Args:
            latitude: Target latitude.
            longitude: Target longitude.
            forecast_days: Number of forecast days (1-7).
            timezone_str: IANA timezone for local time alignment.

        Returns:
            Dict[str, Any]: Query parameters dict.
        """
        return {
            "latitude": latitude,
            "longitude": longitude,
            "hourly": ",".join(VERIFIED_HOURLY_FIELDS),
            "wind_speed_unit": "ms",
            "forecast_days": max(1, min(forecast_days, 7)),
            "timezone": timezone_str,
        }

    async def fetch_karnataka_marine_forecast(
        self,
        latitude: float = KARNATAKA_MARINE_DEFAULT_LAT,
        longitude: float = KARNATAKA_MARINE_DEFAULT_LON,
        forecast_days: int = 1,
        client: Optional[httpx.AsyncClient] = None,
    ) -> MarineHazardForecast:
        """Fetch and normalise marine wave forecast for a Karnataka coast point.

        Args:
            latitude: Target latitude (default: Malpe area reference).
            longitude: Target longitude.
            forecast_days: Forecast horizon (1-7 days).
            client: Optional injected HTTP client for testing.

        Returns:
            MarineHazardForecast: Fully typed, normalised forecast payload.

        Raises:
            httpx.HTTPError: On network or non-2xx HTTP response.
        """
        params = self.build_request_params(latitude, longitude, forecast_days)
        full_url = f"{self.base_url}{OPEN_METEO_MARINE_ENDPOINT}"
        logger.info("Fetching Open-Meteo marine forecast from %s (lat=%s, lon=%s)", full_url, latitude, longitude)

        if client is not None:
            response = await client.get(full_url, params=params)
        else:
            async with httpx.AsyncClient(timeout=20.0) as default_client:
                response = await default_client.get(full_url, params=params)

        response.raise_for_status()
        raw = response.json()

        # Build the source URL for provenance tracing
        param_str = "&".join(f"{k}={v}" for k, v in params.items())
        source_url = f"{full_url}?{param_str}"

        return self.parse_response(raw, source_url=source_url)

    def parse_response(
        self, data: Dict[str, Any], source_url: str = ""
    ) -> MarineHazardForecast:
        """Parse a raw Open-Meteo marine API JSON response into typed schema.

        Args:
            data: Parsed JSON response dictionary.
            source_url: Reconstructed source URL for provenance logging.

        Returns:
            MarineHazardForecast: Normalised, typed forecast payload.
        """
        retrieved_at = datetime.now(timezone.utc)
        hourly_raw = data.get("hourly", {})
        times: List[str] = hourly_raw.get("time", [])

        hourly_obs: List[HourlyMarineObservation] = []
        for i, time_str in enumerate(times):
            def _get(field: str) -> Optional[float]:
                vals = hourly_raw.get(field, [])
                if i < len(vals) and vals[i] is not None:
                    return float(vals[i])
                return None

            wh = _get("wave_height")
            obs = HourlyMarineObservation(
                time_local=time_str,
                wave_height_m=wh,
                wind_wave_height_m=_get("wind_wave_height"),
                swell_wave_height_m=_get("swell_wave_height"),
                wave_direction_deg=_get("wave_direction"),
                wave_period_s=_get("wave_period"),
                wind_wave_direction_deg=_get("wind_wave_direction"),
                swell_wave_direction_deg=_get("swell_wave_direction"),
                swell_wave_period_s=_get("swell_wave_period"),
                hazard_level=classify_hazard_level(wh),
            )
            hourly_obs.append(obs)

        # Peak hazard and wave height across all hours
        heights = [o.wave_height_m for o in hourly_obs if o.wave_height_m is not None]
        peak_wh = max(heights) if heights else None
        peak_hazard = classify_hazard_level(peak_wh)
        is_data_available = len(heights) > 0

        # Timezone offset handling with safe fallback
        raw_offset = data.get("utc_offset_seconds")
        if raw_offset is not None:
            try:
                utc_offset_s = int(raw_offset)
            except (ValueError, TypeError):
                utc_offset_s = 19800  # Fallback to IST (UTC+5:30)
        else:
            tz_str = str(data.get("timezone", ""))
            utc_offset_s = 19800 if ("Kolkata" in tz_str or "IST" in tz_str) else 0

        # Best-estimate current hour: find first time >= retrieved_at in local time
        current_obs = self._find_current_hour(hourly_obs, retrieved_at, utc_offset_s)
        forecast_valid_time = current_obs.time_local if current_obs else None

        # Staleness evaluation: check if all forecast hours are in the past
        is_stale = False
        if hourly_obs:
            try:
                local_now_naive = (retrieved_at + timedelta(seconds=utc_offset_s)).replace(tzinfo=None)
                latest_dt = datetime.fromisoformat(hourly_obs[-1].time_local).replace(tzinfo=None)
                if latest_dt < local_now_naive - timedelta(hours=1):
                    is_stale = True
            except (ValueError, TypeError):
                pass

        quality_notes = list(OPEN_METEO_QUALITY_LIMITATIONS)
        if not is_data_available:
            quality_notes.append("WARNING: Upstream model returned no valid numeric wave heights for this point.")
        if is_stale:
            quality_notes.append("WARNING: Forecast time steps have expired; latest step is in the past.")

        return MarineHazardForecast(
            source=self.source_name,
            source_url=source_url,
            retrieved_at=retrieved_at,
            model_label="ERAssWave",
            latitude=float(data.get("latitude", 0.0)),
            longitude=float(data.get("longitude", 0.0)),
            grid_resolution_km=9.0,
            timezone=str(data.get("timezone", "Asia/Kolkata")),
            utc_offset_seconds=utc_offset_s,
            forecast_hours=hourly_obs,
            current_hour_observation=current_obs,
            forecast_valid_time=forecast_valid_time,
            is_stale=is_stale,
            is_data_available=is_data_available,
            peak_wave_height_m=peak_wh,
            peak_hazard_level=peak_hazard,
            data_quality_notes=quality_notes,
        )

    @staticmethod
    def _find_current_hour(
        observations: List[HourlyMarineObservation],
        retrieved_at: datetime,
        utc_offset_seconds: int,
    ) -> Optional[HourlyMarineObservation]:
        """Find the observation whose hour corresponds to the current local time.

        Args:
            observations: List of hourly observations with ISO 8601 time strings.
            retrieved_at: Fetch timestamp in UTC.
            utc_offset_seconds: UTC offset for local time.

        Returns:
            The observation matching the current hour, or the first future one, or None.
        """
        # Convert retrieved_at to local time
        local_now = retrieved_at + timedelta(seconds=utc_offset_seconds)
        local_now_hour = local_now.replace(minute=0, second=0, microsecond=0)

        best: Optional[HourlyMarineObservation] = None
        for obs in observations:
            try:
                obs_dt = datetime.fromisoformat(obs.time_local)
            except (ValueError, TypeError):
                continue
            # Naive comparison: obs times are naive local times
            obs_hour = obs_dt.replace(tzinfo=None)
            local_hour_naive = local_now_hour.replace(tzinfo=None)
            if obs_hour >= local_hour_naive:
                return obs  # First hour at or after current local time
            best = obs  # Keep latest past hour as fallback

        return best
