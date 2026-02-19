"""Tests for Average True Range (ATR) computation.

Validates true_range and compute_atr against known values,
edge cases, and config integration.
"""

from datetime import datetime, timezone, timedelta

import pytest

from config.vpa_config import load_vpa_config, AtrConfig
from vpa_core.atr import compute_atr, true_range
from vpa_core.contracts import Bar


BASE_TS = datetime(2026, 2, 17, 9, 30, tzinfo=timezone.utc)


def _bar(i: int, *, open_: float = 100.0, high: float = 102.0,
         low: float = 99.0, close: float = 101.0) -> Bar:
    return Bar(
        timestamp=BASE_TS + timedelta(minutes=15 * i),
        open=open_, high=high, low=low,
        close=close, volume=100_000, symbol="TEST",
    )


# ---------------------------------------------------------------------------
# true_range
# ---------------------------------------------------------------------------


class TestTrueRange:

    def test_normal_bar_no_gap(self) -> None:
        """When prev_close is within the bar range, TR = high - low."""
        bar = _bar(1, high=105.0, low=100.0, close=103.0)
        assert true_range(bar, 102.0) == 5.0

    def test_gap_up(self) -> None:
        """Gap up: prev_close below bar low → TR = high - prev_close."""
        bar = _bar(1, high=110.0, low=106.0, close=108.0)
        tr = true_range(bar, 100.0)
        assert tr == 10.0  # |110 - 100| = 10

    def test_gap_down(self) -> None:
        """Gap down: prev_close above bar high → TR = prev_close - low."""
        bar = _bar(1, high=95.0, low=90.0, close=93.0)
        tr = true_range(bar, 100.0)
        assert tr == 10.0  # |90 - 100| = 10

    def test_flat_bar(self) -> None:
        """Zero-range bar: open = high = low = close."""
        bar = _bar(1, open_=100.0, high=100.0, low=100.0, close=100.0)
        assert true_range(bar, 100.0) == 0.0

    def test_flat_bar_with_gap(self) -> None:
        """Zero-range bar but with gap from prev_close."""
        bar = _bar(1, open_=100.0, high=100.0, low=100.0, close=100.0)
        tr = true_range(bar, 95.0)
        assert tr == 5.0  # |100 - 95| = 5


# ---------------------------------------------------------------------------
# compute_atr
# ---------------------------------------------------------------------------


def _constant_bars(n: int, *, high: float = 102.0, low: float = 98.0,
                   close: float = 100.0) -> list[Bar]:
    """N bars with identical ranges (TR = high - low each)."""
    return [_bar(i, high=high, low=low, close=close) for i in range(n)]


class TestComputeAtr:

    def test_constant_range_bars(self) -> None:
        """With constant high-low range and no gaps, ATR = high - low."""
        bars = _constant_bars(20, high=105.0, low=100.0)
        atr = compute_atr(bars, period=14)
        assert atr == pytest.approx(5.0, abs=0.01)

    def test_period_respected(self) -> None:
        """ATR uses only the last `period` true ranges."""
        bars = _constant_bars(5, high=110.0, low=100.0)
        bars.extend(_constant_bars(10, high=102.0, low=100.0))
        for i, b in enumerate(bars):
            bars[i] = Bar(
                open=b.open, high=b.high, low=b.low, close=b.close,
                volume=b.volume, timestamp=BASE_TS + timedelta(minutes=15 * i),
                symbol=b.symbol,
            )
        atr_short = compute_atr(bars, period=5)
        assert atr_short == pytest.approx(2.0, abs=0.1)

    def test_known_values(self) -> None:
        """ATR against hand-calculated values.

        Bars (no gaps, close = prev bar close):
            Bar 0: H=105 L=100 C=102 → (base)
            Bar 1: H=107 L=101 C=104 → TR = max(6, |107-102|, |101-102|) = 6
            Bar 2: H=106 L=100 C=103 → TR = max(6, |106-104|, |100-104|) = 6
            Bar 3: H=108 L=102 C=105 → TR = max(6, |108-103|, |102-103|) = 6

        ATR(3) = (6 + 6 + 6) / 3 = 6.0
        """
        bars = [
            _bar(0, high=105.0, low=100.0, close=102.0),
            _bar(1, high=107.0, low=101.0, close=104.0),
            _bar(2, high=106.0, low=100.0, close=103.0),
            _bar(3, high=108.0, low=102.0, close=105.0),
        ]
        atr = compute_atr(bars, period=3)
        assert atr == pytest.approx(6.0, abs=0.01)

    def test_with_gap(self) -> None:
        """Gap up increases true range beyond high-low."""
        bars = [
            _bar(0, high=100.0, low=98.0, close=99.0),
            _bar(1, high=110.0, low=106.0, close=108.0),
        ]
        atr = compute_atr(bars, period=14)
        # TR = max(110-106, |110-99|, |106-99|) = max(4, 11, 7) = 11
        assert atr == pytest.approx(11.0, abs=0.01)

    def test_fewer_bars_than_period(self) -> None:
        """With fewer bars than period, uses all available true ranges."""
        bars = _constant_bars(5, high=104.0, low=100.0)
        atr = compute_atr(bars, period=14)
        # Only 4 TR values from 5 bars, all = 4.0
        assert atr == pytest.approx(4.0, abs=0.01)

    def test_single_bar_returns_zero(self) -> None:
        assert compute_atr([_bar(0)], period=14) == 0.0

    def test_empty_bars_returns_zero(self) -> None:
        assert compute_atr([], period=14) == 0.0

    def test_two_bars_gives_one_tr(self) -> None:
        bars = [
            _bar(0, high=100.0, low=98.0, close=99.0),
            _bar(1, high=103.0, low=97.0, close=101.0),
        ]
        atr = compute_atr(bars, period=14)
        # TR = max(6, |103-99|, |97-99|) = max(6, 4, 2) = 6
        assert atr == pytest.approx(6.0, abs=0.01)

    def test_default_period_is_14(self) -> None:
        bars = _constant_bars(30, high=103.0, low=100.0)
        atr_default = compute_atr(bars)
        atr_explicit = compute_atr(bars, period=14)
        assert atr_default == atr_explicit


# ---------------------------------------------------------------------------
# Config integration
# ---------------------------------------------------------------------------


class TestAtrConfig:

    def test_default_config_has_atr(self) -> None:
        cfg = load_vpa_config()
        assert hasattr(cfg, "atr")
        assert cfg.atr.period == 14
        assert cfg.atr.stop_multiplier == 1.5
        assert cfg.atr.enabled is False

    def test_atr_config_frozen(self) -> None:
        cfg = load_vpa_config()
        with pytest.raises(AttributeError):
            cfg.atr.period = 20  # type: ignore[misc]

    def test_custom_atr_config(self, tmp_path) -> None:
        import json
        from config.vpa_config import DEFAULT_CONFIG_PATH
        with open(DEFAULT_CONFIG_PATH) as f:
            data = json.load(f)
        data["atr"] = {"period": 20, "stop_multiplier": 2.0, "enabled": True}
        p = tmp_path / "atr_cfg.json"
        p.write_text(json.dumps(data))
        cfg = load_vpa_config(config_path=p)
        assert cfg.atr.period == 20
        assert cfg.atr.stop_multiplier == 2.0
        assert cfg.atr.enabled is True
