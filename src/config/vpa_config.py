"""
VPA config loader: JSON file -> frozen dataclass tree, validated against JSON Schema.

Canonical reference: docs/vpa/VPA_CONFIG.md
Default values:      docs/config/vpa.default.json
Schema:              docs/config/vpa_config.schema.json

Usage:
    from config.vpa_config import load_vpa_config
    cfg = load_vpa_config()                     # loads default
    cfg = load_vpa_config("my_overrides.json")  # loads custom file
    cfg.vol.thresholds.low_lt  # -> 0.8
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import jsonschema

# ---------------------------------------------------------------------------
# Project root detection (walk up from this file to find pyproject.toml)
# ---------------------------------------------------------------------------

_THIS_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _THIS_DIR.parent.parent  # src/config -> src -> project root

DEFAULT_CONFIG_PATH = _PROJECT_ROOT / "docs" / "config" / "vpa.default.json"
DEFAULT_SCHEMA_PATH = _PROJECT_ROOT / "docs" / "config" / "vpa_config.schema.json"


# ---------------------------------------------------------------------------
# Frozen dataclass tree — mirrors vpa.default.json structure exactly
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class VolThresholds:
    low_lt: float
    high_gt: float
    ultra_high_gt: float


@dataclass(frozen=True)
class VolConfig:
    avg_window_N: int
    thresholds: VolThresholds


@dataclass(frozen=True)
class SpreadThresholds:
    narrow_lt: float
    wide_gt: float


@dataclass(frozen=True)
class SpreadConfig:
    avg_window_M: int
    thresholds: SpreadThresholds


@dataclass(frozen=True)
class TrendConfig:
    window_K: int


@dataclass(frozen=True)
class SetupConfig:
    window_X: int


@dataclass(frozen=True)
class GatesConfig:
    ctx1_trend_location_required: bool
    ctx2_dominant_alignment_policy: str   # "ALLOW" | "REDUCE_RISK" | "DISALLOW"
    ctx3_congestion_awareness_required: bool


@dataclass(frozen=True)
class VPAExecutionConfig:
    """Anti-lookahead execution semantics (distinct from legacy ExecutionConfig)."""
    signal_eval: str        # "BAR_CLOSE_ONLY"
    entry_timing: str       # "NEXT_BAR_OPEN"
    intrabar_allowed: bool


@dataclass(frozen=True)
class CostsConfig:
    fee_model: str   # "BPS" | "PER_TRADE"
    fee_value: float


@dataclass(frozen=True)
class SlippageConfig:
    model: str    # "BPS" | "TICKS"
    value: float


@dataclass(frozen=True)
class RiskConfig:
    risk_pct_per_trade: float
    max_concurrent_positions: int
    countertrend_multiplier: float
    daily_loss_limit_pct: float | None = None


@dataclass(frozen=True)
class VPAConfig:
    """Top-level VPA configuration. All thresholds for the determinism layer."""
    version: str
    vol: VolConfig
    spread: SpreadConfig
    trend: TrendConfig
    setup: SetupConfig
    gates: GatesConfig
    execution: VPAExecutionConfig
    costs: CostsConfig
    slippage: SlippageConfig
    risk: RiskConfig


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------


class VPAConfigError(Exception):
    """Raised when VPA config loading or validation fails."""


def _validate_schema(data: dict[str, Any], schema_path: Path) -> None:
    """Validate *data* against the JSON Schema at *schema_path*."""
    if not schema_path.exists():
        raise VPAConfigError(f"Schema file not found: {schema_path}")
    with open(schema_path) as f:
        schema = json.load(f)
    try:
        jsonschema.validate(instance=data, schema=schema)
    except jsonschema.ValidationError as exc:
        raise VPAConfigError(f"VPA config validation failed: {exc.message}") from exc


def _build_config(data: dict[str, Any]) -> VPAConfig:
    """Convert a raw dict (already validated) into the frozen dataclass tree."""
    vol_raw = data["vol"]
    spread_raw = data["spread"]
    risk_raw = data["risk"]

    return VPAConfig(
        version=data["version"],
        vol=VolConfig(
            avg_window_N=vol_raw["avg_window_N"],
            thresholds=VolThresholds(
                low_lt=vol_raw["thresholds"]["low_lt"],
                high_gt=vol_raw["thresholds"]["high_gt"],
                ultra_high_gt=vol_raw["thresholds"]["ultra_high_gt"],
            ),
        ),
        spread=SpreadConfig(
            avg_window_M=spread_raw["avg_window_M"],
            thresholds=SpreadThresholds(
                narrow_lt=spread_raw["thresholds"]["narrow_lt"],
                wide_gt=spread_raw["thresholds"]["wide_gt"],
            ),
        ),
        trend=TrendConfig(window_K=data["trend"]["window_K"]),
        setup=SetupConfig(window_X=data["setup"]["window_X"]),
        gates=GatesConfig(
            ctx1_trend_location_required=data["gates"]["ctx1_trend_location_required"],
            ctx2_dominant_alignment_policy=data["gates"]["ctx2_dominant_alignment_policy"],
            ctx3_congestion_awareness_required=data["gates"]["ctx3_congestion_awareness_required"],
        ),
        execution=VPAExecutionConfig(
            signal_eval=data["execution"]["signal_eval"],
            entry_timing=data["execution"]["entry_timing"],
            intrabar_allowed=data["execution"]["intrabar_allowed"],
        ),
        costs=CostsConfig(
            fee_model=data["costs"]["fee_model"],
            fee_value=data["costs"]["fee_value"],
        ),
        slippage=SlippageConfig(
            model=data["slippage"]["model"],
            value=data["slippage"]["value"],
        ),
        risk=RiskConfig(
            risk_pct_per_trade=risk_raw["risk_pct_per_trade"],
            max_concurrent_positions=risk_raw["max_concurrent_positions"],
            countertrend_multiplier=risk_raw["countertrend_multiplier"],
            daily_loss_limit_pct=risk_raw.get("daily_loss_limit_pct"),
        ),
    )


def load_vpa_config(
    config_path: str | Path | None = None,
    schema_path: str | Path | None = None,
) -> VPAConfig:
    """Load and validate VPA configuration.

    Parameters
    ----------
    config_path:
        Path to a VPA JSON config file.  Defaults to ``docs/config/vpa.default.json``.
    schema_path:
        Path to the JSON Schema file.  Defaults to ``docs/config/vpa_config.schema.json``.

    Returns
    -------
    VPAConfig
        Frozen dataclass tree with all VPA parameters.

    Raises
    ------
    VPAConfigError
        If the file is missing, unparseable, or fails schema validation.
    """
    cfg_path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH
    sch_path = Path(schema_path) if schema_path else DEFAULT_SCHEMA_PATH

    if not cfg_path.exists():
        raise VPAConfigError(f"VPA config file not found: {cfg_path}")

    try:
        with open(cfg_path) as f:
            data = json.load(f)
    except json.JSONDecodeError as exc:
        raise VPAConfigError(f"VPA config is not valid JSON: {exc}") from exc

    _validate_schema(data, sch_path)

    return _build_config(data)
