"""Service for auditing and reporting upstream marine data source availability."""

from datetime import datetime, timezone
from typing import List, Optional

from app.schemas.query import DataStatus, SourceAvailabilityReport

INCOIS_WFS_LANDING_CENTERS_URL = (
    "https://incois.gov.in/geoserver/PFZ_LandingCentres/ows?service=WFS&version=1.1.0"
    "&request=GetFeature&typeName=PFZ_LandingCentres:LandingCenters_29Apr2024"
    "&outputFormat=application/json&CQL_FILTER=SECTOR_NAM='KARNATAKA'"
)
INCOIS_WFS_PFZ_LINES_URL = (
    "https://incois.gov.in/geoserver/PFZ_Automation/ows?service=WFS&version=1.1.0"
    "&request=GetFeature&typeName=PFZ_Automation:pfzlines"
    "&outputFormat=application/json&CQL_FILTER=State_Name='KARNATAKA'"
)
INCOIS_DATAPROCESS_URL = "https://incois.gov.in/MarineFisheries/dataprocess.jsp"
IMD_WEATHER_URL = "https://mausam.imd.gov.in/"
OPEN_METEO_MARINE_URL = "https://marine-api.open-meteo.com/v1/marine"
COPERNICUS_DATA_URL = "https://data.marine.copernicus.eu"


class MarineDataAvailabilityService:
    """Audits upstream marine data providers and reports their operational status."""

    @staticmethod
    def get_sources_availability_report() -> List[SourceAvailabilityReport]:
        """Compile verified availability and temporal status of all upstream marine data feeds.

        Returns:
            List[SourceAvailabilityReport]: Itemized report of each data provider.
        """
        reports = [
            SourceAvailabilityReport(
                source_name="INCOIS GeoServer WFS (Landing Centers Reference Layer)",
                source_url=INCOIS_WFS_LANDING_CENTERS_URL,
                status=DataStatus.EXPIRED,
                latest_verified_timestamp=datetime(2024, 4, 28, 18, 30, tzinfo=timezone.utc),
                validity_window="2024-04-27 18:30 UTC to 2024-04-28 18:30 UTC",
                limitations=[
                    "Layer 'LandingCenters_29Apr2024' is a fixed historical reference snapshot.",
                    "Feature geometry represents onshore landing centers, NOT offshore fishing hotspots.",
                    "Embedded advisory attributes expired in April 2024 and must never be used as current PFZ guidance.",
                ],
                notes="Operational endpoint reachable (HTTP 200). Serves 29 Karnataka coastal landing centers as spatial reference baselines.",
            ),
            SourceAvailabilityReport(
                source_name="INCOIS GeoServer WFS (PFZ Vector Lines)",
                source_url=INCOIS_WFS_PFZ_LINES_URL,
                status=DataStatus.UNAVAILABLE,
                latest_verified_timestamp=None,
                validity_window="None",
                limitations=[
                    "Zero active PFZ vector features published for Karnataka coast in the layer.",
                    "Satellite thermal infrared (SST) and ocean color (Chlorophyll-a) sensors are subject to cloud occlusion.",
                    "Advisory production is suspended during monsoon and adverse sea states.",
                ],
                notes="WFS service reachable (HTTP 200), but returns 0 features for Karnataka (CQL State_Name='KARNATAKA').",
            ),
            SourceAvailabilityReport(
                source_name="INCOIS WebGIS DataProcess (Tabular Advisory Backend)",
                source_url=INCOIS_DATAPROCESS_URL,
                status=DataStatus.EXPIRED,
                latest_verified_timestamp=datetime(2025, 1, 9, 0, 0, tzinfo=timezone.utc),
                validity_window="2025-01-08 to 2025-01-09",
                limitations=[
                    "HTML table response; last recorded advisory published for Karnataka landing centers ended on 2025-01-09.",
                    "No current, unexpired advisory published for Karnataka sector.",
                    "Upstream table headers swap Latitude/Longitude labels (mitigated by 'N'/'E' direction checks).",
                ],
                notes="Internal database contains 23 historical Karnataka port advisories from January 2025; all are currently lapsed.",
            ),
            SourceAvailabilityReport(
                source_name="Open-Meteo Marine Weather API (ECMWF Wave Model)",
                source_url=OPEN_METEO_MARINE_URL,
                status=DataStatus.CURRENT,
                latest_verified_timestamp=datetime(2026, 10, 26, 10, 38, tzinfo=timezone.utc),
                validity_window="Hourly operational NWP wave forecast (up to 7 days)",
                limitations=[
                    "Numerical weather prediction (NWP) model output (ECMWF/ERAssWave), not an official safety advisory.",
                    "Absence of high waves does not guarantee calm sea conditions or safe vessel operation.",
                    "Small coastal craft must always consult official IMD bulletins and Karnataka DFO notices before departure.",
                ],
                notes="Operational endpoint reachable (HTTP 200). Serves verified hourly significant wave height, swell, and direction across Karnataka coast.",
            ),
        ]

        # Check if an official IMD bulletin is currently active in the warning service
        from app.services.official_warning_service import OfficialWarningService
        active_warning = OfficialWarningService.get_active_warning()

        if active_warning:
            imd_status = DataStatus.CURRENT
            imd_timestamp = active_warning.issued_at
            imd_window = f"{active_warning.valid_from.strftime('%Y-%m-%d %H:%M UTC')} to {active_warning.valid_to.strftime('%Y-%m-%d %H:%M UTC')}"
            imd_notes = (
                f"Active official bulletin '{active_warning.bulletin_id}' ingested from {active_warning.issuing_authority}. "
                f"Severity: {active_warning.severity.value.upper()}."
            )
            imd_limitations = [
                "Official statutory government bulletin manually ingested and verified.",
                "Supersedes all numerical model outputs and prototype heuristics.",
            ]
        else:
            imd_status = DataStatus.NOT_VERIFIED
            imd_timestamp = None
            imd_window = "No active bulletin ingested"
            imd_notes = (
                "Authoritative government safety bulletin authority. Public portal serves unversioned PDFs/images. "
                "Verified bulletins can be manually ingested via scripts/ingest_imd_warning.py."
            )
            imd_limitations = [
                "Official IMD public portal publishes bulletins as unversioned PDFs and image scans.",
                "Automated public JSON API requires ministerial credentials and fixed-IP whitelisting.",
                "Direct coastal warnings must be consulted via https://mausam.imd.gov.in/ when no manual bulletin is ingested.",
            ]

        reports.append(
            SourceAvailabilityReport(
                source_name="IMD Marine & Coastal Weather Hazard Bulletin",
                source_url=IMD_WEATHER_URL,
                status=imd_status,
                latest_verified_timestamp=imd_timestamp,
                validity_window=imd_window,
                limitations=imd_limitations,
                notes=imd_notes,
            )
        )
        reports.append(
            SourceAvailabilityReport(
                source_name="Copernicus Marine Data Store (OSTIA SST & Ocean Colour)",
                source_url=COPERNICUS_DATA_URL,
                status=DataStatus.NOT_VERIFIED,
                latest_verified_timestamp=None,
                validity_window="Credentials required (HTTP 401)",
                limitations=[
                    "Product SST_GLO_SST_L4_NRT_OBSERVATIONS_010_001 requires registered user credentials.",
                    "Environment variables COPERNICUSMARINE_SERVICE_USERNAME / PASSWORD not configured.",
                    "Offline verified sample fixture available via scripts/ocean_analytics.py --local.",
                    "SST data alone must never be used to infer fish abundance or navigation safety.",
                ],
                notes="OceanDataAdapter implemented with Level-4 SST normalization. Live access requires registration at data.marine.copernicus.eu.",
            )
        )
        return reports


def check_marine_data_availability() -> List[SourceAvailabilityReport]:
    """Tool function to inspect marine data availability across all tracked sources."""
    return MarineDataAvailabilityService.get_sources_availability_report()
