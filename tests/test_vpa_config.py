"""Tests for VPA config loader: JSON loading, schema validation, frozen dataclass tree."""

import json
import tempfile
from pathlib import Path

import pytest

from config.vpa_config import (
    VPAConfig,
    VPAConfigError,
    _deep_merge,
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


# ---------------------------------------------------------------------------
# Deep merge utility
# ---------------------------------------------------------------------------


class TestDeepMerge:
    """Unit tests for the _deep_merge helper."""

    def test_flat_override(self) -> None:
        base = {"a": 1, "b": 2}
        result = _deep_merge(base, {"b": 99})
        assert result == {"a": 1, "b": 99}

    def test_nested_override(self) -> None:
        base = {"x": {"y": 1, "z": 2}}
        result = _deep_merge(base, {"x": {"z": 42}})
        assert result == {"x": {"y": 1, "z": 42}}

    def test_deeply_nested(self) -> None:
        base = {"a": {"b": {"c": 1, "d": 2}}}
        result = _deep_merge(base, {"a": {"b": {"c": 99}}})
        assert result == {"a": {"b": {"c": 99, "d": 2}}}

    def test_new_key_added(self) -> None:
        base = {"a": 1}
        result = _deep_merge(base, {"b": 2})
        assert result == {"a": 1, "b": 2}

    def test_original_not_mutated(self) -> None:
        base = {"a": {"b": 1}}
        _deep_merge(base, {"a": {"b": 99}})
        assert base == {"a": {"b": 1}}

    def test_empty_overrides(self) -> None:
        base = {"a": 1}
        result = _deep_merge(base, {})
        assert result == {"a": 1}

    def test_override_replaces_non_dict_with_dict(self) -> None:
        base = {"a": 1}
        result = _deep_merge(base, {"a": {"nested": True}})
        assert result == {"a": {"nested": True}}


# ---------------------------------------------------------------------------
# Per-symbol config overrides
# ---------------------------------------------------------------------------


class TestPerSymbolConfig:
    """load_vpa_config(symbol=...) merges per-symbol overrides."""

    def _setup_override(self, tmp_path: Path, symbol: str, overrides: dict) -> Path:
        """Write default config + symbol override into tmp_path, return default path."""
        base = _default_raw()
        default_path = tmp_path / "vpa.default.json"
        default_path.write_text(json.dumps(base))
        override_path = tmp_path / f"vpa.{symbol.upper()}.json"
        override_path.write_text(json.dumps(overrides))
        return default_path

    def test_symbol_override_merges_flat(self, tmp_path: Path) -> None:
        """Override a top-level nested value (volume_guard.min_avg_volume)."""
        default_path = self._setup_override(tmp_path, "AAPL", {
            "volume_guard": {"min_avg_volume": 75000}
        })
        cfg = load_vpa_config(config_path=default_path, symbol="AAPL")
        assert cfg.volume_guard.min_avg_volume == 75000
        assert cfg.volume_guard.enabled is True  # unchanged from default

    def test_symbol_override_deep_nested(self, tmp_path: Path) -> None:
        """Override a deeply nested value (vol.thresholds.high_gt)."""
        default_path = self._setup_override(tmp_path, "QQQ", {
            "vol": {"thresholds": {"high_gt": 1.5}}
        })
        cfg = load_vpa_config(config_path=default_path, symbol="QQQ")
        assert cfg.vol.thresholds.high_gt == 1.5
        assert cfg.vol.thresholds.low_lt == 0.8  # unchanged
        assert cfg.vol.avg_window_N == 20         # unchanged

    def test_symbol_override_atr(self, tmp_path: Path) -> None:
        """Override ATR settings per-symbol."""
        default_path = self._setup_override(tmp_path, "TSLA", {
            "atr": {"enabled": True, "stop_multiplier": 2.0}
        })
        cfg = load_vpa_config(config_path=default_path, symbol="TSLA")
        assert cfg.atr.enabled is True
        assert cfg.atr.stop_multiplier == 2.0
        assert cfg.atr.period == 14  # unchanged default

    def test_no_override_file_uses_defaults(self, tmp_path: Path) -> None:
        """When no per-symbol file exists, returns the base config unchanged."""
        base = _default_raw()
        default_path = tmp_path / "vpa.default.json"
        default_path.write_text(json.dumps(base))
        cfg = load_vpa_config(config_path=default_path, symbol="NOPE")
        assert cfg.vol.thresholds.low_lt == 0.8
        assert cfg.volume_guard.min_avg_volume == 10000

    def test_no_symbol_ignores_overrides(self) -> None:
        """Calling without symbol= loads the plain default config."""
        cfg = load_vpa_config()
        assert isinstance(cfg, VPAConfig)
        assert cfg.vol.thresholds.low_lt == 0.8

    def test_symbol_case_insensitive(self, tmp_path: Path) -> None:
        """Symbol is uppercased when looking for the override file."""
        default_path = self._setup_override(tmp_path, "SPY", {
            "atr": {"stop_multiplier": 3.0}
        })
        cfg = load_vpa_config(config_path=default_path, symbol="spy")
        assert cfg.atr.stop_multiplier == 3.0

    def test_bad_symbol_override_json_raises(self, tmp_path: Path) -> None:
        """Invalid JSON in the per-symbol file raises VPAConfigError."""
        base = _default_raw()
        default_path = tmp_path / "vpa.default.json"
        default_path.write_text(json.dumps(base))
        bad_override = tmp_path / "vpa.BAD.json"
        bad_override.write_text("{ not json! }")
        with pytest.raises(VPAConfigError, match="not valid JSON"):
            load_vpa_config(config_path=default_path, symbol="BAD")

    def test_symbol_override_schema_validated(self, tmp_path: Path) -> None:
        """Merged config must still pass schema validation."""
        default_path = self._setup_override(tmp_path, "FAIL", {
            "risk": {"risk_pct_per_trade": 0.99}  # exceeds max 0.05
        })
        with pytest.raises(VPAConfigError, match="validation failed"):
            load_vpa_config(config_path=default_path, symbol="FAIL")

    def test_multiple_overrides_independent(self, tmp_path: Path) -> None:
        """Two different symbol overrides produce different configs."""
        base = _default_raw()
        default_path = tmp_path / "vpa.default.json"
        default_path.write_text(json.dumps(base))

        (tmp_path / "vpa.SPY.json").write_text(json.dumps({
            "atr": {"stop_multiplier": 1.0}
        }))
        (tmp_path / "vpa.TSLA.json").write_text(json.dumps({
            "atr": {"stop_multiplier": 3.0}
        }))

        cfg_spy = load_vpa_config(config_path=default_path, symbol="SPY")
        cfg_tsla = load_vpa_config(config_path=default_path, symbol="TSLA")
        assert cfg_spy.atr.stop_multiplier == 1.0
        assert cfg_tsla.atr.stop_multiplier == 3.0
