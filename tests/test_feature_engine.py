"""Tests for the Feature Engine: bars + config -> CandleFeatures.

Uses a golden-bar fixture with hand-computed expected values.
"""

from datetime import datetime, timezone

import pytest

from config.vpa_config import load_vpa_config, VPAConfig
from vpa_core.contracts import (
    Bar,
    CandleFeatures,
    CandleType,
    SpreadState,
    VolumeState,
)
from vpa_core.feature_engine import extract_features


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

TS = datetime(2026, 2, 17, 14, 30, tzinfo=timezone.utc)


@pytest.fixture()
def cfg() -> VPAConfig:
    return load_vpa_config()


def _bar(
    open_: float,
    high: float,
    low: float,
    close: float,
    volume: int,
    offset_minutes: int = 0,
) -> Bar:
    from datetime import timedelta
    return Bar(open_, high, low, close, volume, TS + timedelta(minutes=offset_minutes), "SPY")


def _golden_bars() -> list[Bar]:
    """20 prior bars + 1 current bar = 21 total.

    Prior bars: all have spread ~2.0, volume ~1000 to establish a stable baseline.
    Current bar (index 20): spread = 5.0, volume = 1800 (clearly above-average).
    """
    bars: list[Bar] = []
    for i in range(20):
        bars.append(_bar(
            open_=100.0,
            high=103.0,
            low=99.0,
            close=102.0,  # spread = |102 - 100| = 2.0
            volume=1000,
            offset_minutes=i * 15,
        ))
    bars.append(_bar(
        open_=105.0,
        high=112.0,  # upper_wick = 112 - 110 = 2.0
        low=103.0,   # lower_wick = 105 - 103 = 2.0
        close=110.0,  # spread = |110 - 105| = 5.0, range = 112 - 103 = 9.0
        volume=1800,  # vol_rel = 1800 / 1000 = 1.8
        offset_minutes=20 * 15,
    ))
    return bars


# ---------------------------------------------------------------------------
# Golden-bar test: assert every field
# ---------------------------------------------------------------------------


class TestGoldenBar:
    """The golden fixture produces fully predictable CandleFeatures."""

    def test_all_fields(self, cfg: VPAConfig) -> None:
        bars = _golden_bars()
        features = extract_features(bars, cfg, tf="15m")

        assert isinstance(features, CandleFeatures)
        assert features.ts == bars[-1].timestamp
        assert features.tf == "15m"

        assert features.spread == pytest.approx(5.0)
        assert features.range == pytest.approx(9.0)
        assert features.upper_wick == pytest.approx(2.0)
        assert features.lower_wick == pytest.approx(2.0)

        # vol_rel: current=1800, avg of 20 prior=1000 -> 1.8
        assert features.vol_rel == pytest.approx(1.8)
        # spread_rel: current=5.0, avg of 20 prior=2.0 -> 2.5
        assert features.spread_rel == pytest.approx(2.5)

        # vol_rel=1.8 with default thresholds: 1.8 <= ultra_high boundary -> HIGH
        assert features.vol_state == VolumeState.HIGH
        # spread_rel=2.5 with default wide_gt=1.2 -> WIDE
        assert features.spread_state == SpreadState.WIDE

        assert features.candle_type == CandleType.UP

    def test_frozen(self, cfg: VPAConfig) -> None:
        bars = _golden_bars()
        features = extract_features(bars, cfg, tf="15m")
        with pytest.raises(AttributeError):
            features.spread = 999.0  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_single_bar_no_history(self, cfg: VPAConfig) -> None:
        """With only one bar, baselines are zero -> vol_rel and spread_rel are 0.0."""
        bars = [_bar(100.0, 105.0, 99.0, 103.0, 500)]
        features = extract_features(bars, cfg, tf="15m")

        assert features.spread == pytest.approx(3.0)
        assert features.range == pytest.approx(6.0)
        assert features.vol_rel == pytest.approx(0.0)
        assert features.spread_rel == pytest.approx(0.0)
        assert features.vol_state == VolumeState.LOW
        assert features.spread_state == SpreadState.NARROW

    def test_empty_bars_raises(self, cfg: VPAConfig) -> None:
        with pytest.raises(ValueError, match="at least one bar"):
            extract_features([], cfg, tf="15m")

    def test_down_bar(self, cfg: VPAConfig) -> None:
        bars = _golden_bars()
        down_bar = _bar(110.0, 112.0, 103.0, 105.0, 1800, offset_minutes=20 * 15)
        bars[-1] = down_bar
        features = extract_features(bars, cfg, tf="15m")
        assert features.candle_type == CandleType.DOWN

    def test_doji_bar(self, cfg: VPAConfig) -> None:
        """When open == close, candle_type is UP (>= boundary) and spread is 0."""
        bars = _golden_bars()
        doji = _bar(105.0, 108.0, 102.0, 105.0, 1000, offset_minutes=20 * 15)
        bars[-1] = doji
        features = extract_features(bars, cfg, tf="15m")
        assert features.candle_type == CandleType.UP
        assert features.spread == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Config-driven behavior
# ---------------------------------------------------------------------------


class TestConfigDriven:
    def test_different_thresholds_change_classification(self, tmp_path) -> None:
        """Tighter thresholds push the same vol_rel into ULTRA_HIGH."""
        import json
        from config.vpa_config import load_vpa_config, DEFAULT_CONFIG_PATH

        with open(DEFAULT_CONFIG_PATH) as f:
            data = json.load(f)
        data["vol"]["thresholds"]["ultra_high_gt"] = 1.5  # lower than default 1.8

        p = tmp_path / "tight.json"
        p.write_text(json.dumps(data))
        cfg = load_vpa_config(config_path=p)

        bars = _golden_bars()  # current vol_rel = 1.8
        features = extract_features(bars, cfg, tf="15m")
        assert features.vol_state == VolumeState.ULTRA_HIGH  # was HIGH with defaults

    def test_different_window_changes_baseline(self, tmp_path) -> None:
        """Shorter vol window uses fewer bars for the average."""
        import json
        from config.vpa_config import load_vpa_config, DEFAULT_CONFIG_PATH

        with open(DEFAULT_CONFIG_PATH) as f:
            data = json.load(f)
        data["vol"]["avg_window_N"] = 5

        p = tmp_path / "short_window.json"
        p.write_text(json.dumps(data))
        cfg = load_vpa_config(config_path=p)

        bars = _golden_bars()
        features = extract_features(bars, cfg, tf="15m")
        # With window=5, avg of last 5 prior bars still = 1000, so vol_rel still 1.8
        assert features.vol_rel == pytest.approx(1.8)
