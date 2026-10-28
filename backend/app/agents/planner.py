"""Query planner for classifying user marine intelligence inquiries and coordinating tools."""

import re
from typing import List, Tuple
from app.schemas.query import QueryIntent


class QueryPlanner:
    """Classifies natural language marine queries into structured intents."""

    # Keywords for nearest_pfz
    _PFZ_PATTERNS = [
        r"\bpfz\b",
        r"\bfish(ing)?\b",
        r"\bcatch\b",
        r"\bshoal(s)?\b",
        r"\bhotspot(s)?\b",
        r"\bwhere\s+to\s+fish\b",
        r"\bpotential\s+fishing\s+zone\b",
        r"\btuna\b",
        r"\bsardine(s)?\b",
        r"\bmackerel\b",
    ]

    # Keywords for marine_conditions
    _CONDITIONS_PATTERNS = [
        r"\bsst\b",
        r"\bsea\s+surface\s+temp(erature)?\b",
        r"\bchlorophyll\b",
        r"\bocean\s+color\b",
        r"\bcurrent(s)?\b",
        r"\bsalinity\b",
        r"\bwater\s+quality\b",
        r"\bclarity\b",
        r"\btide(s)?\b",
        r"\btidal\b",
    ]

    # Keywords for weather_hazard
    _HAZARD_PATTERNS = [
        r"\bwave(s)?\b",
        r"\bwave\s+height\b",
        r"\bwind(s)?\b",
        r"\bcyclone\b",
        r"\bstorm\b",
        r"\bhazard(s)?\b",
        r"\bweather\b",
        r"\bgale\b",
        r"\bsafety\b",
        r"\bis\s+it\s+safe\b",
        r"\bwarning(s)?\b",
        r"\bswell\b",
        r"\brough\s+sea\b",
        r"\bsea\s+state\b",
        r"\bsea\s+condition(s)?\b",
    ]

    @classmethod
    def classify_intent(cls, query: str) -> QueryIntent:
        """Classify a user query string into a QueryIntent enum.

        Args:
            query: User's input question or statement.

        Returns:
            QueryIntent: Identified domain intent.
        """
        text = query.lower().strip()

        # Check for weather hazard
        for pat in cls._HAZARD_PATTERNS:
            if re.search(pat, text):
                return QueryIntent.WEATHER_HAZARD

        # Check for nearest PFZ
        for pat in cls._PFZ_PATTERNS:
            if re.search(pat, text):
                return QueryIntent.NEAREST_PFZ

        # Check for ocean / marine conditions
        for pat in cls._CONDITIONS_PATTERNS:
            if re.search(pat, text):
                return QueryIntent.MARINE_CONDITIONS

        return QueryIntent.GENERAL_MARINE_INFORMATION

    @classmethod
    def plan_workflow(cls, intent: QueryIntent) -> Tuple[List[str], str]:
        """Determine tools and bounded strategy for a given intent.

        Args:
            intent: Classified QueryIntent.

        Returns:
            Tuple[List[str], str]: Required tools list and strategy description.
        """
        if intent == QueryIntent.NEAREST_PFZ:
            tools = [
                "check_marine_data_availability",
                "filter_unexpired_pfz_records",
                "validate_evidence_provenance",
                "calculate_deterministic_distance",
            ]
            strategy = (
                "Verify live upstream PFZ advisory freshness. Reject landing-center reference points "
                "or expired 2024/2025 records. If verified unexpired records exist and user location is provided, "
                "calculate deterministic distance. Otherwise, output structured DATA_UNAVAILABLE."
            )
            return tools, strategy

        if intent == QueryIntent.MARINE_CONDITIONS:
            tools = [
                "check_marine_data_availability",
                "audit_oceanographic_parameters",
            ]
            strategy = "Inspect SST, Chlorophyll, and wave sensors status along Karnataka coast."
            return tools, strategy

        if intent == QueryIntent.WEATHER_HAZARD:
            tools = [
                "check_marine_data_availability",
                "audit_coastal_hazard_bulletins",
            ]
            strategy = "Audit wind speed, wave height, and IMD coastal hazard warnings."
            return tools, strategy

        tools = [
            "check_marine_data_availability",
            "retrieve_karnataka_landing_centers_reference",
        ]
        strategy = "Provide general marine geography, landing center reference baselines, and INCOIS advisory roles."
        return tools, strategy
