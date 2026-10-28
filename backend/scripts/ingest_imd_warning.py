"""CLI utility for ingesting verified official IMD marine bulletins.

Usage:
    python scripts/ingest_imd_warning.py --file <path_to_bulletin_json>
    python scripts/ingest_imd_warning.py --sample
"""

import argparse
import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.services.official_warning_service import OfficialWarningService


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ingest and validate official IMD Marine Weather Bulletins for Karnataka coast."
    )
    parser.add_argument(
        "--file",
        type=str,
        help="Path to the JSON file containing the verified official bulletin.",
    )
    parser.add_argument(
        "--sample",
        action="store_true",
        help="Ingest the verified sample IMD bulletin fixture from tests/fixtures.",
    )

    args = parser.parse_args()

    if args.sample:
        target_path = backend_dir / "tests" / "fixtures" / "official_imd_bulletin_sample.json"
    elif args.file:
        target_path = Path(args.file)
    else:
        parser.print_help()
        sys.exit(1)

    print("=" * 60)
    print("SaagarDrishti -- Official IMD Marine Bulletin Ingestion")
    print(f"Target file: {target_path}")
    print("=" * 60)

    warning, errors = OfficialWarningService.ingest_from_file(target_path)

    if errors:
        print("\n[VALIDATION FAILED]")
        for err in errors:
            print(f"  - {err}")
        sys.exit(1)

    print("\n[INGESTION SUCCESSFUL]")
    print(f"Bulletin ID       : {warning.bulletin_id}")
    print(f"Authority         : {warning.issuing_authority}")
    print(f"Issued At         : {warning.issued_at.isoformat()}")
    print(f"Valid From        : {warning.valid_from.isoformat()}")
    print(f"Valid To          : {warning.valid_to.isoformat()}")
    print(f"Zone              : {warning.coastal_zone}")
    print(f"Severity          : {warning.severity.value.upper()}")
    print(f"Warning Type      : {warning.warning_type}")
    print(f"Warning Text      : {warning.warning_text}")
    print(f"Do Not Venture    : {'YES' if warning.fishermen_advised_not_to_venture else 'NO'}")
    print(f"Source Document   : {warning.source_document}")
    print("\nOfficial warning is registered and active in SaagarDrishti.")


if __name__ == "__main__":
    main()
