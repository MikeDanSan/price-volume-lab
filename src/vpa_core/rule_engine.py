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
    WEAK-2     — Shooting star + LOW volume (no demand)
    CLIMAX-SELL-1 — Selling climax bar (deep upper wick + high vol at top)
    CONF-1     — Positive response (confirmation candle)
    AVOID-NEWS-1 — Long-legged doji on low volume (manipulation/stand-aside)
    TEST-SUP-1 — Test of supply (low-vol quiet bar = selling pressure removed)
    TEST-SUP-2 — Failed test of supply (high-vol = supply still present)
    TEST-DEM-1 — Test of demand (low-vol push higher closes near open = no demand)
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from vpa_core.contracts import (
    CandleFeatures,
    CandleType,
    ContextSnapshot,
    SignalClass,
    SignalEvent,
    SpreadState,
    Trend,
    VolumeState,
    VolumeTrend,
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
# WEAK-2 — Shooting star + LOW volume ("no demand")
# Registry: WEAK-1 candle shape + volState == LOW
# ---------------------------------------------------------------------------


def detect_weak_2(features: CandleFeatures, config: VPAConfig) -> SignalEvent | None:
    """Detect WEAK-2: shooting star on LOW volume = no demand confirmation.

    Conditions (from VPA_ACTIONABLE_RULES §5):
        - WEAK-1 candle shape (shooting star geometry)
        - volState == LOW

    Couling: shooting star shows market pushed higher but "no demand",
    confirmed by low volume. More decisive than WEAK-1 alone because
    volume confirms the lack of buying interest.

    Requires CTX-1 gate (trend/phase context needed).
    """
    rng = features.range
    if rng <= 0:
        return None

    if features.vol_state != VolumeState.LOW:
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
        id="WEAK-2",
        name="ShootingStar_NoDemand",
        tf=features.tf,
        ts=features.ts,
        signal_class=SignalClass.WEAKNESS,
        direction_bias="BEARISH",
        priority=1,
        evidence={
            "upper_wick_ratio": round(upper_ratio, 4),
            "body_ratio": round(body_ratio, 4),
            "lower_wick_ratio": round(lower_ratio, 4),
            "vol_state": features.vol_state.value,
            "vol_rel": features.vol_rel,
        },
        requires_context_gate=True,
    )


# ---------------------------------------------------------------------------
# CLIMAX-SELL-1 — Selling climax bar (deep upper wick + high volume)
# Registry: shooting star shape + volState in {HIGH, ULTRA_HIGH}
# ---------------------------------------------------------------------------


def detect_climax_sell_1(features: CandleFeatures, config: VPAConfig) -> SignalEvent | None:
    """Detect CLIMAX-SELL-1: selling climax bar — surges higher then closes
    back near open on high/ultra-high volume.

    Conditions (from VPA_ACTIONABLE_RULES section 7):
        - range > 0
        - Shooting star geometry (same thresholds as WEAK-1)
        - volState in {HIGH, ULTRA_HIGH}

    Couling: deep upper wick + high volume is one of the most powerful
    combinations. Signals distribution / smart-money selling into retail
    buying. Repeated occurrences = market ready to move fast downward.

    Single-bar detection. Repetition counting (>= 2 within window) is
    handled by the Setup Composer for ENTRY-SHORT-1.

    Requires CTX-1 gate (trend location / distribution context needed).
    """
    rng = features.range
    if rng <= 0:
        return None

    if features.vol_state not in (VolumeState.HIGH, VolumeState.ULTRA_HIGH):
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
        id="CLIMAX-SELL-1",
        name="SellingClimax_Distribution",
        tf=features.tf,
        ts=features.ts,
        signal_class=SignalClass.WEAKNESS,
        direction_bias="BEARISH",
        priority=1,
        evidence={
            "upper_wick_ratio": round(upper_ratio, 4),
            "body_ratio": round(body_ratio, 4),
            "lower_wick_ratio": round(lower_ratio, 4),
            "vol_state": features.vol_state.value,
            "vol_rel": features.vol_rel,
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
# CONF-1 — Positive response bar (confirmation candle)
# Registry: candle_type == UP, volState >= AVERAGE, spreadState >= NORMAL
# ---------------------------------------------------------------------------


def detect_conf_1(features: CandleFeatures, config: VPAConfig) -> SignalEvent | None:
    """Detect CONF-1: positive response bar — bullish confirmation candle.

    Conditions (from VPA_RULE_REGISTRY.yaml):
        - candle_type == UP  (close > open)
        - volState in {AVERAGE, HIGH, ULTRA_HIGH}  (not low — needs backing)
        - spreadState in {NORMAL, WIDE}  (visible body, not a doji)

    This signal is intentionally broad on its own. It becomes meaningful
    only when the Setup Composer pairs it with a prior strength/test
    signal (e.g., STR-1 → CONF-1 = ENTRY-LONG-2 candidate).

    Couling: "Is this stopping volume — perhaps, and we wait for the
    next candle…"; lack of positive response is not bullish.

    No context gate required (the prior signal's gate is sufficient).
    """
    if features.candle_type != CandleType.UP:
        return None
    if features.vol_state not in (VolumeState.AVERAGE, VolumeState.HIGH, VolumeState.ULTRA_HIGH):
        return None
    if features.spread_state not in (SpreadState.NORMAL, SpreadState.WIDE):
        return None

    return SignalEvent(
        id="CONF-1",
        name="PositiveResponse_Confirmation",
        tf=features.tf,
        ts=features.ts,
        signal_class=SignalClass.CONFIRMATION,
        direction_bias="BULLISH",
        priority=3,
        evidence={
            "candle_type": features.candle_type.value,
            "spread_state": features.spread_state.value,
            "vol_state": features.vol_state.value,
            "vol_rel": features.vol_rel,
            "spread_rel": features.spread_rel,
        },
        requires_context_gate=False,
    )


# ---------------------------------------------------------------------------
# AVOID-NEWS-1 — Long-legged doji on LOW volume (manipulation / stand-aside)
# Registry: spread/range <= max, both wicks >= min, volState == LOW
# ---------------------------------------------------------------------------


def detect_avoid_news_1(features: CandleFeatures, config: VPAConfig) -> SignalEvent | None:
    """Detect AVOID-NEWS-1: long-legged doji on low volume = manipulation.

    Conditions (from VPA_RULE_REGISTRY.yaml, thresholds from config):
        - range > 0
        - spread / range  <= long_legged_doji.body_ratio_max  (close near open)
        - upper_wick / range >= long_legged_doji.min_wick_ratio  (significant upper wick)
        - lower_wick / range >= long_legged_doji.min_wick_ratio  (significant lower wick)
        - volState == LOW

    Couling: low volume with wide two-sided range is anomaly — insiders
    "racking" price / stop hunting. "We stay out, and wait for further candles."

    No context gate required (avoidance overrides all).
    """
    rng = features.range
    if rng <= 0:
        return None

    if features.vol_state != VolumeState.LOW:
        return None

    doji = config.candle_patterns.long_legged_doji
    body_ratio = features.spread / rng
    upper_ratio = features.upper_wick / rng
    lower_ratio = features.lower_wick / rng

    if body_ratio > doji.body_ratio_max:
        return None
    if upper_ratio < doji.min_wick_ratio:
        return None
    if lower_ratio < doji.min_wick_ratio:
        return None

    return SignalEvent(
        id="AVOID-NEWS-1",
        name="LongLeggedDoji_Manipulation",
        tf=features.tf,
        ts=features.ts,
        signal_class=SignalClass.AVOIDANCE,
        direction_bias="NEUTRAL",
        priority=0,
        evidence={
            "body_ratio": round(body_ratio, 4),
            "upper_wick_ratio": round(upper_ratio, 4),
            "lower_wick_ratio": round(lower_ratio, 4),
            "vol_state": features.vol_state.value,
        },
        requires_context_gate=False,
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
# TEST-SUP-2 — Failed test of supply (high volume = supply still present)
# Canonical: VPA_ACTIONABLE_RULES §6 — TEST-SUP setup bar but HIGH/ULTRA vol
# ---------------------------------------------------------------------------


def detect_test_sup_2(features: CandleFeatures, config: VPAConfig) -> SignalEvent | None:
    """Detect TEST-SUP-2: failed supply test — supply still present.

    Conditions (from VPA_ACTIONABLE_RULES §6):
        - volState in {HIGH, ULTRA_HIGH}  (supply still present)
        - spreadState in {NARROW, NORMAL}  (same bar shape as TEST-SUP-1)

    Couling: on a failed test, expect insiders to take the market back
    into congestion to flush selling pressure, then test again.

    Requires CTX-1 gate (congestion/trend context must be known).
    """
    if features.vol_state not in (VolumeState.HIGH, VolumeState.ULTRA_HIGH):
        return None
    if features.spread_state not in (SpreadState.NARROW, SpreadState.NORMAL):
        return None

    return SignalEvent(
        id="TEST-SUP-2",
        name="FailedTestOfSupply_SupplyStillPresent",
        tf=features.tf,
        ts=features.ts,
        signal_class=SignalClass.TEST,
        direction_bias="BEARISH_OR_WAIT",
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
# TEST-DEM-1 — Test of demand (post-distribution, no demand confirmation)
# Canonical: VPA_ACTIONABLE_RULES §6 — pushed higher, closes near open, LOW vol
# ---------------------------------------------------------------------------


def detect_test_dem_1(features: CandleFeatures, config: VPAConfig) -> SignalEvent | None:
    """Detect TEST-DEM-1: demand test pass — no demand returning.

    Conditions (from VPA_ACTIONABLE_RULES §6):
        - range > 0
        - spread / range <= body_ratio_max  (close near open)
        - upper_wick > lower_wick  (market was pushed higher)
        - volState == LOW  (no demand backing the push)

    Uses shooting_star.body_ratio_max for the "close near open" threshold.

    Couling: market pushed higher but closes back near open with very
    low volume — safe to start moving the market lower, and fast.

    Requires CTX-1 gate (distribution/trend context must be known).
    """
    rng = features.range
    if rng <= 0:
        return None

    if features.vol_state != VolumeState.LOW:
        return None

    body_ratio = features.spread / rng
    if body_ratio > config.candle_patterns.shooting_star.body_ratio_max:
        return None

    if features.upper_wick <= features.lower_wick:
        return None

    return SignalEvent(
        id="TEST-DEM-1",
        name="TestOfDemand_NoDemand",
        tf=features.tf,
        ts=features.ts,
        signal_class=SignalClass.TEST,
        direction_bias="BEARISH",
        priority=1,
        evidence={
            "body_ratio": round(body_ratio, 4),
            "upper_wick": features.upper_wick,
            "lower_wick": features.lower_wick,
            "vol_state": features.vol_state.value,
            "vol_rel": features.vol_rel,
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
    detect_weak_2,
    detect_climax_sell_1,
    detect_conf_1,
    detect_avoid_news_1,
    detect_test_sup_1,
    detect_test_sup_2,
    detect_test_dem_1,
]


def evaluate_rules(
    features: CandleFeatures,
    config: VPAConfig,
) -> list[SignalEvent]:
    """Run all registered bar-level rule detectors and return any emitted signals.

    Returns an empty list if no rules fire (the common case).
    """
    signals: list[SignalEvent] = []
    for detector in _RULE_DETECTORS:
        result = detector(features, config)
        if result is not None:
            signals.append(result)
    return signals


# ---------------------------------------------------------------------------
# Trend-level rules (multi-bar, context-driven)
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# TREND-VAL-1 — Uptrend validation (rising prices + rising volume)
# Canonical: VPA_ACTIONABLE_RULES §4 — volume confirms price trend
# ---------------------------------------------------------------------------


def detect_trend_val_1(context: ContextSnapshot, config: VPAConfig) -> SignalEvent | None:
    """Detect TREND-VAL-1: price trend UP with volume RISING = validated uptrend.

    Conditions (from VPA_ACTIONABLE_RULES §4):
        - Price trend == UP
        - Volume trend == RISING

    Couling: rising prices with rising volume validates the move.
    No context gate required (this IS a validation signal).
    """
    if context.trend != Trend.UP:
        return None
    if context.volume_trend != VolumeTrend.RISING:
        return None

    return SignalEvent(
        id="TREND-VAL-1",
        name="UptrendValidation_RisingPriceRisingVolume",
        tf=context.tf,
        ts=_now(),
        signal_class=SignalClass.VALIDATION,
        direction_bias="BULLISH",
        priority=2,
        evidence={
            "trend": context.trend.value,
            "volume_trend": context.volume_trend.value,
            "trend_strength": context.trend_strength.value,
        },
        requires_context_gate=False,
    )


# ---------------------------------------------------------------------------
# TREND-ANOM-1 — Uptrend weakness (rising prices + falling volume)
# Canonical: VPA_ACTIONABLE_RULES §4 — alarm bells
# ---------------------------------------------------------------------------


def detect_trend_anom_1(context: ContextSnapshot, config: VPAConfig) -> SignalEvent | None:
    """Detect TREND-ANOM-1: price trend UP but volume FALLING = weakening uptrend.

    Conditions (from VPA_ACTIONABLE_RULES §4):
        - Price trend == UP
        - Volume trend == FALLING

    Couling: rising markets should be associated with rising volume,
    not falling — alarm bells.

    Requires CTX-1 gate (trend location must be known).
    """
    if context.trend != Trend.UP:
        return None
    if context.volume_trend != VolumeTrend.FALLING:
        return None

    return SignalEvent(
        id="TREND-ANOM-1",
        name="UptrendWeakness_RisingPriceFallingVolume",
        tf=context.tf,
        ts=_now(),
        signal_class=SignalClass.ANOMALY,
        direction_bias="BEARISH_OR_WAIT",
        priority=2,
        evidence={
            "trend": context.trend.value,
            "volume_trend": context.volume_trend.value,
            "trend_strength": context.trend_strength.value,
        },
        requires_context_gate=True,
    )


def _now() -> datetime:
    """Return current UTC timestamp for trend-level signals."""
    return datetime.now(timezone.utc)


_TREND_RULE_DETECTORS = [
    detect_trend_val_1,
    detect_trend_anom_1,
]


def evaluate_trend_rules(
    context: ContextSnapshot,
    config: VPAConfig,
) -> list[SignalEvent]:
    """Run all registered trend-level rule detectors.

    Trend-level rules operate on the ContextSnapshot (multi-bar analysis)
    rather than single-bar CandleFeatures. They detect patterns like
    price-volume divergence over the trend window.
    """
    signals: list[SignalEvent] = []
    for detector in _TREND_RULE_DETECTORS:
        result = detector(context, config)
        if result is not None:
            signals.append(result)
    return signals
