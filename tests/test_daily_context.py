"""Tests for daily-timeframe context provider (multi-timeframe analysis).

Validates:
    - compute_daily_context returns a valid daily ContextSnapshot
    - compute_dominant_alignment resolves WITH / AGAINST / UNKNOWN correctly
    - enrich_context_with_daily merges daily alignment into intraday context
"""

from datetime import datetime, timezone

import pytest

from config.vpa_config import load_vpa_config
from vpa_core.contracts import (
    Bar,
    Congestion,
    ContextSnapshot,
    DominantAlignment,
    Trend,
    TrendLocation,
    TrendStrength,
)
from vpa_core.daily_context import (
    compute_daily_context,
    compute_dominant_alignment,
    enrich_context_with_daily,
)


def _cfg():
    return load_vpa_config()


def _daily_bar(day: int, close: float, volume: int = 50_000_000) -> Bar:
    ts = datetime(2024, 1, day, 0, 0, tzinfo=timezone.utc)
    return Bar(
        open=close - 0.5,
        high=close + 1.0,
        low=close - 1.5,
        close=close,
        volume=volume,
        timestamp=ts,
        symbol="SPY",
    )


def _uptrend_bars(n: int = 25) -> list[Bar]:
    """Generate n daily bars in a clear uptrend (monotonically rising closes)."""
    return [_daily_bar(i + 1, 400.0 + i * 1.5) for i in range(n)]


def _downtrend_bars(n: int = 25) -> list[Bar]:
    """Generate n daily bars in a clear downtrend (monotonically falling closes)."""
    return [_daily_bar(i + 1, 500.0 - i * 1.5) for i in range(n)]


def _range_bars(n: int = 25) -> list[Bar]:
    """Generate n daily bars with flat closes (true range / no directional bias)."""
    return [_daily_bar(i + 1, 450.0) for i in range(n)]


def _intraday_context(tf: str = "15m") -> ContextSnapshot:
    return ContextSnapshot(
        tf=tf,
        trend=Trend.UP,
        trend_strength=TrendStrength.MODERATE,
        trend_location=TrendLocation.MIDDLE,
        congestion=Congestion(active=False),
        dominant_alignment=DominantAlignment.UNKNOWN,
    )


# --- compute_daily_context ---


class TestComputeDailyContext:

    def test_uptrend_detected(self) -> None:
        ctx = compute_daily_context(_uptrend_bars(), _cfg())
        assert ctx.trend == Trend.UP
        assert ctx.tf == "1d"

    def test_downtrend_detected(self) -> None:
        ctx = compute_daily_context(_downtrend_bars(), _cfg())
        assert ctx.trend == Trend.DOWN
        assert ctx.tf == "1d"

    def test_range_detected(self) -> None:
        ctx = compute_daily_context(_range_bars(), _cfg())
        assert ctx.trend == Trend.RANGE

    def test_too_few_bars_returns_unknown(self) -> None:
        ctx = compute_daily_context([_daily_bar(1, 400.0)], _cfg())
        assert ctx.trend == Trend.UNKNOWN

    def test_empty_bars_returns_unknown(self) -> None:
        ctx = compute_daily_context([], _cfg())
        assert ctx.trend == Trend.UNKNOWN

    def test_location_top_in_uptrend(self) -> None:
        ctx = compute_daily_context(_uptrend_bars(), _cfg())
        assert ctx.trend_location == TrendLocation.TOP

    def test_location_bottom_in_downtrend(self) -> None:
        ctx = compute_daily_context(_downtrend_bars(), _cfg())
        assert ctx.trend_location == TrendLocation.BOTTOM

    def test_strength_strong_for_clean_trend(self) -> None:
        ctx = compute_daily_context(_uptrend_bars(30), _cfg())
        assert ctx.trend_strength in (TrendStrength.STRONG, TrendStrength.MODERATE)


# --- compute_dominant_alignment ---


class TestComputeDominantAlignment:

    def _daily_ctx(self, trend: Trend) -> ContextSnapshot:
        return ContextSnapshot(
            tf="1d",
            trend=trend,
            trend_strength=TrendStrength.MODERATE,
            trend_location=TrendLocation.MIDDLE,
            congestion=Congestion(active=False),
        )

    def test_bullish_with_uptrend(self) -> None:
        result = compute_dominant_alignment(self._daily_ctx(Trend.UP), "BULLISH")
        assert result == DominantAlignment.WITH

    def test_bearish_with_downtrend(self) -> None:
        result = compute_dominant_alignment(self._daily_ctx(Trend.DOWN), "BEARISH")
        assert result == DominantAlignment.WITH

    def test_bullish_against_downtrend(self) -> None:
        result = compute_dominant_alignment(self._daily_ctx(Trend.DOWN), "BULLISH")
        assert result == DominantAlignment.AGAINST

    def test_bearish_against_uptrend(self) -> None:
        result = compute_dominant_alignment(self._daily_ctx(Trend.UP), "BEARISH")
        assert result == DominantAlignment.AGAINST

    def test_unknown_trend_gives_unknown(self) -> None:
        result = compute_dominant_alignment(self._daily_ctx(Trend.UNKNOWN), "BULLISH")
        assert result == DominantAlignment.UNKNOWN

    def test_range_trend_gives_unknown(self) -> None:
        result = compute_dominant_alignment(self._daily_ctx(Trend.RANGE), "BEARISH")
        assert result == DominantAlignment.UNKNOWN

    def test_ambiguous_bias_gives_unknown(self) -> None:
        result = compute_dominant_alignment(self._daily_ctx(Trend.UP), "NEUTRAL")
        assert result == DominantAlignment.UNKNOWN

    def test_bearish_or_wait_extracts_bearish(self) -> None:
        """The leading word 'BEARISH' from 'BEARISH_OR_WAIT' should match."""
        result = compute_dominant_alignment(self._daily_ctx(Trend.DOWN), "BEARISH_OR_WAIT")
        assert result == DominantAlignment.WITH

    def test_case_insensitive_bias(self) -> None:
        result = compute_dominant_alignment(self._daily_ctx(Trend.UP), "bullish")
        assert result == DominantAlignment.WITH


# --- enrich_context_with_daily ---


class TestEnrichContextWithDaily:

    def test_merges_alignment_into_intraday(self) -> None:
        daily_ctx = compute_daily_context(_uptrend_bars(), _cfg())
        intraday = _intraday_context()
        enriched = enrich_context_with_daily(intraday, daily_ctx, "BULLISH")
        assert enriched.dominant_alignment == DominantAlignment.WITH
        assert enriched.tf == "15m"
        assert enriched.trend == Trend.UP

    def test_preserves_intraday_fields(self) -> None:
        daily_ctx = compute_daily_context(_downtrend_bars(), _cfg())
        intraday = _intraday_context()
        enriched = enrich_context_with_daily(intraday, daily_ctx, "BULLISH")
        assert enriched.dominant_alignment == DominantAlignment.AGAINST
        assert enriched.trend == intraday.trend
        assert enriched.trend_strength == intraday.trend_strength
        assert enriched.trend_location == intraday.trend_location
        assert enriched.congestion == intraday.congestion

    def test_unknown_daily_preserves_unknown_alignment(self) -> None:
        daily_ctx = compute_daily_context([], _cfg())
        intraday = _intraday_context()
        enriched = enrich_context_with_daily(intraday, daily_ctx, "BULLISH")
        assert enriched.dominant_alignment == DominantAlignment.UNKNOWN

    def test_enrichment_does_not_mutate_original(self) -> None:
        daily_ctx = compute_daily_context(_uptrend_bars(), _cfg())
        intraday = _intraday_context()
        enriched = enrich_context_with_daily(intraday, daily_ctx, "BEARISH")
        assert intraday.dominant_alignment == DominantAlignment.UNKNOWN
        assert enriched.dominant_alignment == DominantAlignment.AGAINST
