"""
Context Gates: filter SignalEvent[] based on ContextSnapshot.

Implements the mandatory context gates from VPA_ACTIONABLE_RULES §2
that must be applied *before* any entry logic.

Currently implemented:
    CTX-1 — Trend-location-first gate: anomalies require known trend location.

Returns both actionable and blocked lists for full observability.
No signals are discarded silently.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from vpa_core.contracts import (
    ContextSnapshot,
    SignalClass,
    SignalEvent,
    TrendLocation,
)

if TYPE_CHECKING:
    from config.vpa_config import VPAConfig


@dataclass(frozen=True)
class GateResult:
    """Output of the context gate stage — split into actionable and blocked."""
    actionable: list[SignalEvent] = field(default_factory=list)
    blocked: list[SignalEvent] = field(default_factory=list)
    block_reasons: dict[str, str] = field(default_factory=dict)


def _check_ctx_1(signal: SignalEvent, context: ContextSnapshot, config: VPAConfig) -> str | None:
    """CTX-1: if the signal requires a context gate and trend location is UNKNOWN, block it.

    Returns a reason string if blocked, None if passed.
    """
    if not config.gates.ctx1_trend_location_required:
        return None
    if not signal.requires_context_gate:
        return None
    if context.trend_location == TrendLocation.UNKNOWN:
        return "CTX-1: trend location UNKNOWN — cannot assess anomaly significance"
    return None


def apply_gates(
    signals: list[SignalEvent],
    context: ContextSnapshot,
    config: VPAConfig,
) -> GateResult:
    """Apply all context gates to a list of signals.

    Parameters
    ----------
    signals:
        SignalEvent list from the rule engine.
    context:
        Current ContextSnapshot for the timeframe.
    config:
        VPA configuration (gate toggles).

    Returns
    -------
    GateResult
        Frozen dataclass with ``actionable``, ``blocked``, and ``block_reasons``.
    """
    actionable: list[SignalEvent] = []
    blocked: list[SignalEvent] = []
    reasons: dict[str, str] = {}

    for signal in signals:
        reason = _check_ctx_1(signal, context, config)
        if reason is not None:
            blocked.append(signal)
            key = f"{signal.id}@{signal.ts.isoformat()}"
            reasons[key] = reason
        else:
            actionable.append(signal)

    return GateResult(
        actionable=actionable,
        blocked=blocked,
        block_reasons=reasons,
    )
