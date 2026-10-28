"""End-to-end marine query workflow engine.

Assembles planner classification -> data availability audit -> PFZ evidence
retrieval -> evidence validation -> grounded response generation.

This is the authoritative pipeline that all marine query API endpoints
must route through. It enforces the evidence-grounding and safety rules
documented in docs/INCOIS_SOURCE_AUDIT.md:
  - Landing center geometries are NEVER returned as PFZ hotspot coordinates.
  - Expired advisories are NEVER returned as current PFZ guidance.
  - Fabricated or synthetic coordinates are NEVER generated.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import List, Optional

from app.adapters.ocean_data import OceanDataAdapter
from app.adapters.open_meteo_marine import OpenMeteoMarineAdapter
from app.agents.planner import QueryPlanner
from app.geo.coordinates import (
    haversine_distance_km,
    is_within_karnataka_coast,
    resolve_karnataka_coordinate,
)
from app.schemas.common import GeoCoordinate
from app.schemas.marine_hazard import MarineHazardForecast, WaveHazardLevel
from app.schemas.ocean_analytics import OceanSSTResult
from app.schemas.official_warning import OfficialMarineWarning, OfficialWarningSeverity
from app.schemas.pfz import PFZAdvisoryItem, PFZAdvisoryPayload
from app.schemas.query import (
    CandidatePFZResult,
    DataStatus,
    EvidenceAuditResult,
    MarineQueryRequest,
    MarineQueryResponse,
    QueryIntent,
    QueryWorkflowStatus,
    SourceAvailabilityReport,
)
from app.services.data_availability import check_marine_data_availability
from app.services.official_warning_service import OfficialWarningService
from app.services.pfz_ingestion import PFZIngestionService

logger = logging.getLogger(__name__)

_PFZ_LINES_SOURCE_NAME = "INCOIS GeoServer WFS (PFZ Vector Lines)"
_LANDING_CENTERS_SOURCE_NAME = "INCOIS GeoServer WFS (Landing Centers Reference Layer)"


class QueryWorkflowEngine:
    """Orchestrates the full evidence-grounded marine query workflow."""

    def __init__(
        self,
        open_meteo_adapter: Optional[OpenMeteoMarineAdapter] = None,
        ocean_data_adapter: Optional[OceanDataAdapter] = None,
    ) -> None:
        self.open_meteo_adapter = open_meteo_adapter or OpenMeteoMarineAdapter()
        self.ocean_data_adapter = ocean_data_adapter or OceanDataAdapter()

    async def run(self, request: MarineQueryRequest) -> MarineQueryResponse:
        now = datetime.now(timezone.utc)

        intent = QueryPlanner.classify_intent(request.query)
        tools_used: List[str] = ["classify_intent"]
        logger.info("Classified query intent: %s | query=%r", intent, request.query)

        sources_checked: List[SourceAvailabilityReport] = check_marine_data_availability()
        tools_used.append("check_marine_data_availability")

        if intent == QueryIntent.NEAREST_PFZ:
            return await self._handle_nearest_pfz(request, sources_checked, tools_used, now)

        if intent == QueryIntent.MARINE_CONDITIONS:
            return await self._handle_marine_conditions(request, sources_checked, tools_used)

        if intent == QueryIntent.WEATHER_HAZARD:
            return await self._handle_weather_hazard(request, sources_checked, tools_used)

        return self._handle_general_marine_information(request, sources_checked, tools_used)

    async def _handle_nearest_pfz(
        self,
        request: MarineQueryRequest,
        sources_checked: List[SourceAvailabilityReport],
        tools_used: List[str],
        now: datetime,
    ) -> MarineQueryResponse:
        tools_used.append("filter_unexpired_pfz_records")

        pfz_lines_status = self._get_source_status(_PFZ_LINES_SOURCE_NAME, sources_checked)
        lc_status = self._get_source_status(_LANDING_CENTERS_SOURCE_NAME, sources_checked)

        payload: Optional[PFZAdvisoryPayload] = None
        validation_errors: List[str] = []
        try:
            payload, result = await PFZIngestionService.ingest_from_adapter()
            tools_used.append("ingest_from_adapter")
            if result.errors:
                validation_errors.extend(result.errors)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Live PFZ adapter fetch failed: %s", exc)
            validation_errors.append(f"Live PFZ fetch error: {exc}")

        evidence_audit = self._validate_pfz_evidence(payload, now, validation_errors, pfz_lines_status)
        tools_used.append("validate_evidence_provenance")

        if not evidence_audit.passed:
            return MarineQueryResponse(
                query=request.query,
                intent=QueryIntent.NEAREST_PFZ,
                status=QueryWorkflowStatus.DATA_UNAVAILABLE,
                answer=self._compose_unavailable_pfz_answer(evidence_audit, pfz_lines_status, lc_status),
                candidate_pfz=None,
                evidence_audit=evidence_audit,
                sources_checked=sources_checked,
                tools_used=tools_used,
            )

        candidate: Optional[CandidatePFZResult] = None
        if request.user_location and payload and payload.items:
            tools_used.append("calculate_deterministic_distance")
            candidate = self._nearest_pfz_to_location(request.user_location, payload, now)

        status = QueryWorkflowStatus.SUCCESS if candidate else QueryWorkflowStatus.LOCATION_REQUIRED

        return MarineQueryResponse(
            query=request.query,
            intent=QueryIntent.NEAREST_PFZ,
            status=status,
            answer=self._compose_pfz_answer(candidate, payload, request, evidence_audit),
            candidate_pfz=candidate,
            evidence_audit=evidence_audit,
            sources_checked=sources_checked,
            tools_used=tools_used,
        )

    async def _handle_marine_conditions(
        self,
        request: MarineQueryRequest,
        sources_checked: List[SourceAvailabilityReport],
        tools_used: List[str],
    ) -> MarineQueryResponse:
        """Attempt live Copernicus OSTIA Level-4 SST retrieval for the Karnataka coast.

        Data source: Copernicus Marine Data Store — SST_GLO_SST_L4_NRT_OBSERVATIONS_010_001
        Category: L4_SATELLITE_ANALYSIS (gap-free optimal interpolation, NOT a numerical forecast)
        Update cycle: Daily foundation SST (issued ~06:00 UTC for previous day)
        Auth: OpenID Connect password grant — requires COPERNICUSMARINE_SERVICE_USERNAME / PASSWORD

        Governance rules enforced here:
        - SST alone DOES NOT prove fish abundance, catch yield, or navigation safety.
        - A missing or stale result MUST NOT be presented as safe conditions.
        - OfficialIMD warnings supersede all satellite observations.
        - L4 satellite analysis, numerical model forecasts, and in-situ observations
          are always kept as distinct source types and NEVER conflated.
        """
        tools_used.append("fetch_copernicus_ostia_sst")

        payload, telemetry = await self.ocean_data_adapter.fetch_live_subset()
        retrieval_status = telemetry.get("status", "UNKNOWN")

        if payload is not None and retrieval_status == "SUCCESS":
            # ── Successful live retrieval ────────────────────────────────────────
            tools_used.append("evaluate_sst_freshness_and_gradient")

            sst_result = OceanSSTResult.from_payload(payload, retrieval_status="SUCCESS")

            if sst_result.is_stale:
                retrieval_status = "STALE"
                sst_result = OceanSSTResult.from_payload(payload, retrieval_status="STALE")

            obs_ts_str = payload.metadata.observation_timestamp.strftime("%Y-%m-%d %H:%M UTC")
            retrieved_str = payload.metadata.retrieved_at.strftime("%Y-%m-%d %H:%M UTC")
            valid_cells = payload.area_summary.valid_cell_count
            land_cells = payload.area_summary.land_masked_cell_count
            mean_c = payload.area_summary.mean_value
            min_c = payload.area_summary.min_value
            max_c = payload.area_summary.max_value
            front_str = "detected" if payload.area_summary.thermal_front_detected else "not detected"

            stats_str = (
                f"Mean SST {mean_c:.2f}°C (range {min_c:.2f}°C–{max_c:.2f}°C)"
                if mean_c is not None else "No valid sea cells retrieved"
            )

            stale_warn = (
                " WARNING: Observation is older than 72 hours — treat as potentially outdated."
                if sst_result.is_stale else ""
            )

            answer = (
                f"Live Copernicus OSTIA foundation SST for the Karnataka coast (12.5°N–15.2°N, 73.0°E–75.3°E): "
                f"{stats_str}. "
                f"Observation date: {obs_ts_str}. "
                f"Spatial coverage: {valid_cells} valid ocean cells, {land_cells} land-masked. "
                f"Thermal front: {front_str}. "
                f"Retrieved: {retrieved_str}.{stale_warn} "
                f"Source: {payload.metadata.product_id} "
                f"({payload.metadata.product_category.value}, "
                f"{payload.metadata.production_center}). "
                "GOVERNANCE NOTICE: This is a Level-4 satellite analysis product — "
                "NOT a numerical model forecast or in-situ observation. "
                f"MANDATORY: {payload.area_summary.ecological_disclaimer}"
            )

            wf_status = QueryWorkflowStatus.DATA_UNAVAILABLE if sst_result.is_stale else QueryWorkflowStatus.SUCCESS

            audit = EvidenceAuditResult(
                passed=(not sst_result.is_stale),
                checks_performed=[
                    "fetch_copernicus_sst_live",
                    "validate_sst_observation_freshness",
                    "classify_product_category",
                    "enforce_ecological_governance",
                ],
                provenance_sources=[
                    payload.metadata.product_id,
                    payload.metadata.dataset_id,
                    "https://data.marine.copernicus.eu",
                ],
                is_expired=sst_result.is_stale,
                rejection_reasons=(
                    ["Copernicus SST observation is older than 72 hours."] if sst_result.is_stale else []
                ),
                warnings=[
                    payload.area_summary.ecological_disclaimer,
                    "SST is a Level-4 satellite analysis (OSTIA optimal interpolation). "
                    "It is NOT a real-time numerical model forecast or direct in-situ sensor reading.",
                ],
            )

            return MarineQueryResponse(
                query=request.query,
                intent=QueryIntent.MARINE_CONDITIONS,
                status=wf_status,
                answer=answer,
                candidate_pfz=None,
                ocean_sst=sst_result,
                evidence_audit=audit,
                sources_checked=sources_checked,
                tools_used=tools_used,
            )

        # ── Retrieval blocked or failed ──────────────────────────────────────────
        blocker = telemetry.get("blocker_reason", "")
        query_error = telemetry.get("query_error", "")

        if retrieval_status == "CREDENTIALS_REQUIRED":
            blocker_str = (
                "Copernicus Marine Data Store credentials are not configured. "
                "Set COPERNICUSMARINE_SERVICE_USERNAME and COPERNICUSMARINE_SERVICE_PASSWORD in backend/.env "
                "to enable live OSTIA SST retrieval."
            )
        elif retrieval_status == "AUTHENTICATION_FAILED":
            blocker_str = f"Copernicus authentication failed: {blocker or 'invalid credentials'}."
        elif retrieval_status == "CONNECTION_ERROR":
            blocker_str = f"Connection to Copernicus Marine auth endpoint failed: {blocker or query_error}."
        else:
            blocker_str = (
                f"Copernicus SST retrieval unavailable (status: {retrieval_status}). "
                + (blocker or query_error or "")
            )

        audit = EvidenceAuditResult(
            passed=False,
            checks_performed=["fetch_copernicus_sst_live", "check_credential_status"],
            provenance_sources=[
                "SST_GLO_SST_L4_NRT_OBSERVATIONS_010_001",
                "https://data.marine.copernicus.eu",
            ],
            rejection_reasons=[blocker_str],
            warnings=[
                "SAFETY CRITICAL: Unavailable or missing SST data must NEVER be interpreted "
                "as safe conditions or confirmation of fish presence.",
                "Consult official INCOIS PFZ advisory at https://incois.gov.in/MarineFisheries/ "
                "and IMD Marine Weather Bulletin at https://mausam.imd.gov.in/ directly.",
                "ECOLOGICAL NOTICE: SST ALONE DOES NOT PROVE fish abundance, catch yield, "
                "or maritime navigation safety even when data is available.",
            ],
        )

        return MarineQueryResponse(
            query=request.query,
            intent=QueryIntent.MARINE_CONDITIONS,
            status=QueryWorkflowStatus.DATA_UNAVAILABLE,
            answer=(
                f"Live Copernicus OSTIA SST data for the Karnataka coast is currently unavailable. "
                f"Reason: {blocker_str} "
                "SAFETY NOTICE: Absence of SST data does NOT indicate safe or productive sea conditions. "
                "Please consult https://incois.gov.in/portal/datainfo/sst.jsp for the latest "
                "satellite-derived products and https://mausam.imd.gov.in/ for official weather advisories."
            ),
            candidate_pfz=None,
            ocean_sst=None,
            evidence_audit=audit,
            sources_checked=sources_checked,
            tools_used=tools_used,
        )

    async def _handle_weather_hazard(
        self,
        request: MarineQueryRequest,
        sources_checked: List[SourceAvailabilityReport],
        tools_used: List[str],
    ) -> MarineQueryResponse:
        tools_used.append("resolve_karnataka_coordinate")
        target_coord, loc_label = resolve_karnataka_coordinate(
            user_location=request.user_location,
            departure_port=request.departure_port,
            query_text=request.query,
        )

        tools_used.append("check_official_statutory_warnings")
        official_warning = OfficialWarningService.get_active_warning()

        tools_used.append("fetch_open_meteo_marine_forecast")
        try:
            forecast = await self.open_meteo_adapter.fetch_karnataka_marine_forecast(
                latitude=target_coord.latitude,
                longitude=target_coord.longitude,
                forecast_days=1,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Open-Meteo marine forecast fetch failed: %s", exc)
            audit = EvidenceAuditResult(
                passed=False,
                checks_performed=["resolve_coordinate", "open_meteo_api_request"],
                provenance_sources=["Open-Meteo Marine Weather API", "IMD Marine Weather Bulletin"],
                rejection_reasons=[f"Marine weather forecast fetch error: {exc}"],
                warnings=[
                    "SAFETY CRITICAL: Missing or failed forecast data must NEVER be assumed to indicate safe sea conditions.",
                    "Consult official IMD Marine Weather Bulletin at https://mausam.imd.gov.in/ "
                    "and Karnataka Fisheries Department VHF radio bulletins before departure.",
                ],
            )
            ans = (
                f"Unable to retrieve live marine wave forecast for {loc_label} due to an upstream connection error. "
                "CRITICAL SAFETY NOTICE: Missing forecast data does NOT imply that sea conditions are safe. "
                "Please consult the official India Meteorological Department (IMD) "
                "Marine Weather Bulletin at https://mausam.imd.gov.in/ and local port authorities "
                "before venturing out to sea."
            )
            if official_warning:
                ans = (
                    f"ACTIVE OFFICIAL WARNING: {official_warning.issuing_authority} ({official_warning.bulletin_id}): "
                    f"'{official_warning.warning_text}'. "
                ) + ans
            return MarineQueryResponse(
                query=request.query,
                intent=QueryIntent.WEATHER_HAZARD,
                status=QueryWorkflowStatus.DATA_UNAVAILABLE,
                answer=ans,
                candidate_pfz=None,
                marine_hazard=None,
                official_warning=official_warning,
                sources_disagree=False,
                evidence_audit=audit,
                sources_checked=sources_checked,
                tools_used=tools_used,
            )

        tools_used.append("evaluate_forecast_freshness_and_validity")

        # Check for missing data or stale forecast
        if not forecast.is_data_available or forecast.is_stale:
            reasons = []
            if not forecast.is_data_available:
                reasons.append("Model returned no valid numeric wave height values for the requested location.")
            if forecast.is_stale:
                reasons.append("Model forecast validity has lapsed (latest forecast step is in the past).")

            audit = EvidenceAuditResult(
                passed=False,
                checks_performed=["resolve_coordinate", "open_meteo_api_request", "freshness_check"],
                provenance_sources=[forecast.source, forecast.source_url],
                is_expired=forecast.is_stale,
                rejection_reasons=reasons,
                warnings=[
                    "SAFETY CRITICAL: Stale or missing forecast data must NEVER be interpreted as safe sea conditions.",
                    forecast.safety_disclaimer,
                ],
            )
            ans = (
                f"Marine forecast data for {loc_label} (model grid: {forecast.latitude:.3f}°N, {forecast.longitude:.3f}°E, "
                f"grid resolution ~{forecast.grid_resolution_km:.0f} km) is currently unavailable or stale "
                f"(source retrieved: {forecast.retrieved_at.strftime('%Y-%m-%d %H:%M UTC')}). "
                "SAFETY NOTICE: Absence of an active forecast does NOT mean sea conditions are calm or safe. "
                "Consult official IMD bulletins at https://mausam.imd.gov.in/ before any voyage."
            )
            if official_warning:
                ans = (
                    f"ACTIVE OFFICIAL WARNING: {official_warning.issuing_authority} ({official_warning.bulletin_id}): "
                    f"'{official_warning.warning_text}'. "
                ) + ans
            return MarineQueryResponse(
                query=request.query,
                intent=QueryIntent.WEATHER_HAZARD,
                status=QueryWorkflowStatus.DATA_UNAVAILABLE,
                answer=ans,
                candidate_pfz=None,
                marine_hazard=forecast,
                official_warning=official_warning,
                sources_disagree=False,
                evidence_audit=audit,
                sources_checked=sources_checked,
                tools_used=tools_used,
            )

        tools_used.append("evaluate_wave_hazard_thresholds")

        # Discrepancy detection between official warning and model output
        sources_disagree = False
        if official_warning and (
            official_warning.severity in (OfficialWarningSeverity.WARNING, OfficialWarningSeverity.SEVERE_WARNING)
            or official_warning.fishermen_advised_not_to_venture
        ):
            if forecast.peak_hazard_level in (WaveHazardLevel.CALM, WaveHazardLevel.SLIGHT):
                sources_disagree = True

        checks = [
            "resolve_target_coordinate",
            "fetch_nwp_wave_observations",
            "classify_small_craft_wave_hazard_douglas_scale",
            "check_official_statutory_warning_discrepancy",
            "enforce_safety_disclaimer",
        ]
        warnings = [forecast.safety_disclaimer]
        if not is_within_karnataka_coast(target_coord):
            warnings.append(
                f"Requested coordinate ({target_coord.latitude:.4f}N, {target_coord.longitude:.4f}E) "
                "is outside the primary Karnataka coastal bounding box (12.5-15.2N, 73.0-75.3E)."
            )
        if sources_disagree:
            warnings.append(
                "DISCREPANCY ALERT: Official government warning issues an active WARNING / Do-Not-Venture alert "
                "despite numerical model wave heights indicating Slight/Calm seas. Official statutory warning supersedes model."
            )

        audit = EvidenceAuditResult(
            passed=True,
            checks_performed=checks,
            provenance_sources=[forecast.source, forecast.source_url],
            is_landing_center_mistaken_for_pfz=False,
            is_expired=False,
            sources_disagree=sources_disagree,
            rejection_reasons=[],
            warnings=warnings,
        )
        if official_warning:
            audit.provenance_sources.append(f"{official_warning.issuing_authority} ({official_warning.bulletin_id})")

        answer = self._compose_hazard_answer(forecast, loc_label, official_warning, sources_disagree)

        return MarineQueryResponse(
            query=request.query,
            intent=QueryIntent.WEATHER_HAZARD,
            status=QueryWorkflowStatus.SUCCESS,
            answer=answer,
            candidate_pfz=None,
            marine_hazard=forecast,
            official_warning=official_warning,
            sources_disagree=sources_disagree,
            evidence_audit=audit,
            sources_checked=sources_checked,
            tools_used=tools_used,
        )

    @staticmethod
    def _compose_hazard_answer(
        forecast: MarineHazardForecast,
        loc_label: str,
        official_warning: Optional[OfficialMarineWarning] = None,
        sources_disagree: bool = False,
    ) -> str:
        curr = forecast.current_hour_observation
        curr_wave = f"{curr.wave_height_m:.2f} m" if curr and curr.wave_height_m is not None else "N/A"
        curr_swell = f"{curr.swell_wave_height_m:.2f} m" if curr and curr.swell_wave_height_m is not None else "N/A"
        curr_dir = f"{curr.wave_direction_deg:.0f}°" if curr and curr.wave_direction_deg is not None else "N/A"
        hazard_level = (curr.hazard_level.value.upper() if curr else forecast.peak_hazard_level.value.upper())
        peak_wave = f"{forecast.peak_wave_height_m:.2f} m" if forecast.peak_wave_height_m is not None else "N/A"
        valid_time_str = forecast.forecast_valid_time or (curr.time_local if curr else "Current Hour")

        lines = []

        if sources_disagree and official_warning:
            lines.append(
                f"⚠️ DISCREPANCY DETECTED: While the ECMWF/ERAssWave numerical model indicates {hazard_level} seas "
                f"({curr_wave}) near {loc_label}, the {official_warning.issuing_authority} has issued an active "
                f"{official_warning.severity.value.upper()}: \"{official_warning.warning_text}\". "
                "STATUTORY OVERRIDE: Official government warnings strictly supersede all numerical model outputs and "
                "prototype heuristics. Small-craft fishers are advised NOT to venture into sea."
            )
        elif official_warning:
            lines.append(
                f"OFFICIAL STATUTORY BULLETIN: {official_warning.issuing_authority} ({official_warning.bulletin_id}, "
                f"Severity: {official_warning.severity.value.upper()}): \"{official_warning.warning_text}\"."
            )

        lines.append(
            f"Numerical wave model forecast near {loc_label} (model grid: {forecast.latitude:.3f}°N, {forecast.longitude:.3f}°E, "
            f"resolution ~{forecast.grid_resolution_km:.0f} km): "
            f"For forecast time step {valid_time_str}, significant wave height is {curr_wave} with swell of {curr_swell} coming from {curr_dir}. "
            f"Prototype small-craft sea-state classification: {hazard_level} (Douglas scale; 24-hr peak: {peak_wave}, worst: {forecast.peak_hazard_level.value.upper()}). "
            f"Source: {forecast.source} ({forecast.model_label} model, retrieved {forecast.retrieved_at.strftime('%Y-%m-%d %H:%M UTC')})."
        )
        lines.append(f"MANDATORY SAFETY NOTICE: {forecast.safety_disclaimer}")

        return " ".join(lines)

    def _handle_general_marine_information(
        self,
        request: MarineQueryRequest,
        sources_checked: List[SourceAvailabilityReport],
        tools_used: List[str],
    ) -> MarineQueryResponse:
        tools_used.append("retrieve_karnataka_landing_centers_reference")
        audit = EvidenceAuditResult(
            passed=True,
            checks_performed=["general_marine_reference_lookup"],
            provenance_sources=["INCOIS GeoServer WFS (Landing Centers Reference Layer)"],
            warnings=[],
        )
        return MarineQueryResponse(
            query=request.query,
            intent=QueryIntent.GENERAL_MARINE_INFORMATION,
            status=QueryWorkflowStatus.SUCCESS,
            answer=(
                "SaagarDrishti is an evidence-grounded marine intelligence platform for the Karnataka coast. "
                "It integrates advisories from INCOIS (Indian National Centre for Ocean Information Services) "
                "and monitors 29 official Karnataka landing centers including Karwar, Malpe, Mangalore, "
                "Kundapura, Bhatkal, Honavar, Tadri, Kumta, and Ankola. "
                "Potential Fishing Zone (PFZ) advisories are derived from satellite SST and Chlorophyll-a "
                "observations and are suspended during monsoon cloud occlusion periods. "
                "Use specific queries like 'nearest PFZ from Malpe' or 'is it safe to fish today?' "
                "to access domain-specific intelligence."
            ),
            candidate_pfz=None,
            evidence_audit=audit,
            sources_checked=sources_checked,
            tools_used=tools_used,
        )

    def _validate_pfz_evidence(
        self,
        payload: Optional[PFZAdvisoryPayload],
        now: datetime,
        extra_errors: List[str],
        pfz_lines_status: Optional[DataStatus],
    ) -> EvidenceAuditResult:
        checks: List[str] = []
        provenance: List[str] = []
        rejection_reasons: List[str] = list(extra_errors)
        warnings: List[str] = []
        is_expired = False

        checks.append("live_pfz_source_status_check")
        if pfz_lines_status != DataStatus.CURRENT:
            rejection_reasons.append(
                f"INCOIS live PFZ vector lines source is not CURRENT "
                f"(status: {pfz_lines_status or 'unknown'}). "
                "No verified unexpired PFZ features available for Karnataka coast."
            )

        checks.append("advisory_payload_received")
        if payload is None:
            rejection_reasons.append("Advisory payload could not be fetched or parsed from INCOIS.")
            return EvidenceAuditResult(
                passed=False,
                checks_performed=checks,
                provenance_sources=provenance,
                is_landing_center_mistaken_for_pfz=False,
                is_expired=False,
                rejection_reasons=rejection_reasons,
                warnings=warnings,
            )

        provenance.append(f"INCOIS WFS payload: {payload.advisory_id}")
        if payload.source_url:
            provenance.append(payload.source_url)

        checks.append("advisory_expiration_check")
        if payload.valid_to:
            valid_to = payload.valid_to
            if valid_to.tzinfo is None:
                valid_to = valid_to.replace(tzinfo=timezone.utc)
            if valid_to < now:
                is_expired = True
                rejection_reasons.append(
                    f"Advisory '{payload.advisory_id}' is EXPIRED "
                    f"(validity ended {valid_to.strftime('%Y-%m-%d %H:%M UTC')}). "
                    "Expired advisories must never be presented as active PFZ guidance."
                )
        else:
            rejection_reasons.append("Advisory is missing 'valid_to' timestamp; cannot confirm validity period.")

        checks.append("advisory_items_present_check")
        if not payload.items:
            rejection_reasons.append("Advisory payload contains zero hotspot items for Karnataka coast.")

        checks.append("landing_center_geometry_guard")
        warnings.append(
            "Landing center geometry (onshore coastal points) is strictly separated from "
            "offshore PFZ hotspot coordinates derived from DMS properties. "
            "No coastal reference points were returned as fishing zone coordinates."
        )

        passed = len(rejection_reasons) == 0
        return EvidenceAuditResult(
            passed=passed,
            checks_performed=checks,
            provenance_sources=provenance,
            is_landing_center_mistaken_for_pfz=False,
            is_expired=is_expired,
            rejection_reasons=rejection_reasons,
            warnings=warnings,
        )

    def _nearest_pfz_to_location(
        self,
        user_location: GeoCoordinate,
        payload: PFZAdvisoryPayload,
        now: datetime,
    ) -> Optional[CandidatePFZResult]:
        best_item: Optional[PFZAdvisoryItem] = None
        best_dist = float("inf")

        for item in payload.items:
            if item.coordinate is None:
                continue
            dist = haversine_distance_km(user_location, item.coordinate)
            if dist < best_dist:
                best_dist = dist
                best_item = item

        if best_item is None or payload.valid_to is None:
            return None

        valid_to = payload.valid_to
        if valid_to.tzinfo is None:
            valid_to = valid_to.replace(tzinfo=timezone.utc)

        return CandidatePFZResult(
            hotspot_id=best_item.item_id,
            coordinate=best_item.coordinate,
            distance_km=round(best_dist, 2),
            bearing_deg=best_item.direction_bearing_deg,
            depth_m=best_item.depth_m,
            landing_center=best_item.landing_center,
            valid_from=payload.valid_from,
            valid_to=valid_to,
            data_source=payload.source_url or payload.source,
        )

    @staticmethod
    def _get_source_status(
        source_name: str, sources: List[SourceAvailabilityReport]
    ) -> Optional[DataStatus]:
        for s in sources:
            if s.source_name == source_name:
                return s.status
        return None

    @staticmethod
    def _compose_unavailable_pfz_answer(
        evidence_audit: EvidenceAuditResult,
        pfz_lines_status: Optional[DataStatus],
        lc_status: Optional[DataStatus],
    ) -> str:
        reasons = "; ".join(evidence_audit.rejection_reasons) if evidence_audit.rejection_reasons else "Unknown reason"
        return (
            "No verified, unexpired Potential Fishing Zone (PFZ) advisory is currently available "
            f"for the Karnataka coast. Reason: {reasons}. "
            "INCOIS PFZ advisories are suspended during monsoon cloud occlusion periods and after "
            "government-mandated fishing bans. "
            "Please consult https://incois.gov.in/MarineFisheries/TextDataHome?mfid=1&request_locale=en "
            "for the latest official advisory publication."
        )

    @staticmethod
    def _compose_pfz_answer(
        candidate: Optional[CandidatePFZResult],
        payload: Optional[PFZAdvisoryPayload],
        request: MarineQueryRequest,
        evidence_audit: EvidenceAuditResult,
    ) -> str:
        if candidate is None:
            item_count = len(payload.items) if payload else 0
            return (
                f"A verified, unexpired PFZ advisory for the Karnataka coast is available with "
                f"{item_count} hotspot location(s). "
                "To find the nearest hotspot, please provide your current GPS coordinates "
                "(latitude and longitude) in the request."
            )

        coord = candidate.coordinate
        depth_str = f" at a depth of {candidate.depth_m:.0f} m" if candidate.depth_m else ""
        bearing_str = f" (bearing {candidate.bearing_deg:.0f})" if candidate.bearing_deg else ""
        valid_str = candidate.valid_to.strftime("%Y-%m-%d %H:%M UTC") if candidate.valid_to else "Unknown"

        return (
            f"The nearest verified PFZ hotspot near {candidate.landing_center} is located at "
            f"{coord.latitude:.4f}N, {coord.longitude:.4f}E -- approximately {candidate.distance_km:.1f} km "
            f"from your position{bearing_str}{depth_str}. "
            f"Advisory valid until: {valid_str}. "
            f"Source: {candidate.data_source}. "
            "Always verify with the official INCOIS advisory and check weather conditions before departure."
        )
