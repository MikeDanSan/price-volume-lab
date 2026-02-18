"""
Relative volume classification vs recent baseline.

Volume is always interpreted relatively (per book). Baseline = average
volume over the last N bars (excluding current). Pure function; no I/O.

Canonical 4-state classification: LOW / AVERAGE / HIGH / ULTRA_HIGH
driven by VPAConfig thresholds (docs/vpa/VPA_CONFIG.md §2.1).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from vpa_core.contracts import Bar, RelativeVolume, VolumeState

if TYPE_CHECKING:
    from config.vpa_config import VPAConfig


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def average_volume(bars: list[Bar], lookback: int) -> float:
    """Average volume over the last ``lookback`` bars (excluding current)."""
    if lookback <= 0 or not bars or len(bars) < 2:
        return 0.0
    window = bars[-(lookback + 1) : -1] if len(bars) > lookback + 1 else bars[:-1]
    if not window:
        return float(bars[-1].volume) if bars else 0.0
    return sum(b.volume for b in window) / len(window)


def vol_rel(current_volume: int | float, baseline_avg: float) -> float:
    """Compute VolRel = current_volume / baseline_avg.  Returns 0.0 if baseline is non-positive."""
    if baseline_avg <= 0:
        return 0.0
    return current_volume / baseline_avg


# ---------------------------------------------------------------------------
# Canonical 4-state classifier (config-driven)
# ---------------------------------------------------------------------------


def classify_volume(vol_rel_value: float, config: VPAConfig) -> VolumeState:
    """Classify VolRel into the canonical 4-state VolumeState using config thresholds.

    Thresholds from ``config.vol.thresholds``:
      LOW        : vol_rel < low_lt
      AVERAGE    : low_lt <= vol_rel <= high_gt
      HIGH       : high_gt < vol_rel <= ultra_high_gt
      ULTRA_HIGH : vol_rel > ultra_high_gt
    """
    t = config.vol.thresholds
    if vol_rel_value > t.ultra_high_gt:
        return VolumeState.ULTRA_HIGH
    if vol_rel_value > t.high_gt:
        return VolumeState.HIGH
    if vol_rel_value < t.low_lt:
        return VolumeState.LOW
    return VolumeState.AVERAGE


# ---------------------------------------------------------------------------
# Legacy 3-state classifier (DEPRECATED — kept for backward compat)
# ---------------------------------------------------------------------------


def classify_relative_volume(
    current_volume: int,
    baseline_avg: float,
    *,
    high_threshold: float = 1.2,
    low_threshold: float = 0.8,
) -> RelativeVolume:
    """DEPRECATED: use ``classify_volume()`` with VPAConfig for new code.

    Classify volume as high / normal / low vs baseline.
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
    """DEPRECATED: use ``classify_volume()`` with VPAConfig for new code.

    Classify relative volume for the last (current) bar in ``bars``.
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
