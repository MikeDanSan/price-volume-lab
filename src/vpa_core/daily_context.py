"""
Daily-timeframe context provider for multi-timeframe analysis.

Computes the higher-timeframe (daily) trend and determines dominant
alignment — whether a signal's directional bias agrees with the
daily trend. This feeds into CTX-2 (dominant alignment gate).

Pure functions; no I/O. Daily bars must be loaded beforehand.

Couling canonical logic: the dominant (slower) timeframe sets the
backdrop. Intraday signals that agree with the daily trend are
"WITH"; those opposing it are "AGAINST".
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from vpa_core.context_engine import analyze as analyze_context
from vpa_core.contracts import (
    Bar,
    ContextSnapshot,
    DominantAlignment,
    Trend,
)

if TYPE_CHECKING:
    from config.vpa_config import VPAConfig


def compute_daily_context(daily_bars: list[Bar], config: VPAConfig) -> ContextSnapshot:
    """Analyze daily bars and produce a higher-timeframe ContextSnapshot.

    Reuses the same context engine logic (trend direction, strength,
    location, congestion) but scoped to the daily timeframe.

    Parameters
    ----------
    daily_bars:
        Daily OHLCV bars in ascending time order (oldest first).
        At least ``config.trend.window_K + 1`` bars recommended
        for a reliable trend reading.
    config:
        VPA configuration (shares trend windows with intraday).

    Returns
    -------
    ContextSnapshot
        Daily-timeframe context with trend, location, congestion.
        ``dominant_alignment`` is left UNKNOWN here — call
        ``compute_dominant_alignment`` to resolve it per signal.
    """
    return analyze_context(daily_bars, config, tf="1d")


def compute_dominant_alignment(
    daily_context: ContextSnapshot,
    signal_direction_bias: str,
) -> DominantAlignment:
    """Determine if a signal's direction aligns with the daily trend.

    Alignment logic:
        WITH:    bullish signal + daily UP, or bearish signal + daily DOWN.
        AGAINST: bullish signal + daily DOWN, or bearish signal + daily UP.
        UNKNOWN: daily trend is UNKNOWN/RANGE, or signal bias is ambiguous.

    Parameters
    ----------
    daily_context:
        ContextSnapshot from ``compute_daily_context``.
    signal_direction_bias:
        The signal's ``direction_bias`` string, e.g. "BULLISH",
        "BEARISH", "BEARISH_OR_WAIT". Only the leading word is used.
    """
    daily_trend = daily_context.trend

    if daily_trend in (Trend.UNKNOWN, Trend.RANGE):
        return DominantAlignment.UNKNOWN

    bias = signal_direction_bias.upper().split("_")[0]
    if bias not in ("BULLISH", "BEARISH"):
        return DominantAlignment.UNKNOWN

    if bias == "BULLISH" and daily_trend == Trend.UP:
        return DominantAlignment.WITH
    if bias == "BEARISH" and daily_trend == Trend.DOWN:
        return DominantAlignment.WITH
    if bias == "BULLISH" and daily_trend == Trend.DOWN:
        return DominantAlignment.AGAINST
    if bias == "BEARISH" and daily_trend == Trend.UP:
        return DominantAlignment.AGAINST

    return DominantAlignment.UNKNOWN


def enrich_context_with_daily(
    intraday_context: ContextSnapshot,
    daily_context: ContextSnapshot,
    signal_direction_bias: str,
) -> ContextSnapshot:
    """Return an updated intraday context with dominant alignment resolved.

    Creates a new ContextSnapshot identical to ``intraday_context``
    but with ``dominant_alignment`` set based on the daily trend
    and the signal's directional bias.

    This is the entry point used by the pipeline to merge timeframes.
    """
    alignment = compute_dominant_alignment(daily_context, signal_direction_bias)
    return ContextSnapshot(
        tf=intraday_context.tf,
        trend=intraday_context.trend,
        trend_strength=intraday_context.trend_strength,
        trend_location=intraday_context.trend_location,
        congestion=intraday_context.congestion,
        dominant_alignment=alignment,
    )
