"""Tests for VPA config loader: JSON loading, schema validation, frozen dataclass tree."""

import json
import tempfile
from pathlib import Path

import pytest

from config.vpa_config import (
    VPAConfig,
    VPAConfigError,
    load_vpa_config,
    DEFAULT_CONFIG_PATH,
    DEFAULT_SCHEMA_PATH,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _default_raw() -> dict:
    """Return the canonical default config as a dict for mutation in tests."""
    with open(DEFAULT_CONFIG_PATH) as f:
        return json.load(f)


def _write_json(data: dict, dir_path: Path, name: str = "test_vpa.json") -> Path:
    p = dir_path / name
    p.write_text(json.dumps(data))
    return p


# ---------------------------------------------------------------------------
# Loading the default config
# ---------------------------------------------------------------------------


class TestLoadDefault:
    """Load docs/config/vpa.default.json and verify the dataclass tree."""

    def test_loads_successfully(self) -> None:
        cfg = load_vpa_config()
        assert isinstance(cfg, VPAConfig)

    def test_version(self) -> None:
        cfg = load_vpa_config()
        assert cfg.version == "0.1"

    def test_vol_thresholds(self) -> None:
        cfg = load_vpa_config()
        assert cfg.vol.avg_window_N == 20
        assert cfg.vol.thresholds.low_lt == 0.8
        assert cfg.vol.thresholds.high_gt == 1.2
        assert cfg.vol.thresholds.ultra_high_gt == 1.8

    def test_spread_thresholds(self) -> None:
        cfg = load_vpa_config()
        assert cfg.spread.avg_window_M == 20
        assert cfg.spread.thresholds.narrow_lt == 0.8
        assert cfg.spread.thresholds.wide_gt == 1.2

    def test_trend_and_setup_windows(self) -> None:
        cfg = load_vpa_config()
        assert cfg.trend.window_K == 5
        assert cfg.setup.window_X == 5

    def test_gates(self) -> None:
        cfg = load_vpa_config()
        assert cfg.gates.ctx1_trend_location_required is True
        assert cfg.gates.ctx2_dominant_alignment_policy == "REDUCE_RISK"
        assert cfg.gates.ctx3_congestion_awareness_required is True

    def test_execution_semantics(self) -> None:
        cfg = load_vpa_config()
        assert cfg.execution.signal_eval == "BAR_CLOSE_ONLY"
        assert cfg.execution.entry_timing == "NEXT_BAR_OPEN"
        assert cfg.execution.intrabar_allowed is False

    def test_costs_and_slippage(self) -> None:
        cfg = load_vpa_config()
        assert cfg.costs.fee_model == "BPS"
        assert cfg.costs.fee_value == 0
        assert cfg.slippage.model == "BPS"
        assert cfg.slippage.value == 0

    def test_risk(self) -> None:
        cfg = load_vpa_config()
        assert cfg.risk.risk_pct_per_trade == 0.005
        assert cfg.risk.max_concurrent_positions == 1
        assert cfg.risk.countertrend_multiplier == 0.5
        assert cfg.risk.daily_loss_limit_pct == 0.02


# ---------------------------------------------------------------------------
# Loading a custom config (overrides)
# ---------------------------------------------------------------------------


class TestLoadOverride:
    """Load a custom JSON file with different values."""

    def test_custom_vol_thresholds(self, tmp_path: Path) -> None:
        data = _default_raw()
        data["vol"]["thresholds"]["low_lt"] = 0.7
        data["vol"]["thresholds"]["ultra_high_gt"] = 2.0
        p = _write_json(data, tmp_path)

        cfg = load_vpa_config(config_path=p)
        assert cfg.vol.thresholds.low_lt == 0.7
        assert cfg.vol.thresholds.ultra_high_gt == 2.0

    def test_custom_risk(self, tmp_path: Path) -> None:
        data = _default_raw()
        data["risk"]["risk_pct_per_trade"] = 0.01
        data["risk"]["max_concurrent_positions"] = 3
        p = _write_json(data, tmp_path)

        cfg = load_vpa_config(config_path=p)
        assert cfg.risk.risk_pct_per_trade == 0.01
        assert cfg.risk.max_concurrent_positions == 3

    def test_custom_gates_policy(self, tmp_path: Path) -> None:
        data = _default_raw()
        data["gates"]["ctx2_dominant_alignment_policy"] = "DISALLOW"
        p = _write_json(data, tmp_path)

        cfg = load_vpa_config(config_path=p)
        assert cfg.gates.ctx2_dominant_alignment_policy == "DISALLOW"

    def test_optional_daily_loss_limit_absent(self, tmp_path: Path) -> None:
        data = _default_raw()
        data["risk"].pop("daily_loss_limit_pct", None)
        p = _write_json(data, tmp_path)

        cfg = load_vpa_config(config_path=p)
        assert cfg.risk.daily_loss_limit_pct is None


# ---------------------------------------------------------------------------
# Schema validation rejects invalid configs
# ---------------------------------------------------------------------------


class TestSchemaRejection:
    """Configs that violate the JSON Schema must raise VPAConfigError."""

    def test_missing_required_section(self, tmp_path: Path) -> None:
        data = _default_raw()
        del data["vol"]
        p = _write_json(data, tmp_path)

        with pytest.raises(VPAConfigError, match="validation failed"):
            load_vpa_config(config_path=p)

    def test_invalid_vol_window_too_low(self, tmp_path: Path) -> None:
        data = _default_raw()
        data["vol"]["avg_window_N"] = 2  # minimum is 5
        p = _write_json(data, tmp_path)

        with pytest.raises(VPAConfigError, match="validation failed"):
            load_vpa_config(config_path=p)

    def test_invalid_gate_policy_enum(self, tmp_path: Path) -> None:
        data = _default_raw()
        data["gates"]["ctx2_dominant_alignment_policy"] = "YOLO"
        p = _write_json(data, tmp_path)

        with pytest.raises(VPAConfigError, match="validation failed"):
            load_vpa_config(config_path=p)

    def test_risk_pct_too_high(self, tmp_path: Path) -> None:
        data = _default_raw()
        data["risk"]["risk_pct_per_trade"] = 0.10  # max is 0.05
        p = _write_json(data, tmp_path)

        with pytest.raises(VPAConfigError, match="validation failed"):
            load_vpa_config(config_path=p)

    def test_invalid_entry_timing(self, tmp_path: Path) -> None:
        data = _default_raw()
        data["execution"]["entry_timing"] = "IMMEDIATE"
        p = _write_json(data, tmp_path)

        with pytest.raises(VPAConfigError, match="validation failed"):
            load_vpa_config(config_path=p)


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


class TestErrorHandling:
    """File-level errors: missing file, bad JSON, missing schema."""

    def test_missing_config_file(self) -> None:
        with pytest.raises(VPAConfigError, match="not found"):
            load_vpa_config(config_path="/nonexistent/vpa.json")

    def test_missing_schema_file(self, tmp_path: Path) -> None:
        data = _default_raw()
        p = _write_json(data, tmp_path)

        with pytest.raises(VPAConfigError, match="Schema file not found"):
            load_vpa_config(config_path=p, schema_path="/nonexistent/schema.json")

    def test_invalid_json(self, tmp_path: Path) -> None:
        p = tmp_path / "bad.json"
        p.write_text("{ this is not json }")

        with pytest.raises(VPAConfigError, match="not valid JSON"):
            load_vpa_config(config_path=p)


# ---------------------------------------------------------------------------
# Immutability
# ---------------------------------------------------------------------------


class TestImmutability:
    """VPAConfig and sub-configs must be frozen."""

    def test_top_level_frozen(self) -> None:
        cfg = load_vpa_config()
        with pytest.raises(AttributeError):
            cfg.version = "hacked"  # type: ignore[misc]

    def test_nested_frozen(self) -> None:
        cfg = load_vpa_config()
        with pytest.raises(AttributeError):
            cfg.vol.thresholds.low_lt = 999  # type: ignore[misc]

    def test_risk_frozen(self) -> None:
        cfg = load_vpa_config()
        with pytest.raises(AttributeError):
            cfg.risk.risk_pct_per_trade = 1.0  # type: ignore[misc]
