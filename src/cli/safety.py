"""
Safety guard: kill switch and max daily loss enforcement.

Checked before every order submission in the scheduler. Designed to be
the last line of defense before real or paper money is committed.

- kill_switch: immediately disables all order submission.
- max_daily_loss_pct: halts trading when realized daily loss exceeds threshold.
  Resets automatically at the start of each trading day.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass
class SafetyResult:
    allowed: bool
    reason: str = ""


class SafetyGuard:
    """Pre-submission safety checks.

    Parameters
    ----------
    kill_switch:
        If True, all orders are blocked unconditionally.
    max_daily_loss_pct:
        Maximum allowed daily loss as percentage of initial_cash.
        When breached, all further orders for the day are blocked.
    initial_cash:
        Starting equity for percentage calculations.
    """

    def __init__(
        self,
        *,
        kill_switch: bool = False,
        max_daily_loss_pct: float = 3.0,
        initial_cash: float = 100_000.0,
    ) -> None:
        self._kill_switch = kill_switch
        self._max_daily_loss_pct = max_daily_loss_pct
        self._initial_cash = initial_cash
        self._daily_pnl: float = 0.0
        self._trading_date: date | None = None

    @property
    def kill_switch(self) -> bool:
        return self._kill_switch

    @property
    def daily_pnl(self) -> float:
        return self._daily_pnl

    @property
    def max_daily_loss(self) -> float:
        return self._initial_cash * (self._max_daily_loss_pct / 100.0)

    def _reset_if_new_day(self, today: date) -> None:
        if self._trading_date != today:
            self._daily_pnl = 0.0
            self._trading_date = today

    def record_pnl(self, pnl: float, today: date | None = None) -> None:
        """Record realized PnL from a closed trade."""
        if today is None:
            today = date.today()
        self._reset_if_new_day(today)
        self._daily_pnl += pnl

    def check(self, today: date | None = None) -> SafetyResult:
        """Check all safety conditions before order submission.

        Returns SafetyResult with allowed=True if trading is permitted,
        or allowed=False with a reason string.
        """
        if self._kill_switch:
            return SafetyResult(allowed=False, reason="Kill switch is ON — all trading disabled")

        if today is None:
            today = date.today()
        self._reset_if_new_day(today)

        loss_limit = self.max_daily_loss
        if self._daily_pnl < 0 and abs(self._daily_pnl) >= loss_limit:
            return SafetyResult(
                allowed=False,
                reason=f"Daily loss limit breached: ${self._daily_pnl:.2f} "
                       f"(limit: -${loss_limit:.2f}, {self._max_daily_loss_pct}%)",
            )

        return SafetyResult(allowed=True)
