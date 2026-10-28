"""CLI utility and smoke test for Copernicus Ocean Analytics and Sea Surface Temperature.

Usage:
    python scripts/ocean_analytics.py --local
    python scripts/ocean_analytics.py --live
    python scripts/ocean_analytics.py --file <path_to_fixture>
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Add backend directory to sys.path and load environment variables safely
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

import dotenv
dotenv.load_dotenv(backend_dir / ".env")

from app.adapters.ocean_data import (
    COPERNICUS_DATASET_ID,
    COPERNICUS_PRODUCT_ID,
    OceanDataAdapter,
)
from app.geo.coordinates import KARNATAKA_COASTAL_BBOX
from app.schemas.common import GeoBoundingBox

SAMPLE_FIXTURE_PATH = backend_dir / "tests" / "fixtures" / "copernicus_sst_karnataka_sample.json"


async def run_live_probe(adapter: OceanDataAdapter, bbox: GeoBoundingBox) -> None:
    print("=" * 65)
    print("SaagarDrishti -- Copernicus Marine Data Store Live Probe")
    print(f"Product ID   : {COPERNICUS_PRODUCT_ID}")
    print(f"Dataset ID   : {COPERNICUS_DATASET_ID}")
    print(f"Target BBox  : {bbox.min_latitude}°N-{bbox.max_latitude}°N, {bbox.min_longitude}°E-{bbox.max_longitude}°E")
    print("=" * 65)

    payload, telemetry = await adapter.fetch_live_subset(bbox=bbox)

    print(f"Status           : {telemetry.get('status')}")
    print(f"HTTP Status Code : {telemetry.get('http_status')}")
    print(f"Timestamp        : {telemetry.get('timestamp')}")

    if telemetry.get("status") == "CREDENTIALS_REQUIRED":
        print("\n[ACCESS REQUIREMENT & CREDENTIAL BLOCKER]")
        print(f"  Reason         : {telemetry.get('blocker_reason')}")
        print(f"  Auth Endpoint  : {telemetry.get('auth_endpoint')}")
        print(f"  Data Store     : {telemetry.get('data_store_endpoint')}")
        print("\nTo enable live Copernicus Marine downloads:")
        print("  1. Create a free account at https://data.marine.copernicus.eu/")
        print("  2. Set COPERNICUSMARINE_SERVICE_USERNAME and COPERNICUSMARINE_SERVICE_PASSWORD in backend/.env")
    elif telemetry.get("status") == "AUTHENTICATION_FAILED":
        print(f"\n[AUTHENTICATION FAILED] {telemetry.get('blocker_reason')}")
    elif telemetry.get("status") == "CONNECTION_ERROR":
        print(f"\n[CONNECTION ERROR] {telemetry.get('blocker_reason')}")
    else:
        print("\n[LIVE ACCESS GRANTED & AUTHENTICATED]")
        print(f"  Token type     : {telemetry.get('token_type')}")
        print(f"  Token validity : {telemetry.get('expires_in')} seconds")

        if payload is not None:
            summary = payload.area_summary
            meta = payload.metadata
            print(f"\n[LIVE DATA RETRIEVAL SUCCESSFUL -- {len(payload.grid_points)} FEATURES]")
            print(f"  Data Source    : {meta.data_format}")
            print(f"  Observation Date: {summary.observation_date}")
            print(f"  Valid Sea Cells: {summary.valid_cell_count}")
            print(f"  Land Cells     : {summary.land_masked_cell_count}")
            print(f"  Missing Cells  : {summary.missing_cell_count}")

            print("\n[RETRIEVED LIVE COASTAL GRID POINTS]")
            print(f"  {'Latitude':<10} {'Longitude':<10} {'Raw (K)':<12} {'Celsius':<10} {'Status'}")
            for pt in payload.grid_points:
                val_raw_str = f"{pt.value_raw:.2f}" if pt.value_raw is not None else "null"
                val_si_str = f"{pt.value_si:.2f} °C" if pt.value_si is not None else "N/A"
                status_str = "Land Masked" if pt.is_land_masked else "Valid Ocean"
                print(f"  {pt.coordinate.latitude:<10.2f} {pt.coordinate.longitude:<10.2f} {val_raw_str:<12} {val_si_str:<10} {status_str}")

            print("\n[STATISTICAL TEMPERATURE METRICS]")
            if summary.mean_value is not None:
                print(f"  Mean SST       : {summary.mean_value:.2f} °C")
                print(f"  Min SST        : {summary.min_value:.2f} °C")
                print(f"  Max SST        : {summary.max_value:.2f} °C")
                print(f"  Std Deviation  : {summary.std_dev:.2f} °C")
            if summary.regional_range_celsius is not None:
                print(f"  Regional Range : {summary.regional_range_celsius:.2f} °C")
            if summary.max_spatial_gradient_c_per_km is not None:
                print(f"  Max Gradient   : {summary.max_spatial_gradient_c_per_km:.4f} °C/km")
            print(f"  Thermal Front  : {'YES' if summary.thermal_front_detected else 'NO'}")

            print("\n[MANDATORY ECOLOGICAL GOVERNANCE NOTICE]")
            print(f"  {summary.ecological_disclaimer}")
        else:
            if "query_error" in telemetry:
                print(f"\n[DATA RETRIEVAL NOTICE] Authenticated successfully, but live feature query returned: {telemetry.get('query_error')}")


def run_local_analytics(adapter: OceanDataAdapter, file_path: Path) -> None:
    print("=" * 65)
    print("SaagarDrishti -- Copernicus Level-4 SST Ocean Analytics")
    print(f"Source file  : {file_path}")
    print("=" * 65)

    payload = adapter.parse_local_sample(file_path)
    meta = payload.metadata
    summary = payload.area_summary

    print("\n[DATASET SPECIFICATIONS & AUDITED PROVENANCE]")
    print(f"  Product ID         : {meta.product_id}")
    print(f"  Dataset ID         : {meta.dataset_id}")
    print(f"  Production Center  : {meta.production_center}")
    print(f"  Product Category   : {meta.product_category.value}")
    print(f"  Fixture Type       : {meta.fixture_type or 'MANUALLY_PREPARED_TEST_FIXTURE'}")
    print(f"  Real Live Download : {'YES' if meta.is_real_download else 'NO (Manually prepared test fixture)'}")
    print(f"  Spatial Resolution : {meta.spatial_resolution_deg}° (~5.5 km grid spacing)")
    print(f"  Temporal Cadence   : {meta.temporal_resolution}")
    print(f"  Format             : {meta.data_format}")
    print(f"  Usage Terms        : {meta.usage_terms}")
    print(f"  Observation Date   : {summary.observation_date}")
    print(f"  Data Is Stale (>72h): {'YES' if summary.is_stale else 'NO'}")

    print("\n[SPATIAL GRID SUMMARY]")
    print(f"  Valid Sea Cells    : {summary.valid_cell_count}")
    print(f"  Land Masked Cells  : {summary.land_masked_cell_count}")
    print(f"  Missing Cells      : {summary.missing_cell_count}")

    print("\n[STATISTICAL TEMPERATURE METRICS]")
    print(f"  Mean SST           : {summary.mean_value:.2f} °C")
    print(f"  Min SST            : {summary.min_value:.2f} °C")
    print(f"  Max SST            : {summary.max_value:.2f} °C")
    print(f"  Std Deviation      : {summary.std_dev:.2f} °C")
    if summary.regional_range_celsius is not None:
        print(f"  Regional SST Range : {summary.regional_range_celsius:.2f} °C (macro spread max-min)")
    if summary.mean_error is not None:
        print(f"  Mean Analysis Error: ±{summary.mean_error:.3f} K")

    print("\n[SPATIAL GRADIENT & THERMAL FRONT ANALYSIS]")
    print(f"  Evaluated Pairs    : {summary.evaluated_neighbor_pairs_count} (neighboring sea cells within radius)")
    if summary.max_spatial_gradient_c_per_km is not None:
        print(f"  Max Spatial Grad   : {summary.max_spatial_gradient_c_per_km:.4f} °C/km")
    if summary.mean_spatial_gradient_c_per_km is not None:
        print(f"  Mean Spatial Grad  : {summary.mean_spatial_gradient_c_per_km:.4f} °C/km")
    print(f"  Front Threshold    : {summary.thermal_front_threshold_c_per_km:.4f} °C/km")
    print(f"  Thermal Front Found: {'YES' if summary.thermal_front_detected else 'NO'}")

    print("\n[ANALYTICAL & GRADIENT NOTES]")
    for note in summary.gradient_notes:
        print(f"  - {note}")

    print("\n[MANDATORY ECOLOGICAL GOVERNANCE NOTICE]")
    print(f"  {summary.ecological_disclaimer}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Copernicus Ocean Analytics & SST Inspection for Karnataka Coast."
    )
    parser.add_argument("--local", action="store_true", help="Analyze verified local Copernicus SST sample fixture.")
    parser.add_argument("--file", type=str, help="Path to custom Copernicus SST JSON fixture file.")
    parser.add_argument("--live", action="store_true", help="Attempt live connection to Copernicus Marine Data Store.")
    parser.add_argument(
        "--bbox",
        nargs=4,
        type=float,
        metavar=("MIN_LAT", "MAX_LAT", "MIN_LON", "MAX_LON"),
        help="Custom bounding box coordinates.",
    )

    args = parser.parse_args()

    adapter = OceanDataAdapter()

    if args.bbox:
        target_bbox = GeoBoundingBox(
            min_latitude=args.bbox[0],
            max_latitude=args.bbox[1],
            min_longitude=args.bbox[2],
            max_longitude=args.bbox[3],
        )
    else:
        target_bbox = KARNATAKA_COASTAL_BBOX

    if args.live:
        asyncio.run(run_live_probe(adapter, target_bbox))
    else:
        target_file = Path(args.file) if args.file else SAMPLE_FIXTURE_PATH
        run_local_analytics(adapter, target_file)


if __name__ == "__main__":
    main()
