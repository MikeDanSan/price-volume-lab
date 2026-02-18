"""
DEPRECATED — Use ``vpa_core.pipeline.run_pipeline`` instead.

This module is a stub kept only for backward compatibility with
legacy CLI commands (scan, paper) that have not yet migrated.
It always returns an empty list; the canonical pipeline handles
all signal detection.
"""

import warnings

from vpa_core.contracts import (
    ContextWindow,
    Signal,
    TradePlan,
)


def evaluate(window: ContextWindow) -> list[tuple[Signal, TradePlan]]:
    """DEPRECATED: Use ``vpa_core.pipeline.run_pipeline`` instead.

    Always returns an empty list. Legacy no_demand detection has been
    removed; all signal detection is now in the canonical pipeline.
    """
    warnings.warn(
        "signals.evaluate() is deprecated — use vpa_core.pipeline.run_pipeline()",
        DeprecationWarning,
        stacklevel=2,
    )
    return []
