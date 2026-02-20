"""
Pipeline orchestrator: chains Features -> Rules -> Gates -> Composer -> Risk.

Single entry point for processing one bar through all VPA pipeline stages.
Matches VPA_SIGNAL_FLOW.md stage ordering.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from vpa_core.contracts import (
    Bar,
    CandleFeatures,
    ContextSnapshot,
    SignalEvent,
    TradeIntent,
)
from vpa_core.atr import compute_atr
from vpa_core.context_gates import GateResult, apply_gates
from vpa_core.feature_engine import extract_features
from vpa_core.relative_volume import average_volume
from vpa_core.risk_engine import AccountState, evaluate_risk
from vpa_core.rule_engine import (
    detect_conf_2,
    evaluate_avoidance_rules,
    evaluate_cluster_rules,
    evaluate_rules,
    evaluate_trend_rules,
)
from vpa_core.setup_composer import SetupComposer, SetupMatch

if TYPE_CHECKING:
    from config.vpa_config import VPAConfig


@dataclass(frozen=True)
class PipelineResult:
    """Complete output of one bar's pipeline evaluation.

    Every stage's output is preserved for observability and journaling.
    """

    bar_index: int
    features: CandleFeatures | None = None
    signals: list[SignalEvent] = field(default_factory=list)
    gate_result: GateResult | None = None
    matches: list[SetupMatch] = field(default_factory=list)
    intents: list[TradeIntent] = field(default_factory=list)
    daily_context: ContextSnapshot | None = None


def run_pipeline(
    bars: list[Bar],
    bar_index: int,
    context: ContextSnapshot,
    account: AccountState,
    config: VPAConfig,
    composer: SetupComposer,
    tf: str = "15m",
    daily_context: ContextSnapshot | None = None,
) -> PipelineResult:
    """Process one bar through the full VPA pipeline.

    Stages (per VPA_SIGNAL_FLOW.md):
        1. Feature Engine:  bars -> CandleFeatures
        2. Rule Engine:     CandleFeatures -> SignalEvent[]
        3. Context Gates:   SignalEvent[] + context -> GateResult
        4. Setup Composer:  actionable signals -> SetupMatch[]
        5. Risk Engine:     SetupMatch + account -> TradeIntent[]

    Parameters
    ----------
    bars:
        Bar history up to and including the current bar (oldest first).
    bar_index:
        Sequential bar counter for the setup composer.
    context:
        Current ContextSnapshot (from context engine or stub).
    account:
        Account state for risk calculations.
    config:
        VPA configuration.
    composer:
        Stateful SetupComposer instance (persists across bars).
    tf:
        Timeframe label.
    daily_context:
        Optional daily-timeframe ContextSnapshot for multi-timeframe
        analysis. When provided, CTX-2 resolves per-signal dominant
        alignment based on the daily trend.

    Returns
    -------
    PipelineResult
        Frozen dataclass with outputs from every stage.
    """
    if not bars:
        return PipelineResult(bar_index=bar_index)

    features = extract_features(bars, config, tf)

    if config.volume_guard.enabled:
        avg_vol = average_volume(bars, lookback=config.vol.avg_window_N)
        if avg_vol < config.volume_guard.min_avg_volume:
            return PipelineResult(bar_index=bar_index, features=features)

    bar_signals = evaluate_rules(features, config)
    trend_signals = evaluate_trend_rules(context, config)
    cluster_signals = evaluate_cluster_rules(bars, config, tf)

    conf_2 = detect_conf_2(bar_signals, trend_signals + cluster_signals, config)
    avoidance_signals = evaluate_avoidance_rules(bar_signals, context, config)
    signals = bar_signals + trend_signals + cluster_signals + avoidance_signals
    if conf_2 is not None:
        signals.append(conf_2)

    current_bar = bars[-1]
    for sig in signals:
        sig.evidence.setdefault("bar_low", current_bar.low)
        sig.evidence.setdefault("bar_high", current_bar.high)

    gate_result = apply_gates(signals, context, config, daily_context=daily_context)

    matches = composer.process_signals(gate_result.actionable, bar_index, context)

    current_price = bars[-1].close
    atr_value = compute_atr(bars, period=config.atr.period) if config.atr.enabled else 0.0

    intents: list[TradeIntent] = []
    for match in matches:
        intent = evaluate_risk(match, current_price, account, context, config, atr_value=atr_value)
        intents.append(intent)

    return PipelineResult(
        bar_index=bar_index,
        features=features,
        signals=signals,
        gate_result=gate_result,
        matches=matches,
        intents=intents,
        daily_context=daily_context,
    )
