"""
Rule Engine: CandleFeatures -> SignalEvent[].

Each registered rule is a pure function:
    detect_<rule_id>(features, config) -> SignalEvent | None

The orchestrator ``evaluate_rules`` collects all non-None results.

**Separation contract:** This module emits SignalEvents ONLY.
No TradePlan, no orders, no sizing. That belongs to later stages.

Canonical rules implemented:
    VAL-1  — Single-bar validation (bullish drive)
    ANOM-1 — "Big result, little effort" trap-up anomaly
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from vpa_core.contracts import (
    CandleFeatures,
    CandleType,
    SignalClass,
    SignalEvent,
    SpreadState,
    VolumeState,
)

if TYPE_CHECKING:
    from config.vpa_config import VPAConfig


# ---------------------------------------------------------------------------
# VAL-1 — Single-bar validation (bullish drive)
# Registry: close > open, spreadState == WIDE, volState in {HIGH, ULTRA_HIGH}
# ---------------------------------------------------------------------------


def detect_val_1(features: CandleFeatures, config: VPAConfig) -> SignalEvent | None:
    """Detect VAL-1: wide up bar on high/ultra-high volume = validated bullish drive.

    Conditions (from VPA_RULE_REGISTRY.yaml):
        - close > open  (candle_type == UP)
        - spreadState == WIDE
        - volState in {HIGH, ULTRA_HIGH}

    No context gate required for validation signals.
    """
    if features.candle_type != CandleType.UP:
        return None
    if features.spread_state != SpreadState.WIDE:
        return None
    if features.vol_state not in (VolumeState.HIGH, VolumeState.ULTRA_HIGH):
        return None

    return SignalEvent(
        id="VAL-1",
        name="SingleBarValidation_BullishDrive",
        tf=features.tf,
        ts=features.ts,
        signal_class=SignalClass.VALIDATION,
        direction_bias="BULLISH",
        priority=1,
        evidence={
            "spread_state": features.spread_state.value,
            "vol_state": features.vol_state.value,
            "vol_rel": features.vol_rel,
            "spread_rel": features.spread_rel,
        },
        requires_context_gate=False,
    )


# ---------------------------------------------------------------------------
# ANOM-1 — "Big result, little effort" trap-up anomaly
# Registry: close > open, spreadState == WIDE, volState == LOW
# ---------------------------------------------------------------------------


def detect_anom_1(features: CandleFeatures, config: VPAConfig) -> SignalEvent | None:
    """Detect ANOM-1: wide up bar on low volume = anomaly / trap-up warning.

    Conditions (from VPA_RULE_REGISTRY.yaml):
        - close > open  (candle_type == UP)
        - spreadState == WIDE
        - volState == LOW

    Requires CTX-1 gate (trend location must be known before acting).
    """
    if features.candle_type != CandleType.UP:
        return None
    if features.spread_state != SpreadState.WIDE:
        return None
    if features.vol_state != VolumeState.LOW:
        return None

    return SignalEvent(
        id="ANOM-1",
        name="BigResultLittleEffort_TrapUpWarning",
        tf=features.tf,
        ts=features.ts,
        signal_class=SignalClass.ANOMALY,
        direction_bias="BEARISH_OR_WAIT",
        priority=2,
        evidence={
            "spread_state": features.spread_state.value,
            "vol_state": features.vol_state.value,
            "vol_rel": features.vol_rel,
            "spread_rel": features.spread_rel,
        },
        requires_context_gate=True,
    )


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

_RULE_DETECTORS = [
    detect_val_1,
    detect_anom_1,
]


def evaluate_rules(
    features: CandleFeatures,
    config: VPAConfig,
) -> list[SignalEvent]:
    """Run all registered rule detectors and return any emitted signals.

    Returns an empty list if no rules fire (the common case).
    """
    signals: list[SignalEvent] = []
    for detector in _RULE_DETECTORS:
        result = detector(features, config)
        if result is not None:
            signals.append(result)
    return signals
