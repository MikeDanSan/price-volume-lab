"""Tests for Rule Engine: CandleFeatures -> SignalEvent[].

Fixture-driven tests for VAL-1, ANOM-1, ANOM-2, STR-1, TEST-SUP-1
per VPA_RULE_REGISTRY.yaml.
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
from vpa_core.rule_engine import detect_anom_1, detect_anom_2, detect_avoid_news_1, detect_climax_sell_1, detect_conf_1, detect_str_1, detect_test_sup_1, detect_val_1, detect_weak_1, detect_weak_2, evaluate_rules


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
    spread_val: float = 3.0,
    range_val: float = 5.0,
    upper_wick: float = 1.0,
    lower_wick: float = 1.0,
) -> CandleFeatures:
    """Build a CandleFeatures with controllable fields."""
    return CandleFeatures(
        ts=TS,
        tf="15m",
        spread=spread_val,
        range=range_val,
        upper_wick=upper_wick,
        lower_wick=lower_wick,
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
# ANOM-2: high volume + narrow/normal spread = absorption/weakness
# ---------------------------------------------------------------------------


class TestANOM2:
    """FXT-ANOM-2-basic equivalent."""

    def test_fires_on_high_vol_narrow_spread(self, cfg: VPAConfig) -> None:
        f = _features(vol_state=VolumeState.HIGH, spread_state=SpreadState.NARROW)
        signal = detect_anom_2(f, cfg)
        assert signal is not None
        assert signal.id == "ANOM-2"
        assert signal.signal_class == SignalClass.ANOMALY
        assert signal.direction_bias == "BEARISH_OR_WAIT"
        assert signal.requires_context_gate is True

    def test_fires_on_ultra_high_vol_normal_spread(self, cfg: VPAConfig) -> None:
        f = _features(vol_state=VolumeState.ULTRA_HIGH, spread_state=SpreadState.NORMAL)
        signal = detect_anom_2(f, cfg)
        assert signal is not None
        assert signal.id == "ANOM-2"

    def test_fires_on_up_bar(self, cfg: VPAConfig) -> None:
        """Direction-agnostic: fires on up bars too (selling into rally)."""
        f = _features(candle_type=CandleType.UP, vol_state=VolumeState.HIGH, spread_state=SpreadState.NARROW)
        assert detect_anom_2(f, cfg) is not None

    def test_fires_on_down_bar(self, cfg: VPAConfig) -> None:
        f = _features(candle_type=CandleType.DOWN, vol_state=VolumeState.HIGH, spread_state=SpreadState.NORMAL)
        assert detect_anom_2(f, cfg) is not None

    def test_no_fire_wide_spread(self, cfg: VPAConfig) -> None:
        """Wide spread + high volume = VAL-1 territory, not absorption."""
        f = _features(vol_state=VolumeState.HIGH, spread_state=SpreadState.WIDE)
        assert detect_anom_2(f, cfg) is None

    def test_no_fire_low_volume(self, cfg: VPAConfig) -> None:
        f = _features(vol_state=VolumeState.LOW, spread_state=SpreadState.NARROW)
        assert detect_anom_2(f, cfg) is None

    def test_no_fire_average_volume(self, cfg: VPAConfig) -> None:
        f = _features(vol_state=VolumeState.AVERAGE, spread_state=SpreadState.NARROW)
        assert detect_anom_2(f, cfg) is None

    def test_evidence_includes_candle_type(self, cfg: VPAConfig) -> None:
        f = _features(candle_type=CandleType.UP, vol_state=VolumeState.HIGH, spread_state=SpreadState.NARROW, vol_rel=1.5, spread_rel=0.6)
        signal = detect_anom_2(f, cfg)
        assert signal is not None
        assert signal.evidence["candle_type"] == "UP"
        assert signal.evidence["vol_rel"] == 1.5
        assert signal.evidence["spread_rel"] == 0.6

    def test_priority_matches_anom_1(self, cfg: VPAConfig) -> None:
        """Both anomaly rules share priority=2."""
        f = _features(vol_state=VolumeState.HIGH, spread_state=SpreadState.NARROW)
        signal = detect_anom_2(f, cfg)
        assert signal.priority == 2


# ---------------------------------------------------------------------------
# STR-1: hammer candle (large lower wick, small body, minimal upper wick)
# ---------------------------------------------------------------------------


class TestSTR1:
    """FXT-STR-1-basic equivalent."""

    def _hammer(self, **kw) -> CandleFeatures:
        """Classic hammer: lower_wick=7, body=2, upper_wick=1, range=10."""
        defaults = dict(
            lower_wick=7.0, spread_val=2.0, upper_wick=1.0, range_val=10.0,
        )
        defaults.update(kw)
        return _features(**defaults)

    def test_fires_on_classic_hammer(self, cfg: VPAConfig) -> None:
        f = self._hammer()
        signal = detect_str_1(f, cfg)
        assert signal is not None
        assert signal.id == "STR-1"
        assert signal.signal_class == SignalClass.STRENGTH
        assert signal.direction_bias == "BULLISH"
        assert signal.requires_context_gate is True

    def test_fires_on_down_bar_hammer(self, cfg: VPAConfig) -> None:
        """Hammer works on both up and down bars (close near open either way)."""
        f = self._hammer(candle_type=CandleType.DOWN)
        assert detect_str_1(f, cfg) is not None

    def test_fires_at_boundary(self, cfg: VPAConfig) -> None:
        """Exactly at threshold boundaries (60% wick, 33% body, 10% upper)."""
        f = _features(
            lower_wick=6.0, spread_val=3.3, upper_wick=1.0, range_val=10.0,
        )
        assert detect_str_1(f, cfg) is not None

    def test_no_fire_small_lower_wick(self, cfg: VPAConfig) -> None:
        """Lower wick too small — not a hammer."""
        f = _features(
            lower_wick=4.0, spread_val=2.0, upper_wick=1.0, range_val=10.0,
        )
        assert detect_str_1(f, cfg) is None

    def test_no_fire_large_body(self, cfg: VPAConfig) -> None:
        """Body too large relative to range — normal candle, not hammer."""
        f = _features(
            lower_wick=6.0, spread_val=4.0, upper_wick=0.0, range_val=10.0,
        )
        assert detect_str_1(f, cfg) is None

    def test_no_fire_large_upper_wick(self, cfg: VPAConfig) -> None:
        """Upper wick too large — more like a doji/spinning top than hammer."""
        f = _features(
            lower_wick=6.0, spread_val=1.0, upper_wick=3.0, range_val=10.0,
        )
        assert detect_str_1(f, cfg) is None

    def test_no_fire_zero_range(self, cfg: VPAConfig) -> None:
        """Zero-range bar (open=high=low=close) is not a hammer."""
        f = _features(
            lower_wick=0.0, spread_val=0.0, upper_wick=0.0, range_val=0.0,
        )
        assert detect_str_1(f, cfg) is None

    def test_evidence_includes_ratios(self, cfg: VPAConfig) -> None:
        f = self._hammer(vol_state=VolumeState.HIGH)
        signal = detect_str_1(f, cfg)
        assert signal is not None
        assert signal.evidence["lower_wick_ratio"] == 0.7
        assert signal.evidence["body_ratio"] == 0.2
        assert signal.evidence["upper_wick_ratio"] == 0.1
        assert signal.evidence["vol_state"] == "HIGH"

    def test_config_driven_thresholds(self) -> None:
        """Tighter config rejects a candle that default config accepts."""
        from config.vpa_config import (
            CandlePatternsConfig,
            HammerConfig,
            ShootingStarConfig,
        )

        base_cfg = load_vpa_config()
        tight_hammer = HammerConfig(
            lower_wick_ratio_min=0.80, body_ratio_max=0.15, upper_wick_ratio_max=0.05,
        )
        tight_patterns = CandlePatternsConfig(
            hammer=tight_hammer,
            shooting_star=base_cfg.candle_patterns.shooting_star,
            long_legged_doji=base_cfg.candle_patterns.long_legged_doji,
        )
        tight_cfg = VPAConfig(
            version=base_cfg.version,
            vol=base_cfg.vol,
            spread=base_cfg.spread,
            trend=base_cfg.trend,
            setup=base_cfg.setup,
            gates=base_cfg.gates,
            execution=base_cfg.execution,
            costs=base_cfg.costs,
            slippage=base_cfg.slippage,
            candle_patterns=tight_patterns,
            risk=base_cfg.risk,
        )
        f = self._hammer()
        assert detect_str_1(f, base_cfg) is not None
        assert detect_str_1(f, tight_cfg) is None


# ---------------------------------------------------------------------------
# WEAK-1: shooting star (large upper wick, small body, minimal lower wick)
# ---------------------------------------------------------------------------


class TestWEAK1:
    """FXT-WEAK-1-basic equivalent."""

    def _shooting_star(self, **kw) -> CandleFeatures:
        """Classic shooting star: upper_wick=7, body=2, lower_wick=1, range=10."""
        defaults = dict(
            upper_wick=7.0, spread_val=2.0, lower_wick=1.0, range_val=10.0,
        )
        defaults.update(kw)
        return _features(**defaults)

    def test_fires_on_classic_shooting_star(self, cfg: VPAConfig) -> None:
        f = self._shooting_star()
        signal = detect_weak_1(f, cfg)
        assert signal is not None
        assert signal.id == "WEAK-1"
        assert signal.signal_class == SignalClass.WEAKNESS
        assert signal.direction_bias == "BEARISH"
        assert signal.requires_context_gate is True

    def test_fires_on_up_bar_shooting_star(self, cfg: VPAConfig) -> None:
        """Works on both UP and DOWN bars (wick structure is what matters)."""
        f = self._shooting_star(candle_type=CandleType.UP)
        assert detect_weak_1(f, cfg) is not None

    def test_fires_at_boundary(self, cfg: VPAConfig) -> None:
        """Exactly at threshold boundaries (60% wick, 33% body, 10% lower)."""
        f = _features(
            upper_wick=6.0, spread_val=3.3, lower_wick=1.0, range_val=10.0,
        )
        assert detect_weak_1(f, cfg) is not None

    def test_no_fire_small_upper_wick(self, cfg: VPAConfig) -> None:
        f = _features(
            upper_wick=4.0, spread_val=2.0, lower_wick=1.0, range_val=10.0,
        )
        assert detect_weak_1(f, cfg) is None

    def test_no_fire_large_body(self, cfg: VPAConfig) -> None:
        f = _features(
            upper_wick=6.0, spread_val=4.0, lower_wick=0.0, range_val=10.0,
        )
        assert detect_weak_1(f, cfg) is None

    def test_no_fire_large_lower_wick(self, cfg: VPAConfig) -> None:
        """Large lower wick pushes toward hammer territory, not shooting star."""
        f = _features(
            upper_wick=6.0, spread_val=1.0, lower_wick=3.0, range_val=10.0,
        )
        assert detect_weak_1(f, cfg) is None

    def test_no_fire_zero_range(self, cfg: VPAConfig) -> None:
        f = _features(
            upper_wick=0.0, spread_val=0.0, lower_wick=0.0, range_val=0.0,
        )
        assert detect_weak_1(f, cfg) is None

    def test_evidence_includes_ratios(self, cfg: VPAConfig) -> None:
        f = self._shooting_star(vol_state=VolumeState.HIGH)
        signal = detect_weak_1(f, cfg)
        assert signal is not None
        assert signal.evidence["upper_wick_ratio"] == 0.7
        assert signal.evidence["body_ratio"] == 0.2
        assert signal.evidence["lower_wick_ratio"] == 0.1
        assert signal.evidence["vol_state"] == "HIGH"

    def test_str_1_and_weak_1_mutual_exclusion(self, cfg: VPAConfig) -> None:
        """A classic hammer cannot also be a shooting star and vice versa."""
        hammer = _features(lower_wick=7.0, spread_val=2.0, upper_wick=1.0, range_val=10.0)
        star = _features(upper_wick=7.0, spread_val=2.0, lower_wick=1.0, range_val=10.0)
        assert detect_str_1(hammer, cfg) is not None
        assert detect_weak_1(hammer, cfg) is None
        assert detect_weak_1(star, cfg) is not None
        assert detect_str_1(star, cfg) is None


# ---------------------------------------------------------------------------
# WEAK-2: shooting star + LOW volume = no demand
# ---------------------------------------------------------------------------


class TestWEAK2:
    """FXT-WEAK-2-basic: shooting star shape + LOW volume fires WEAK-2."""

    def _shooting_star_low_vol(self, **kw) -> CandleFeatures:
        """Classic shooting star with LOW volume."""
        defaults = dict(
            upper_wick=7.0, spread_val=2.0, lower_wick=1.0, range_val=10.0,
            vol_state=VolumeState.LOW,
        )
        defaults.update(kw)
        return _features(**defaults)

    def test_fires_on_shooting_star_low_vol(self, cfg: VPAConfig) -> None:
        f = self._shooting_star_low_vol()
        signal = detect_weak_2(f, cfg)
        assert signal is not None
        assert signal.id == "WEAK-2"
        assert signal.name == "ShootingStar_NoDemand"
        assert signal.signal_class == SignalClass.WEAKNESS
        assert signal.direction_bias == "BEARISH"
        assert signal.requires_context_gate is True
        assert signal.priority == 1

    def test_no_fire_average_volume(self, cfg: VPAConfig) -> None:
        """Shooting star with AVERAGE volume -> WEAK-1 only, not WEAK-2."""
        f = self._shooting_star_low_vol(vol_state=VolumeState.AVERAGE)
        assert detect_weak_2(f, cfg) is None

    def test_no_fire_high_volume(self, cfg: VPAConfig) -> None:
        f = self._shooting_star_low_vol(vol_state=VolumeState.HIGH)
        assert detect_weak_2(f, cfg) is None

    def test_no_fire_small_upper_wick(self, cfg: VPAConfig) -> None:
        """Not a shooting star shape -> no fire even with LOW volume."""
        f = _features(
            upper_wick=4.0, spread_val=2.0, lower_wick=1.0, range_val=10.0,
            vol_state=VolumeState.LOW,
        )
        assert detect_weak_2(f, cfg) is None

    def test_no_fire_zero_range(self, cfg: VPAConfig) -> None:
        f = _features(
            upper_wick=0.0, spread_val=0.0, lower_wick=0.0, range_val=0.0,
            vol_state=VolumeState.LOW,
        )
        assert detect_weak_2(f, cfg) is None

    def test_evidence_includes_vol_state(self, cfg: VPAConfig) -> None:
        f = self._shooting_star_low_vol()
        signal = detect_weak_2(f, cfg)
        assert signal is not None
        assert signal.evidence["vol_state"] == "LOW"
        assert signal.evidence["upper_wick_ratio"] == 0.7
        assert signal.evidence["body_ratio"] == 0.2

    def test_weak_1_also_fires_on_same_bar(self, cfg: VPAConfig) -> None:
        """WEAK-1 and WEAK-2 can co-fire (both detect the shooting star)."""
        f = self._shooting_star_low_vol()
        assert detect_weak_1(f, cfg) is not None
        assert detect_weak_2(f, cfg) is not None

    def test_higher_priority_than_weak_1(self, cfg: VPAConfig) -> None:
        """WEAK-2 (priority 1) is more decisive than WEAK-1 (priority 2)."""
        f = self._shooting_star_low_vol()
        w1 = detect_weak_1(f, cfg)
        w2 = detect_weak_2(f, cfg)
        assert w1 is not None and w2 is not None
        assert w2.priority < w1.priority


# ---------------------------------------------------------------------------
# CLIMAX-SELL-1: shooting star shape + HIGH/ULTRA_HIGH volume = selling climax
# ---------------------------------------------------------------------------


class TestCLIMAXSELL1:
    """FXT-CLIMAX-SELL-1-basic: shooting star shape + high volume fires."""

    def _climax_bar(self, **kw) -> CandleFeatures:
        """Classic shooting star with HIGH volume."""
        defaults = dict(
            upper_wick=7.0, spread_val=2.0, lower_wick=1.0, range_val=10.0,
            vol_state=VolumeState.HIGH,
        )
        defaults.update(kw)
        return _features(**defaults)

    def test_fires_on_shooting_star_high_vol(self, cfg: VPAConfig) -> None:
        f = self._climax_bar()
        signal = detect_climax_sell_1(f, cfg)
        assert signal is not None
        assert signal.id == "CLIMAX-SELL-1"
        assert signal.name == "SellingClimax_Distribution"
        assert signal.signal_class == SignalClass.WEAKNESS
        assert signal.direction_bias == "BEARISH"
        assert signal.requires_context_gate is True
        assert signal.priority == 1

    def test_fires_on_ultra_high_vol(self, cfg: VPAConfig) -> None:
        f = self._climax_bar(vol_state=VolumeState.ULTRA_HIGH)
        signal = detect_climax_sell_1(f, cfg)
        assert signal is not None
        assert signal.id == "CLIMAX-SELL-1"

    def test_no_fire_average_volume(self, cfg: VPAConfig) -> None:
        f = self._climax_bar(vol_state=VolumeState.AVERAGE)
        assert detect_climax_sell_1(f, cfg) is None

    def test_no_fire_low_volume(self, cfg: VPAConfig) -> None:
        """LOW volume shooting star is WEAK-2, not CLIMAX-SELL-1."""
        f = self._climax_bar(vol_state=VolumeState.LOW)
        assert detect_climax_sell_1(f, cfg) is None

    def test_no_fire_small_upper_wick(self, cfg: VPAConfig) -> None:
        f = _features(
            upper_wick=4.0, spread_val=2.0, lower_wick=1.0, range_val=10.0,
            vol_state=VolumeState.HIGH,
        )
        assert detect_climax_sell_1(f, cfg) is None

    def test_no_fire_zero_range(self, cfg: VPAConfig) -> None:
        f = _features(
            upper_wick=0.0, spread_val=0.0, lower_wick=0.0, range_val=0.0,
            vol_state=VolumeState.HIGH,
        )
        assert detect_climax_sell_1(f, cfg) is None

    def test_evidence_payload(self, cfg: VPAConfig) -> None:
        f = self._climax_bar(vol_state=VolumeState.ULTRA_HIGH, vol_rel=2.5)
        signal = detect_climax_sell_1(f, cfg)
        assert signal is not None
        assert signal.evidence["vol_state"] == "ULTRA_HIGH"
        assert signal.evidence["vol_rel"] == 2.5
        assert signal.evidence["upper_wick_ratio"] == 0.7

    def test_weak_1_also_fires_same_bar(self, cfg: VPAConfig) -> None:
        """WEAK-1 fires on any volume shooting star; CLIMAX-SELL-1 only on high vol."""
        f = self._climax_bar()
        assert detect_weak_1(f, cfg) is not None
        assert detect_climax_sell_1(f, cfg) is not None

    def test_mutual_exclusion_with_weak_2(self, cfg: VPAConfig) -> None:
        """LOW vol = WEAK-2, HIGH vol = CLIMAX-SELL-1. Never both on same bar."""
        low = self._climax_bar(vol_state=VolumeState.LOW)
        high = self._climax_bar(vol_state=VolumeState.HIGH)
        assert detect_weak_2(low, cfg) is not None
        assert detect_climax_sell_1(low, cfg) is None
        assert detect_climax_sell_1(high, cfg) is not None
        assert detect_weak_2(high, cfg) is None


# ---------------------------------------------------------------------------
# CONF-1: positive response bar (up bar, non-low volume, non-narrow spread)
# ---------------------------------------------------------------------------


class TestCONF1:
    """FXT-CONF-1-basic equivalent."""

    def test_fires_on_up_average_vol_normal_spread(self, cfg: VPAConfig) -> None:
        f = _features(candle_type=CandleType.UP, vol_state=VolumeState.AVERAGE, spread_state=SpreadState.NORMAL)
        signal = detect_conf_1(f, cfg)
        assert signal is not None
        assert signal.id == "CONF-1"
        assert signal.signal_class == SignalClass.CONFIRMATION
        assert signal.direction_bias == "BULLISH"
        assert signal.requires_context_gate is False

    def test_fires_on_high_vol_wide_spread(self, cfg: VPAConfig) -> None:
        f = _features(candle_type=CandleType.UP, vol_state=VolumeState.HIGH, spread_state=SpreadState.WIDE)
        assert detect_conf_1(f, cfg) is not None

    def test_fires_on_ultra_high_vol(self, cfg: VPAConfig) -> None:
        f = _features(candle_type=CandleType.UP, vol_state=VolumeState.ULTRA_HIGH, spread_state=SpreadState.NORMAL)
        assert detect_conf_1(f, cfg) is not None

    def test_no_fire_down_bar(self, cfg: VPAConfig) -> None:
        """Down bar cannot be a positive response."""
        f = _features(candle_type=CandleType.DOWN, vol_state=VolumeState.HIGH, spread_state=SpreadState.WIDE)
        assert detect_conf_1(f, cfg) is None

    def test_no_fire_low_volume(self, cfg: VPAConfig) -> None:
        """Low volume up bar lacks conviction — not a real response."""
        f = _features(candle_type=CandleType.UP, vol_state=VolumeState.LOW, spread_state=SpreadState.NORMAL)
        assert detect_conf_1(f, cfg) is None

    def test_no_fire_narrow_spread(self, cfg: VPAConfig) -> None:
        """Narrow body means the bar barely moved — not a response."""
        f = _features(candle_type=CandleType.UP, vol_state=VolumeState.AVERAGE, spread_state=SpreadState.NARROW)
        assert detect_conf_1(f, cfg) is None

    def test_priority_lower_than_signals(self, cfg: VPAConfig) -> None:
        """Confirmation has lower priority than the signals it confirms."""
        f = _features(candle_type=CandleType.UP, vol_state=VolumeState.AVERAGE, spread_state=SpreadState.NORMAL)
        signal = detect_conf_1(f, cfg)
        assert signal.priority == 3

    def test_evidence_populated(self, cfg: VPAConfig) -> None:
        f = _features(candle_type=CandleType.UP, vol_state=VolumeState.HIGH, spread_state=SpreadState.WIDE, vol_rel=1.5, spread_rel=1.4)
        signal = detect_conf_1(f, cfg)
        assert signal is not None
        assert signal.evidence["candle_type"] == "UP"
        assert signal.evidence["vol_state"] == "HIGH"
        assert signal.evidence["spread_state"] == "WIDE"
        assert signal.evidence["vol_rel"] == 1.5
        assert signal.evidence["spread_rel"] == 1.4

    def test_can_cofire_with_val_1(self, cfg: VPAConfig) -> None:
        """A wide up bar on high vol can be both VAL-1 and CONF-1 simultaneously."""
        f = _features(candle_type=CandleType.UP, vol_state=VolumeState.HIGH, spread_state=SpreadState.WIDE)
        signals = evaluate_rules(f, cfg)
        ids = {s.id for s in signals}
        assert "VAL-1" in ids
        assert "CONF-1" in ids


# ---------------------------------------------------------------------------
# AVOID-NEWS-1: long-legged doji on LOW volume (manipulation / stand-aside)
# ---------------------------------------------------------------------------


class TestAVOIDNEWS1:
    """FXT-AVOID-NEWS-1-basic equivalent."""

    def _doji(self, **kw) -> CandleFeatures:
        """Classic long-legged doji: upper=4, body=2, lower=4, range=10, LOW vol."""
        defaults = dict(
            upper_wick=4.0, spread_val=2.0, lower_wick=4.0, range_val=10.0,
            vol_state=VolumeState.LOW,
        )
        defaults.update(kw)
        return _features(**defaults)

    def test_fires_on_classic_doji_low_vol(self, cfg: VPAConfig) -> None:
        f = self._doji()
        signal = detect_avoid_news_1(f, cfg)
        assert signal is not None
        assert signal.id == "AVOID-NEWS-1"
        assert signal.signal_class == SignalClass.AVOIDANCE
        assert signal.direction_bias == "NEUTRAL"
        assert signal.requires_context_gate is False

    def test_fires_on_up_or_down_bar(self, cfg: VPAConfig) -> None:
        """Doji can be either UP or DOWN — doesn't matter for avoidance."""
        f_up = self._doji(candle_type=CandleType.UP)
        f_down = self._doji(candle_type=CandleType.DOWN)
        assert detect_avoid_news_1(f_up, cfg) is not None
        assert detect_avoid_news_1(f_down, cfg) is not None

    def test_no_fire_high_volume(self, cfg: VPAConfig) -> None:
        """High volume doji is NOT manipulation — it's genuine activity."""
        f = self._doji(vol_state=VolumeState.HIGH)
        assert detect_avoid_news_1(f, cfg) is None

    def test_no_fire_average_volume(self, cfg: VPAConfig) -> None:
        f = self._doji(vol_state=VolumeState.AVERAGE)
        assert detect_avoid_news_1(f, cfg) is None

    def test_no_fire_large_body(self, cfg: VPAConfig) -> None:
        """Large body = not a doji."""
        f = _features(
            upper_wick=3.0, spread_val=4.0, lower_wick=3.0, range_val=10.0,
            vol_state=VolumeState.LOW,
        )
        assert detect_avoid_news_1(f, cfg) is None

    def test_no_fire_one_sided_wick(self, cfg: VPAConfig) -> None:
        """Only one big wick = not long-legged (more like hammer or shooting star)."""
        f = _features(
            upper_wick=1.0, spread_val=2.0, lower_wick=7.0, range_val=10.0,
            vol_state=VolumeState.LOW,
        )
        assert detect_avoid_news_1(f, cfg) is None

    def test_no_fire_zero_range(self, cfg: VPAConfig) -> None:
        f = _features(
            upper_wick=0.0, spread_val=0.0, lower_wick=0.0, range_val=0.0,
            vol_state=VolumeState.LOW,
        )
        assert detect_avoid_news_1(f, cfg) is None

    def test_priority_highest(self, cfg: VPAConfig) -> None:
        """Avoidance has priority=0 (highest) — overrides everything."""
        f = self._doji()
        signal = detect_avoid_news_1(f, cfg)
        assert signal.priority == 0

    def test_evidence_includes_ratios(self, cfg: VPAConfig) -> None:
        f = self._doji()
        signal = detect_avoid_news_1(f, cfg)
        assert signal is not None
        assert signal.evidence["body_ratio"] == 0.2
        assert signal.evidence["upper_wick_ratio"] == 0.4
        assert signal.evidence["lower_wick_ratio"] == 0.4
        assert signal.evidence["vol_state"] == "LOW"

    def test_can_cofire_with_test_sup_1(self, cfg: VPAConfig) -> None:
        """LOW vol + NARROW spread doji fires both AVOID-NEWS-1 and TEST-SUP-1."""
        f = _features(
            upper_wick=4.0, spread_val=1.0, lower_wick=5.0, range_val=10.0,
            vol_state=VolumeState.LOW, spread_state=SpreadState.NARROW,
        )
        signals = evaluate_rules(f, cfg)
        ids = {s.id for s in signals}
        assert "AVOID-NEWS-1" in ids
        assert "TEST-SUP-1" in ids


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
        """DOWN bar with AVERAGE volume and NORMAL spread fires nothing."""
        f = _features(candle_type=CandleType.DOWN)
        signals = evaluate_rules(f, cfg)
        assert signals == []

    def test_val_1_collected(self, cfg: VPAConfig) -> None:
        f = _features(candle_type=CandleType.UP, spread_state=SpreadState.WIDE, vol_state=VolumeState.HIGH)
        signals = evaluate_rules(f, cfg)
        ids = {s.id for s in signals}
        assert "VAL-1" in ids

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
        val_ids = {s.id for s in evaluate_rules(f_val, cfg)}
        anom_ids = {s.id for s in evaluate_rules(f_anom, cfg)}
        assert "VAL-1" in val_ids
        assert "VAL-1" not in anom_ids
        assert "ANOM-1" in anom_ids
        assert "ANOM-1" not in val_ids

    def test_str_1_collected(self, cfg: VPAConfig) -> None:
        f = _features(lower_wick=7.0, spread_val=2.0, upper_wick=1.0, range_val=10.0)
        signals = evaluate_rules(f, cfg)
        ids = {s.id for s in signals}
        assert "STR-1" in ids

    def test_weak_1_collected(self, cfg: VPAConfig) -> None:
        f = _features(upper_wick=7.0, spread_val=2.0, lower_wick=1.0, range_val=10.0)
        signals = evaluate_rules(f, cfg)
        ids = {s.id for s in signals}
        assert "WEAK-1" in ids

    def test_conf_1_collected(self, cfg: VPAConfig) -> None:
        f = _features(candle_type=CandleType.UP, vol_state=VolumeState.AVERAGE, spread_state=SpreadState.NORMAL)
        signals = evaluate_rules(f, cfg)
        ids = {s.id for s in signals}
        assert "CONF-1" in ids

    def test_avoid_news_1_collected(self, cfg: VPAConfig) -> None:
        f = _features(upper_wick=4.0, spread_val=2.0, lower_wick=4.0, range_val=10.0, vol_state=VolumeState.LOW)
        signals = evaluate_rules(f, cfg)
        ids = {s.id for s in signals}
        assert "AVOID-NEWS-1" in ids

    def test_anom_2_collected(self, cfg: VPAConfig) -> None:
        f = _features(vol_state=VolumeState.HIGH, spread_state=SpreadState.NARROW)
        signals = evaluate_rules(f, cfg)
        assert len(signals) == 1
        assert signals[0].id == "ANOM-2"

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

    def test_val_1_and_anom_2_mutual_exclusion(self, cfg: VPAConfig) -> None:
        """VAL-1 requires WIDE spread; ANOM-2 requires NARROW/NORMAL. Cannot co-fire."""
        f_val = _features(candle_type=CandleType.UP, spread_state=SpreadState.WIDE, vol_state=VolumeState.HIGH)
        f_anom2 = _features(vol_state=VolumeState.HIGH, spread_state=SpreadState.NARROW)
        val_ids = {s.id for s in evaluate_rules(f_val, cfg)}
        anom2_ids = {s.id for s in evaluate_rules(f_anom2, cfg)}
        assert "VAL-1" in val_ids
        assert "ANOM-2" not in val_ids
        assert "ANOM-2" in anom2_ids
        assert "VAL-1" not in anom2_ids
