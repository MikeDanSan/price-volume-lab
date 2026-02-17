"""
Fetch OHLCV bars from a data source. Configurable adapter; sync for MVP.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from vpa_core.contracts import Bar


@dataclass
class FetchResult:
    """Result of a fetch: bars and optional next cursor for pagination."""

    bars: list[Bar]
    symbol: str
    timeframe: str
    next_cursor: str | None = None


class BarFetcher(Protocol):
    """Protocol for bar fetchers. Implement per provider (Polygon, Alpaca, etc.)."""

    def fetch(
        self,
        symbol: str,
        timeframe: str,
        *,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int | None = None,
        cursor: str | None = None,
    ) -> FetchResult:
        """Fetch bars; normalize timestamps to UTC. Returns FetchResult."""
        ...


class MockBarFetcher:
    """Returns no bars; for tests and when no API is configured."""

    def fetch(
        self,
        symbol: str,
        timeframe: str,
        *,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int | None = None,
        cursor: str | None = None,
    ) -> FetchResult:
        return FetchResult(bars=[], symbol=symbol, timeframe=timeframe)
