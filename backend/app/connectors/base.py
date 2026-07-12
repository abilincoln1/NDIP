"""
Base connector interface — all social API connectors implement this.
Each connector is isolated and fails gracefully if credentials are missing.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class RawPost:
    platform: str
    external_id: str
    content_text: Optional[str]
    url: Optional[str]
    language: Optional[str]
    published_at: Optional[datetime]
    query_tag: str


class BaseConnector(ABC):
    """All connectors must implement fetch() and return a list of RawPost."""

    @property
    @abstractmethod
    def platform(self) -> str:
        ...

    @property
    @abstractmethod
    def is_configured(self) -> bool:
        """Return False if required credentials are missing."""
        ...

    @abstractmethod
    async def fetch(self, query: str, max_results: int = 100) -> list[RawPost]:
        """
        Fetch public posts matching the query.
        Must never store author-identifying information.
        Must use only official API endpoints.
        """
        ...
