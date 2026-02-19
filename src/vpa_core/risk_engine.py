"""
Risk Engine: SetupMatch + account state + config -> TradeIntent.

Computes stop placement, position sizing, and applies hard rejects.
This is the final gate before execution.

Responsibilities:
    - Stop placement per setup-scoped rules (bar-based or ATR-based)
    - Position sizing from risk budget (risk_pct_per_trade)
    - Countertrend risk multiplier (CTX-2)
    - Hard rejects: max concurrent positions, daily loss limit
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from config.vpa_config import VPAConfig
from vpa_core.contracts import (
    ContextSnapshot,
    DominantAlignment,
    EntryPlan,
    RiskPlan,
    TradeIntent,
    TradeIntentStatus,
)
from vpa_core.setup_composer import SetupMatch


@dataclass(frozen=True)
class AccountState:
    """Current account snapshot for risk calculations."""
    equity: float
    open_position_count: int = 0
    daily_realized_pnl: float = 0.0


def _compute_stop_bar_based(match: SetupMatch, current_price: float) -> float:
    """Compute stop from the trigger bar's high/low.

    LONG: stop = trigger bar's low (fallback 2% below price).
    SHORT: stop = trigger bar's high (fallback 2% above price).
    """
    if match.signals:
        trigger = match.signals[0]
        if match.direction == "SHORT":
            bar_high = trigger.evidence.get("bar_high")
            if bar_high is not None:
                return float(bar_high)
            return current_price * 1.02
        bar_low = trigger.evidence.get("bar_low")
        if bar_low is not None:
            return float(bar_low)
    return current_price * 0.98


def _compute_stop_atr(
    direction: str,
    current_price: float,
    atr_value: float,
    multiplier: float,
) -> float:
    """Compute stop using ATR distance.

    LONG:  stop = current_price - (ATR × multiplier)
    SHORT: stop = current_price + (ATR × multiplier)
    """
    distance = atr_value * multiplier
    if direction == "SHORT":
        return current_price + distance
    return current_price - distance


def _compute_stop(
    match: SetupMatch,
    current_price: float,
    config: VPAConfig,
    atr_value: float = 0.0,
) -> tuple[float, str]:
    """Compute stop level and method label.

    When config.atr.enabled and atr_value > 0, uses ATR-based stop.
    Otherwise falls back to bar-based stop placement.

    Returns (stop_price, method) where method is "ATR" or "BAR".
    """
    if config.atr.enabled and atr_value > 0:
        stop = _compute_stop_atr(
            match.direction, current_price,
            atr_value, config.atr.stop_multiplier,
        )
        return stop, "ATR"

    return _compute_stop_bar_based(match, current_price), "BAR"


def _compute_size(
    equity: float,
    risk_pct: float,
    entry_price: float,
    stop_price: float,
) -> int:
    """Compute position size from risk budget.

    size = (equity * risk_pct) / |entry_price - stop_price|
    """
    risk_per_share = abs(entry_price - stop_price)
    if risk_per_share <= 0:
        return 0
    raw_size = (equity * risk_pct) / risk_per_share
    return max(1, math.floor(raw_size))


def evaluate_risk(
    match: SetupMatch,
    current_price: float,
    account: AccountState,
    context: ContextSnapshot,
    config: VPAConfig,
    atr_value: float = 0.0,
) -> TradeIntent:
    """Evaluate a completed setup match and produce a TradeIntent.

    Parameters
    ----------
    match:
        Completed setup from the Setup Composer.
    current_price:
        Latest bar close (approximation for next-bar entry).
    account:
        Current account state (equity, open positions, daily PnL).
    context:
        ContextSnapshot for dominant alignment check.
    config:
        VPA configuration (risk params, execution semantics).
    atr_value:
        Current ATR value (0.0 if unavailable). Used for
        volatility-adaptive stop placement when config.atr.enabled.

    Returns
    -------
    TradeIntent
        Status READY (approved) or REJECTED (with reason).
    """
    intent_id = f"TI-{match.setup_id}-bar{match.matched_at_bar}"
    rationale = [sig.id for sig in match.signals]

    # --- Hard rejects ---

    if account.open_position_count >= config.risk.max_concurrent_positions:
        return _reject(
            intent_id, match, config,
            reason=f"Max concurrent positions ({config.risk.max_concurrent_positions}) reached",
            rationale=rationale,
        )

    if config.risk.daily_loss_limit_pct is not None:
        daily_loss_limit = account.equity * config.risk.daily_loss_limit_pct
        if account.daily_realized_pnl <= -daily_loss_limit:
            return _reject(
                intent_id, match, config,
                reason=f"Daily loss limit ({config.risk.daily_loss_limit_pct:.1%}) reached",
                rationale=rationale,
            )

    # --- Compute stop and size ---

    stop, stop_method = _compute_stop(match, current_price, config, atr_value)
    if stop_method == "ATR":
        rationale.append(f"stop:ATR({config.atr.period})x{config.atr.stop_multiplier}")
    risk_pct = config.risk.risk_pct_per_trade

    if config.gates.ctx2_dominant_alignment_policy == "REDUCE_RISK":
        if context.dominant_alignment == DominantAlignment.AGAINST:
            risk_pct *= config.risk.countertrend_multiplier
            rationale.append("CTX-2:AGAINST(risk_reduced)")
        elif context.dominant_alignment == DominantAlignment.WITH:
            rationale.append("CTX-2:WITH")

    size = _compute_size(account.equity, risk_pct, current_price, stop)

    if size <= 0:
        return _reject(
            intent_id, match, config,
            reason="Computed size is zero (stop too close or equity too low)",
            rationale=rationale,
        )

    return TradeIntent(
        intent_id=intent_id,
        direction=match.direction,
        tf=match.tf,
        setup=match.setup_id,
        status=TradeIntentStatus.READY,
        entry_plan=EntryPlan(
            timing=config.execution.entry_timing,
            order_type="MARKET",
        ),
        risk_plan=RiskPlan(
            stop=stop,
            risk_pct=risk_pct,
            size=size,
        ),
        rationale=rationale,
    )


def _reject(
    intent_id: str,
    match: SetupMatch,
    config: VPAConfig,
    *,
    reason: str,
    rationale: list[str],
) -> TradeIntent:
    """Build a REJECTED TradeIntent."""
    return TradeIntent(
        intent_id=intent_id,
        direction=match.direction,
        tf=match.tf,
        setup=match.setup_id,
        status=TradeIntentStatus.REJECTED,
        entry_plan=EntryPlan(
            timing=config.execution.entry_timing,
            order_type="MARKET",
        ),
        risk_plan=RiskPlan(stop=0.0, risk_pct=0.0, size=0),
        rationale=rationale,
        reject_reason=reason,
    )
