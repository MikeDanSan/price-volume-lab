"""Tests for the Context Engine (context_engine.analyze).

Covers: trend direction, trend strength, trend location (percentile),
congestion detection, and edge cases.
"""

from datetime import datetime, timezone

import pytest

from config.vpa_config import load_vpa_config
from vpa_core.contracts import Bar, Congestion, DominantAlignment, Trend, TrendLocation, TrendStrength, VolumeTrend
from vpa_core.context_engine import analyze


def _ts(day: int) -> datetime:
    return datetime(2024, 1, day, 9, 30, 0, tzinfo=timezone.utc)


def _bar(
    day: int,
    o: float,
    h: float,
    l: float,
    c: float,
    v: int = 1_000_000,
) -> Bar:
    return Bar(open=o, high=h, low=l, close=c, volume=v, timestamp=_ts(day), symbol="SPY")


@pytest.fixture
def cfg():
    return load_vpa_config()


# ---------------------------------------------------------------------------
# Trend direction
# ---------------------------------------------------------------------------


class TestTrendDirection:
    def test_uptrend_detected(self, cfg):
        bars = [
            _bar(1, 100, 101, 99, 100.5),
            _bar(2, 100.5, 102, 100, 101.5),
            _bar(3, 101.5, 103, 101, 102.5),
            _bar(4, 102.5, 104, 102, 103.5),
            _bar(5, 103.5, 105, 103, 104.5),
            _bar(6, 104.5, 106, 104, 105.5),
        ]
        ctx = analyze(bars, cfg, "15m")
        assert ctx.trend == Trend.UP

    def test_downtrend_detected(self, cfg):
        bars = [
            _bar(1, 105, 106, 104, 105),
            _bar(2, 105, 105.5, 103, 103.5),
            _bar(3, 103.5, 104, 102, 102.5),
            _bar(4, 102.5, 103, 101, 101.5),
            _bar(5, 101.5, 102, 100, 100.5),
            _bar(6, 100.5, 101, 99, 99.5),
        ]
        ctx = analyze(bars, cfg, "15m")
        assert ctx.trend == Trend.DOWN

    def test_range_on_mixed_closes(self, cfg):
        """2 up + 2 down + 1 flat in window_K=5 → RANGE.

        recent = bars[-6:] = bars[1..6], yielding 5 transitions:
          100→101 UP, 101→100 DOWN, 100→100 flat, 100→101 UP, 101→100 DOWN
        ups=2, downs=2 → RANGE.
        """
        bars = [
            _bar(1, 100, 102, 99, 99),     # anchor outside window
            _bar(2, 100, 102, 99, 100),
            _bar(3, 100, 102, 99, 101),     # up
            _bar(4, 101, 102, 99, 100),     # down
            _bar(5, 100, 102, 99, 100),     # flat
            _bar(6, 100, 102, 99, 101),     # up
            _bar(7, 101, 102, 99, 100),     # down
        ]
        ctx = analyze(bars, cfg, "15m")
        assert ctx.trend == Trend.RANGE

    def test_unknown_on_single_bar(self, cfg):
        bars = [_bar(1, 100, 101, 99, 100.5)]
        ctx = analyze(bars, cfg, "15m")
        assert ctx.trend == Trend.UNKNOWN

    def test_unknown_on_empty(self, cfg):
        ctx = analyze([], cfg, "15m")
        assert ctx.trend == Trend.UNKNOWN


# ---------------------------------------------------------------------------
# Trend strength
# ---------------------------------------------------------------------------


class TestTrendStrength:
    def test_strong_uptrend(self, cfg):
        """5 consecutive up closes out of 5 → 100% consistency → STRONG."""
        bars = [
            _bar(1, 100, 101, 99, 100.5),
            _bar(2, 100.5, 102, 100, 101.5),
            _bar(3, 101.5, 103, 101, 102.5),
            _bar(4, 102.5, 104, 102, 103.5),
            _bar(5, 103.5, 105, 103, 104.5),
            _bar(6, 104.5, 106, 104, 105.5),
        ]
        ctx = analyze(bars, cfg, "15m")
        assert ctx.trend_strength == TrendStrength.STRONG

    def test_weak_range(self, cfg):
        """Equal ups and downs → RANGE → always WEAK."""
        bars = [
            _bar(1, 100, 102, 99, 99),
            _bar(2, 100, 102, 99, 100),
            _bar(3, 100, 102, 99, 101),     # up
            _bar(4, 101, 102, 99, 100),     # down
            _bar(5, 100, 102, 99, 100),     # flat
            _bar(6, 100, 102, 99, 101),     # up
            _bar(7, 101, 102, 99, 100),     # down
        ]
        ctx = analyze(bars, cfg, "15m")
        assert ctx.trend_strength == TrendStrength.WEAK

    def test_moderate_trend(self, cfg):
        """4 up closes out of 5 → 80% → boundary: STRONG. 3 out of 5 → 60% → MODERATE."""
        bars = [
            _bar(1, 100, 101, 99, 100.5),
            _bar(2, 100.5, 102, 100, 101.5),
            _bar(3, 101.5, 103, 101, 101.0),   # down close
            _bar(4, 101.0, 103, 100, 102.0),
            _bar(5, 102.0, 103, 101, 101.5),    # down close
            _bar(6, 101.5, 103, 101, 102.5),
        ]
        ctx = analyze(bars, cfg, "15m")
        assert ctx.trend == Trend.UP
        assert ctx.trend_strength in (TrendStrength.MODERATE, TrendStrength.WEAK)


# ---------------------------------------------------------------------------
# Trend location
# ---------------------------------------------------------------------------


class TestTrendLocation:
    def _make_trending_bars(self, start: float, end: float, n: int = 25):
        """Generate n bars trending from start to end price."""
        bars = []
        step = (end - start) / n
        for i in range(n):
            c = start + step * (i + 1)
            o = start + step * i
            h = max(o, c) + 0.5
            l = min(o, c) - 0.5
            bars.append(_bar(min(i + 1, 28), o, h, l, c))
        return bars

    def test_top_location(self, cfg):
        """Price near the top of a lookback range → TOP."""
        bars = self._make_trending_bars(90, 110, 25)
        ctx = analyze(bars, cfg, "15m")
        assert ctx.trend_location == TrendLocation.TOP

    def test_bottom_location(self, cfg):
        """Price near the bottom of a lookback range → BOTTOM."""
        bars = self._make_trending_bars(110, 90, 25)
        ctx = analyze(bars, cfg, "15m")
        assert ctx.trend_location == TrendLocation.BOTTOM

    def test_middle_location(self, cfg):
        """Price closes at 100, midpoint of [89, 111] range → MIDDLE.

        location_lookback=20. Bars 5-24 form the window, with extremes
        at 110 (high=111) and 90 (low=89), then settling at 100.
        pct = (100 - 89) / (111 - 89) ≈ 0.50 → MIDDLE.
        """
        bars = []
        for i in range(5):
            bars.append(_bar(min(i + 1, 28), 100, 101, 99, 100))
        for i in range(5, 8):
            bars.append(_bar(min(i + 1, 28), 109, 111, 109, 110))
        for i in range(8, 11):
            bars.append(_bar(min(i + 1, 28), 91, 91, 89, 90))
        for i in range(11, 25):
            bars.append(_bar(min(i + 1, 28), 100, 101, 99, 100))
        ctx = analyze(bars, cfg, "15m")
        assert ctx.trend_location == TrendLocation.MIDDLE

    def test_unknown_on_insufficient_data(self, cfg):
        bars = [_bar(1, 100, 101, 99, 100.5)]
        ctx = analyze(bars, cfg, "15m")
        assert ctx.trend_location == TrendLocation.UNKNOWN


# ---------------------------------------------------------------------------
# Congestion detection
# ---------------------------------------------------------------------------


class TestCongestion:
    def test_congestion_detected(self, cfg):
        """Tight recent range vs wide lookback → congestion active.

        Need: location_lookback=20 bars with a wide range, then
        congestion_window=10 most-recent bars in a very tight range.
        The tight range must be < congestion_pct (30%) of the wide range.
        """
        bars = []
        for i in range(1, 16):
            c = 80 + i * 2
            bars.append(_bar(min(i, 28), c - 1, c + 1, c - 2, c))
        for i in range(16, 26):
            bars.append(_bar(min(i, 28), 100, 100.2, 99.9, 100.1))
        ctx = analyze(bars, cfg, "15m")
        assert ctx.congestion.active is True
        assert ctx.congestion.range_high is not None
        assert ctx.congestion.range_low is not None

    def test_no_congestion_in_trend(self, cfg):
        """Wide recent range → no congestion."""
        bars = []
        for i in range(1, 25):
            c = 100 + i
            bars.append(_bar(min(i, 28), c - 1, c + 1, c - 2, c))
        ctx = analyze(bars, cfg, "15m")
        assert ctx.congestion.active is False

    def test_congestion_not_active_with_few_bars(self, cfg):
        bars = [_bar(1, 100, 101, 99, 100.5), _bar(2, 100.5, 101.5, 100, 101)]
        ctx = analyze(bars, cfg, "15m")
        assert ctx.congestion.active is False


# ---------------------------------------------------------------------------
# Dominant alignment
# ---------------------------------------------------------------------------


class TestDominantAlignment:
    def test_unknown_for_single_timeframe(self, cfg):
        """Without MTF data, dominant alignment should be UNKNOWN."""
        bars = [
            _bar(1, 100, 101, 99, 100.5),
            _bar(2, 100.5, 102, 100, 101.5),
            _bar(3, 101.5, 103, 101, 102.5),
        ]
        ctx = analyze(bars, cfg, "15m")
        assert ctx.dominant_alignment == DominantAlignment.UNKNOWN


# ---------------------------------------------------------------------------
# Integration: full snapshot
# ---------------------------------------------------------------------------


class TestFullSnapshot:
    def test_snapshot_has_all_fields(self, cfg):
        bars = [
            _bar(1, 100, 101, 99, 100.5),
            _bar(2, 100.5, 102, 100, 101.5),
            _bar(3, 101.5, 103, 101, 102.5),
        ]
        ctx = analyze(bars, cfg, "15m")
        assert ctx.tf == "15m"
        assert isinstance(ctx.trend, Trend)
        assert isinstance(ctx.trend_strength, TrendStrength)
        assert isinstance(ctx.trend_location, TrendLocation)
        assert isinstance(ctx.congestion, Congestion)
        assert isinstance(ctx.dominant_alignment, DominantAlignment)

    def test_config_driven_window(self):
        """location_lookback and congestion params come from config."""
        cfg = load_vpa_config()
        assert cfg.trend.location_lookback == 20
        assert cfg.trend.congestion_window == 10
        assert cfg.trend.congestion_pct == pytest.approx(0.30)


# ---------------------------------------------------------------------------
# Volume trend detection
# ---------------------------------------------------------------------------


class TestVolumeTrend:
    """Volume trend computed from bar-to-bar volume changes."""

    def test_rising_volume(self, cfg):
        """Each bar has higher volume than previous → RISING."""
        bars = [
            _bar(1, 100, 101, 99, 100.5, v=1000),
            _bar(2, 100.5, 102, 100, 101, v=1100),
            _bar(3, 101, 103, 100.5, 102, v=1200),
            _bar(4, 102, 104, 101, 103, v=1300),
            _bar(5, 103, 105, 102, 104, v=1400),
            _bar(6, 104, 106, 103, 105, v=1500),
        ]
        ctx = analyze(bars, cfg, "15m")
        assert ctx.volume_trend == VolumeTrend.RISING

    def test_falling_volume(self, cfg):
        """Each bar has lower volume than previous → FALLING."""
        bars = [
            _bar(1, 100, 101, 99, 100.5, v=1500),
            _bar(2, 100.5, 102, 100, 101, v=1400),
            _bar(3, 101, 103, 100.5, 102, v=1300),
            _bar(4, 102, 104, 101, 103, v=1200),
            _bar(5, 103, 105, 102, 104, v=1100),
            _bar(6, 104, 106, 103, 105, v=1000),
        ]
        ctx = analyze(bars, cfg, "15m")
        assert ctx.volume_trend == VolumeTrend.FALLING

    def test_flat_volume(self, cfg):
        """All bars have the same volume → FLAT."""
        bars = [
            _bar(1, 100, 101, 99, 100.5, v=1000),
            _bar(2, 100.5, 102, 100, 101, v=1000),
            _bar(3, 101, 103, 100.5, 102, v=1000),
            _bar(4, 102, 104, 101, 103, v=1000),
            _bar(5, 103, 105, 102, 104, v=1000),
            _bar(6, 104, 106, 103, 105, v=1000),
        ]
        ctx = analyze(bars, cfg, "15m")
        assert ctx.volume_trend == VolumeTrend.FLAT

    def test_unknown_on_single_bar(self, cfg):
        """Single bar → UNKNOWN volume trend (not enough data)."""
        bars = [_bar(1, 100, 101, 99, 100)]
        ctx = analyze(bars, cfg, "15m")
        assert ctx.volume_trend == VolumeTrend.UNKNOWN

    def test_mixed_mostly_rising(self, cfg):
        """Majority rising → RISING (3 up, 2 down in window of 5)."""
        bars = [
            _bar(1, 100, 101, 99, 100.5, v=1000),
            _bar(2, 100.5, 102, 100, 101, v=1200),
            _bar(3, 101, 103, 100.5, 102, v=1100),
            _bar(4, 102, 104, 101, 103, v=1300),
            _bar(5, 103, 105, 102, 104, v=1200),
            _bar(6, 104, 106, 103, 105, v=1400),
        ]
        ctx = analyze(bars, cfg, "15m")
        assert ctx.volume_trend == VolumeTrend.RISING
