"""Tests for paper execution. Single writer; restart-safe."""

import tempfile
from datetime import datetime, timezone

import pytest

from execution.paper_executor import PaperExecutor
from vpa_core.contracts import TradePlan


def test_paper_executor_submit_long() -> None:
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name
    try:
        ex = PaperExecutor(path, initial_cash=100_000.0)
        plan = TradePlan(
            signal_id="sig1",
            setup_type="no_demand",
            direction="long",
            entry_condition="next_bar_open",
            stop_level=99.0,
            invalidation_rules=[],
            rationale="Test",
            rulebook_ref="no_demand",
        )
        order = ex.submit("SPY", plan, current_price=100.0)
        assert order is not None
        assert order.symbol == "SPY"
        assert order.side == "buy"
        assert order.qty > 0
        pos = ex.get_position("SPY")
        assert pos is not None
        assert pos.side == "long"
        assert pos.qty == order.qty
        fills = ex.list_fills(symbol="SPY")
        assert len(fills) == 1
    finally:
        import os
        os.unlink(path)


def test_paper_executor_rejects_second_position() -> None:
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name
    try:
        ex = PaperExecutor(path, initial_cash=100_000.0)
        plan = TradePlan(
            signal_id="sig1",
            setup_type="no_demand",
            direction="long",
            entry_condition="next_bar_open",
            stop_level=99.0,
            invalidation_rules=[],
            rationale="Test",
            rulebook_ref="no_demand",
        )
        ex.submit("SPY", plan, current_price=100.0)
        order2 = ex.submit("SPY", plan, current_price=101.0)
        assert order2 is None
    finally:
        import os
        os.unlink(path)
