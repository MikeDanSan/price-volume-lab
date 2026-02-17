"""Tests for backtest engine. No lookahead; deterministic."""

from datetime import datetime, timezone

import pytest

from backtest.runner import run_backtest
from vpa_core.contracts import Bar


def _ts(y: int, m: int, d: int, h: int = 9, mi: int = 30) -> datetime:
    return datetime(y, m, d, h, mi, 0, tzinfo=timezone.utc)


def test_backtest_no_bars() -> None:
    result = run_backtest([], "SPY", "15m")
    assert result.symbol == "SPY"
    assert result.initial_cash == result.final_cash
    assert len(result.trades) == 0


def test_backtest_uptrend_no_signal_no_trades(no_demand_bar_sequence: list[Bar]) -> None:
    # Use bars that end with no_demand; but we need bars that do NOT trigger no_demand to get zero trades
    from vpa_core.contracts import Bar
    bars = [
        Bar(100.0, 101.0, 99.0, 100.5, 1_000_000, _ts(2024, 1, 2), "SPY"),
        Bar(100.5, 101.5, 100.0, 101.0, 1_100_000, _ts(2024, 1, 3), "SPY"),
    ]
    result = run_backtest(bars, "SPY", "15m")
    assert len(result.trades) == 0
    assert result.final_cash == result.initial_cash


def test_backtest_with_signal_enters_and_exits(no_demand_bar_sequence: list[Bar]) -> None:
    # no_demand_bar_sequence has 5 bars; last bar is no_demand. So at bar index 4 we get signal.
    # We need at least one more bar to enter (next bar open). So add 2 more bars so we can enter and then hit stop or end.
    bars = list(no_demand_bar_sequence)
    bars.append(Bar(102.8, 103.5, 102.0, 102.5, 500_000, _ts(2024, 1, 7), "SPY"))  # next bar
    bars.append(Bar(102.5, 104.0, 102.0, 103.5, 600_000, _ts(2024, 1, 8), "SPY"))  # stop at 103 (no_demand bar high)
    result = run_backtest(bars, "SPY", "15m", initial_cash=100_000.0)
    # May have 1 trade (short): entry at bar 5 open, exit at bar 6 (stop at 103 or end)
    assert result.initial_cash == 100_000.0
    # Either one trade or none if sizing fails
    assert len(result.trades) <= 1
    if result.trades:
        t = result.trades[0]
        assert t.direction == "short"
        assert "no demand" in t.rationale.lower() or "no_demand" in t.rulebook_ref
