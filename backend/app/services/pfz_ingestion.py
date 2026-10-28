"""Service for ingesting, validating, and parsing Potential Fishing Zone (PFZ) advisories."""

from datetime import datetime, timezone
import logging
from pathlib import Path
from typing import List, Optional, Set, Tuple, Union

from app.adapters.incois import INCOISAdapter
from app.geo.coordinates import is_within_karnataka_coast
from app.schemas.pfz import PFZAdvisoryPayload, PFZValidationResult

logger = logging.getLogger(__name__)


class PFZIngestionService:
    """Service to ingest, validate, and report on PFZ advisory payloads."""

    @staticmethod
    def validate_advisory(
        payload: PFZAdvisoryPayload, as_of: Optional[datetime] = None
    ) -> PFZValidationResult:
        """Validate an ingested PFZ advisory document against domain rules.

        Validation rules:
        1. Date validation: Checks for missing dates and timeline ordering.
        2. Expiration check: Flags whether advisory validity has lapsed.
        3. Empty items check: Requires at least one advisory hotspot.
        4. Coordinate checks: Validates geographic ranges and Karnataka coastal boundaries.
        5. Duplicate detection: Flags repeated item IDs or duplicate landing center targets.
        6. Operational quality: Audits inactive statuses and attaches quality limitations.

        Args:
            payload: Typed PFZ advisory payload.
            as_of: Optional reference timestamp (defaults to current UTC time).

        Returns:
            PFZValidationResult: Comprehensive validation outcome.
        """
        errors: List[str] = []
        warnings: List[str] = []
        data_quality_notes: List[str] = list(payload.quality_limitations)

        now = as_of or datetime.now(timezone.utc)
        is_expired = False

        # 1. Date Validation
        if payload.valid_from is None or payload.valid_to is None:
            errors.append("Missing advisory validity timeline: 'valid_from' and 'valid_to' dates are required.")
        else:
            if payload.valid_to <= payload.valid_from:
                errors.append("Invalid advisory timeline: 'valid_to' must be strictly after 'valid_from'.")

            # 2. Expiration Check
            # Ensure timezone-aware comparison
            valid_to_dt = payload.valid_to
            if valid_to_dt.tzinfo is None:
                valid_to_dt = valid_to_dt.replace(tzinfo=timezone.utc)
            if now.tzinfo is None:
                now = now.replace(tzinfo=timezone.utc)

            if valid_to_dt < now:
                is_expired = True
                warnings.append(
                    f"Advisory is expired (validity ended on {valid_to_dt.strftime('%Y-%m-%d %H:%M UTC')})."
                )

        # 3. Item count check
        if not payload.items:
            errors.append("Advisory payload contains no advisory items or hotspots.")

        # 4. Item-level validation & Duplicate Detection
        seen_item_ids: Set[str] = set()
        seen_targets: Set[Tuple[str, Optional[float], Optional[float]]] = set()
        duplicate_count = 0
        valid_items_count = 0

        for idx, item in enumerate(payload.items):
            item_has_error = False

            # Duplicate check
            target_signature = (
                item.landing_center.lower(),
                item.direction_bearing_deg,
                item.distance_km,
            )
            if item.item_id in seen_item_ids:
                duplicate_count += 1
                warnings.append(f"Duplicate advisory record detected for item_id '{item.item_id}'.")
            elif target_signature in seen_targets and item.direction_bearing_deg is not None:
                duplicate_count += 1
                warnings.append(
                    f"Duplicate hotspot target detected: Landing center '{item.landing_center}', "
                    f"bearing {item.direction_bearing_deg}°, distance {item.distance_km} km."
                )
            else:
                seen_item_ids.add(item.item_id)
                seen_targets.add(target_signature)

            # Coordinate validation
            if item.coordinate is None:
                errors.append(f"Item '{item.item_id}' (index {idx}) is missing geographic coordinates.")
                item_has_error = True
            else:
                lat = item.coordinate.latitude
                lon = item.coordinate.longitude

                # Check numerical coordinate limits
                if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
                    errors.append(
                        f"Item '{item.item_id}' has invalid coordinates: Lat {lat}, Lon {lon}."
                    )
                    item_has_error = True
                elif not is_within_karnataka_coast(item.coordinate):
                    # Outside Karnataka BBox is a regional warning, not a fatal crash
                    warnings.append(
                        f"Item '{item.item_id}' coordinate ({lat:.4f}°N, {lon:.4f}°E) lies outside "
                        "expected Karnataka coastal bounding box."
                    )

            # Operational status audit
            if item.status and item.status.upper() not in ("YES", "ACTIVE", "1"):
                warnings.append(
                    f"Item '{item.item_id}' for landing center '{item.landing_center}' has status '{item.status}' (inactive)."
                )

            if not item_has_error:
                valid_items_count += 1

        is_valid = len(errors) == 0

        return PFZValidationResult(
            advisory_id=payload.advisory_id,
            is_valid=is_valid,
            is_expired=is_expired,
            total_items=len(payload.items),
            valid_items_count=valid_items_count if is_valid else 0,
            duplicate_items_count=duplicate_count,
            errors=errors,
            warnings=warnings,
            data_quality_notes=data_quality_notes,
        )

    @classmethod
    def ingest_from_file(
        cls, file_path: Union[str, Path], as_of: Optional[datetime] = None
    ) -> Tuple[PFZAdvisoryPayload, PFZValidationResult]:
        """Ingest and validate an authorized local INCOIS advisory file.

        Args:
            file_path: Local path to GeoJSON/JSON advisory file.
            as_of: Optional reference time for expiration evaluation.

        Returns:
            Tuple[PFZAdvisoryPayload, PFZValidationResult]: Parsed payload and validation report.
        """
        adapter = INCOISAdapter()
        payload = adapter.parse_file(file_path)
        validation_result = cls.validate_advisory(payload, as_of=as_of)
        return payload, validation_result

    @classmethod
    async def ingest_from_adapter(
        cls,
        adapter: Optional[INCOISAdapter] = None,
        as_of: Optional[datetime] = None,
    ) -> Tuple[PFZAdvisoryPayload, PFZValidationResult]:
        """Fetch latest Karnataka PFZ advisory from INCOIS and execute validation.

        Args:
            adapter: Optional INCOIS adapter instance.
            as_of: Optional reference time for expiration evaluation.

        Returns:
            Tuple[PFZAdvisoryPayload, PFZValidationResult]: Parsed payload and validation report.
        """
        resolved_adapter = adapter or INCOISAdapter()
        payload = await resolved_adapter.fetch_karnataka_pfz_advisory()
        validation_result = cls.validate_advisory(payload, as_of=as_of)
        return payload, validation_result
