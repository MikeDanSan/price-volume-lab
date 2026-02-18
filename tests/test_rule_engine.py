"""Tests for Rule Engine: CandleFeatures -> SignalEvent[].

Fixture-driven tests for VAL-1, ANOM-1, TEST-SUP-1 per VPA_RULE_REGISTRY.yaml.
"""

from datetime import datetime, timezone

import pytest

from config.vpa_config import load_vpa_config, VPAConfig
from vpa_core.contracts import (
    CandleFeatures,
    CandleType,
    SignalClass,
    SignalEvent,
    SpreadState,
    VolumeState,
)
from vpa_core.rule_engine import detect_anom_1, detect_test_sup_1, detect_val_1, evaluate_rules


TS = datetime(2026, 2, 17, 14, 30, tzinfo=timezone.utc)


@pytest.fixture()
def cfg() -> VPAConfig:
    return load_vpa_config()


def _features(
    *,
    candle_type: CandleType = CandleType.UP,
    spread_state: SpreadState = SpreadState.NORMAL,
    vol_state: VolumeState = VolumeState.AVERAGE,
    vol_rel: float = 1.0,
    spread_rel: float = 1.0,
) -> CandleFeatures:
    """Build a CandleFeatures with controllable classification fields."""
    return CandleFeatures(
        ts=TS,
        tf="15m",
        spread=3.0,
        range=5.0,
        upper_wick=1.0,
        lower_wick=1.0,
        spread_rel=spread_rel,
        vol_rel=vol_rel,
        vol_state=vol_state,
        spread_state=spread_state,
        candle_type=candle_type,
    )


# ---------------------------------------------------------------------------
# VAL-1: wide up bar + high/ultra-high volume
# ---------------------------------------------------------------------------


class TestVAL1:
    """FXT-VAL-1-basic equivalent."""

    def test_fires_on_wide_up_high_vol(self, cfg: VPAConfig) -> None:
        f = _features(candle_type=CandleType.UP, spread_state=SpreadState.WIDE, vol_state=VolumeState.HIGH)
        signal = detect_val_1(f, cfg)
        assert signal is not None
        assert signal.id == "VAL-1"
        assert signal.signal_class == SignalClass.VALIDATION
        assert signal.direction_bias == "BULLISH"
        assert signal.requires_context_gate is False

    def test_fires_on_wide_up_ultra_high_vol(self, cfg: VPAConfig) -> None:
        f = _features(candle_type=CandleType.UP, spread_state=SpreadState.WIDE, vol_state=VolumeState.ULTRA_HIGH)
        signal = detect_val_1(f, cfg)
        assert signal is not None
        assert signal.id == "VAL-1"

    def test_no_fire_down_bar(self, cfg: VPAConfig) -> None:
        f = _features(candle_type=CandleType.DOWN, spread_state=SpreadState.WIDE, vol_state=VolumeState.HIGH)
        assert detect_val_1(f, cfg) is None

    def test_no_fire_narrow_spread(self, cfg: VPAConfig) -> None:
        f = _features(candle_type=CandleType.UP, spread_state=SpreadState.NARROW, vol_state=VolumeState.HIGH)
        assert detect_val_1(f, cfg) is None

    def test_no_fire_low_volume(self, cfg: VPAConfig) -> None:
        f = _features(candle_type=CandleType.UP, spread_state=SpreadState.WIDE, vol_state=VolumeState.LOW)
        assert detect_val_1(f, cfg) is None

    def test_no_fire_average_volume(self, cfg: VPAConfig) -> None:
        f = _features(candle_type=CandleType.UP, spread_state=SpreadState.WIDE, vol_state=VolumeState.AVERAGE)
        assert detect_val_1(f, cfg) is None

    def test_evidence_populated(self, cfg: VPAConfig) -> None:
        f = _features(
            candle_type=CandleType.UP,
            spread_state=SpreadState.WIDE,
            vol_state=VolumeState.HIGH,
            vol_rel=1.5,
            spread_rel=1.4,
        )
        signal = detect_val_1(f, cfg)
        assert signal is not None
        assert signal.evidence["vol_state"] == "HIGH"
        assert signal.evidence["spread_state"] == "WIDE"
        assert signal.evidence["vol_rel"] == 1.5
        assert signal.evidence["spread_rel"] == 1.4


# ---------------------------------------------------------------------------
# ANOM-1: wide up bar + low volume
# ---------------------------------------------------------------------------


class TestANOM1:
    """FXT-ANOM-1-basic equivalent."""

    def test_fires_on_wide_up_low_vol(self, cfg: VPAConfig) -> None:
        f = _features(candle_type=CandleType.UP, spread_state=SpreadState.WIDE, vol_state=VolumeState.LOW)
        signal = detect_anom_1(f, cfg)
        assert signal is not None
        assert signal.id == "ANOM-1"
        assert signal.signal_class == SignalClass.ANOMALY
        assert signal.direction_bias == "BEARISH_OR_WAIT"
        assert signal.requires_context_gate is True

    def test_no_fire_down_bar(self, cfg: VPAConfig) -> None:
        f = _features(candle_type=CandleType.DOWN, spread_state=SpreadState.WIDE, vol_state=VolumeState.LOW)
        assert detect_anom_1(f, cfg) is None

    def test_no_fire_narrow_spread(self, cfg: VPAConfig) -> None:
        f = _features(candle_type=CandleType.UP, spread_state=SpreadState.NARROW, vol_state=VolumeState.LOW)
        assert detect_anom_1(f, cfg) is None

    def test_no_fire_high_volume(self, cfg: VPAConfig) -> None:
        f = _features(candle_type=CandleType.UP, spread_state=SpreadState.WIDE, vol_state=VolumeState.HIGH)
        assert detect_anom_1(f, cfg) is None

    def test_no_fire_average_volume(self, cfg: VPAConfig) -> None:
        f = _features(candle_type=CandleType.UP, spread_state=SpreadState.WIDE, vol_state=VolumeState.AVERAGE)
        assert detect_anom_1(f, cfg) is None

    def test_priority_higher_than_val(self, cfg: VPAConfig) -> None:
        f = _features(candle_type=CandleType.UP, spread_state=SpreadState.WIDE, vol_state=VolumeState.LOW)
        signal = detect_anom_1(f, cfg)
        assert signal is not None
        assert signal.priority == 2


# ---------------------------------------------------------------------------
# TEST-SUP-1: low volume + narrow/normal spread = supply test pass
# ---------------------------------------------------------------------------


class TestTESTSUP1:
    """FXT-TEST-SUP-1-basic equivalent."""

    def test_fires_on_low_vol_narrow_spread(self, cfg: VPAConfig) -> None:
        f = _features(vol_state=VolumeState.LOW, spread_state=SpreadState.NARROW)
        signal = detect_test_sup_1(f, cfg)
        assert signal is not None
        assert signal.id == "TEST-SUP-1"
        assert signal.signal_class == SignalClass.TEST
        assert signal.direction_bias == "BULLISH"
        assert signal.requires_context_gate is True

    def test_fires_on_low_vol_normal_spread(self, cfg: VPAConfig) -> None:
        f = _features(vol_state=VolumeState.LOW, spread_state=SpreadState.NORMAL)
        signal = detect_test_sup_1(f, cfg)
        assert signal is not None
        assert signal.id == "TEST-SUP-1"

    def test_fires_on_down_bar_too(self, cfg: VPAConfig) -> None:
        """Supply tests can be up or down bars — direction doesn't matter."""
        f = _features(candle_type=CandleType.DOWN, vol_state=VolumeState.LOW, spread_state=SpreadState.NARROW)
        signal = detect_test_sup_1(f, cfg)
        assert signal is not None

    def test_no_fire_high_volume(self, cfg: VPAConfig) -> None:
        """High volume = supply still present (would be TEST-SUP-2 / failed test)."""
        f = _features(vol_state=VolumeState.HIGH, spread_state=SpreadState.NARROW)
        assert detect_test_sup_1(f, cfg) is None

    def test_no_fire_average_volume(self, cfg: VPAConfig) -> None:
        f = _features(vol_state=VolumeState.AVERAGE, spread_state=SpreadState.NARROW)
        assert detect_test_sup_1(f, cfg) is None

    def test_no_fire_wide_spread(self, cfg: VPAConfig) -> None:
        """Wide spread = significant move, not a quiet test."""
        f = _features(vol_state=VolumeState.LOW, spread_state=SpreadState.WIDE)
        assert detect_test_sup_1(f, cfg) is None

    def test_evidence_populated(self, cfg: VPAConfig) -> None:
        f = _features(vol_state=VolumeState.LOW, spread_state=SpreadState.NARROW, vol_rel=0.5, spread_rel=0.6)
        signal = detect_test_sup_1(f, cfg)
        assert signal is not None
        assert signal.evidence["vol_state"] == "LOW"
        assert signal.evidence["spread_state"] == "NARROW"
        assert signal.evidence["vol_rel"] == 0.5
        assert signal.evidence["spread_rel"] == 0.6


# ---------------------------------------------------------------------------
# evaluate_rules orchestrator
# ---------------------------------------------------------------------------


class TestEvaluateRules:
    def test_no_signals_on_neutral_bar(self, cfg: VPAConfig) -> None:
        f = _features()  # NORMAL spread, AVERAGE volume
        signals = evaluate_rules(f, cfg)
        assert signals == []

    def test_val_1_collected(self, cfg: VPAConfig) -> None:
        f = _features(candle_type=CandleType.UP, spread_state=SpreadState.WIDE, vol_state=VolumeState.HIGH)
        signals = evaluate_rules(f, cfg)
        assert len(signals) == 1
        assert signals[0].id == "VAL-1"

    def test_anom_1_collected(self, cfg: VPAConfig) -> None:
        f = _features(candle_type=CandleType.UP, spread_state=SpreadState.WIDE, vol_state=VolumeState.LOW)
        signals = evaluate_rules(f, cfg)
        assert len(signals) == 1
        assert signals[0].id == "ANOM-1"

    def test_test_sup_1_collected(self, cfg: VPAConfig) -> None:
        f = _features(vol_state=VolumeState.LOW, spread_state=SpreadState.NARROW)
        signals = evaluate_rules(f, cfg)
        assert len(signals) == 1
        assert signals[0].id == "TEST-SUP-1"

    def test_mutual_exclusion_val_anom(self, cfg: VPAConfig) -> None:
        """VAL-1 and ANOM-1 cannot both fire on the same bar (volume can't be HIGH and LOW)."""
        f_val = _features(candle_type=CandleType.UP, spread_state=SpreadState.WIDE, vol_state=VolumeState.HIGH)
        f_anom = _features(candle_type=CandleType.UP, spread_state=SpreadState.WIDE, vol_state=VolumeState.LOW)
        assert len(evaluate_rules(f_val, cfg)) == 1
        assert len(evaluate_rules(f_anom, cfg)) == 1
        assert evaluate_rules(f_val, cfg)[0].id != evaluate_rules(f_anom, cfg)[0].id

    def test_test_sup_1_and_anom_1_mutual_exclusion(self, cfg: VPAConfig) -> None:
        """TEST-SUP-1 requires NARROW/NORMAL spread; ANOM-1 requires WIDE. Cannot co-fire."""
        f_test = _features(vol_state=VolumeState.LOW, spread_state=SpreadState.NARROW)
        f_anom = _features(candle_type=CandleType.UP, spread_state=SpreadState.WIDE, vol_state=VolumeState.LOW)
        test_ids = {s.id for s in evaluate_rules(f_test, cfg)}
        anom_ids = {s.id for s in evaluate_rules(f_anom, cfg)}
        assert "TEST-SUP-1" in test_ids
        assert "ANOM-1" not in test_ids
        assert "ANOM-1" in anom_ids
        assert "TEST-SUP-1" not in anom_ids
