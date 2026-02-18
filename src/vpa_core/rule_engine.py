"""
Rule Engine: CandleFeatures -> SignalEvent[].

Each registered rule is a pure function:
    detect_<rule_id>(features, config) -> SignalEvent | None

The orchestrator ``evaluate_rules`` collects all non-None results.

**Separation contract:** This module emits SignalEvents ONLY.
No TradePlan, no orders, no sizing. That belongs to later stages.

Canonical rules implemented:
    VAL-1      — Single-bar validation (bullish drive)
    ANOM-1     — "Big result, little effort" trap-up anomaly
    ANOM-2     — "Big effort, little result" absorption/weakness
    STR-1      — Hammer (strength: selling absorbed, reversal candidate)
    WEAK-1     — Shooting star (weakness: demand exhaustion)
    TEST-SUP-1 — Test of supply (low-vol quiet bar = selling pressure removed)
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
# STR-1 — Hammer (strength: selling absorbed, reversal candidate)
# Registry: lower_wick/range >= min, body/range <= max, upper_wick/range <= max
# ---------------------------------------------------------------------------


def detect_str_1(features: CandleFeatures, config: VPAConfig) -> SignalEvent | None:
    """Detect STR-1: hammer candle — session falls then recovers.

    Conditions (from VPA_RULE_REGISTRY.yaml, thresholds from config):
        - range > 0  (skip doji / zero-range bars)
        - lower_wick / range >= hammer.lower_wick_ratio_min
        - spread / range      <= hammer.body_ratio_max
        - upper_wick / range  <= hammer.upper_wick_ratio_max

    Couling: hammer signals selling absorbed; powerful with VPA context.
    Requires CTX-1 gate (typically after decline).
    """
    rng = features.range
    if rng <= 0:
        return None

    h = config.candle_patterns.hammer
    lower_ratio = features.lower_wick / rng
    body_ratio = features.spread / rng
    upper_ratio = features.upper_wick / rng

    if lower_ratio < h.lower_wick_ratio_min:
        return None
    if body_ratio > h.body_ratio_max:
        return None
    if upper_ratio > h.upper_wick_ratio_max:
        return None

    return SignalEvent(
        id="STR-1",
        name="Hammer_SellingAbsorbed",
        tf=features.tf,
        ts=features.ts,
        signal_class=SignalClass.STRENGTH,
        direction_bias="BULLISH",
        priority=2,
        evidence={
            "lower_wick_ratio": round(lower_ratio, 4),
            "body_ratio": round(body_ratio, 4),
            "upper_wick_ratio": round(upper_ratio, 4),
            "vol_state": features.vol_state.value,
            "spread_state": features.spread_state.value,
        },
        requires_context_gate=True,
    )


# ---------------------------------------------------------------------------
# WEAK-1 — Shooting star (weakness: demand exhaustion)
# Registry: upper_wick/range >= min, body/range <= max, lower_wick/range <= max
# ---------------------------------------------------------------------------


def detect_weak_1(features: CandleFeatures, config: VPAConfig) -> SignalEvent | None:
    """Detect WEAK-1: shooting star — market pushed higher then falls back.

    Conditions (from VPA_RULE_REGISTRY.yaml, thresholds from config):
        - range > 0  (skip doji / zero-range bars)
        - upper_wick / range >= shooting_star.upper_wick_ratio_min
        - spread / range      <= shooting_star.body_ratio_max
        - lower_wick / range  <= shooting_star.lower_wick_ratio_max

    Couling: in downtrends confirms weakness; after selling climax can
    be a test of demand as market moves lower.
    Requires CTX-1 gate (trend/phase context needed).
    """
    rng = features.range
    if rng <= 0:
        return None

    ss = config.candle_patterns.shooting_star
    upper_ratio = features.upper_wick / rng
    body_ratio = features.spread / rng
    lower_ratio = features.lower_wick / rng

    if upper_ratio < ss.upper_wick_ratio_min:
        return None
    if body_ratio > ss.body_ratio_max:
        return None
    if lower_ratio > ss.lower_wick_ratio_max:
        return None

    return SignalEvent(
        id="WEAK-1",
        name="ShootingStar_DemandExhaustion",
        tf=features.tf,
        ts=features.ts,
        signal_class=SignalClass.WEAKNESS,
        direction_bias="BEARISH",
        priority=2,
        evidence={
            "upper_wick_ratio": round(upper_ratio, 4),
            "body_ratio": round(body_ratio, 4),
            "lower_wick_ratio": round(lower_ratio, 4),
            "vol_state": features.vol_state.value,
            "spread_state": features.spread_state.value,
        },
        requires_context_gate=True,
    )


# ---------------------------------------------------------------------------
# ANOM-2 — "Big effort, little result" (absorption/weakness)
# Registry: volState in {HIGH, ULTRA_HIGH}, spreadState in {NARROW, NORMAL}
# ---------------------------------------------------------------------------


def detect_anom_2(features: CandleFeatures, config: VPAConfig) -> SignalEvent | None:
    """Detect ANOM-2: high volume but narrow/normal spread = absorption/weakness.

    Conditions (from VPA_RULE_REGISTRY.yaml):
        - volState in {HIGH, ULTRA_HIGH}
        - spreadState in {NARROW, NORMAL}

    Couling: high effort not producing expected result — insiders
    selling/absorbing at this level. Direction-agnostic: works on
    both up and down bars.

    Requires CTX-1 gate (trend location must be known).
    """
    if features.vol_state not in (VolumeState.HIGH, VolumeState.ULTRA_HIGH):
        return None
    if features.spread_state not in (SpreadState.NARROW, SpreadState.NORMAL):
        return None

    return SignalEvent(
        id="ANOM-2",
        name="BigEffortLittleResult_Absorption",
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
            "candle_type": features.candle_type.value,
        },
        requires_context_gate=True,
    )


# ---------------------------------------------------------------------------
# TEST-SUP-1 — Test of supply (low-vol quiet bar = selling pressure removed)
# Registry: volState == LOW, spreadState in {NARROW, NORMAL}
# ---------------------------------------------------------------------------


def detect_test_sup_1(features: CandleFeatures, config: VPAConfig) -> SignalEvent | None:
    """Detect TEST-SUP-1: quiet, low-volume bar = supply test pass.

    Conditions (from VPA_RULE_REGISTRY.yaml):
        - volState == LOW
        - spreadState in {NARROW, NORMAL}

    Couling: a low-volume test bar near support/congestion confirms
    selling pressure has been removed. "One of the most powerful signals."

    Requires CTX-1 gate (congestion/trend context must be known).
    Evidence includes bar_low for stop placement in ENTRY-LONG-1.
    """
    if features.vol_state != VolumeState.LOW:
        return None
    if features.spread_state not in (SpreadState.NARROW, SpreadState.NORMAL):
        return None

    return SignalEvent(
        id="TEST-SUP-1",
        name="TestOfSupply_SellingPressureRemoved",
        tf=features.tf,
        ts=features.ts,
        signal_class=SignalClass.TEST,
        direction_bias="BULLISH",
        priority=1,
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
    detect_anom_2,
    detect_str_1,
    detect_weak_1,
    detect_test_sup_1,
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
