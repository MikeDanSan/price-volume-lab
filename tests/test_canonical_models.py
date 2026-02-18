"""Tests for canonical data models (VPA_SYSTEM_SPEC §3.3).

Verify construction, field access, immutability, and enum values.
"""

from datetime import datetime, timezone

import pytest

from vpa_core.contracts import (
    CandleFeatures,
    CandleType,
    Congestion,
    ContextSnapshot,
    DominantAlignment,
    EntryPlan,
    RiskPlan,
    SignalClass,
    SignalEvent,
    SpreadState,
    TradeIntent,
    TradeIntentStatus,
    Trend,
    TrendLocation,
    TrendStrength,
    VolumeState,
)


TS = datetime(2026, 2, 17, 14, 30, tzinfo=timezone.utc)
TF = "15m"


# ---------------------------------------------------------------------------
# Enum completeness
# ---------------------------------------------------------------------------


def test_volume_state_values() -> None:
    assert set(VolumeState) == {
        VolumeState.LOW,
        VolumeState.AVERAGE,
        VolumeState.HIGH,
        VolumeState.ULTRA_HIGH,
    }


def test_spread_state_values() -> None:
    assert set(SpreadState) == {
        SpreadState.NARROW,
        SpreadState.NORMAL,
        SpreadState.WIDE,
    }


def test_trend_values() -> None:
    assert set(Trend) == {Trend.UP, Trend.DOWN, Trend.RANGE, Trend.UNKNOWN}


def test_trend_location_values() -> None:
    assert set(TrendLocation) == {
        TrendLocation.TOP,
        TrendLocation.BOTTOM,
        TrendLocation.MIDDLE,
        TrendLocation.UNKNOWN,
    }


def test_signal_class_values() -> None:
    assert SignalClass.VALIDATION.value == "VALIDATION"
    assert SignalClass.ANOMALY.value == "ANOMALY"
    assert SignalClass.TEST.value == "TEST"


# ---------------------------------------------------------------------------
# CandleFeatures
# ---------------------------------------------------------------------------


def test_candle_features_construction() -> None:
    cf = CandleFeatures(
        ts=TS,
        tf=TF,
        spread=1.25,
        range=2.10,
        upper_wick=0.70,
        lower_wick=0.15,
        spread_rel=1.22,
        vol_rel=1.65,
        vol_state=VolumeState.HIGH,
        spread_state=SpreadState.WIDE,
        candle_type=CandleType.UP,
    )
    assert cf.spread == 1.25
    assert cf.range == 2.10
    assert cf.vol_state == VolumeState.HIGH
    assert cf.spread_state == SpreadState.WIDE
    assert cf.candle_type == CandleType.UP


def test_candle_features_frozen() -> None:
    cf = CandleFeatures(
        ts=TS, tf=TF, spread=1.0, range=2.0,
        upper_wick=0.5, lower_wick=0.5,
        spread_rel=1.0, vol_rel=1.0,
        vol_state=VolumeState.AVERAGE,
        spread_state=SpreadState.NORMAL,
        candle_type=CandleType.UP,
    )
    with pytest.raises(AttributeError):
        cf.spread = 999  # type: ignore[misc]


# ---------------------------------------------------------------------------
# ContextSnapshot
# ---------------------------------------------------------------------------


def test_context_snapshot_construction() -> None:
    ctx = ContextSnapshot(
        tf=TF,
        trend=Trend.UP,
        trend_strength=TrendStrength.MODERATE,
        trend_location=TrendLocation.MIDDLE,
        congestion=Congestion(active=False),
        dominant_alignment=DominantAlignment.WITH,
    )
    assert ctx.trend == Trend.UP
    assert ctx.trend_location == TrendLocation.MIDDLE
    assert ctx.dominant_alignment == DominantAlignment.WITH
    assert ctx.congestion.active is False


def test_context_snapshot_defaults() -> None:
    ctx = ContextSnapshot(
        tf=TF,
        trend=Trend.UNKNOWN,
        trend_strength=TrendStrength.WEAK,
        trend_location=TrendLocation.UNKNOWN,
        congestion=Congestion(active=False),
    )
    assert ctx.dominant_alignment == DominantAlignment.UNKNOWN


def test_congestion_with_range() -> None:
    cong = Congestion(active=True, range_high=105.2, range_low=100.8)
    assert cong.active is True
    assert cong.range_high == 105.2
    assert cong.range_low == 100.8


# ---------------------------------------------------------------------------
# SignalEvent
# ---------------------------------------------------------------------------


def test_signal_event_construction() -> None:
    sig = SignalEvent(
        id="ANOM-1",
        name="BigResultLittleEffort_TrapUpWarning",
        tf=TF,
        ts=TS,
        signal_class=SignalClass.ANOMALY,
        direction_bias="BEARISH_OR_WAIT",
        priority=2,
        evidence={"spreadState": "WIDE", "volState": "LOW"},
        requires_context_gate=True,
    )
    assert sig.id == "ANOM-1"
    assert sig.signal_class == SignalClass.ANOMALY
    assert sig.evidence["spreadState"] == "WIDE"
    assert sig.requires_context_gate is True


def test_signal_event_defaults() -> None:
    sig = SignalEvent(
        id="VAL-1",
        name="SingleBarValidation_BullishDrive",
        tf=TF,
        ts=TS,
        signal_class=SignalClass.VALIDATION,
        direction_bias="BULLISH",
    )
    assert sig.priority == 1
    assert sig.evidence == {}
    assert sig.requires_context_gate is False


# ---------------------------------------------------------------------------
# TradeIntent
# ---------------------------------------------------------------------------


def test_trade_intent_construction() -> None:
    ti = TradeIntent(
        intent_id="TI-20260217-001",
        direction="LONG",
        tf=TF,
        setup="ENTRY-LONG-1",
        status=TradeIntentStatus.READY,
        entry_plan=EntryPlan(timing="NEXT_BAR_OPEN", order_type="MARKET"),
        risk_plan=RiskPlan(stop=100.6, risk_pct=0.5, size=120),
        rationale=["TEST-SUP-1", "VAL-1", "CTX-1:OK", "CTX-2:WITH"],
    )
    assert ti.status == TradeIntentStatus.READY
    assert ti.entry_plan.timing == "NEXT_BAR_OPEN"
    assert ti.risk_plan.stop == 100.6
    assert ti.risk_plan.size == 120
    assert len(ti.rationale) == 4


def test_trade_intent_rejected() -> None:
    ti = TradeIntent(
        intent_id="TI-20260217-002",
        direction="SHORT",
        tf=TF,
        setup="ENTRY-SHORT-1",
        status=TradeIntentStatus.REJECTED,
        entry_plan=EntryPlan(),
        risk_plan=RiskPlan(stop=0, risk_pct=0, size=0),
        reject_reason="CTX-1 gate failed: trendLocation == UNKNOWN",
    )
    assert ti.status == TradeIntentStatus.REJECTED
    assert ti.reject_reason is not None
    assert "CTX-1" in ti.reject_reason


def test_trade_intent_defaults() -> None:
    ti = TradeIntent(
        intent_id="TI-001",
        direction="LONG",
        tf=TF,
        setup="ENTRY-LONG-1",
        status=TradeIntentStatus.PENDING_CONFIRM,
        entry_plan=EntryPlan(),
        risk_plan=RiskPlan(stop=100.0, risk_pct=0.5, size=50),
    )
    assert ti.rationale == []
    assert ti.reject_reason is None
    assert ti.entry_plan.timing == "NEXT_BAR_OPEN"
    assert ti.entry_plan.order_type == "MARKET"
