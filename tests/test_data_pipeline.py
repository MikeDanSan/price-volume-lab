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
