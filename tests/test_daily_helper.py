"""Tests for the daily context helper (load_daily_context)."""

import tempfile
from datetime import datetime, timezone

import pytest

from config.vpa_config import load_vpa_config
from data.bar_store import BarStore
from vpa_core.contracts import Bar, DominantAlignment, Trend
from cli.daily_helper import load_daily_context, MIN_DAILY_BARS


def _cfg():
    return load_vpa_config()


def _daily_bar(day: int, close: float, volume: int = 50_000_000) -> Bar:
    ts = datetime(2024, 1, day, 0, 0, tzinfo=timezone.utc)
    return Bar(
        open=close - 0.5, high=close + 1.0, low=close - 1.5,
        close=close, volume=volume, timestamp=ts, symbol="SPY",
    )


def _uptrend_daily_bars(n: int = 25) -> list[Bar]:
    return [_daily_bar(i + 1, 400.0 + i * 1.5) for i in range(n)]


class TestLoadDailyContext:

    def test_returns_context_when_enough_bars(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            path = f.name
        store = BarStore(path)
        store.write_bars("SPY", "1d", _uptrend_daily_bars(25))

        ctx = load_daily_context(store, "SPY", _cfg())
        assert ctx is not None
        assert ctx.tf == "1d"
        assert ctx.trend == Trend.UP

    def test_returns_none_when_too_few_bars(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            path = f.name
        store = BarStore(path)
        store.write_bars("SPY", "1d", _uptrend_daily_bars(5))

        ctx = load_daily_context(store, "SPY", _cfg())
        assert ctx is None

    def test_returns_none_when_no_daily_bars(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            path = f.name
        store = BarStore(path)

        ctx = load_daily_context(store, "SPY", _cfg())
        assert ctx is None

    def test_uses_correct_symbol(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            path = f.name
        store = BarStore(path)
        store.write_bars("SPY", "1d", _uptrend_daily_bars(25))

        ctx = load_daily_context(store, "AAPL", _cfg())
        assert ctx is None

    def test_daily_lookback_limits_bars(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            path = f.name
        store = BarStore(path)
        store.write_bars("SPY", "1d", _uptrend_daily_bars(25))

        ctx = load_daily_context(store, "SPY", _cfg(), daily_lookback=15)
        assert ctx is not None

    def test_exactly_min_bars_returns_context(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            path = f.name
        store = BarStore(path)
        store.write_bars("SPY", "1d", _uptrend_daily_bars(MIN_DAILY_BARS))

        ctx = load_daily_context(store, "SPY", _cfg())
        assert ctx is not None
