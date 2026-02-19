"""
Config loader: YAML file -> frozen dataclass tree.

API secrets resolved from environment variables (APCA_API_KEY_ID, APCA_API_SECRET_KEY).
Config file holds only non-secret values.
"""

import os
from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class DataConfig:
    source: str
    bar_store_path: str
    api_key: str = ""
    api_secret: str = ""


@dataclass(frozen=True)
class BacktestConfig:
    initial_cash: float = 100_000.0
    slippage_bps: float = 5.0
    commission_per_share: float = 0.0
    risk_pct_per_trade: float = 1.0


@dataclass(frozen=True)
class ExecutionConfig:
    state_path: str = "data/paper_state.db"
    max_position_pct: float = 10.0
    max_cash_per_trade_pct: float = 5.0
    initial_cash: float = 100_000.0


@dataclass(frozen=True)
class JournalConfig:
    path: str = "data/journal.jsonl"
    echo_stdout: bool = False


@dataclass(frozen=True)
class AlertingConfig:
    structured_logs: bool = True
    webhook_url: str = ""


@dataclass(frozen=True)
class AppConfig:
    symbol: str
    timeframe: str
    data: DataConfig
    backtest: BacktestConfig
    execution: ExecutionConfig
    journal: JournalConfig
    alerting: AlertingConfig = AlertingConfig()


def load_config(path: str | Path = "config.yaml") -> AppConfig:
    """
    Load configuration from a YAML file.

    API keys are resolved from environment variables:
      - APCA_API_KEY_ID
      - APCA_API_SECRET_KEY
    These follow Alpaca's standard env var names.
    """
    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path) as f:
        raw = yaml.safe_load(f)

    if not isinstance(raw, dict):
        raise ValueError(f"Config file must be a YAML mapping, got {type(raw).__name__}")

    data_raw = raw.get("data", {})
    data_cfg = DataConfig(
        source=data_raw.get("source", "alpaca"),
        bar_store_path=data_raw.get("bar_store_path", "data/bars.db"),
        api_key=os.environ.get("APCA_API_KEY_ID", ""),
        api_secret=os.environ.get("APCA_API_SECRET_KEY", ""),
    )

    bt_raw = raw.get("backtest", {})
    bt_cfg = BacktestConfig(
        initial_cash=float(bt_raw.get("initial_cash", 100_000)),
        slippage_bps=float(bt_raw.get("slippage_bps", 5.0)),
        commission_per_share=float(bt_raw.get("commission_per_share", 0.0)),
        risk_pct_per_trade=float(bt_raw.get("risk_pct_per_trade", 1.0)),
    )

    ex_raw = raw.get("execution", {})
    ex_cfg = ExecutionConfig(
        state_path=ex_raw.get("state_path", "data/paper_state.db"),
        max_position_pct=float(ex_raw.get("max_position_pct", 10.0)),
        max_cash_per_trade_pct=float(ex_raw.get("max_cash_per_trade_pct", 5.0)),
        initial_cash=float(ex_raw.get("initial_cash", 100_000)),
    )

    j_raw = raw.get("journal", {})
    j_cfg = JournalConfig(
        path=j_raw.get("path", "data/journal.jsonl"),
        echo_stdout=bool(j_raw.get("echo_stdout", False)),
    )

    a_raw = raw.get("alerting", {})
    a_cfg = AlertingConfig(
        structured_logs=bool(a_raw.get("structured_logs", True)),
        webhook_url=str(a_raw.get("webhook_url", "")),
    )

    return AppConfig(
        symbol=raw.get("symbol", "SPY"),
        timeframe=raw.get("timeframe", "15m"),
        data=data_cfg,
        backtest=bt_cfg,
        execution=ex_cfg,
        journal=j_cfg,
        alerting=a_cfg,
    )
