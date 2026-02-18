"""
Event-driven backtest: replay bars in order, run pipeline per bar, simulate fills.

No lookahead. Bar-close evaluation, next-bar-open execution.
Sizing delegated entirely to the Risk Engine via the pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable

from config.vpa_config import VPAConfig, load_vpa_config
from vpa_core.contracts import (
    Bar,
    TradeIntent,
    TradeIntentStatus,
)
from vpa_core.context_engine import analyze as analyze_context
from vpa_core.pipeline import PipelineResult, run_pipeline
from vpa_core.risk_engine import AccountState
from vpa_core.setup_composer import SetupComposer


@dataclass
class BacktestTrade:
    """One round-trip trade in backtest."""

    symbol: str
    direction: str
    entry_time: datetime
    entry_price: float
    exit_time: datetime
    exit_price: float
    qty: int | float
    pnl: float
    setup: str
    rationale: list[str]


@dataclass
class BacktestResult:
    """Result of a backtest run."""

    symbol: str
    timeframe: str
    start_time: datetime
    end_time: datetime
    initial_cash: float
    final_cash: float
    trades: list[BacktestTrade] = field(default_factory=list)
    pipeline_events: list[PipelineResult] = field(default_factory=list)

    @property
    def total_return_pct(self) -> float:
        if self.initial_cash <= 0:
            return 0.0
        return (self.final_cash - self.initial_cash) / self.initial_cash * 100

    @property
    def win_count(self) -> int:
        return sum(1 for t in self.trades if t.pnl > 0)

    @property
    def loss_count(self) -> int:
        return sum(1 for t in self.trades if t.pnl < 0)


def _fill_price(bar: Bar, direction: str, slippage_bps: float) -> float:
    """Simulate fill at bar open with slippage (bps)."""
    price = bar.open
    bps = slippage_bps / 10_000
    if direction == "LONG":
        return price * (1 + bps)
    return price * (1 - bps)


@dataclass
class _OpenPosition:
    """Tracks an open position during backtest."""
    intent: TradeIntent
    entry_price: float
    qty: int
    entry_bar_idx: int
    stop: float


def run_backtest(
    bars: list[Bar],
    symbol: str,
    timeframe: str,
    *,
    config: VPAConfig | None = None,
    initial_cash: float = 100_000.0,
    slippage_bps: float | None = None,
    journal_callback: Callable[[str, dict], None] | None = None,
) -> BacktestResult:
    """Replay bars through the canonical pipeline. Next-bar-open execution.

    Parameters
    ----------
    bars:
        Chronological bar history for one symbol.
    symbol:
        Ticker symbol.
    timeframe:
        Timeframe label (e.g. "15m").
    config:
        VPA configuration. Loaded from default if None.
    initial_cash:
        Starting equity.
    slippage_bps:
        Override slippage in basis points. If None, uses config.slippage.value.
    journal_callback:
        Optional callback for event journaling.
    """
    if config is None:
        config = load_vpa_config()

    if slippage_bps is None:
        slippage_bps = config.slippage.value

    now = datetime.now(timezone.utc)
    start_time = bars[0].timestamp if bars else now
    end_time = bars[-1].timestamp if bars else now

    cash = initial_cash
    daily_pnl = 0.0
    composer = SetupComposer(config)
    position: _OpenPosition | None = None
    pending_intent: TradeIntent | None = None
    trades: list[BacktestTrade] = []
    pipeline_events: list[PipelineResult] = []

    for i in range(len(bars)):
        current_bars = bars[: i + 1]
        current_bar = bars[i]

        # --- Execute pending intent at this bar's open (next-bar execution) ---
        if pending_intent is not None and position is None:
            entry_price = _fill_price(current_bar, pending_intent.direction, slippage_bps)
            position = _OpenPosition(
                intent=pending_intent,
                entry_price=entry_price,
                qty=pending_intent.risk_plan.size,
                entry_bar_idx=i,
                stop=pending_intent.risk_plan.stop,
            )
            if journal_callback:
                journal_callback("entry", {
                    "intent_id": pending_intent.intent_id,
                    "bar_index": i,
                    "entry_price": entry_price,
                    "qty": pending_intent.risk_plan.size,
                })
            pending_intent = None

        # --- Check stop on open position ---
        if position is not None:
            exited = False
            exit_price = 0.0
            exit_reason = ""

            if position.intent.direction == "LONG" and current_bar.low <= position.stop:
                exit_price = position.stop * (1 - slippage_bps / 10_000)
                exited = True
                exit_reason = "stop"
            elif position.intent.direction == "SHORT" and current_bar.high >= position.stop:
                exit_price = position.stop * (1 + slippage_bps / 10_000)
                exited = True
                exit_reason = "stop"
            elif i == len(bars) - 1:
                exit_price = current_bar.close
                exited = True
                exit_reason = "end_of_data"

            if exited:
                if position.intent.direction == "LONG":
                    pnl = (exit_price - position.entry_price) * position.qty
                else:
                    pnl = (position.entry_price - exit_price) * position.qty

                cash += pnl
                daily_pnl += pnl

                trade = BacktestTrade(
                    symbol=symbol,
                    direction=position.intent.direction,
                    entry_time=bars[position.entry_bar_idx].timestamp,
                    entry_price=position.entry_price,
                    exit_time=current_bar.timestamp,
                    exit_price=exit_price,
                    qty=position.qty,
                    pnl=pnl,
                    setup=position.intent.setup,
                    rationale=position.intent.rationale,
                )
                trades.append(trade)

                if journal_callback:
                    journal_callback("exit", {
                        "trade": trade,
                        "reason": exit_reason,
                    })
                position = None
                continue

        # --- Run pipeline on completed bar ---
        open_count = 1 if position is not None else 0
        account = AccountState(
            equity=cash,
            open_position_count=open_count,
            daily_realized_pnl=daily_pnl,
        )
        context = analyze_context(current_bars, config, timeframe)

        result = run_pipeline(
            bars=current_bars,
            bar_index=i,
            context=context,
            account=account,
            config=config,
            composer=composer,
            tf=timeframe,
        )
        pipeline_events.append(result)

        # --- Queue the first READY intent for next-bar execution ---
        if position is None and pending_intent is None and i + 1 < len(bars):
            for intent in result.intents:
                if intent.status == TradeIntentStatus.READY:
                    pending_intent = intent
                    if journal_callback:
                        journal_callback("signal", {
                            "intent": intent,
                            "bar_index": i,
                        })
                    break

    return BacktestResult(
        symbol=symbol,
        timeframe=timeframe,
        start_time=start_time,
        end_time=end_time,
        initial_cash=initial_cash,
        final_cash=cash,
        trades=trades,
        pipeline_events=pipeline_events,
    )
