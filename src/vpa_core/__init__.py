"""
vpa-core: pure Volume Price Analysis rules engine.

No I/O, no network, no side effects. Consumes bars/context, produces
signals and TradePlans. Fully deterministic and unit-testable.
"""

from vpa_core.contracts import (
    Bar,
    ContextWindow,
    RelativeVolume,
    Signal,
    TradePlan,
)
from vpa_core.signals import evaluate

__all__ = [
    "Bar",
    "ContextWindow",
    "evaluate",
    "RelativeVolume",
    "Signal",
    "TradePlan",
]
