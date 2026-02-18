"""
Alpaca bar fetcher: implements BarFetcher protocol using alpaca-py SDK.

Maps Alpaca Bar objects to vpa_core.contracts.Bar (OHLCV, UTC timestamp, symbol).
Handles pagination via next_page_token.
Free tier uses IEX data; SIP requires Algo Trader Plus subscription.
"""

import logging
from datetime import datetime, timezone

from vpa_core.contracts import Bar

from data.fetcher import FetchResult

logger = logging.getLogger(__name__)

_TIMEFRAME_MAP = {
    "1m": ("Minute", 1),
    "5m": ("Minute", 5),
    "15m": ("Minute", 15),
    "30m": ("Minute", 30),
    "1h": ("Hour", 1),
    "1d": ("Day", 1),
}


def _parse_timeframe(tf_str: str):
    """Convert string timeframe to Alpaca TimeFrame object."""
    from alpaca.data.timeframe import TimeFrame, TimeFrameUnit

    if tf_str not in _TIMEFRAME_MAP:
        raise ValueError(
            f"Unsupported timeframe '{tf_str}'. Supported: {list(_TIMEFRAME_MAP.keys())}"
        )
    unit_str, amount = _TIMEFRAME_MAP[tf_str]
    unit = getattr(TimeFrameUnit, unit_str)
    return TimeFrame(amount, unit)


class AlpacaBarFetcher:
    """
    Fetch OHLCV bars from Alpaca Market Data API.

    Uses StockHistoricalDataClient from alpaca-py.
    API keys via constructor (typically from AppConfig, sourced from env vars).
    """

    def __init__(self, api_key: str, api_secret: str) -> None:
        if not api_key or not api_secret:
            raise ValueError(
                "Alpaca API key and secret are required. "
            "Set APCA_API_KEY_ID and APCA_API_SECRET_KEY environment variables."
        )
        try:
            from alpaca.data.historical import StockHistoricalDataClient
        except ImportError:
            raise ImportError(
                "alpaca-py is required for AlpacaBarFetcher. "
                "Install with: pip install 'vpa-engine[data]'"
            )
        self._client = StockHistoricalDataClient(api_key, api_secret)

    def fetch(
        self,
        symbol: str,
        timeframe: str,
        *,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int | None = None,
        cursor: str | None = None,
        feed: str = "iex",
    ) -> FetchResult:
        """Fetch bars from Alpaca; normalize timestamps to UTC. Returns FetchResult."""
        from alpaca.data.enums import DataFeed
        from alpaca.data.requests import StockBarsRequest

        feed_enum = DataFeed(feed.lower())
        tf = _parse_timeframe(timeframe)
        request_params = StockBarsRequest(
            symbol_or_symbols=symbol,
            timeframe=tf,
            start=start,
            end=end,
            limit=limit,
            feed=feed_enum,
        )
        response = self._client.get_stock_bars(request_params)
        bars: list[Bar] = []
        raw_bars = response.data.get(symbol, []) if hasattr(response, "data") else response.get(symbol, [])
        for i, alpaca_bar in enumerate(raw_bars):
            ts = alpaca_bar.timestamp
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            else:
                ts = ts.astimezone(timezone.utc)
            bars.append(
                Bar(
                    open=float(alpaca_bar.open),
                    high=float(alpaca_bar.high),
                    low=float(alpaca_bar.low),
                    close=float(alpaca_bar.close),
                    volume=int(alpaca_bar.volume),
                    timestamp=ts,
                    symbol=symbol,
                    bar_index=i,
                )
            )
        next_token = getattr(response, "next_page_token", None)
        logger.info("Fetched %d bars for %s %s", len(bars), symbol, timeframe)
        return FetchResult(
            bars=bars,
            symbol=symbol,
            timeframe=timeframe,
            next_cursor=next_token,
        )
