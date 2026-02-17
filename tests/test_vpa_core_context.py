"""Unit tests for context detection. Deterministic."""

import pytest

from vpa_core.context import CONTEXT_DOWNTREND, CONTEXT_RANGE, CONTEXT_UPTREND, detect_context


def test_detect_uptrend(uptrend_bars: list) -> None:
    assert detect_context(uptrend_bars, lookback=4) == CONTEXT_UPTREND


def test_detect_downtrend(symbol: str) -> None:
    from datetime import datetime, timezone
    from vpa_core.contracts import Bar
    ts = datetime.now(timezone.utc)
    bars = [
        Bar(102.0, 103.0, 101.0, 102.5, 1000, ts, symbol),
        Bar(102.5, 103.0, 101.5, 102.0, 1000, ts, symbol),
        Bar(102.0, 102.5, 101.0, 101.5, 1000, ts, symbol),
        Bar(101.5, 102.0, 100.5, 101.0, 1000, ts, symbol),
        Bar(101.0, 101.5, 100.0, 100.5, 1000, ts, symbol),
    ]
    assert detect_context(bars, lookback=4) == CONTEXT_DOWNTREND


def test_detect_range_insufficient_bars(symbol: str) -> None:
    from datetime import datetime, timezone
    from vpa_core.contracts import Bar
    ts = datetime.now(timezone.utc)
    bars = [
        Bar(100.0, 101.0, 99.0, 100.5, 1000, ts, symbol),
        Bar(100.5, 101.5, 100.0, 101.0, 1000, ts, symbol),
    ]
    assert detect_context(bars, lookback=5) == CONTEXT_RANGE
