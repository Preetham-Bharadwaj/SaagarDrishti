"""Typed schemas for Copernicus Ocean Analytics and Sea Surface Temperature (SST).

Covers data structures for Copernicus Marine Data Store products:
- SST_GLO_SST_L4_NRT_OBSERVATIONS_010_001 (Global Ocean OSTIA Sea Surface Temperature)
- OCEANCOLOUR_GLO_BGC_L4_NRT_009_102 (Global Ocean Colour Bio-Geo-Chemical Chlorophyll-a)

Critical Ecological Boundary:
- SST and Chlorophyll are oceanographic physical and biological parameters.
- SST alone DOES NOT PROVE fish abundance, catch yield, or a safe fishing location.
- Multi-parameter advisories (e.g. INCOIS PFZ) and official IMD warnings must be consulted.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field

from app.schemas.common import GeoBoundingBox, GeoCoordinate


class OceanVariableType(str, Enum):
    """Categorized oceanographic variables."""

    SST = "analysed_sst"
    CHLOROPHYLL_A = "chlorophyll_a"
    ANALYSIS_ERROR = "analysis_error"
    SEA_ICE_FRACTION = "sea_ice_fraction"


class OceanProductCategory(str, Enum):
    """Processing level and nature of oceanographic datasets."""

    L4_SATELLITE_ANALYSIS = "L4_SATELLITE_ANALYSIS"  # Gap-free interpolated multi-sensor analysis + in-situ
    L3_SATELLITE_COLLATED = "L3_SATELLITE_COLLATED"  # Single-day collated satellite swaths
    NUMERICAL_MODEL_FORECAST = "NUMERICAL_MODEL_FORECAST"  # Physics-based NWP / circulation model
    IN_SITU_SENSOR = "IN_SITU_SENSOR"  # Direct moored buoy / Argo float measurement


class OceanGridPoint(BaseModel):
    """Normalized ocean observation or analysis value at a discrete grid point."""

    coordinate: GeoCoordinate
    variable: OceanVariableType
    value_raw: Optional[float] = Field(None, description="Raw variable value in source units (e.g., Kelvin for SST)")
    value_si: Optional[float] = Field(None, description="Standardized value (e.g., Celsius for SST, mg/m^3 for CHL)")
    units: str = Field(..., description="Measurement units of value_si (e.g., 'degC', 'mg/m^3')")
    analysis_error: Optional[float] = Field(None, description="Estimated error standard deviation in Kelvin or variable units")
    is_land_masked: bool = Field(False, description="True if cell is masked as land or bathymetric barrier")
    quality_flag: int = Field(0, description="Quality flag: 0=good/nominal, 1=suspect, 2=land_masked, 3=missing")


class OceanAreaSummary(BaseModel):
    """Deterministic spatial and statistical summary for a bounded coastal ocean area."""

    variable: OceanVariableType
    bounding_box: GeoBoundingBox
    observation_date: str = Field(..., description="ISO date (YYYY-MM-DD) of the oceanographic slice")
    mean_value: Optional[float] = Field(None, description="Spatial mean of valid sea cells in value_si units")
    min_value: Optional[float] = Field(None, description="Spatial minimum of valid sea cells")
    max_value: Optional[float] = Field(None, description="Spatial maximum of valid sea cells")
    std_dev: Optional[float] = Field(None, description="Spatial standard deviation across valid sea cells")
    mean_error: Optional[float] = Field(None, description="Mean analysis error across valid sea cells in Kelvin/units")
    valid_cell_count: int = Field(..., description="Count of valid, unmasked ocean cells")
    land_masked_cell_count: int = Field(..., description="Count of grid points on land or masked")
    missing_cell_count: int = Field(0, description="Count of cells with missing/null data")
    regional_range_celsius: Optional[float] = Field(
        None, description="Macro-regional SST spread across all valid sea cells (max - min) in degC"
    )
    max_spatial_gradient_c_per_km: Optional[float] = Field(
        None, description="Maximum local horizontal temperature gradient between neighboring valid sea cells in degC/km"
    )
    mean_spatial_gradient_c_per_km: Optional[float] = Field(
        None, description="Mean horizontal temperature gradient across all evaluated neighboring sea-cell pairs in degC/km"
    )
    evaluated_neighbor_pairs_count: int = Field(
        0, description="Count of neighboring sea-cell pairs evaluated for spatial gradient"
    )
    thermal_front_threshold_c_per_km: float = Field(
        0.05, description="Physical gradient threshold in degC/km to detect a localized thermal front"
    )
    thermal_front_detected: bool = Field(
        False, description="True if max_spatial_gradient_c_per_km exceeds thermal_front_threshold_c_per_km"
    )
    is_stale: bool = Field(
        False, description="True if observation timestamp exceeds maximum allowed age (e.g. >72 hours)"
    )
    gradient_notes: List[str] = Field(default_factory=list, description="Notes on spatial gradients or front features")
    ecological_disclaimer: str = Field(
        default=(
            "ECOLOGICAL & SAFETY NOTICE: Sea Surface Temperature (SST) is an oceanographic physical parameter. "
            "Thermal fronts or gradients may indicate upwelling or water mass boundaries, but SST ALONE DOES NOT "
            "PROVE fish abundance, catch yield, or maritime navigation safety. Operational fishing decisions require "
            "official multi-parameter advisories (INCOIS PFZ) and official statutory IMD weather clearances."
        ),
        description="Mandatory ecological disclaimer attached to all ocean analytics summaries.",
    )


class OceanProductMetadata(BaseModel):
    """Provenance and specification metadata for an oceanographic dataset."""

    product_id: str = Field(..., description="Official Copernicus Marine product ID")
    dataset_id: str = Field(..., description="Official Copernicus Marine dataset ID")
    production_center: str = Field(..., description="Authoritative production center (e.g. UK Met Office / ACRI-ST)")
    product_category: OceanProductCategory = Field(..., description="Level-4 analysis, satellite swath, or forecast")
    spatial_resolution_deg: float = Field(..., description="Spatial grid resolution in decimal degrees (~0.05 deg = 5.5 km)")
    temporal_resolution: str = Field("daily", description="Temporal cadence: daily, hourly, monthly")
    data_format: str = Field("NetCDF-4", description="Original distribution format")
    usage_terms: str = Field("Copernicus Open Access (CC-BY 4.0)", description="License and usage terms")
    access_requirement: str = Field(
        "Copernicus Marine Data Store account (auth.marine.copernicus.eu)",
        description="Authentication and credential requirements",
    )
    fixture_type: Optional[str] = Field(
        None, description="'MANUALLY_PREPARED_TEST_FIXTURE' or 'LIVE_DOWNLOADED_PRODUCT'"
    )
    is_real_download: bool = Field(
        False, description="True if downloaded from live CMEMS API; False if synthetic/test fixture"
    )
    provenance_audit: Optional[str] = Field(
        None, description="Audited description of data provenance and preparation"
    )
    is_stale: bool = Field(
        False, description="True if foundation observation timestamp is older than 72 hours"
    )
    retrieved_at: datetime = Field(..., description="UTC timestamp when data was fetched or loaded")
    observation_timestamp: datetime = Field(..., description="UTC timestamp of the foundation ocean observation")
    coverage_bbox: GeoBoundingBox = Field(..., description="Geographic boundary of the product slice")


class OceanAnalyticsPayload(BaseModel):
    """Complete ocean analytics payload containing metadata, grid points, and summary."""

    metadata: OceanProductMetadata
    grid_points: List[OceanGridPoint] = Field(default_factory=list)
    area_summary: OceanAreaSummary
    provenance_notes: List[str] = Field(default_factory=list)
    is_live_retrieval: bool = Field(False, description="True if fetched live; False if loaded from verified sample")


class OceanSSTResult(BaseModel):
    """Compact SST summary embedded in a MarineQueryResponse.

    This is the workflow-layer view of the live Copernicus OSTIA foundation SST
    retrieval. It carries the fields a UI or API consumer needs without embedding
    the full grid-point list.

    Governance rules (mandatory):
    - ``is_live_retrieval`` must be False for any synthetic fixture.
    - ``ecological_disclaimer`` must always be propagated to the user.
    - SST alone MUST NOT be presented as proof of fish abundance or a safe
      fishing location. Multi-parameter INCOIS PFZ advisories and official IMD
      weather warnings always take precedence.
    """

    # Source identity
    source_name: str = Field(..., description="Human-readable data source name")
    product_id: str = Field(..., description="Copernicus Marine product identifier")
    dataset_id: str = Field(..., description="Copernicus Marine dataset identifier")
    product_category: OceanProductCategory = Field(
        ..., description="L4_SATELLITE_ANALYSIS / NUMERICAL_MODEL_FORECAST / IN_SITU_SENSOR"
    )
    production_center: str = Field(..., description="Authoritative production center")

    # Temporal provenance
    observation_timestamp: datetime = Field(..., description="UTC timestamp of the foundation ocean observation")
    retrieved_at: datetime = Field(..., description="UTC timestamp when data was fetched from Copernicus")
    is_live_retrieval: bool = Field(
        False, description="True only when data came from an authenticated live Copernicus request"
    )
    is_stale: bool = Field(
        False, description="True when observation timestamp is older than 72 hours"
    )

    # Spatial coverage
    coverage_min_lat: float
    coverage_max_lat: float
    coverage_min_lon: float
    coverage_max_lon: float
    spatial_resolution_deg: float = Field(0.05, description="Grid resolution in decimal degrees (~5.5 km)")

    # Statistics (None when no valid sea cells retrieved)
    valid_cell_count: int = Field(0, description="Count of valid, unmasked ocean cells")
    land_masked_cell_count: int = Field(0, description="Count of land-masked grid points")
    missing_cell_count: int = Field(0, description="Count of missing-value cells")
    mean_sst_celsius: Optional[float] = Field(None, description="Spatial mean SST in °C across valid sea cells")
    min_sst_celsius: Optional[float] = Field(None, description="Spatial minimum SST in °C")
    max_sst_celsius: Optional[float] = Field(None, description="Spatial maximum SST in °C")
    regional_range_celsius: Optional[float] = Field(
        None, description="Macro regional SST spread (max-min) in °C — not a localized gradient"
    )
    max_spatial_gradient_c_per_km: Optional[float] = Field(
        None, description="Maximum local horizontal SST gradient between neighboring valid sea cells (°C/km)"
    )
    thermal_front_detected: Optional[bool] = Field(
        None, description="True if max gradient exceeds the 0.05 °C/km thermal front threshold"
    )

    # Quality & access
    retrieval_status: str = Field(
        ...,
        description=(
            "Retrieval status: 'SUCCESS', 'CREDENTIALS_REQUIRED', 'AUTHENTICATION_FAILED', "
            "'CONNECTION_ERROR', 'DATA_UNAVAILABLE', or 'STALE'"
        ),
    )
    quality_notes: List[str] = Field(default_factory=list)

    # Mandatory ecological governance
    ecological_disclaimer: str = Field(
        default=(
            "ECOLOGICAL & SAFETY NOTICE: Sea Surface Temperature (SST) is an oceanographic physical parameter. "
            "Thermal fronts or gradients may indicate upwelling or water mass boundaries, but SST ALONE DOES NOT "
            "PROVE fish abundance, catch yield, or maritime navigation safety. Operational fishing decisions require "
            "official multi-parameter advisories (INCOIS PFZ) and official statutory IMD weather clearances."
        ),
        description="Mandatory disclaimer: SST does not imply fish abundance or navigation safety.",
    )

    @classmethod
    def from_payload(cls, payload: "OceanAnalyticsPayload", retrieval_status: str = "SUCCESS") -> "OceanSSTResult":
        """Build a compact OceanSSTResult from a full OceanAnalyticsPayload."""
        meta = payload.metadata
        summary = payload.area_summary
        return cls(
            source_name="Copernicus Marine Data Store — OSTIA Level-4 Foundation SST",
            product_id=meta.product_id,
            dataset_id=meta.dataset_id,
            product_category=meta.product_category,
            production_center=meta.production_center,
            observation_timestamp=meta.observation_timestamp,
            retrieved_at=meta.retrieved_at,
            is_live_retrieval=payload.is_live_retrieval,
            is_stale=meta.is_stale,
            coverage_min_lat=meta.coverage_bbox.min_latitude,
            coverage_max_lat=meta.coverage_bbox.max_latitude,
            coverage_min_lon=meta.coverage_bbox.min_longitude,
            coverage_max_lon=meta.coverage_bbox.max_longitude,
            spatial_resolution_deg=meta.spatial_resolution_deg,
            valid_cell_count=summary.valid_cell_count,
            land_masked_cell_count=summary.land_masked_cell_count,
            missing_cell_count=summary.missing_cell_count,
            mean_sst_celsius=summary.mean_value,
            min_sst_celsius=summary.min_value,
            max_sst_celsius=summary.max_value,
            regional_range_celsius=summary.regional_range_celsius,
            max_spatial_gradient_c_per_km=summary.max_spatial_gradient_c_per_km,
            thermal_front_detected=summary.thermal_front_detected,
            retrieval_status=retrieval_status,
            quality_notes=summary.gradient_notes,
            ecological_disclaimer=summary.ecological_disclaimer,
        )
