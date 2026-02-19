"""
Configuration loaders.

App config:  reads config.yaml, resolves env vars for secrets.
VPA config:  reads vpa.default.json (or override), validates against JSON Schema.
"""

from config.loader import (
    AppConfig,
    BacktestConfig,
    DataConfig,
    ExecutionConfig,
    JournalConfig,
    load_config,
)
from config.vpa_config import (
    AtrConfig,
    CostsConfig,
    GatesConfig,
    RiskConfig,
    SetupConfig,
    SlippageConfig,
    SpreadConfig,
    SpreadThresholds,
    TrendConfig,
    VolConfig,
    VolThresholds,
    VPAConfig,
    VPAConfigError,
    VPAExecutionConfig,
    load_vpa_config,
)

__all__ = [
    # App config (YAML)
    "AppConfig",
    "BacktestConfig",
    "DataConfig",
    "ExecutionConfig",
    "JournalConfig",
    "load_config",
    # VPA config (JSON + schema)
    "AtrConfig",
    "CostsConfig",
    "GatesConfig",
    "RiskConfig",
    "SetupConfig",
    "SlippageConfig",
    "SpreadConfig",
    "SpreadThresholds",
    "TrendConfig",
    "VolConfig",
    "VolThresholds",
    "VPAConfig",
    "VPAConfigError",
    "VPAExecutionConfig",
    "load_vpa_config",
]
