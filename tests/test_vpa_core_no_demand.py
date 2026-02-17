"""Unit tests for No Demand setup. Fidelity to rulebook; deterministic."""

from vpa_core.contracts import Bar, ContextWindow
from vpa_core.signals import evaluate
from vpa_core.setups.no_demand import check_no_demand


def test_no_demand_detected(no_demand_bar_sequence: list[Bar], symbol: str) -> None:
    bars = no_demand_bar_sequence
    assert check_no_demand(bars) is True
    window = ContextWindow(bars=bars, symbol=symbol)
    results = evaluate(window)
    assert len(results) == 1
    signal, trade_plan = results[0]
    assert signal.setup_type == "no_demand"
    assert signal.direction == "short"
    assert signal.rulebook_ref == "no_demand"
    assert trade_plan.setup_type == "no_demand"
    assert "no demand" in signal.rationale.lower()


def test_no_demand_not_detected_on_down_bar(down_bar_sequence: list[Bar], symbol: str) -> None:
    assert check_no_demand(down_bar_sequence) is False
    window = ContextWindow(bars=down_bar_sequence, symbol=symbol)
    assert len(evaluate(window)) == 0


def test_no_demand_not_detected_uptrend_high_volume(uptrend_bars: list[Bar], symbol: str) -> None:
    # Last bar is up but volume is not clearly low (900k vs ~1.1M); may or may not trigger
    # depending on threshold. For strict test: use bars that are clearly high volume on last bar
    bars = list(uptrend_bars)
    # Replace last bar with same close but very high volume
    last = bars[-1]
    bars[-1] = Bar(
        last.open, last.high, last.low, last.close,
        2_000_000, last.timestamp, last.symbol,
    )
    assert check_no_demand(bars) is False
    window = ContextWindow(bars=bars, symbol=symbol)
    assert len(evaluate(window)) == 0


def test_evaluate_empty_window(symbol: str) -> None:
    window = ContextWindow(bars=[], symbol=symbol)
    assert evaluate(window) == []
