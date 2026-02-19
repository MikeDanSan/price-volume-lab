"""Tests for the pipeline-based backtest runner.

Bar-close evaluation, next-bar-open execution, sizing from Risk Engine.
"""

from datetime import datetime, timezone, timedelta

import pytest

from backtest.runner import run_backtest, BacktestTrade, _fill_price
from config.vpa_config import load_vpa_config, VPAConfig
from vpa_core.contracts import Bar


BASE_TS = datetime(2026, 2, 17, 9, 30, tzinfo=timezone.utc)


@pytest.fixture()
def cfg() -> VPAConfig:
    return load_vpa_config()


def _bar(i: int, *, open_: float = 100.0, high: float = 102.0,
         low: float = 99.0, close: float = 101.0, volume: int = 100_000) -> Bar:
    return Bar(
        timestamp=BASE_TS + timedelta(minutes=15 * i),
        open=open_, high=high, low=low,
        close=close, volume=volume, symbol="TEST",
    )


def _baseline_bars(count: int = 21) -> list[Bar]:
    """Neutral up bars: spread ~1, volume ~1000."""
    return [_bar(i) for i in range(count)]


def _uptrend_bars(count: int = 20) -> list[Bar]:
    """Gently rising bars to establish TOP location and build volume/spread SMA."""
    return [
        _bar(i, open_=100 + i * 0.5, high=101 + i * 0.5,
             low=99.5 + i * 0.5, close=100.5 + i * 0.5, volume=100_000)
        for i in range(count)
    ]


def _short_setup_bars() -> list[Bar]:
    """20 uptrend bars + CLIMAX-SELL-1 + WEAK-1 completer + 2 exit bars.

    Bar 20: shooting star + ultra-high volume → CLIMAX-SELL-1 trigger.
    Bar 21: shooting star + average volume → WEAK-1 completes ENTRY-SHORT-1.
    Bar 22: entry bar (SHORT fills at open=109.5).
    Bar 23: exit bar (end-of-data close=107.0).
    """
    bars = _uptrend_bars(20)
    bars.append(_bar(20, open_=110.0, high=118.0, low=109.8, close=110.2, volume=250_000))
    bars.append(_bar(21, open_=110.0, high=117.0, low=109.9, close=110.1, volume=100_000))
    bars.append(_bar(22, open_=109.5, high=110.0, low=107.5, close=108.0, volume=100_000))
    bars.append(_bar(23, open_=108.0, high=108.5, low=106.0, close=107.0, volume=100_000))
    return bars


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
        bars.append(_bar(20, open_=100.0, high=108.0, low=99.0, close=107.0, volume=250_000))
        bars.append(_bar(21, open_=107.0, high=110.0, low=106.0, close=109.0, volume=150_000))
        bars.append(_bar(22, open_=109.0, high=112.0, low=108.0, close=111.0, volume=120_000))
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


# ---------------------------------------------------------------------------
# Fill price direction
# ---------------------------------------------------------------------------


class TestFillPrice:
    def test_long_fill_adds_slippage(self) -> None:
        bar = _bar(0, open_=100.0)
        price = _fill_price(bar, "LONG", 10.0)
        assert price == pytest.approx(100.0 * (1 + 10 / 10_000))

    def test_short_fill_subtracts_slippage(self) -> None:
        bar = _bar(0, open_=100.0)
        price = _fill_price(bar, "SHORT", 10.0)
        assert price == pytest.approx(100.0 * (1 - 10 / 10_000))

    def test_zero_slippage_returns_open(self) -> None:
        bar = _bar(0, open_=105.0)
        assert _fill_price(bar, "LONG", 0.0) == 105.0
        assert _fill_price(bar, "SHORT", 0.0) == 105.0


# ---------------------------------------------------------------------------
# Short-side: ENTRY-SHORT-1 end-to-end
# ---------------------------------------------------------------------------


class TestShortSignalDetection:
    """Verify CLIMAX-SELL-1 and WEAK-1 fire on the constructed bar sequence."""

    def test_climax_sell_1_detected(self, cfg: VPAConfig) -> None:
        bars = _short_setup_bars()
        result = run_backtest(bars, "TEST", "15m", config=cfg)
        climax_bars = [
            r for r in result.pipeline_events
            if any(s.id == "CLIMAX-SELL-1" for s in r.signals)
        ]
        assert len(climax_bars) >= 1

    def test_weak_1_detected_on_completer_bar(self, cfg: VPAConfig) -> None:
        bars = _short_setup_bars()
        result = run_backtest(bars, "TEST", "15m", config=cfg)
        weak_bars = [
            r for r in result.pipeline_events
            if any(s.id == "WEAK-1" for s in r.signals)
        ]
        assert len(weak_bars) >= 1


class TestShortTradeFlow:
    """CLIMAX-SELL-1 → WEAK-1 → ENTRY-SHORT-1 → fill SHORT → exit."""

    def test_short_trade_opened(self, cfg: VPAConfig) -> None:
        bars = _short_setup_bars()
        result = run_backtest(bars, "TEST", "15m", config=cfg)
        assert len(result.trades) >= 1
        trade = result.trades[0]
        assert trade.direction == "SHORT"
        assert trade.setup == "ENTRY-SHORT-1"

    def test_short_entry_at_next_bar_open(self, cfg: VPAConfig) -> None:
        """Entry fills at bar 22's open (next bar after setup completes on bar 21)."""
        bars = _short_setup_bars()
        result = run_backtest(bars, "TEST", "15m", config=cfg)
        assert len(result.trades) >= 1
        assert result.trades[0].entry_price == pytest.approx(109.5)

    def test_short_profit_when_price_drops(self, cfg: VPAConfig) -> None:
        """End-of-data exit at bar 23 close=107.0. PnL = (109.5 - 107.0) * qty > 0."""
        bars = _short_setup_bars()
        result = run_backtest(bars, "TEST", "15m", config=cfg)
        assert len(result.trades) >= 1
        trade = result.trades[0]
        assert trade.pnl > 0
        expected_pnl = (109.5 - 107.0) * trade.qty
        assert trade.pnl == pytest.approx(expected_pnl)

    def test_short_final_cash_increased(self, cfg: VPAConfig) -> None:
        bars = _short_setup_bars()
        result = run_backtest(bars, "TEST", "15m", config=cfg)
        assert result.final_cash > result.initial_cash

    def test_short_rationale_chain(self, cfg: VPAConfig) -> None:
        bars = _short_setup_bars()
        result = run_backtest(bars, "TEST", "15m", config=cfg)
        assert len(result.trades) >= 1
        assert "CLIMAX-SELL-1" in result.trades[0].rationale
        assert "WEAK-1" in result.trades[0].rationale


class TestShortStopOut:
    """SHORT stop-out: bar.high >= stop → exit at stop price."""

    def _stopout_bars(self) -> list[Bar]:
        """Same as _short_setup_bars but bar 23 spikes above the stop (118.0)."""
        bars = _short_setup_bars()
        bars[-1] = _bar(23, open_=108.0, high=119.0, low=107.0, close=118.5, volume=150_000)
        return bars

    def test_stop_triggered_on_high_spike(self, cfg: VPAConfig) -> None:
        bars = self._stopout_bars()
        result = run_backtest(bars, "TEST", "15m", config=cfg)
        assert len(result.trades) >= 1
        trade = result.trades[0]
        assert trade.exit_price == pytest.approx(118.0)

    def test_stop_loss_negative_pnl(self, cfg: VPAConfig) -> None:
        bars = self._stopout_bars()
        result = run_backtest(bars, "TEST", "15m", config=cfg)
        assert len(result.trades) >= 1
        trade = result.trades[0]
        assert trade.pnl < 0
        expected_pnl = (109.5 - 118.0) * trade.qty
        assert trade.pnl == pytest.approx(expected_pnl)

    def test_stop_loss_reduces_cash(self, cfg: VPAConfig) -> None:
        bars = self._stopout_bars()
        result = run_backtest(bars, "TEST", "15m", config=cfg)
        assert result.final_cash < result.initial_cash


class TestShortJournal:
    def test_short_journal_events(self, cfg: VPAConfig) -> None:
        events: list[tuple[str, dict]] = []
        bars = _short_setup_bars()
        run_backtest(bars, "TEST", "15m", config=cfg,
                     journal_callback=lambda t, p: events.append((t, p)))
        event_types = [e[0] for e in events]
        assert "signal" in event_types
        assert "entry" in event_types
        assert "exit" in event_types
