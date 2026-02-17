"""Tests for journal writer. Append-only; rationale and rulebook_ref."""

import json
import tempfile
from pathlib import Path

import pytest

from journal.writer import JournalWriter


def test_journal_writer_append_only() -> None:
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
        path = Path(f.name)
    try:
        j = JournalWriter(path)
        j.signal("no_demand", "short", "No demand bar.", "no_demand", bar_index=4)
        j.trade("SPY", "short", 100.0, 98.0, 10, 20.0, "No demand.", "no_demand")
        with open(path) as f:
            lines = f.readlines()
        assert len(lines) == 2
        r0 = json.loads(lines[0])
        assert r0["event"] == "signal"
        assert r0["rationale"] == "No demand bar."
        assert r0["rulebook_ref"] == "no_demand"
        r1 = json.loads(lines[1])
        assert r1["event"] == "trade"
        assert r1["pnl"] == 20.0
    finally:
        path.unlink(missing_ok=True)
