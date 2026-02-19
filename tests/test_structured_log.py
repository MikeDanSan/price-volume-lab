"""Tests for structured JSON event logger."""

import io
import json

import pytest

from cli.structured_log import StructuredEventLogger


@pytest.fixture
def buf() -> io.StringIO:
    return io.StringIO()


@pytest.fixture
def logger(buf: io.StringIO) -> StructuredEventLogger:
    return StructuredEventLogger("SPY", enabled=True, stream=buf)


class TestEmit:
    """Basic event emission and format."""

    def test_cycle_start_json(self, logger: StructuredEventLogger, buf: io.StringIO) -> None:
        logger.cycle_start(bar_close="2026-02-17T10:00:00", bars_ingested=5)
        line = buf.getvalue().strip()
        record = json.loads(line)
        assert record["event"] == "cycle_start"
        assert record["symbol"] == "SPY"
        assert record["bars_ingested"] == 5
        assert "ts" in record

    def test_signal_detected(self, logger: StructuredEventLogger, buf: io.StringIO) -> None:
        logger.signal_detected(
            signal_ids=["VAL-1", "ANOM-1"],
            setup_ids=["ENTRY-LONG-1"],
            intent_count=1,
        )
        record = json.loads(buf.getvalue().strip())
        assert record["event"] == "signal_detected"
        assert record["signals"] == ["VAL-1", "ANOM-1"]
        assert record["setups"] == ["ENTRY-LONG-1"]
        assert record["intents"] == 1

    def test_trade_submitted(self, logger: StructuredEventLogger, buf: io.StringIO) -> None:
        logger.trade_submitted(setup="ENTRY-LONG-1", direction="LONG", qty=10.0, stop=99.5)
        record = json.loads(buf.getvalue().strip())
        assert record["event"] == "trade_submitted"
        assert record["setup"] == "ENTRY-LONG-1"
        assert record["direction"] == "LONG"
        assert record["qty"] == 10.0
        assert record["stop"] == 99.5

    def test_order_rejected(self, logger: StructuredEventLogger, buf: io.StringIO) -> None:
        logger.order_rejected(reason="Max positions reached")
        record = json.loads(buf.getvalue().strip())
        assert record["event"] == "order_rejected"
        assert record["reason"] == "Max positions reached"

    def test_cycle_complete(self, logger: StructuredEventLogger, buf: io.StringIO) -> None:
        logger.cycle_complete(signals=3, intents=1)
        record = json.loads(buf.getvalue().strip())
        assert record["event"] == "cycle_complete"
        assert record["signals"] == 3
        assert record["intents"] == 1

    def test_market_closed(self, logger: StructuredEventLogger, buf: io.StringIO) -> None:
        logger.market_closed(next_open="2026-02-18T09:30:00", wait_hours=16.5)
        record = json.loads(buf.getvalue().strip())
        assert record["event"] == "market_closed"
        assert record["wait_hours"] == 16.5

    def test_error_event(self, logger: StructuredEventLogger, buf: io.StringIO) -> None:
        logger.error(message="DB locked", detail="OperationalError")
        record = json.loads(buf.getvalue().strip())
        assert record["event"] == "error"
        assert record["message"] == "DB locked"
        assert record["detail"] == "OperationalError"

    def test_shutdown(self, logger: StructuredEventLogger, buf: io.StringIO) -> None:
        logger.shutdown(cycles=42)
        record = json.loads(buf.getvalue().strip())
        assert record["event"] == "shutdown"
        assert record["cycles"] == 42


class TestDisabled:
    """When structured_logs=False, nothing is written to stream."""

    def test_no_output_when_disabled(self, buf: io.StringIO) -> None:
        logger = StructuredEventLogger("SPY", enabled=False, stream=buf)
        logger.cycle_start(bar_close="2026-02-17T10:00:00", bars_ingested=5)
        logger.signal_detected(signal_ids=["VAL-1"], setup_ids=[], intent_count=0)
        logger.trade_submitted(setup="X", direction="LONG", qty=1, stop=100)
        logger.shutdown(cycles=1)
        assert buf.getvalue() == ""


class TestMultipleEvents:
    """Multiple events produce multiple JSON lines."""

    def test_newline_delimited(self, logger: StructuredEventLogger, buf: io.StringIO) -> None:
        logger.cycle_start(bar_close="t1", bars_ingested=0)
        logger.cycle_complete(signals=0, intents=0)
        lines = buf.getvalue().strip().split("\n")
        assert len(lines) == 2
        assert json.loads(lines[0])["event"] == "cycle_start"
        assert json.loads(lines[1])["event"] == "cycle_complete"


class TestReturnValue:
    """Each method returns the record dict for testability."""

    def test_returns_record(self, logger: StructuredEventLogger, buf: io.StringIO) -> None:
        record = logger.cycle_start(bar_close="t1", bars_ingested=3)
        assert isinstance(record, dict)
        assert record["event"] == "cycle_start"
        assert record["symbol"] == "SPY"
        assert record["bars_ingested"] == 3
