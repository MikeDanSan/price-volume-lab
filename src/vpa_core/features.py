"""
Candle feature extraction: spread, bar_range, body, close location, wicks,
spread classification.

Pure functions; no I/O.

Per canonical glossary (vpa_glossary.md):
  spread = |close - open|  (candle body; proxy for "result" in effort vs result)
  range  = high - low      (full extent of the candle)

Canonical 3-state spread classification: NARROW / NORMAL / WIDE
driven by VPAConfig thresholds (docs/vpa/VPA_CONFIG.md §2.2).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from vpa_core.contracts import Bar, SpreadState

if TYPE_CHECKING:
    from config.vpa_config import VPAConfig


# ---------------------------------------------------------------------------
# Single-bar candle anatomy
# ---------------------------------------------------------------------------


def spread(bar: Bar) -> float:
    """Candle body magnitude: |close - open|.

    Per canonical glossary: spread is the candle body, used as a proxy
    for 'result' in effort vs result.
    """
    return abs(bar.close - bar.open)


def body(bar: Bar) -> float:
    """Alias for spread(): absolute difference between open and close."""
    return abs(bar.close - bar.open)


def bar_range(bar: Bar) -> float:
    """Full extent of the candle: high - low."""
    return bar.high - bar.low


def upper_wick(bar: Bar) -> float:
    """Upper wick: high - max(open, close)."""
    return bar.high - max(bar.open, bar.close)


def lower_wick(bar: Bar) -> float:
    """Lower wick: min(open, close) - low."""
    return min(bar.open, bar.close) - bar.low


def close_location(bar: Bar) -> str:
    """Where the close sits within the bar's range: upper / middle / lower third."""
    if bar.high == bar.low:
        return "middle"
    range_ = bar.high - bar.low
    pos = (bar.close - bar.low) / range_
    if pos >= 2 / 3:
        return "upper"
    if pos <= 1 / 3:
        return "lower"
    return "middle"


# ---------------------------------------------------------------------------
# Rolling spread baseline + relative spread
# ---------------------------------------------------------------------------


def average_spread(bars: list[Bar], lookback: int) -> float:
    """Average spread (|close - open|) over the last ``lookback`` bars (excluding current).

    Mirrors ``average_volume`` in relative_volume.py — same windowing logic.
    """
    if lookback <= 0 or not bars or len(bars) < 2:
        return 0.0
    window = bars[-(lookback + 1) : -1] if len(bars) > lookback + 1 else bars[:-1]
    if not window:
        return spread(bars[-1]) if bars else 0.0
    return sum(spread(b) for b in window) / len(window)


def spread_rel(bar: Bar, baseline_avg: float) -> float:
    """Compute SpreadRel = spread(bar) / baseline_avg.  Returns 0.0 if baseline is non-positive."""
    if baseline_avg <= 0:
        return 0.0
    return spread(bar) / baseline_avg


# ---------------------------------------------------------------------------
# Canonical 3-state spread classifier (config-driven)
# ---------------------------------------------------------------------------


def classify_spread(spread_rel_value: float, config: VPAConfig) -> SpreadState:
    """Classify SpreadRel into the canonical 3-state SpreadState using config thresholds.

    Thresholds from ``config.spread.thresholds``:
      NARROW : spread_rel < narrow_lt
      NORMAL : narrow_lt <= spread_rel <= wide_gt
      WIDE   : spread_rel > wide_gt
    """
    t = config.spread.thresholds
    if spread_rel_value > t.wide_gt:
        return SpreadState.WIDE
    if spread_rel_value < t.narrow_lt:
        return SpreadState.NARROW
    return SpreadState.NORMAL
