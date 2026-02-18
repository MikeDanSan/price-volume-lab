"""
vpa-core: pure Volume Price Analysis rules engine.

No I/O, no network, no side effects. Consumes bars/context, produces
signals and TradePlans. Fully deterministic and unit-testable.
"""

from vpa_core.contracts import (
    Bar,
    CandleFeatures,
    CandleType,
    Congestion,
    ContextSnapshot,
    ContextWindow,
    DominantAlignment,
    EntryPlan,
    RelativeVolume,
    RiskPlan,
    Signal,
    SignalClass,
    SignalEvent,
    SpreadState,
    TradeIntent,
    TradeIntentStatus,
    TradePlan,
    Trend,
    TrendLocation,
    TrendStrength,
    VolumeState,
)
from vpa_core.signals import evaluate

__all__ = [
    "Bar",
    "CandleFeatures",
    "CandleType",
    "Congestion",
    "ContextSnapshot",
    "ContextWindow",
    "DominantAlignment",
    "EntryPlan",
    "evaluate",
    "RelativeVolume",
    "RiskPlan",
    "Signal",
    "SignalClass",
    "SignalEvent",
    "SpreadState",
    "TradeIntent",
    "TradeIntentStatus",
    "TradePlan",
    "Trend",
    "TrendLocation",
    "TrendStrength",
    "VolumeState",
]
