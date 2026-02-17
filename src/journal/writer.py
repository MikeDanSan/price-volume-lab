"""
Structured journal: append-only JSON lines. Every event has rationale and rulebook_ref when applicable.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _serialize(obj: Any) -> Any:
    if isinstance(obj, datetime):
        return obj.isoformat()
    if hasattr(obj, "__dict__") and not isinstance(obj, type):
        return {k: _serialize(v) for k, v in vars(obj).items() if not k.startswith("_")}
    if isinstance(obj, dict):
        return {k: _serialize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_serialize(x) for x in obj]
    return obj


class JournalWriter:
    """Append-only journal. Each line is a JSON object with event type and payload."""

    def __init__(self, path: str | Path, *, echo_stdout: bool = False) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._echo = echo_stdout

    def _write(self, event_type: str, payload: dict) -> None:
        record = {"ts_utc": datetime.now(timezone.utc).isoformat(), "event": event_type, **payload}
        line = json.dumps(_serialize(record)) + "\n"
        with open(self._path, "a") as f:
            f.write(line)
        if self._echo:
            print(line.rstrip())

    def signal(self, setup_type: str, direction: str, rationale: str, rulebook_ref: str, **extra: Any) -> None:
        self._write(
            "signal",
            {"setup_type": setup_type, "direction": direction, "rationale": rationale, "rulebook_ref": rulebook_ref, **extra},
        )

    def trade_plan(self, signal_id: str, setup_type: str, direction: str, rationale: str, rulebook_ref: str, **extra: Any) -> None:
        self._write(
            "trade_plan",
            {"signal_id": signal_id, "setup_type": setup_type, "direction": direction, "rationale": rationale, "rulebook_ref": rulebook_ref, **extra},
        )

    def trade(self, symbol: str, direction: str, entry_price: float, exit_price: float, qty: float, pnl: float, rationale: str, rulebook_ref: str, **extra: Any) -> None:
        self._write(
            "trade",
            {"symbol": symbol, "direction": direction, "entry_price": entry_price, "exit_price": exit_price, "qty": qty, "pnl": pnl, "rationale": rationale, "rulebook_ref": rulebook_ref, **extra},
        )

    def fill(self, order_id: str, symbol: str, side: str, qty: float, price: float, trade_plan_ref: str | None = None, **extra: Any) -> None:
        self._write("fill", {"order_id": order_id, "symbol": symbol, "side": side, "qty": qty, "price": price, "trade_plan_ref": trade_plan_ref, **extra})

    def invalidation(self, reason: str, setup_type: str, rulebook_ref: str, **extra: Any) -> None:
        self._write("invalidation", {"reason": reason, "setup_type": setup_type, "rulebook_ref": rulebook_ref, **extra})
