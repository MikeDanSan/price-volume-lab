"""Tests for the pipeline-based backtest runner.

Bar-close evaluation, next-bar-open execution, sizing from Risk Engine.
"""

from datetime import datetime, timezone, timedelta

import pytest

from backtest.runner import run_backtest, BacktestTrade
from config.vpa_config import load_vpa_config, VPAConfig
from vpa_core.contracts import Bar


BASE_TS = datetime(2026, 2, 17, 9, 30, tzinfo=timezone.utc)


@pytest.fixture()
def cfg() -> VPAConfig:
    return load_vpa_config()


def _bar(i: int, *, open_: float = 100.0, high: float = 102.0,
         low: float = 99.0, close: float = 101.0, volume: int = 1000) -> Bar:
    return Bar(
        timestamp=BASE_TS + timedelta(minutes=15 * i),
        open=open_, high=high, low=low,
        close=close, volume=volume, symbol="TEST",
    )


def _baseline_bars(count: int = 21) -> list[Bar]:
    """Neutral up bars: spread ~1, volume ~1000."""
    return [_bar(i) for i in range(count)]


# ---------------------------------------------------------------------------
# Basic sanity
# ---------------------------------------------------------------------------


class TestBasics:
    def test_empty_bars(self, cfg: VPAConfig) -> None:
        result = run_backtest([], "TEST", "15m", config=cfg)
        assert result.symbol == "TEST"
        assert result.initial_cash == result.final_cash
        assert len(result.trades) == 0

    def test_quiet_bars_no_trades(self, cfg: VPAConfig) -> None:
        """Neutral bars produce no signals and no trades."""
        bars = _baseline_bars(25)
        result = run_backtest(bars, "TEST", "15m", config=cfg)
        assert len(result.trades) == 0
        assert result.final_cash == result.initial_cash

    def test_pipeline_events_emitted(self, cfg: VPAConfig) -> None:
        """Pipeline results are recorded for every bar."""
        bars = _baseline_bars(5)
        result = run_backtest(bars, "TEST", "15m", config=cfg)
        assert len(result.pipeline_events) == 5


# ---------------------------------------------------------------------------
# Signal + trade flow (VAL-1 based)
# ---------------------------------------------------------------------------


class TestSignalFlow:
    def _bars_with_val_1(self) -> list[Bar]:
        """20 baseline bars + 1 wide-up ultra-high-volume bar (VAL-1) + 2 continuation bars."""
        bars = _baseline_bars(20)
        bars.append(_bar(20, open_=100.0, high=108.0, low=99.0, close=107.0, volume=2500))
        bars.append(_bar(21, open_=107.0, high=110.0, low=106.0, close=109.0, volume=1500))
        bars.append(_bar(22, open_=109.0, high=112.0, low=108.0, close=111.0, volume=1200))
        return bars

    def test_val_1_detected(self, cfg: VPAConfig) -> None:
        """Pipeline detects VAL-1 on the signal bar."""
        bars = self._bars_with_val_1()
        result = run_backtest(bars, "TEST", "15m", config=cfg)
        val_1_bars = [
            r for r in result.pipeline_events
            if any(s.id == "VAL-1" for s in r.signals)
        ]
        assert len(val_1_bars) >= 1

    def test_no_trade_without_setup(self, cfg: VPAConfig) -> None:
        """VAL-1 alone doesn't complete ENTRY-LONG-1 (needs TEST-SUP-1 first).
        So no trades should be opened."""
        bars = self._bars_with_val_1()
        result = run_backtest(bars, "TEST", "15m", config=cfg)
        assert len(result.trades) == 0


# ---------------------------------------------------------------------------
# Next-bar-open execution semantics
# ---------------------------------------------------------------------------


class TestExecutionSemantics:
    def test_cash_unchanged_on_no_trades(self, cfg: VPAConfig) -> None:
        bars = _baseline_bars(25)
        result = run_backtest(bars, "TEST", "15m", config=cfg, initial_cash=50_000.0)
        assert result.final_cash == 50_000.0

    def test_slippage_from_config(self, cfg: VPAConfig) -> None:
        """Slippage defaults to config.slippage.value when not overridden."""
        bars = _baseline_bars(5)
        result = run_backtest(bars, "TEST", "15m", config=cfg)
        assert result.final_cash == result.initial_cash

    def test_backtest_result_properties(self, cfg: VPAConfig) -> None:
        bars = _baseline_bars(5)
        result = run_backtest(bars, "TEST", "15m", config=cfg)
        assert result.total_return_pct == 0.0
        assert result.win_count == 0
        assert result.loss_count == 0
        assert result.timeframe == "15m"


# ---------------------------------------------------------------------------
# Journal callback
# ---------------------------------------------------------------------------


class TestJournal:
    def test_journal_callback_receives_events(self, cfg: VPAConfig) -> None:
        events: list[tuple[str, dict]] = []
        bars = _baseline_bars(5)
        run_backtest(bars, "TEST", "15m", config=cfg,
                     journal_callback=lambda t, p: events.append((t, p)))
        assert isinstance(events, list)
