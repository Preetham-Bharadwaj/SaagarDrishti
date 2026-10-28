"""Command-line ingestion tool for Karnataka Potential Fishing Zone (PFZ) advisories.

Usage on Windows:
    # Ingest local sample fixture (offline/safe mode):
    python scripts/ingest_karnataka_pfz.py --file tests/fixtures/incois_karnataka_sample.json

    # Attempt live acquisition from official INCOIS WFS server:
    python scripts/ingest_karnataka_pfz.py --live
"""

import argparse
import asyncio
from datetime import datetime, timezone
from pathlib import Path
import sys

# Ensure backend root is on sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.adapters.incois import INCOISAdapter
from app.services.pfz_ingestion import PFZIngestionService


async def main_async(args: argparse.Namespace) -> None:
    print("=" * 70)
    print(" SaagarDrishti: Karnataka PFZ Advisory Ingestion Tool")
    print("=" * 70)

    adapter = INCOISAdapter()

    if args.file:
        file_path = Path(args.file)
        print(f"\n[Mode] Ingesting from local authorized file: {file_path}")
        if not file_path.exists():
            print(f"[Error] File not found: {file_path}")
            sys.exit(1)
        payload, result = PFZIngestionService.ingest_from_file(file_path)
    else:
        print("\n[Mode] Attempting live acquisition from official INCOIS GeoServer WFS...")
        try:
            payload, result = await PFZIngestionService.ingest_from_adapter(adapter)
            print("[Success] Received WFS response from INCOIS (Layer: LandingCenters_29Apr2024).")
        except Exception as exc:
            print(f"[Warning] Live fetch failed ({exc}).")
            default_fixture = backend_dir / "tests" / "fixtures" / "incois_karnataka_sample.json"
            print(f"[Fallback] Falling back to verified local fixture: {default_fixture}")
            payload, result = PFZIngestionService.ingest_from_file(default_fixture)

    print("\n--- Advisory Summary ---")
    print(f"Advisory ID:      {payload.advisory_id}")
    print(f"Source:           {payload.source}")
    print(f"Source URL:       {payload.source_url or 'N/A'}")
    print(f"Region:           {payload.region} (Sector: {payload.sector_id})")
    print(f"Data Category:    Landing-Centre Spatial Reference (with historical advisory attributes)")
    print(f"Retrieved At:     {payload.retrieved_at.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"Issued At:        {payload.issued_at.strftime('%Y-%m-%d %H:%M:%S UTC') if payload.issued_at else 'N/A'}")
    print(f"Validity Start:   {payload.valid_from.strftime('%Y-%m-%d %H:%M:%S UTC') if payload.valid_from else 'N/A'}")
    print(f"Validity End:     {payload.valid_to.strftime('%Y-%m-%d %H:%M:%S UTC') if payload.valid_to else 'N/A'}")


    print("\n--- Validation Audit ---")
    print(f"Valid Structure:  {'PASSED' if result.is_valid else 'FAILED'}")
    print(f"Validity Status:  {'EXPIRED' if result.is_expired else 'ACTIVE'}")
    print(f"Total Hotspots:   {result.total_items}")
    print(f"Valid Items:      {result.valid_items_count}")
    print(f"Duplicates Found: {result.duplicate_items_count}")

    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except AttributeError:
            pass

    if result.errors:
        print("\n[Errors]")
        for err in result.errors:
            print(f"  [ERROR] {err}")

    if result.warnings:
        print("\n[Warnings]")
        for warn in result.warnings:
            print(f"  [WARN]  {warn}")

    print("\n--- Hotspot Details (First 5 records) ---")
    for idx, item in enumerate(payload.items[:5], 1):
        dist_str = f"{item.distance_km} km" if item.distance_km is not None else "N/A"
        bearing_str = f"{item.direction_bearing_deg} deg ({item.direction_compass or 'N/A'})"
        depth_str = f"{item.depth_m} m" if item.depth_m is not None else "N/A"
        print(
            f"  {idx}. [{item.item_id}] Landing Center: {item.landing_center} ({item.district or 'N/A'})"
        )
        print(
            f"     PFZ Hotspot: {item.coordinate.latitude:.4f} N, {item.coordinate.longitude:.4f} E | "
            f"Bearing: {bearing_str} | Distance: {dist_str} | Depth: {depth_str} | Status: {item.status}"
        )

    print("\n--- Data-Quality Limitations ---")
    for note in result.data_quality_notes:
        print(f"  - {note}")

    print("\n" + "=" * 70)


def main():
    parser = argparse.ArgumentParser(
        description="Ingest and validate INCOIS PFZ advisory data for Karnataka coast."
    )
    parser.add_argument(
        "--file",
        type=str,
        default=None,
        help="Path to local GeoJSON / JSON file downloaded from INCOIS.",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Attempt live retrieval from INCOIS GeoServer WFS endpoint.",
    )
    args = parser.parse_args()
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
