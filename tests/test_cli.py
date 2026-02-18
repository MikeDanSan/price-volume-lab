"""Tests for CLI commands using click CliRunner. No network; uses fixture data."""

import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest
from click.testing import CliRunner

from cli.main import cli
from data.bar_store import BarStore
from vpa_core.contracts import Bar


def _ts(y: int, m: int, d: int, h: int = 9, mi: int = 30) -> datetime:
    return datetime(y, m, d, h, mi, 0, tzinfo=timezone.utc)


@pytest.fixture
def tmp_config(tmp_path: Path) -> Path:
    """Write a temp config.yaml and populate a BarStore with bars."""
    db_path = tmp_path / "bars.db"
    state_path = tmp_path / "state.db"
    journal_path = tmp_path / "journal.jsonl"
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        f"""
symbol: SPY
timeframe: "15m"
data:
  source: alpaca
  bar_store_path: "{db_path}"
backtest:
  initial_cash: 100000
  slippage_bps: 5
  risk_pct_per_trade: 1.0
execution:
  state_path: "{state_path}"
  initial_cash: 100000
journal:
  path: "{journal_path}"
  echo_stdout: false
"""
    )
    store = BarStore(str(db_path))
    bars = [
        Bar(100.0, 101.0, 99.0, 100.5, 1_000_000, _ts(2024, 1, 2), "SPY"),
        Bar(100.5, 101.5, 100.0, 101.0, 1_100_000, _ts(2024, 1, 3), "SPY"),
        Bar(101.0, 102.0, 100.5, 101.5, 1_050_000, _ts(2024, 1, 4), "SPY"),
        Bar(101.5, 102.5, 101.0, 102.0, 1_200_000, _ts(2024, 1, 5), "SPY"),
        Bar(102.0, 103.0, 101.5, 102.8, 400_000, _ts(2024, 1, 6), "SPY"),
        Bar(102.8, 103.5, 102.0, 102.5, 500_000, _ts(2024, 1, 7), "SPY"),
        Bar(102.5, 104.0, 102.0, 103.5, 600_000, _ts(2024, 1, 8), "SPY"),
    ]
    store.write_bars("SPY", "15m", bars)
    return config_path


def test_cli_scan(tmp_config: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["--config", str(tmp_config), "scan"])
    assert result.exit_code == 0, result.output
    assert "VPA Pipeline Scan" in result.output
    assert "Volume" in result.output
    assert "Spread" in result.output
    assert "Context" in result.output


def test_cli_backtest(tmp_config: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["--config", str(tmp_config), "backtest"])
    assert result.exit_code == 0
    assert "Backtest" in result.output
    assert "Return" in result.output


def test_cli_status(tmp_config: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["--config", str(tmp_config), "status"])
    assert result.exit_code == 0
    assert "Account Status" in result.output
    assert "Cash" in result.output


def test_cli_paper(tmp_config: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["--config", str(tmp_config), "paper"])
    assert result.exit_code == 0
    assert "VPA Analysis" in result.output


def test_cli_scan_empty_store(tmp_path: Path) -> None:
    db_path = tmp_path / "empty.db"
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        f"""
symbol: SPY
timeframe: "15m"
data:
  source: alpaca
  bar_store_path: "{db_path}"
"""
    )
    BarStore(str(db_path))  # create empty DB
    runner = CliRunner()
    result = runner.invoke(cli, ["--config", str(config_path), "scan"])
    assert result.exit_code == 0
    assert "Not enough bars" in result.output or "No bars" in result.output
