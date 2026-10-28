"""Base interface for agents within the SaagarDrishti multi-agent system."""

from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseAgent(ABC):
    """Abstract base class for domain-specific marine AI agents."""

    def __init__(self, name: str, description: str) -> None:
        self.name = name
        self.description = description

    @abstractmethod
    async def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute agent's specialized task with the given context.

        Args:
            context: Dictionary containing state, user query, or ingested observation data.

        Returns:
            Dict[str, Any]: Agent output, rationale, or structured recommendations.
        """
        pass
