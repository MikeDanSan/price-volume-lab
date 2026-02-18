"""
Context Gates: filter SignalEvent[] based on ContextSnapshot.

Implements the mandatory context gates from VPA_ACTIONABLE_RULES §2
that must be applied *before* any entry logic.

Implemented gates:
    CTX-1 — Trend-location-first: anomalies require known trend location.
    CTX-2 — Dominant alignment: block counter-trend signals when policy is DISALLOW.

Returns both actionable and blocked lists for full observability.
No signals are discarded silently.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from vpa_core.contracts import (
    ContextSnapshot,
    DominantAlignment,
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


def _check_ctx_2(signal: SignalEvent, context: ContextSnapshot, config: VPAConfig) -> str | None:
    """CTX-2: dominant alignment gate.

    Policy-driven behavior (config.gates.ctx2_dominant_alignment_policy):
        DISALLOW  — block gated signals when dominant alignment is AGAINST.
        REDUCE_RISK — pass through (Risk Engine handles sizing reduction).
        ALLOW — no action.

    Returns a reason string if blocked, None if passed.
    """
    if config.gates.ctx2_dominant_alignment_policy != "DISALLOW":
        return None
    if not signal.requires_context_gate:
        return None
    if context.dominant_alignment == DominantAlignment.AGAINST:
        return "CTX-2: dominant alignment AGAINST — counter-trend signal blocked (DISALLOW policy)"
    return None


def apply_gates(
    signals: list[SignalEvent],
    context: ContextSnapshot,
    config: VPAConfig,
) -> GateResult:
    """Apply all context gates to a list of signals.

    Gate ordering: CTX-1 checked first, then CTX-2. A signal blocked by
    an earlier gate is not checked against later gates.

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

    gate_checks = [_check_ctx_1, _check_ctx_2]

    for signal in signals:
        block_reason: str | None = None
        for check in gate_checks:
            block_reason = check(signal, context, config)
            if block_reason is not None:
                break

        if block_reason is not None:
            blocked.append(signal)
            key = f"{signal.id}@{signal.ts.isoformat()}"
            reasons[key] = block_reason
        else:
            actionable.append(signal)

    return GateResult(
        actionable=actionable,
        blocked=blocked,
        block_reasons=reasons,
    )
