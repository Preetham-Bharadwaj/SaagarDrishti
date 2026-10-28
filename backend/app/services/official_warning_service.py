"""Service for ingesting, validating, and retrieving official government marine warnings.

Provides structured ingestion for official bulletins issued by the India
Meteorological Department (IMD) / Cyclone Warning Centre (CWC) and Karnataka
Fisheries Department.

Adheres to strict safety governance:
- Official government warnings represent statutory legal safety authority.
- Official warnings are maintained strictly separate from prototype numerical wave models.
- If official warnings conflict with numerical model outputs, the system explicitly
  highlights the discrepancy and defers to the official warning.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.schemas.official_warning import OfficialMarineWarning, OfficialWarningSeverity

logger = logging.getLogger(__name__)

# In-memory store for currently active official warning (session or cached)
_ACTIVE_OFFICIAL_WARNING: Optional[OfficialMarineWarning] = None


class OfficialWarningService:
    """Manages ingestion and lifecycle of official government marine bulletins."""

    @classmethod
    def get_active_warning(cls) -> Optional[OfficialMarineWarning]:
        """Retrieve the currently active official warning for the Karnataka coast."""
        global _ACTIVE_OFFICIAL_WARNING
        if _ACTIVE_OFFICIAL_WARNING is None:
            return None
        # Verify temporal validity
        now = datetime.now(timezone.utc)
        vt = (
            _ACTIVE_OFFICIAL_WARNING.valid_to
            if _ACTIVE_OFFICIAL_WARNING.valid_to.tzinfo
            else _ACTIVE_OFFICIAL_WARNING.valid_to.replace(tzinfo=timezone.utc)
        )
        if vt < now:
            logger.info("Active official warning %s has lapsed (valid until %s)", _ACTIVE_OFFICIAL_WARNING.bulletin_id, vt)
            return None
        return _ACTIVE_OFFICIAL_WARNING

    @classmethod
    def set_active_warning(cls, warning: Optional[OfficialMarineWarning]) -> None:
        """Register an active official warning in memory."""
        global _ACTIVE_OFFICIAL_WARNING
        _ACTIVE_OFFICIAL_WARNING = warning

    @classmethod
    def clear_active_warning(cls) -> None:
        """Clear the active official warning."""
        global _ACTIVE_OFFICIAL_WARNING
        _ACTIVE_OFFICIAL_WARNING = None

    @classmethod
    def parse_and_validate_dict(cls, data: Dict[str, Any]) -> Tuple[Optional[OfficialMarineWarning], List[str]]:
        """Parse and validate raw bulletin dictionary against OfficialMarineWarning schema.

        Args:
            data: Parsed dictionary from JSON or manual input.

        Returns:
            Tuple[Optional[OfficialMarineWarning], List[str]]: (Parsed warning or None, list of validation errors).
        """
        errors: List[str] = []

        required_keys = [
            "bulletin_id",
            "issuing_authority",
            "issued_at",
            "valid_from",
            "valid_to",
            "warning_text",
            "source_document",
        ]
        for key in required_keys:
            if not data.get(key):
                errors.append(f"Missing required bulletin field: '{key}'.")

        if errors:
            return None, errors

        try:
            warning = OfficialMarineWarning(**data)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"Schema validation error: {exc}")
            return None, errors

        # Validate date consistency
        vf = warning.valid_from if warning.valid_from.tzinfo else warning.valid_from.replace(tzinfo=timezone.utc)
        vt = warning.valid_to if warning.valid_to.tzinfo else warning.valid_to.replace(tzinfo=timezone.utc)
        ia = warning.issued_at if warning.issued_at.tzinfo else warning.issued_at.replace(tzinfo=timezone.utc)

        if vt <= vf:
            errors.append(f"Invalid timeline: 'valid_to' ({vt}) must be later than 'valid_from' ({vf}).")

        if vf < ia:
            errors.append(f"Invalid timeline: 'valid_from' ({vf}) cannot precede 'issued_at' ({ia}).")

        if errors:
            return None, errors

        return warning, []

    @classmethod
    def ingest_from_file(cls, file_path: Path) -> Tuple[Optional[OfficialMarineWarning], List[str]]:
        """Ingest and validate an official IMD bulletin from a verified local JSON file.

        Args:
            file_path: Path to the JSON bulletin file.

        Returns:
            Tuple[Optional[OfficialMarineWarning], List[str]]: (Validated warning, errors).
        """
        if not file_path.exists():
            return None, [f"Bulletin file does not exist: {file_path}"]

        try:
            with file_path.open("r", encoding="utf-8-sig") as f:
                data = json.load(f)
        except Exception as exc:  # noqa: BLE001
            return None, [f"Failed to read or parse JSON from {file_path}: {exc}"]

        warning, errors = cls.parse_and_validate_dict(data)
        if warning and not errors:
            cls.set_active_warning(warning)
            logger.info("Successfully ingested official bulletin %s from %s", warning.bulletin_id, file_path)

        return warning, errors
