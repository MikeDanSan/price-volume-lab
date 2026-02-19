"""
Persist and load OHLCV bars (SQLite). Timestamps in UTC.
"""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

from vpa_core.contracts import Bar


def _utc_ts(ts: datetime) -> datetime:
    if ts.tzinfo is None:
        return ts.replace(tzinfo=timezone.utc)
    return ts.astimezone(timezone.utc)


class BarStore:
    """SQLite-backed bar storage. One file per path."""

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _conn(self) -> sqlite3.Connection:
        return sqlite3.connect(str(self._path))

    def _init_schema(self) -> None:
        with self._conn() as c:
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS bars (
                    symbol TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    ts_utc TEXT NOT NULL,
                    open REAL NOT NULL,
                    high REAL NOT NULL,
                    low REAL NOT NULL,
                    close REAL NOT NULL,
                    volume INTEGER NOT NULL,
                    PRIMARY KEY (symbol, timeframe, ts_utc)
                )
                """
            )

    def write_bars(
        self,
        symbol: str,
        timeframe: str,
        bars: Sequence[Bar],
    ) -> None:
        """Upsert bars (by symbol, timeframe, ts_utc)."""
        with self._conn() as c:
            for b in bars:
                ts = _utc_ts(b.timestamp).isoformat()
                c.execute(
                    """
                    INSERT OR REPLACE INTO bars (symbol, timeframe, ts_utc, open, high, low, close, volume)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (symbol, timeframe, ts, b.open, b.high, b.low, b.close, b.volume),
                )

    def get_bars(
        self,
        symbol: str,
        timeframe: str,
        *,
        since: datetime | None = None,
        until: datetime | None = None,
        limit: int | None = None,
    ) -> list[Bar]:
        """Return bars in ascending time order. All timestamps in UTC."""
        with self._conn() as c:
            q = "SELECT ts_utc, open, high, low, close, volume FROM bars WHERE symbol = ? AND timeframe = ?"
            params: list = [symbol, timeframe]
            if since is not None:
                q += " AND ts_utc >= ?"
                params.append(_utc_ts(since).isoformat())
            if until is not None:
                q += " AND ts_utc <= ?"
                params.append(_utc_ts(until).isoformat())
            q += " ORDER BY ts_utc ASC"
            if limit is not None:
                q += " LIMIT ?"
                params.append(limit)
            rows = c.execute(q, params).fetchall()
        return self._rows_to_bars(rows, symbol)

    def count_bars(self, symbol: str, timeframe: str) -> int:
        """Return the total number of bars stored for a symbol/timeframe pair."""
        with self._conn() as c:
            row = c.execute(
                "SELECT COUNT(*) FROM bars WHERE symbol = ? AND timeframe = ?",
                (symbol, timeframe),
            ).fetchone()
        return row[0] if row else 0

    def get_last_bars(
        self,
        symbol: str,
        timeframe: str,
        n: int,
        *,
        until: datetime | None = None,
    ) -> list[Bar]:
        """Return the last n bars (by time) in ascending order. For context window."""
        with self._conn() as c:
            q = (
                "SELECT ts_utc, open, high, low, close, volume FROM bars "
                "WHERE symbol = ? AND timeframe = ?"
            )
            params: list = [symbol, timeframe]
            if until is not None:
                q += " AND ts_utc <= ?"
                params.append(_utc_ts(until).isoformat())
            q += " ORDER BY ts_utc DESC LIMIT ?"
            params.append(n)
            rows = c.execute(q, params).fetchall()
        rows = list(reversed(rows))  # back to ascending
        return self._rows_to_bars(rows, symbol)

    def _rows_to_bars(self, rows: list, symbol: str) -> list[Bar]:
        out: list[Bar] = []
        for i, (ts_utc, o, h, l, c, vol) in enumerate(rows):
            # SQLite has no native datetime; we store ISO strings
            ts = datetime.fromisoformat(ts_utc.replace("Z", "+00:00"))
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            out.append(
                Bar(
                    open=o,
                    high=h,
                    low=l,
                    close=c,
                    volume=vol,
                    timestamp=ts,
                    symbol=symbol,
                    bar_index=i,
                )
            )
        return out
