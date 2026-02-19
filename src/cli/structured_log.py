"""
Structured JSON event logger for Docker observability.

Emits one JSON object per line to stderr. Events are designed to be
parsed by log aggregators (Grafana Loki, CloudWatch, ELK).

Optional webhook: when configured, trade-level events (signal_detected,
trade_submitted, order_rejected, error) are POSTed to the URL.
"""

from __future__ import annotations

import json
import logging
import sys
import urllib.request
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("vpa.events")


class StructuredEventLogger:
    """Emit structured JSON events to stderr and optional webhook."""

    def __init__(
        self,
        symbol: str,
        *,
        enabled: bool = True,
        webhook_url: str = "",
        stream: Any = None,
    ) -> None:
        self._symbol = symbol
        self._enabled = enabled
        self._webhook_url = webhook_url.strip()
        self._stream = stream or sys.stderr
        self._ALERT_EVENTS = {
            "signal_detected",
            "trade_submitted",
            "order_rejected",
            "error",
        }

    def _emit(self, event_type: str, **fields: Any) -> dict:
        record = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "event": event_type,
            "symbol": self._symbol,
            **fields,
        }
        if self._enabled:
            self._stream.write(json.dumps(record) + "\n")
            self._stream.flush()

        if self._webhook_url and event_type in self._ALERT_EVENTS:
            self._post_webhook(record)

        return record

    def _post_webhook(self, record: dict) -> None:
        try:
            data = json.dumps(record).encode("utf-8")
            req = urllib.request.Request(
                self._webhook_url,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            urllib.request.urlopen(req, timeout=5)
        except Exception as exc:
            logger.warning("Webhook POST failed: %s", exc)

    def cycle_start(self, bar_close: str, bars_ingested: int) -> dict:
        return self._emit(
            "cycle_start",
            bar_close=bar_close,
            bars_ingested=bars_ingested,
        )

    def signal_detected(
        self,
        signal_ids: list[str],
        setup_ids: list[str],
        intent_count: int,
    ) -> dict:
        return self._emit(
            "signal_detected",
            signals=signal_ids,
            setups=setup_ids,
            intents=intent_count,
        )

    def trade_submitted(
        self,
        setup: str,
        direction: str,
        qty: float,
        stop: float,
    ) -> dict:
        return self._emit(
            "trade_submitted",
            setup=setup,
            direction=direction,
            qty=qty,
            stop=stop,
        )

    def order_rejected(self, reason: str) -> dict:
        return self._emit("order_rejected", reason=reason)

    def cycle_complete(self, signals: int, intents: int) -> dict:
        return self._emit(
            "cycle_complete",
            signals=signals,
            intents=intents,
        )

    def market_closed(self, next_open: str, wait_hours: float) -> dict:
        return self._emit(
            "market_closed",
            next_open=next_open,
            wait_hours=round(wait_hours, 1),
        )

    def error(self, message: str, detail: str = "") -> dict:
        return self._emit("error", message=message, detail=detail)

    def shutdown(self, cycles: int) -> dict:
        return self._emit("shutdown", cycles=cycles)
