"""Live smoke test for the Open-Meteo Marine Hazard adapter.

This script makes a REAL HTTP request to the Open-Meteo Marine API and
reports the actual response. It is intentionally separate from the unit
test suite so that unit tests do NOT require network access.

Usage:
    python scripts/marine_hazard_smoke_test.py

Expected output (example from live probe 2026-10-26):
    HTTP 200, 24 hourly observations, wave_height ~0.66 m (SLIGHT hazard)

Exit codes:
    0  -- Live request succeeded and response was parseable
    1  -- HTTP error or parse failure
"""

import asyncio
import json
import sys
from datetime import datetime, timezone

import httpx


ENDPOINT = "https://marine-api.open-meteo.com/v1/marine"
KARNATAKA_LAT = 13.36   # Near Malpe / Udupi
KARNATAKA_LON = 74.70

HOURLY_FIELDS = [
    "wave_height",
    "wind_wave_height",
    "swell_wave_height",
    "wave_direction",
    "wave_period",
    "wind_wave_direction",
    "swell_wave_direction",
    "swell_wave_period",
]

PARAMS = {
    "latitude": KARNATAKA_LAT,
    "longitude": KARNATAKA_LON,
    "hourly": ",".join(HOURLY_FIELDS),
    "wind_speed_unit": "ms",
    "forecast_days": 1,
    "timezone": "Asia/Kolkata",
}


async def run_smoke_test() -> int:
    print("=" * 60)
    print("SaagarDrishti -- Open-Meteo Marine API Live Smoke Test")
    print(f"Timestamp (UTC): {datetime.now(timezone.utc).isoformat()}")
    print(f"Target: lat={KARNATAKA_LAT}, lon={KARNATAKA_LON} (Karnataka coast)")
    print("=" * 60)

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(ENDPOINT, params=PARAMS)

        print(f"HTTP Status      : {response.status_code}")
        print(f"Content-Type     : {response.headers.get('content-type', '?')}")
        print(f"Response Size    : {len(response.content)} bytes")

        if response.status_code != 200:
            print(f"FAIL: Non-200 response. Body: {response.text[:500]}")
            return 1

        data = response.json()
        lat_snap = data.get("latitude")
        lon_snap = data.get("longitude")
        tz = data.get("timezone")
        utc_off = data.get("utc_offset_seconds")
        hourly = data.get("hourly", {})
        times = hourly.get("time", [])
        wave_heights = hourly.get("wave_height", [])

        print(f"Snapped lat/lon  : {lat_snap}N, {lon_snap}E")
        print(f"Timezone         : {tz}  (UTC+{utc_off // 3600}h)")
        print(f"Hourly obs count : {len(times)}")

        if not times or not wave_heights:
            print("FAIL: No hourly time or wave_height data returned.")
            return 1

        # Report first 4 hours
        print()
        print("First 4 hourly observations:")
        print(f"  {'Time':22s}  {'wave_ht_m':>10s}  {'swell_ht_m':>11s}  {'dir_deg':>8s}")
        swells = hourly.get("swell_wave_height", [])
        dirs = hourly.get("wave_direction", [])
        for i in range(min(4, len(times))):
            wh = wave_heights[i] if i < len(wave_heights) else None
            sw = swells[i] if i < len(swells) else None
            dr = dirs[i] if i < len(dirs) else None
            print(f"  {times[i]:22s}  {str(wh):>10s}  {str(sw):>11s}  {str(dr):>8s}")

        # Max wave height
        valid_wh = [v for v in wave_heights if v is not None]
        if valid_wh:
            peak = max(valid_wh)
            if peak < 0.5:
                hazard = "CALM"
            elif peak < 1.25:
                hazard = "SLIGHT"
            elif peak < 2.5:
                hazard = "MODERATE"
            elif peak <= 4.0:
                hazard = "ROUGH"
            else:
                hazard = "VERY ROUGH"
            print()
            print(f"Peak wave height : {peak:.2f} m => {hazard}")

        print()
        print("PASS: Live smoke test completed successfully.")
        print()
        print("SAFETY NOTICE: This NWP model output is NOT an authoritative safety advisory.")
        print("Consult official IMD Marine Weather Bulletins before any sea departure.")
        return 0

    except httpx.HTTPError as exc:
        print(f"FAIL: HTTP error: {exc}")
        return 1
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL: Unexpected error: {exc}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(run_smoke_test())
    sys.exit(exit_code)
