"""Tests for config loader: YAML parsing, env var resolution, error cases."""

import os
import tempfile
from pathlib import Path

import pytest

from config import load_config


def _write_yaml(path: Path, content: str) -> None:
    path.write_text(content)


def test_load_config_basic() -> None:
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(
            """
symbol: AAPL
timeframe: "1h"
data:
  source: alpaca
  bar_store_path: test_bars.db
backtest:
  initial_cash: 50000
execution:
  state_path: test_state.db
journal:
  path: test_journal.jsonl
"""
        )
        path = f.name
    try:
        cfg = load_config(path)
        assert cfg.symbol == "AAPL"
        assert cfg.timeframe == "1h"
        assert cfg.data.source == "alpaca"
        assert cfg.data.bar_store_path == "test_bars.db"
        assert cfg.backtest.initial_cash == 50_000.0
        assert cfg.execution.state_path == "test_state.db"
        assert cfg.journal.path == "test_journal.jsonl"
    finally:
        os.unlink(path)


def test_load_config_env_vars() -> None:
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write("symbol: SPY\ntimeframe: '15m'\ndata:\n  source: alpaca\n  bar_store_path: b.db\n")
        path = f.name
    try:
        os.environ["APCA_API_KEY_ID"] = "test_key_123"
        os.environ["APCA_API_SECRET_KEY"] = "test_secret_456"
        cfg = load_config(path)
        assert cfg.data.api_key == "test_key_123"
        assert cfg.data.api_secret == "test_secret_456"
    finally:
        os.environ.pop("APCA_API_KEY_ID", None)
        os.environ.pop("APCA_API_SECRET_KEY", None)
        os.unlink(path)


def test_load_config_defaults() -> None:
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write("symbol: SPY\ntimeframe: '15m'\ndata:\n  source: alpaca\n  bar_store_path: b.db\n")
        path = f.name
    try:
        cfg = load_config(path)
        assert cfg.backtest.slippage_bps == 5.0
        assert cfg.backtest.risk_pct_per_trade == 1.0
        assert cfg.execution.max_position_pct == 10.0
        assert cfg.journal.echo_stdout is False
    finally:
        os.unlink(path)


def test_load_config_missing_file() -> None:
    with pytest.raises(FileNotFoundError):
        load_config("/nonexistent/path.yaml")
