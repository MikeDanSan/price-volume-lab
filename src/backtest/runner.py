"""
Event-driven backtest: replay bars in order, call vpa-core per bar, simulate fills.
No lookahead. Produces metrics and trade log.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable

from vpa_core.contracts import Bar, ContextWindow, TradePlan
from vpa_core.signals import evaluate


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
    rationale: str
    rulebook_ref: str


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


def _fill_price(bar: Bar, side: str, slippage_bps: float) -> float:
    """Simulate fill at bar open with slippage (bps)."""
    price = bar.open
    bps = slippage_bps / 10_000
    if side == "buy":
        return price * (1 + bps)
    return price * (1 - bps)


def run_backtest(
    bars: list[Bar],
    symbol: str,
    timeframe: str,
    *,
    initial_cash: float = 100_000.0,
    slippage_bps: float = 5.0,
    commission_per_share: float = 0.0,
    risk_pct_per_trade: float = 1.0,
    journal_callback: Callable[[str, dict], None] | None = None,
) -> BacktestResult:
    """
    Replay bars in order. At each bar, build context window (past + current only),
    run vpa-core. On TradePlan: size by risk_pct, fill at next bar open with slippage/commission.
    Single position: one trade at a time; exit on stop or invalidation (simplified: next bar).
    """
    start_time = bars[0].timestamp if bars else datetime.now(timezone.utc)
    end_time = bars[-1].timestamp if bars else datetime.now(timezone.utc)
    cash = initial_cash
    position: tuple[float, int | float, TradePlan, int] | None = None  # (entry_price, qty, plan, entry_bar_idx)
    trades: list[BacktestTrade] = []

    for i in range(len(bars)):
        current_bars = bars[: i + 1]
        window = ContextWindow(bars=current_bars, symbol=symbol, timeframe=timeframe)
        results = evaluate(window)

        if position is not None:
            entry_price, qty, plan, entry_bar_idx = position
            bar = bars[i]
            stop_level = plan.stop_level
            stop_price = float(stop_level) if isinstance(stop_level, (int, float)) else (bar.high if plan.direction == "short" else bar.low)
            exit_price = _fill_price(bar, "sell" if plan.direction == "long" else "buy", slippage_bps)
            stopped = False
            if plan.direction == "short" and bar.high >= stop_price:
                stopped = True
                exit_price = stop_price * (1 + slippage_bps / 10_000)
            elif plan.direction == "long" and bar.low <= stop_price:
                stopped = True
                exit_price = stop_price * (1 - slippage_bps / 10_000)
            if stopped or i == len(bars) - 1:
                commission = commission_per_share * abs(qty) * 2
                pnl = (entry_price - exit_price) * abs(qty) if plan.direction == "short" else (exit_price - entry_price) * abs(qty)
                pnl -= commission
                cash += pnl
                entry_ts = bars[entry_bar_idx].timestamp
                trade = BacktestTrade(
                    symbol=symbol,
                    direction=plan.direction,
                    entry_time=entry_ts,
                    entry_price=entry_price,
                    exit_time=bar.timestamp,
                    exit_price=exit_price,
                    qty=abs(qty),
                    pnl=pnl,
                    rationale=plan.rationale,
                    rulebook_ref=plan.rulebook_ref,
                )
                trades.append(trade)
                if journal_callback:
                    journal_callback("trade", {"trade": trade, "reason": "stop" if stopped else "end"})
                position = None
            continue

        if not results or i + 1 >= len(bars):
            continue
        for _signal, plan in results:
            if position is not None:
                break
            next_bar = bars[i + 1]
            side = "buy" if plan.direction == "long" else "sell"
            entry_price = _fill_price(next_bar, side, slippage_bps)
            stop_level = plan.stop_level
            stop_price = float(stop_level) if isinstance(stop_level, (int, float)) else (next_bar.low if plan.direction == "long" else next_bar.high)
            risk_per_share = abs(entry_price - stop_price)
            if risk_per_share <= 0:
                continue
            risk_amount = cash * (risk_pct_per_trade / 100)
            qty = int(risk_amount / risk_per_share)
            if qty <= 0:
                continue
            if plan.direction == "long" and entry_price * qty > cash:
                qty = int(cash / entry_price)
            if qty <= 0:
                continue
            position = (entry_price, qty, plan, i + 1)
            if journal_callback:
                journal_callback("signal", {"plan": plan, "bar_index": i, "entry_price": entry_price, "qty": qty})
            break

    final_cash = cash

    return BacktestResult(
        symbol=symbol,
        timeframe=timeframe,
        start_time=start_time,
        end_time=end_time,
        initial_cash=initial_cash,
        final_cash=final_cash,
        trades=trades,
    )
