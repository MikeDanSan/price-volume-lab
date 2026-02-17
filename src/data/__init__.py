"""
Data pipeline: fetch OHLCV, normalize to UTC, persist bars, expose context window.

Depends on vpa_core.contracts for Bar; no dependency from vpa_core back to data.
"""

from data.bar_store import BarStore
from data.context_window import get_context_window
from data.fetcher import BarFetcher, FetchResult

__all__ = [
    "BarFetcher",
    "BarStore",
    "FetchResult",
    "get_context_window",
]


def get_alpaca_fetcher(api_key: str, api_secret: str):
    """Lazy import to avoid requiring alpaca-py when not used."""
    from data.alpaca_fetcher import AlpacaBarFetcher

    return AlpacaBarFetcher(api_key, api_secret)
