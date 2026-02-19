"""
VPA config loader: JSON file -> frozen dataclass tree, validated against JSON Schema.

Canonical reference: docs/vpa/VPA_CONFIG.md
Default values:      docs/config/vpa.default.json
Schema:              docs/config/vpa_config.schema.json

Per-symbol overrides: place a partial JSON file named ``vpa.{SYMBOL}.json``
next to the default config (e.g. ``docs/config/vpa.SPY.json``). Only the
keys you want to override need to be present; they are deep-merged on top
of the base config before schema validation.

Usage:
    from config.vpa_config import load_vpa_config
    cfg = load_vpa_config()                        # loads default
    cfg = load_vpa_config(symbol="SPY")            # merges vpa.SPY.json if present
    cfg = load_vpa_config("my_overrides.json")     # loads custom file
    cfg.vol.thresholds.low_lt  # -> 0.8
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import jsonschema

logger = logging.getLogger("vpa.config")

# ---------------------------------------------------------------------------
# Project root detection (walk up from this file to find pyproject.toml)
# ---------------------------------------------------------------------------


def _find_project_root() -> Path:
    """Walk up from this file looking for pyproject.toml.

    When running from source, finds the repo root.  When installed as a
    package (e.g. inside Docker), pyproject.toml won't exist — fall back
    to CWD which is /app in the container.
    """
    candidate = Path(__file__).resolve().parent
    for _ in range(10):
        if (candidate / "pyproject.toml").exists():
            return candidate
        parent = candidate.parent
        if parent == candidate:
            break
        candidate = parent
    return Path.cwd()


_PROJECT_ROOT = _find_project_root()

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
    location_lookback: int = 20
    congestion_window: int = 10
    congestion_pct: float = 0.30


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
class HammerConfig:
    lower_wick_ratio_min: float
    body_ratio_max: float
    upper_wick_ratio_max: float


@dataclass(frozen=True)
class ShootingStarConfig:
    upper_wick_ratio_min: float
    body_ratio_max: float
    lower_wick_ratio_max: float


@dataclass(frozen=True)
class LongLeggedDojiConfig:
    body_ratio_max: float
    min_wick_ratio: float


@dataclass(frozen=True)
class CandlePatternsConfig:
    hammer: HammerConfig
    shooting_star: ShootingStarConfig
    long_legged_doji: LongLeggedDojiConfig


@dataclass(frozen=True)
class RiskConfig:
    risk_pct_per_trade: float
    max_concurrent_positions: int
    countertrend_multiplier: float
    daily_loss_limit_pct: float | None = None


@dataclass(frozen=True)
class VolumeGuardConfig:
    enabled: bool = True
    min_avg_volume: int = 10_000


@dataclass(frozen=True)
class AtrConfig:
    period: int = 14
    stop_multiplier: float = 1.5
    enabled: bool = False


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
    candle_patterns: CandlePatternsConfig
    risk: RiskConfig
    volume_guard: VolumeGuardConfig = VolumeGuardConfig()
    atr: AtrConfig = AtrConfig()


# ---------------------------------------------------------------------------
# Deep merge for per-symbol overrides
# ---------------------------------------------------------------------------


def _deep_merge(base: dict[str, Any], overrides: dict[str, Any]) -> dict[str, Any]:
    """Recursively merge *overrides* into a copy of *base*.

    - Dict values are merged recursively (override keys win).
    - Non-dict values in overrides replace the base value.
    - Keys in base that are absent from overrides are preserved.
    """
    merged = dict(base)
    for key, val in overrides.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(val, dict):
            merged[key] = _deep_merge(merged[key], val)
        else:
            merged[key] = val
    return merged


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
    cp_raw = data.get("candle_patterns", {})

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
        trend=TrendConfig(
            window_K=data["trend"]["window_K"],
            location_lookback=data["trend"].get("location_lookback", 20),
            congestion_window=data["trend"].get("congestion_window", 10),
            congestion_pct=data["trend"].get("congestion_pct", 0.30),
        ),
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
        candle_patterns=CandlePatternsConfig(
            hammer=HammerConfig(
                lower_wick_ratio_min=cp_raw.get("hammer", {}).get("lower_wick_ratio_min", 0.60),
                body_ratio_max=cp_raw.get("hammer", {}).get("body_ratio_max", 0.33),
                upper_wick_ratio_max=cp_raw.get("hammer", {}).get("upper_wick_ratio_max", 0.10),
            ),
            shooting_star=ShootingStarConfig(
                upper_wick_ratio_min=cp_raw.get("shooting_star", {}).get("upper_wick_ratio_min", 0.60),
                body_ratio_max=cp_raw.get("shooting_star", {}).get("body_ratio_max", 0.33),
                lower_wick_ratio_max=cp_raw.get("shooting_star", {}).get("lower_wick_ratio_max", 0.10),
            ),
            long_legged_doji=LongLeggedDojiConfig(
                body_ratio_max=cp_raw.get("long_legged_doji", {}).get("body_ratio_max", 0.25),
                min_wick_ratio=cp_raw.get("long_legged_doji", {}).get("min_wick_ratio", 0.25),
            ),
        ),
        risk=RiskConfig(
            risk_pct_per_trade=risk_raw["risk_pct_per_trade"],
            max_concurrent_positions=risk_raw["max_concurrent_positions"],
            countertrend_multiplier=risk_raw["countertrend_multiplier"],
            daily_loss_limit_pct=risk_raw.get("daily_loss_limit_pct"),
        ),
        volume_guard=VolumeGuardConfig(
            enabled=data.get("volume_guard", {}).get("enabled", True),
            min_avg_volume=data.get("volume_guard", {}).get("min_avg_volume", 10_000),
        ),
        atr=AtrConfig(
            period=data.get("atr", {}).get("period", 14),
            stop_multiplier=data.get("atr", {}).get("stop_multiplier", 1.5),
            enabled=data.get("atr", {}).get("enabled", False),
        ),
    )


def load_vpa_config(
    config_path: str | Path | None = None,
    schema_path: str | Path | None = None,
    symbol: str | None = None,
) -> VPAConfig:
    """Load and validate VPA configuration.

    Parameters
    ----------
    config_path:
        Path to a VPA JSON config file.  Defaults to ``docs/config/vpa.default.json``.
    schema_path:
        Path to the JSON Schema file.  Defaults to ``docs/config/vpa_config.schema.json``.
    symbol:
        Optional ticker symbol.  When provided, the loader looks for a
        per-symbol override file ``vpa.{SYMBOL}.json`` in the same directory
        as the base config.  If found, the override is deep-merged on top
        of the base config before schema validation.  If not found, the
        base config is used as-is (no error).

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

    if symbol:
        override_path = cfg_path.parent / f"vpa.{symbol.upper()}.json"
        if override_path.exists():
            try:
                with open(override_path) as f:
                    overrides = json.load(f)
            except json.JSONDecodeError as exc:
                raise VPAConfigError(
                    f"Per-symbol config {override_path.name} is not valid JSON: {exc}"
                ) from exc
            data = _deep_merge(data, overrides)
            logger.info("Loaded per-symbol config: %s", override_path.name)
        else:
            logger.debug("No per-symbol config found at %s — using defaults", override_path)

    _validate_schema(data, sch_path)

    return _build_config(data)
