"""Unit tests for candle features and relative volume. Deterministic."""

from datetime import datetime, timezone

import pytest

from vpa_core.contracts import Bar, RelativeVolume
from vpa_core.features import bar_range, body, close_location, lower_wick, spread, upper_wick
from vpa_core.relative_volume import (
    average_volume,
    classify_relative_volume,
    relative_volume_for_bar,
)


def test_spread_is_body() -> None:
    """Spread = |close - open| per canonical glossary (candle body)."""
    bar = Bar(100.0, 105.0, 99.0, 104.0, 1000, datetime.now(timezone.utc), "SPY")
    assert spread(bar) == 4.0


def test_spread_equals_body() -> None:
    """spread() and body() must return the same value."""
    bar = Bar(100.0, 105.0, 99.0, 104.0, 1000, datetime.now(timezone.utc), "SPY")
    assert spread(bar) == body(bar)


def test_bar_range() -> None:
    """bar_range = high - low (full candle extent)."""
    bar = Bar(100.0, 105.0, 99.0, 104.0, 1000, datetime.now(timezone.utc), "SPY")
    assert bar_range(bar) == 6.0


def test_body() -> None:
    bar = Bar(100.0, 105.0, 99.0, 104.0, 1000, datetime.now(timezone.utc), "SPY")
    assert body(bar) == 4.0


def test_upper_wick() -> None:
    """Upper wick = high - max(open, close)."""
    bar = Bar(100.0, 105.0, 99.0, 104.0, 1000, datetime.now(timezone.utc), "SPY")
    assert upper_wick(bar) == 1.0  # 105 - 104


def test_lower_wick() -> None:
    """Lower wick = min(open, close) - low."""
    bar = Bar(100.0, 105.0, 99.0, 104.0, 1000, datetime.now(timezone.utc), "SPY")
    assert lower_wick(bar) == 1.0  # 100 - 99


def test_bar_spread_method_matches_feature() -> None:
    """Bar.spread() method must agree with features.spread() function."""
    bar = Bar(100.0, 105.0, 99.0, 104.0, 1000, datetime.now(timezone.utc), "SPY")
    assert bar.spread() == spread(bar)
    assert bar.body() == body(bar)
    assert bar.bar_range() == bar_range(bar)


def test_close_location_upper() -> None:
    bar = Bar(100.0, 110.0, 100.0, 107.0, 1000, datetime.now(timezone.utc), "SPY")
    assert close_location(bar) == "upper"


def test_close_location_lower() -> None:
    bar = Bar(110.0, 110.0, 100.0, 102.0, 1000, datetime.now(timezone.utc), "SPY")
    assert close_location(bar) == "lower"


def test_close_location_middle() -> None:
    bar = Bar(100.0, 110.0, 100.0, 105.0, 1000, datetime.now(timezone.utc), "SPY")
    assert close_location(bar) == "middle"


def test_classify_relative_volume() -> None:
    assert classify_relative_volume(120, 100.0) == RelativeVolume.HIGH
    assert classify_relative_volume(80, 100.0) == RelativeVolume.LOW
    assert classify_relative_volume(100, 100.0) == RelativeVolume.NORMAL


def test_average_volume() -> None:
    ts = datetime.now(timezone.utc)
    bars = [
        Bar(100.0, 101.0, 99.0, 100.5, 100, ts, "SPY"),
        Bar(100.5, 101.5, 100.0, 101.0, 200, ts, "SPY"),
        Bar(101.0, 102.0, 100.5, 101.5, 300, ts, "SPY"),
    ]
    assert average_volume(bars, lookback=2) == 150.0  # (100+200)/2 for bars before last


def test_relative_volume_for_bar_low(no_demand_bar_sequence: list[Bar]) -> None:
    rv = relative_volume_for_bar(no_demand_bar_sequence)
    assert rv == RelativeVolume.LOW


def test_relative_volume_for_bar_high(uptrend_bars: list[Bar]) -> None:
    # Last bar volume 900k vs ~1.1M avg -> still in normal or low range
    rv = relative_volume_for_bar(uptrend_bars)
    assert rv in (RelativeVolume.NORMAL, RelativeVolume.LOW)
