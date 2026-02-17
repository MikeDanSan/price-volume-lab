"""
Relative volume classification vs recent baseline.

Volume is always interpreted relatively (per book). Baseline = average
volume over the last N bars (excluding current). Pure function; no I/O.
"""

from vpa_core.contracts import Bar, RelativeVolume


def average_volume(bars: list[Bar], lookback: int) -> float:
    """Average volume over the last `lookback` bars (from the bars before current)."""
    if lookback <= 0 or not bars or len(bars) < 2:
        return 0.0
    # Use bars[:-1] so we don't include "current" bar in baseline when used for current
    window = bars[-(lookback + 1) : -1] if len(bars) > lookback + 1 else bars[:-1]
    if not window:
        return float(bars[-1].volume) if bars else 0.0
    return sum(b.volume for b in window) / len(window)


def classify_relative_volume(
    current_volume: int,
    baseline_avg: float,
    *,
    high_threshold: float = 1.2,
    low_threshold: float = 0.8,
) -> RelativeVolume:
    """
    Classify volume as high / normal / low vs baseline.

    Default: above 1.2x baseline = high, below 0.8x = low.
    Thresholds must match rulebook; no optimization.
    """
    if baseline_avg <= 0:
        return RelativeVolume.NORMAL
    ratio = current_volume / baseline_avg
    if ratio >= high_threshold:
        return RelativeVolume.HIGH
    if ratio <= low_threshold:
        return RelativeVolume.LOW
    return RelativeVolume.NORMAL


def relative_volume_for_bar(
    bars: list[Bar],
    lookback: int = 20,
    high_threshold: float = 1.2,
    low_threshold: float = 0.8,
) -> RelativeVolume:
    """
    Classify relative volume for the last (current) bar in `bars`.
    Baseline = average volume of previous `lookback` bars.
    """
    if not bars or len(bars) < 2:
        return RelativeVolume.NORMAL
    baseline = average_volume(bars, lookback)
    return classify_relative_volume(
        bars[-1].volume,
        baseline,
        high_threshold=high_threshold,
        low_threshold=low_threshold,
    )
