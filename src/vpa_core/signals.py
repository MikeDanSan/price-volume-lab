"""
DEPRECATED — Use ``vpa_core.pipeline.run_pipeline`` instead.

This module exists only for backward compatibility with the legacy
CLI and backtest runner.  It will be removed once all callers have
migrated to the canonical pipeline (Commit 12+).
"""

import warnings

from vpa_core.contracts import (
    Bar,
    ContextWindow,
    Signal,
    TradePlan,
)
from vpa_core.setups.no_demand import check_no_demand


def evaluate(window: ContextWindow) -> list[tuple[Signal, TradePlan]]:
    """DEPRECATED: Use ``vpa_core.pipeline.run_pipeline`` instead."""
    warnings.warn(
        "signals.evaluate() is deprecated — use vpa_core.pipeline.run_pipeline()",
        DeprecationWarning,
        stacklevel=2,
    )
    bars = list(window.bars)
    if not bars:
        return []
    out: list[tuple[Signal, TradePlan]] = []
    current = bars[-1]
    bar_index = len(bars) - 1
    symbol = window.symbol

    # No Demand (bearish)
    if check_no_demand(bars):
        rationale = (
            "No demand: up bar(s) on low/declining volume in uptrend. "
            "Effort does not support result; buyers not in control. Rulebook: no_demand."
        )
        signal = Signal(
            setup_type="no_demand",
            direction="short",
            bar_index=bar_index,
            timestamp=current.timestamp,
            rationale=rationale,
            rulebook_ref="no_demand",
            strength=None,
        )
        signal_id = f"{symbol}_{current.timestamp.isoformat()}_bar_{bar_index}"
        trade_plan = TradePlan(
            signal_id=signal_id,
            setup_type="no_demand",
            direction="short",
            entry_condition="next_bar_open_or_close_below_no_demand_low",
            stop_level=current.high,
            invalidation_rules=[
                "next_bar_high_volume_up_move",
                "close_above_no_demand_high",
            ],
            rationale=rationale,
            rulebook_ref="no_demand",
            target_logic=None,
        )
        out.append((signal, trade_plan))

    return out
