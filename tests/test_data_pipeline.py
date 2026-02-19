"""Integration tests for data pipeline: bar store and context window."""

import tempfile
from datetime import datetime, timezone

import pytest

from data.bar_store import BarStore
from data.context_window import get_context_window
from vpa_core.contracts import Bar


def _ts(y: int, m: int, d: int) -> datetime:
    return datetime(y, m, d, 9, 30, 0, tzinfo=timezone.utc)


def test_bar_store_write_and_get() -> None:
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name
    try:
        store = BarStore(path)
        bars = [
            Bar(100.0, 101.0, 99.0, 100.5, 1_000_000, _ts(2024, 1, 2), "SPY"),
            Bar(100.5, 101.5, 100.0, 101.0, 1_100_000, _ts(2024, 1, 3), "SPY"),
        ]
        store.write_bars("SPY", "15m", bars)
        out = store.get_bars("SPY", "15m")
        assert len(out) == 2
        assert out[0].close == 100.5
        assert out[1].close == 101.0
    finally:
        import os
        os.unlink(path)


def test_get_last_bars() -> None:
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name
    try:
        store = BarStore(path)
        bars = [
            Bar(100.0 + i * 0.5, 101.0, 99.0, 100.5 + i * 0.5, 1_000_000, _ts(2024, 1, 2 + i), "SPY")
            for i in range(5)
        ]
        store.write_bars("SPY", "15m", bars)
        last3 = store.get_last_bars("SPY", "15m", 3)
        assert len(last3) == 3
        assert last3[0].timestamp.day == 4
        assert last3[-1].timestamp.day == 6
    finally:
        import os
        os.unlink(path)


def test_count_bars() -> None:
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name
    try:
        store = BarStore(path)
        bars = [
            Bar(100.0 + i, 101.0, 99.0, 100.5, 1_000_000, _ts(2024, 1, 2 + i), "SPY")
            for i in range(5)
        ]
        store.write_bars("SPY", "15m", bars)
        assert store.count_bars("SPY", "15m") == 5
        assert store.count_bars("SPY", "1d") == 0
        assert store.count_bars("AAPL", "15m") == 0
    finally:
        import os
        os.unlink(path)


def test_multi_timeframe_isolation() -> None:
    """Daily and intraday bars coexist independently in the same database."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name
    try:
        store = BarStore(path)

        intraday = [
            Bar(100.0, 101.0, 99.0, 100.5, 500_000, _ts(2024, 1, 2), "SPY"),
            Bar(100.5, 101.5, 100.0, 101.0, 550_000, _ts(2024, 1, 3), "SPY"),
            Bar(101.0, 102.0, 100.5, 101.5, 520_000, _ts(2024, 1, 4), "SPY"),
        ]
        store.write_bars("SPY", "15m", intraday)

        daily = [
            Bar(99.0, 102.0, 98.0, 101.0, 80_000_000, _ts(2024, 1, 2), "SPY"),
            Bar(101.0, 103.0, 100.0, 102.5, 75_000_000, _ts(2024, 1, 3), "SPY"),
        ]
        store.write_bars("SPY", "1d", daily)

        assert store.count_bars("SPY", "15m") == 3
        assert store.count_bars("SPY", "1d") == 2

        intraday_out = store.get_bars("SPY", "15m")
        daily_out = store.get_bars("SPY", "1d")

        assert len(intraday_out) == 3
        assert len(daily_out) == 2

        assert intraday_out[0].volume == 500_000
        assert daily_out[0].volume == 80_000_000
    finally:
        import os
        os.unlink(path)


def test_daily_get_last_bars() -> None:
    """get_last_bars works correctly for daily timeframe."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name
    try:
        store = BarStore(path)
        daily = [
            Bar(100.0 + i, 102.0 + i, 99.0 + i, 101.0 + i, 50_000_000, _ts(2024, 1, 2 + i), "SPY")
            for i in range(30)
        ]
        store.write_bars("SPY", "1d", daily)

        last_20 = store.get_last_bars("SPY", "1d", 20)
        assert len(last_20) == 20
        assert last_20[0].timestamp.day == 12
        assert last_20[-1].timestamp.day == 31
    finally:
        import os
        os.unlink(path)


def test_upsert_does_not_duplicate() -> None:
    """Writing the same bar twice (same symbol, tf, ts) replaces, not duplicates."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name
    try:
        store = BarStore(path)
        bar = Bar(100.0, 101.0, 99.0, 100.5, 1_000_000, _ts(2024, 1, 2), "SPY")
        store.write_bars("SPY", "1d", [bar])
        store.write_bars("SPY", "1d", [bar])
        assert store.count_bars("SPY", "1d") == 1
    finally:
        import os
        os.unlink(path)


def test_get_context_window() -> None:
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name
    try:
        store = BarStore(path)
        bars = [
            Bar(100.0 + i * 0.5, 101.0, 99.0, 100.5 + i * 0.5, 1_000_000, _ts(2024, 1, 2 + i), "SPY")
            for i in range(5)
        ]
        store.write_bars("SPY", "15m", bars)
        window = get_context_window(store, "SPY", "15m", window_size=10)
        assert window is not None
        assert len(window.bars) == 5
        assert window.symbol == "SPY"
        assert window.timeframe == "15m"
    finally:
        import os
        os.unlink(path)
