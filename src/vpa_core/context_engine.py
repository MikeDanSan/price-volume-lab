"""
Context Engine: bars → ContextSnapshot.

Produces trend direction, trend strength, trend location (percentile),
and congestion detection. All thresholds config-driven via VPAConfig.

Pure function; no I/O. Replaces the _build_context() stubs.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from vpa_core.contracts import (
    Bar,
    Congestion,
    ContextSnapshot,
    DominantAlignment,
    Trend,
    TrendLocation,
    TrendStrength,
)

if TYPE_CHECKING:
    from config.vpa_config import VPAConfig


def analyze(bars: list[Bar], config: VPAConfig, tf: str) -> ContextSnapshot:
    """Analyze bar history and produce a ContextSnapshot.

    Parameters
    ----------
    bars:
        Full bar history available (oldest first). The engine uses
        trailing windows sized by config.
    config:
        VPA configuration with trend.window_K, trend.location_lookback,
        trend.congestion_window, and trend.congestion_pct.
    tf:
        Timeframe label for the snapshot.
    """
    if len(bars) < 2:
        return _unknown_context(tf)

    trend, strength = _detect_trend(bars, config.trend.window_K)
    location = _detect_location(bars, config.trend.location_lookback)
    congestion = _detect_congestion(
        bars, config.trend.congestion_window,
        config.trend.location_lookback, config.trend.congestion_pct,
    )

    return ContextSnapshot(
        tf=tf,
        trend=trend,
        trend_strength=strength,
        trend_location=location,
        congestion=congestion,
        dominant_alignment=DominantAlignment.UNKNOWN,
    )


def _unknown_context(tf: str) -> ContextSnapshot:
    return ContextSnapshot(
        tf=tf,
        trend=Trend.UNKNOWN,
        trend_strength=TrendStrength.WEAK,
        trend_location=TrendLocation.UNKNOWN,
        congestion=Congestion(active=False),
        dominant_alignment=DominantAlignment.UNKNOWN,
    )


def _detect_trend(bars: list[Bar], window_k: int) -> tuple[Trend, TrendStrength]:
    """Determine trend direction and strength from recent closes.

    Counts up-closes vs down-closes in a trailing window.
    Strength is derived from the consistency ratio.
    """
    lookback = min(window_k, len(bars) - 1)
    if lookback < 1:
        return Trend.UNKNOWN, TrendStrength.WEAK

    recent = bars[-(lookback + 1):]
    ups = 0
    downs = 0
    for i in range(1, len(recent)):
        if recent[i].close > recent[i - 1].close:
            ups += 1
        elif recent[i].close < recent[i - 1].close:
            downs += 1

    total = ups + downs
    if total == 0:
        return Trend.RANGE, TrendStrength.WEAK

    dominant = max(ups, downs)
    ratio = dominant / lookback

    if ups > downs:
        trend = Trend.UP
    elif downs > ups:
        trend = Trend.DOWN
    else:
        return Trend.RANGE, TrendStrength.WEAK

    if ratio >= 0.80:
        strength = TrendStrength.STRONG
    elif ratio >= 0.60:
        strength = TrendStrength.MODERATE
    else:
        strength = TrendStrength.WEAK

    return trend, strength


def _detect_location(bars: list[Bar], location_lookback: int) -> TrendLocation:
    """Where the current close sits within the lookback price range.

    - Above 75th percentile → TOP
    - Below 25th percentile → BOTTOM
    - Otherwise → MIDDLE
    """
    window = bars[-location_lookback:] if len(bars) >= location_lookback else bars
    if len(window) < 2:
        return TrendLocation.UNKNOWN

    highest = max(b.high for b in window)
    lowest = min(b.low for b in window)
    full_range = highest - lowest
    if full_range <= 0:
        return TrendLocation.MIDDLE

    current_close = bars[-1].close
    pct = (current_close - lowest) / full_range

    if pct >= 0.75:
        return TrendLocation.TOP
    if pct <= 0.25:
        return TrendLocation.BOTTOM
    return TrendLocation.MIDDLE


def _detect_congestion(
    bars: list[Bar],
    congestion_window: int,
    location_lookback: int,
    congestion_pct: float,
) -> Congestion:
    """Detect congestion by comparing recent range to lookback range.

    If the high-low range of the last `congestion_window` bars is less
    than `congestion_pct` of the wider `location_lookback` range, the
    market is in a tight congestion zone.
    """
    if len(bars) < max(congestion_window, 2):
        return Congestion(active=False)

    recent = bars[-congestion_window:]
    recent_high = max(b.high for b in recent)
    recent_low = min(b.low for b in recent)
    recent_range = recent_high - recent_low

    wider = bars[-location_lookback:] if len(bars) >= location_lookback else bars
    wider_high = max(b.high for b in wider)
    wider_low = min(b.low for b in wider)
    wider_range = wider_high - wider_low

    if wider_range <= 0:
        return Congestion(active=False)

    ratio = recent_range / wider_range
    if ratio < congestion_pct:
        return Congestion(active=True, range_high=recent_high, range_low=recent_low)
    return Congestion(active=False, range_high=recent_high, range_low=recent_low)
