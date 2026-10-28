"""Base abstract adapter interface for external marine data providers."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class BaseMarineDataAdapter(ABC):
    """Abstract interface that all external marine data adapters must implement."""

    def __init__(self, source_name: str, base_url: Optional[str] = None) -> None:
        self.source_name = source_name
        self.base_url = base_url

    @abstractmethod
    async def fetch_feed(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Fetch raw payload from the upstream data provider.

        Args:
            endpoint: API path or feed identifier.
            params: Query parameters or filtering criteria.

        Returns:
            Dict[str, Any]: Parsed raw payload from provider.
        """
        pass

    @abstractmethod
    def validate_connection(self) -> bool:
        """Verify whether credentials and provider endpoint are reachable."""
        pass
