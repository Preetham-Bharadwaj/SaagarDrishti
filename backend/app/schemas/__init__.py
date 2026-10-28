"""Typed request and response schemas module."""

from app.schemas.common import APIResponse, GeoBoundingBox, GeoCoordinate, HealthCheckResponse
from app.schemas.marine import OceanographicObservation
from app.schemas.ocean_analytics import (
    OceanAnalyticsPayload,
    OceanAreaSummary,
    OceanGridPoint,
    OceanProductCategory,
    OceanProductMetadata,
    OceanSSTResult,
    OceanVariableType,
)
from app.schemas.pfz import PFZAdvisoryItem, PFZAdvisoryPayload, PFZValidationResult
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

__all__ = [
    "HealthCheckResponse",
    "GeoCoordinate",
    "GeoBoundingBox",
    "APIResponse",
    "PFZAdvisoryItem",
    "PFZAdvisoryPayload",
    "PFZValidationResult",
    "OceanographicObservation",
    "OceanAnalyticsPayload",
    "OceanAreaSummary",
    "OceanGridPoint",
    "OceanProductCategory",
    "OceanProductMetadata",
    "OceanSSTResult",
    "OceanVariableType",
    "QueryIntent",
    "DataStatus",
    "QueryWorkflowStatus",
    "SourceAvailabilityReport",
    "MarineQueryRequest",
    "CandidatePFZResult",
    "EvidenceAuditResult",
    "MarineQueryResponse",
]

