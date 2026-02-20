"""
Read-only data access for the VPA dashboard.
Discovers symbols from data/<SYMBOL>/paper_state.db and reads positions, cash, journal, fills.
"""

import json
import os
import sqlite3
from pathlib import Path
from typing import Any


def _data_dir() -> Path:
    """Base data dir: repo root / data, or VPA_DASHBOARD_DATA_DIR if set."""
    if env := os.environ.get("VPA_DASHBOARD_DATA_DIR"):
        return Path(env)
    return Path(__file__).resolve().parent.parent / "data"


def discover_symbols(data_dir: Path | None = None) -> list[str]:
    """Find symbols: any subdir of data/ that has paper_state.db, journal.jsonl, or bars.db."""
    root = data_dir or _data_dir()
    if not root.is_dir():
        return []
    symbols = []
    for child in sorted(root.iterdir()):
        if not child.is_dir():
            continue
        if (child / "paper_state.db").exists() or (child / "journal.jsonl").exists() or (child / "bars.db").exists():
            symbols.append(child.name)
    return symbols


def get_position(symbol: str, data_dir: Path | None = None) -> dict[str, Any] | None:
    """Return current position for symbol: { side, qty, avg_price } or None if flat."""
    root = data_dir or _data_dir()
    db = root / symbol / "paper_state.db"
    if not db.exists():
        return None
    try:
        with sqlite3.connect(str(db), timeout=5.0) as c:
            row = c.execute(
                "SELECT side, qty, avg_price FROM positions WHERE symbol = ?",
                (symbol,),
            ).fetchone()
            if not row or row[1] == 0:
                return None
            return {"side": row[0], "qty": row[1], "avg_price": row[2]}
    except (sqlite3.Error, OSError):
        return None


def get_cash(symbol: str, data_dir: Path | None = None) -> float | None:
    """Return cash balance for symbol, or None if DB missing."""
    root = data_dir or _data_dir()
    db = root / symbol / "paper_state.db"
    if not db.exists():
        return None
    try:
        with sqlite3.connect(str(db), timeout=5.0) as c:
            row = c.execute("SELECT balance FROM cash WHERE id = 1").fetchone()
            return float(row[0]) if row else None
    except (sqlite3.Error, OSError):
        return None


def get_recent_fills(symbol: str, limit: int = 20, data_dir: Path | None = None) -> list[dict[str, Any]]:
    """Return recent fills from paper_state.db (id, order_id, symbol, side, qty, price, ts_utc)."""
    root = data_dir or _data_dir()
    db = root / symbol / "paper_state.db"
    if not db.exists():
        return []
    try:
        with sqlite3.connect(str(db), timeout=5.0) as c:
            rows = c.execute(
                "SELECT id, order_id, symbol, side, qty, price, ts_utc FROM fills WHERE symbol = ? ORDER BY ts_utc DESC LIMIT ?",
                (symbol, limit),
            ).fetchall()
            return [
                {
                    "id": r[0],
                    "order_id": r[1],
                    "symbol": r[2],
                    "side": r[3],
                    "qty": r[4],
                    "price": r[5],
                    "ts_utc": r[6],
                }
                for r in rows
            ]
    except (sqlite3.Error, OSError):
        return []


def get_recent_journal_events(
    symbol: str,
    event_type: str | None = None,
    limit: int = 50,
    data_dir: Path | None = None,
) -> list[dict[str, Any]]:
    """
    Read last `limit` journal events from data/<symbol>/journal.jsonl.
    If event_type is set, filter to that event (signal, trade_plan, fill, invalidation, trade).
    Returns list of parsed JSON objects (newest first).
    """
    root = data_dir or _data_dir()
    path = root / symbol / "journal.jsonl"
    if not path.exists():
        return []
    lines: list[str] = []
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line:
                    lines.append(line)
    except OSError:
        return []
    # Take last N, then reverse so newest first
    chosen = lines[-limit:] if limit else lines
    chosen.reverse()
    out = []
    for line in chosen:
        try:
            obj = json.loads(line)
            if event_type is None or obj.get("event") == event_type:
                out.append(obj)
        except json.JSONDecodeError:
            continue
    return out
