"""
Shared helper to load daily bars and compute daily context.

Used by scan, paper, scheduler, and backtest CLI paths. Gracefully
returns None when no daily bars are available (single-timeframe mode).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from vpa_core.contracts import Bar, ContextSnapshot
from vpa_core.daily_context import compute_daily_context

if TYPE_CHECKING:
    from config.vpa_config import VPAConfig
    from data.bar_store import BarStore

logger = logging.getLogger("vpa.daily")

MIN_DAILY_BARS = 10


def load_daily_context(
    store: BarStore,
    symbol: str,
    config: VPAConfig,
    *,
    daily_lookback: int = 100,
) -> ContextSnapshot | None:
    """Load daily bars from the store and compute daily context.

    Returns None if fewer than MIN_DAILY_BARS daily bars are available,
    which causes the pipeline to fall back to single-timeframe mode
    (dominant_alignment stays UNKNOWN).

    Parameters
    ----------
    store:
        BarStore instance (same database as intraday bars).
    symbol:
        Ticker symbol to query.
    config:
        VPA config for trend analysis parameters.
    daily_lookback:
        Maximum number of daily bars to load (default 100).
    """
    daily_bars = store.get_last_bars(symbol, "1d", daily_lookback)

    if len(daily_bars) < MIN_DAILY_BARS:
        if daily_bars:
            logger.info(
                "Only %d daily bars for %s (need %d). "
                "Run 'vpa ingest --timeframe 1d' for multi-timeframe analysis.",
                len(daily_bars), symbol, MIN_DAILY_BARS,
            )
        return None

    ctx = compute_daily_context(daily_bars, config)
    logger.info(
        "Daily context for %s: trend=%s strength=%s location=%s (%d bars)",
        symbol, ctx.trend.value, ctx.trend_strength.value,
        ctx.trend_location.value, len(daily_bars),
    )
    return ctx
