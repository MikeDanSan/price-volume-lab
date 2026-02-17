"""
Paper executor: single-writer order/position state, risk limits, restart-safe (SQLite).
"""

import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

from vpa_core.contracts import TradePlan

from execution.models import Fill, Order, Position


def _utc(ts: datetime) -> datetime:
    if ts.tzinfo is None:
        return ts.replace(tzinfo=timezone.utc)
    return ts.astimezone(timezone.utc)


class PaperExecutor:
    """
    Convert TradePlans to orders; track orders and positions in SQLite.
    Single writer (one process). Risk limits enforced before placing order.
    """

    def __init__(
        self,
        state_path: str | Path,
        *,
        max_position_pct: float = 10.0,
        max_cash_per_trade_pct: float = 5.0,
        initial_cash: float = 100_000.0,
    ) -> None:
        self._path = Path(state_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._max_position_pct = max_position_pct
        self._max_cash_per_trade_pct = max_cash_per_trade_pct
        self._initial_cash = initial_cash
        self._init_schema()

    def _conn(self) -> sqlite3.Connection:
        return sqlite3.connect(str(self._path), timeout=10.0)

    def _init_schema(self) -> None:
        with self._conn() as c:
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS orders (
                    id TEXT PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    side TEXT NOT NULL,
                    qty REAL NOT NULL,
                    order_type TEXT NOT NULL,
                    ts_utc TEXT NOT NULL,
                    trade_plan_ref TEXT,
                    limit_price REAL
                )
                """
            )
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS fills (
                    id TEXT PRIMARY KEY,
                    order_id TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    side TEXT NOT NULL,
                    qty REAL NOT NULL,
                    price REAL NOT NULL,
                    ts_utc TEXT NOT NULL,
                    slippage_bps REAL
                )
                """
            )
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS positions (
                    symbol TEXT PRIMARY KEY,
                    side TEXT NOT NULL,
                    qty REAL NOT NULL,
                    avg_price REAL NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS cash (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    balance REAL NOT NULL
                )
                """
            )
            c.execute("INSERT OR IGNORE INTO cash (id, balance) VALUES (1, ?)", (self._initial_cash,))

    def _get_cash(self) -> float:
        with self._conn() as c:
            row = c.execute("SELECT balance FROM cash WHERE id = 1").fetchone()
            return float(row[0]) if row else self._initial_cash

    def _set_cash(self, balance: float) -> None:
        with self._conn() as c:
            c.execute("UPDATE cash SET balance = ? WHERE id = 1", (balance,))

    def submit(self, symbol: str, plan: TradePlan, current_price: float, *, slippage_bps: float = 5.0) -> Order | None:
        """Convert TradePlan to order if risk limits allow. Returns Order or None."""
        return self._submit_impl(plan, symbol, current_price, slippage_bps)

    def _submit_impl(
        self,
        plan: TradePlan,
        symbol: str,
        current_price: float,
        slippage_bps: float,
    ) -> Order | None:
        with self._conn() as c:
            pos_row = c.execute("SELECT qty FROM positions WHERE symbol = ?", (symbol,)).fetchone()
            if pos_row and pos_row[0] != 0:
                return None  # Already have position
            cash = self._get_cash()
            stop_level = plan.stop_level
            stop_price = float(stop_level) if isinstance(stop_level, (int, float)) else current_price * 0.99
            risk_per_share = abs(current_price - stop_price)
            if risk_per_share <= 0:
                return None
            risk_amount = cash * (self._max_cash_per_trade_pct / 100)
            qty = int(risk_amount / risk_per_share)
            if qty <= 0:
                return None
            cost = current_price * qty
            if plan.direction == "long" and cost > cash:
                qty = int(cash / current_price)
            if qty <= 0:
                return None
            order_id = str(uuid.uuid4())
            ts = _utc(datetime.now(timezone.utc)).isoformat()
            c.execute(
                """INSERT INTO orders (id, symbol, side, qty, order_type, ts_utc, trade_plan_ref, limit_price)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    order_id,
                    symbol,
                    "buy" if plan.direction == "long" else "sell",
                    qty,
                    "market",
                    ts,
                    plan.signal_id,
                    None,
                ),
            )
            # Paper: fill immediately at current_price with slippage
            fill_id = str(uuid.uuid4())
            fill_price = current_price * (1 + slippage_bps / 10_000) if plan.direction == "long" else current_price * (1 - slippage_bps / 10_000)
            c.execute(
                """INSERT INTO fills (id, order_id, symbol, side, qty, price, ts_utc, slippage_bps) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (fill_id, order_id, symbol, "buy" if plan.direction == "long" else "sell", qty, fill_price, ts, slippage_bps),
            )
            c.execute(
                """INSERT OR REPLACE INTO positions (symbol, side, qty, avg_price, updated_at) VALUES (?, ?, ?, ?, ?)""",
                (symbol, plan.direction, qty if plan.direction == "long" else -qty, fill_price, ts),
            )
            if plan.direction == "long":
                c.execute("UPDATE cash SET balance = balance - ?", (fill_price * qty,))
        return Order(
            id=order_id,
            symbol=symbol,
            side="buy" if plan.direction == "long" else "sell",
            qty=qty,
            order_type="market",
            timestamp=datetime.fromisoformat(ts.replace("Z", "+00:00")),
            trade_plan_ref=plan.signal_id,
            limit_price=None,
        )

    def get_position(self, symbol: str) -> Position | None:
        with self._conn() as c:
            row = c.execute("SELECT symbol, side, qty, avg_price, updated_at FROM positions WHERE symbol = ?", (symbol,)).fetchone()
            if not row or row[2] == 0:
                return None
            ts = datetime.fromisoformat(row[4].replace("Z", "+00:00"))
            return Position(symbol=row[0], side=row[1], qty=row[2], avg_price=row[3], updated_at=ts)

    def list_fills(self, symbol: str | None = None, limit: int = 100) -> list[Fill]:
        with self._conn() as c:
            if symbol:
                rows = c.execute(
                    "SELECT id, order_id, symbol, side, qty, price, ts_utc, slippage_bps FROM fills WHERE symbol = ? ORDER BY ts_utc DESC LIMIT ?",
                    (symbol, limit),
                ).fetchall()
            else:
                rows = c.execute(
                    "SELECT id, order_id, symbol, side, qty, price, ts_utc, slippage_bps FROM fills ORDER BY ts_utc DESC LIMIT ?",
                    (limit,),
                ).fetchall()
        return [
            Fill(
                id=r[0],
                order_id=r[1],
                symbol=r[2],
                side=r[3],
                qty=r[4],
                price=r[5],
                timestamp=datetime.fromisoformat(r[6].replace("Z", "+00:00")),
                slippage_bps=r[7],
            )
            for r in rows
        ]
