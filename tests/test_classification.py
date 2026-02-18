"""Tests for canonical 4-state volume and 3-state spread classification.

All classifiers are config-driven — no hardcoded thresholds.
"""

from datetime import datetime, timezone

import pytest

from config.vpa_config import load_vpa_config, VPAConfig
from vpa_core.contracts import Bar, SpreadState, VolumeState
from vpa_core.features import average_spread, classify_spread, spread_rel
from vpa_core.relative_volume import average_volume, classify_volume, vol_rel


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def cfg() -> VPAConfig:
    """Default VPA config (low_lt=0.8, high_gt=1.2, ultra_high_gt=1.8)."""
    return load_vpa_config()


def _bar(open_: float, close: float, volume: int = 1000) -> Bar:
    return Bar(open_, open_ + 5.0, open_ - 1.0, close, volume, datetime.now(timezone.utc), "TEST")


# ---------------------------------------------------------------------------
# classify_volume — 4-state boundary tests
# ---------------------------------------------------------------------------


class TestClassifyVolume:
    """Boundary tests for VolumeState with default thresholds (0.8 / 1.2 / 1.8)."""

    def test_low(self, cfg: VPAConfig) -> None:
        assert classify_volume(0.5, cfg) == VolumeState.LOW
        assert classify_volume(0.79, cfg) == VolumeState.LOW

    def test_average_at_boundary(self, cfg: VPAConfig) -> None:
        assert classify_volume(0.8, cfg) == VolumeState.AVERAGE
        assert classify_volume(1.0, cfg) == VolumeState.AVERAGE
        assert classify_volume(1.2, cfg) == VolumeState.AVERAGE

    def test_high(self, cfg: VPAConfig) -> None:
        assert classify_volume(1.21, cfg) == VolumeState.HIGH
        assert classify_volume(1.5, cfg) == VolumeState.HIGH
        assert classify_volume(1.8, cfg) == VolumeState.HIGH

    def test_ultra_high(self, cfg: VPAConfig) -> None:
        assert classify_volume(1.81, cfg) == VolumeState.ULTRA_HIGH
        assert classify_volume(3.0, cfg) == VolumeState.ULTRA_HIGH

    def test_zero_vol_rel(self, cfg: VPAConfig) -> None:
        assert classify_volume(0.0, cfg) == VolumeState.LOW


class TestClassifyVolumeOverrides:
    """Custom thresholds via override config."""

    def test_tighter_thresholds(self, tmp_path) -> None:
        import json
        from config.vpa_config import load_vpa_config, DEFAULT_CONFIG_PATH

        with open(DEFAULT_CONFIG_PATH) as f:
            data = json.load(f)
        data["vol"]["thresholds"]["low_lt"] = 0.9
        data["vol"]["thresholds"]["high_gt"] = 1.1
        data["vol"]["thresholds"]["ultra_high_gt"] = 1.5

        p = tmp_path / "tight.json"
        p.write_text(json.dumps(data))
        cfg = load_vpa_config(config_path=p)

        assert classify_volume(0.89, cfg) == VolumeState.LOW
        assert classify_volume(0.95, cfg) == VolumeState.AVERAGE
        assert classify_volume(1.15, cfg) == VolumeState.HIGH
        assert classify_volume(1.51, cfg) == VolumeState.ULTRA_HIGH


# ---------------------------------------------------------------------------
# classify_spread — 3-state boundary tests
# ---------------------------------------------------------------------------


class TestClassifySpread:
    """Boundary tests for SpreadState with default thresholds (0.8 / 1.2)."""

    def test_narrow(self, cfg: VPAConfig) -> None:
        assert classify_spread(0.5, cfg) == SpreadState.NARROW
        assert classify_spread(0.79, cfg) == SpreadState.NARROW

    def test_normal_at_boundary(self, cfg: VPAConfig) -> None:
        assert classify_spread(0.8, cfg) == SpreadState.NORMAL
        assert classify_spread(1.0, cfg) == SpreadState.NORMAL
        assert classify_spread(1.2, cfg) == SpreadState.NORMAL

    def test_wide(self, cfg: VPAConfig) -> None:
        assert classify_spread(1.21, cfg) == SpreadState.WIDE
        assert classify_spread(2.0, cfg) == SpreadState.WIDE

    def test_zero_spread_rel(self, cfg: VPAConfig) -> None:
        assert classify_spread(0.0, cfg) == SpreadState.NARROW


class TestClassifySpreadOverrides:
    """Custom spread thresholds via override config."""

    def test_wider_normal_band(self, tmp_path) -> None:
        import json
        from config.vpa_config import load_vpa_config, DEFAULT_CONFIG_PATH

        with open(DEFAULT_CONFIG_PATH) as f:
            data = json.load(f)
        data["spread"]["thresholds"]["narrow_lt"] = 0.6
        data["spread"]["thresholds"]["wide_gt"] = 1.4

        p = tmp_path / "wide_band.json"
        p.write_text(json.dumps(data))
        cfg = load_vpa_config(config_path=p)

        assert classify_spread(0.7, cfg) == SpreadState.NORMAL  # would be NARROW with defaults
        assert classify_spread(1.3, cfg) == SpreadState.NORMAL  # would be WIDE with defaults
        assert classify_spread(0.59, cfg) == SpreadState.NARROW
        assert classify_spread(1.41, cfg) == SpreadState.WIDE


# ---------------------------------------------------------------------------
# vol_rel and spread_rel helper functions
# ---------------------------------------------------------------------------


class TestVolRel:
    def test_basic_ratio(self) -> None:
        assert vol_rel(150, 100.0) == 1.5

    def test_zero_baseline(self) -> None:
        assert vol_rel(100, 0.0) == 0.0

    def test_negative_baseline(self) -> None:
        assert vol_rel(100, -50.0) == 0.0


class TestSpreadRel:
    def test_basic_ratio(self) -> None:
        bar = _bar(100.0, 104.0)  # spread = 4.0
        assert spread_rel(bar, 2.0) == pytest.approx(2.0)

    def test_zero_baseline(self) -> None:
        bar = _bar(100.0, 104.0)
        assert spread_rel(bar, 0.0) == 0.0


# ---------------------------------------------------------------------------
# average_spread
# ---------------------------------------------------------------------------


class TestAverageSpread:
    def test_basic(self) -> None:
        ts = datetime.now(timezone.utc)
        bars = [
            Bar(100.0, 105.0, 99.0, 102.0, 100, ts, "SPY"),  # spread = 2
            Bar(100.0, 106.0, 99.0, 104.0, 100, ts, "SPY"),  # spread = 4
            Bar(100.0, 107.0, 99.0, 106.0, 100, ts, "SPY"),  # spread = 6 (current)
        ]
        avg = average_spread(bars, lookback=2)
        assert avg == pytest.approx(3.0)  # (2 + 4) / 2

    def test_insufficient_bars(self) -> None:
        assert average_spread([], lookback=20) == 0.0

    def test_single_bar(self) -> None:
        ts = datetime.now(timezone.utc)
        bars = [Bar(100.0, 105.0, 99.0, 103.0, 100, ts, "SPY")]
        assert average_spread(bars, lookback=20) == 0.0
