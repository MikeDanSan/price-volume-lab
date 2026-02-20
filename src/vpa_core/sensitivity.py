"""
Threshold proximity analysis for VPA rule tuning.

For each bar, computes how close the features were to crossing key
signal thresholds. Reports "near-misses" — conditions that failed
by a small margin — to help assess whether thresholds are reasonable
without blindly optimizing them.

Pure functions; no I/O.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from vpa_core.contracts import (
    CandleFeatures,
    CandleType,
    SpreadState,
    VolumeState,
)

if TYPE_CHECKING:
    from config.vpa_config import VPAConfig


@dataclass(frozen=True)
class NearMiss:
    """A signal condition that was close to firing but didn't."""
    rule_id: str
    condition: str
    actual: float
    threshold: float
    gap_pct: float


def compute_near_misses(
    features: CandleFeatures,
    config: VPAConfig,
    *,
    gap_threshold: float = 0.15,
) -> list[NearMiss]:
    """Identify near-miss conditions for the given bar.

    Parameters
    ----------
    features:
        CandleFeatures for one bar.
    config:
        VPA config with thresholds.
    gap_threshold:
        Maximum relative gap (as fraction) to report. Default 0.15 means
        conditions within 15% of the threshold are reported.

    Returns
    -------
    list[NearMiss]
        Near-miss entries sorted by gap (closest first).
    """
    misses: list[NearMiss] = []

    _check_volume_proximity(features, config, gap_threshold, misses)
    _check_spread_proximity(features, config, gap_threshold, misses)
    _check_val1_proximity(features, config, gap_threshold, misses)
    _check_hammer_proximity(features, config, gap_threshold, misses)
    _check_shooting_star_proximity(features, config, gap_threshold, misses)

    misses.sort(key=lambda m: abs(m.gap_pct))
    return misses


def _gap(actual: float, threshold: float) -> float:
    """Relative distance from threshold as a fraction of threshold."""
    if threshold == 0:
        return float("inf")
    return (actual - threshold) / abs(threshold)


def _check_volume_proximity(
    f: CandleFeatures,
    cfg: VPAConfig,
    gap_thr: float,
    out: list[NearMiss],
) -> None:
    vt = cfg.vol.thresholds

    if f.vol_state != VolumeState.LOW:
        g = _gap(f.vol_rel, vt.low_lt)
        if abs(g) <= gap_thr:
            out.append(NearMiss("(volume)", f"vol_rel near LOW boundary", f.vol_rel, vt.low_lt, round(g, 4)))

    if f.vol_state not in (VolumeState.HIGH, VolumeState.ULTRA_HIGH):
        g = _gap(f.vol_rel, vt.high_gt)
        if abs(g) <= gap_thr:
            out.append(NearMiss("(volume)", f"vol_rel near HIGH boundary", f.vol_rel, vt.high_gt, round(g, 4)))


def _check_spread_proximity(
    f: CandleFeatures,
    cfg: VPAConfig,
    gap_thr: float,
    out: list[NearMiss],
) -> None:
    st = cfg.spread.thresholds

    if f.spread_state != SpreadState.NARROW:
        g = _gap(f.spread_rel, st.narrow_lt)
        if abs(g) <= gap_thr:
            out.append(NearMiss("(spread)", "spread_rel near NARROW boundary", f.spread_rel, st.narrow_lt, round(g, 4)))

    if f.spread_state != SpreadState.WIDE:
        g = _gap(f.spread_rel, st.wide_gt)
        if abs(g) <= gap_thr:
            out.append(NearMiss("(spread)", "spread_rel near WIDE boundary", f.spread_rel, st.wide_gt, round(g, 4)))


def _check_val1_proximity(
    f: CandleFeatures,
    cfg: VPAConfig,
    gap_thr: float,
    out: list[NearMiss],
) -> None:
    """Check if a bar was close to firing VAL-1 (wide up bar + high volume)."""
    if f.candle_type != CandleType.UP:
        return

    vt = cfg.vol.thresholds
    st = cfg.spread.thresholds
    has_wide = f.spread_state == SpreadState.WIDE
    has_high_vol = f.vol_state in (VolumeState.HIGH, VolumeState.ULTRA_HIGH)

    if has_wide and not has_high_vol:
        g = _gap(f.vol_rel, vt.high_gt)
        if abs(g) <= gap_thr:
            out.append(NearMiss("VAL-1", "wide up bar but vol_rel just below HIGH", f.vol_rel, vt.high_gt, round(g, 4)))

    if has_high_vol and not has_wide:
        g = _gap(f.spread_rel, st.wide_gt)
        if abs(g) <= gap_thr:
            out.append(NearMiss("VAL-1", "high vol up bar but spread_rel just below WIDE", f.spread_rel, st.wide_gt, round(g, 4)))


def _check_hammer_proximity(
    f: CandleFeatures,
    cfg: VPAConfig,
    gap_thr: float,
    out: list[NearMiss],
) -> None:
    """Check if a bar was close to qualifying as a hammer (STR-1)."""
    rng = f.range
    if rng <= 0:
        return

    h = cfg.candle_patterns.hammer
    lower_ratio = f.lower_wick / rng
    body_ratio = f.spread / rng
    upper_ratio = f.upper_wick / rng

    passes_lower = lower_ratio >= h.lower_wick_ratio_min
    passes_body = body_ratio <= h.body_ratio_max
    passes_upper = upper_ratio <= h.upper_wick_ratio_max

    passing = sum([passes_lower, passes_body, passes_upper])
    if passing < 2:
        return

    if not passes_lower:
        g = _gap(lower_ratio, h.lower_wick_ratio_min)
        if abs(g) <= gap_thr:
            out.append(NearMiss("STR-1", "lower_wick_ratio just below hammer min", round(lower_ratio, 4), h.lower_wick_ratio_min, round(g, 4)))

    if not passes_body:
        g = _gap(body_ratio, h.body_ratio_max)
        if abs(g) <= gap_thr:
            out.append(NearMiss("STR-1", "body_ratio just above hammer max", round(body_ratio, 4), h.body_ratio_max, round(g, 4)))

    if not passes_upper:
        g = _gap(upper_ratio, h.upper_wick_ratio_max)
        if abs(g) <= gap_thr:
            out.append(NearMiss("STR-1", "upper_wick_ratio just above hammer max", round(upper_ratio, 4), h.upper_wick_ratio_max, round(g, 4)))


def _check_shooting_star_proximity(
    f: CandleFeatures,
    cfg: VPAConfig,
    gap_thr: float,
    out: list[NearMiss],
) -> None:
    """Check if a bar was close to qualifying as a shooting star (WEAK-1)."""
    rng = f.range
    if rng <= 0:
        return

    ss = cfg.candle_patterns.shooting_star
    upper_ratio = f.upper_wick / rng
    body_ratio = f.spread / rng
    lower_ratio = f.lower_wick / rng

    passes_upper = upper_ratio >= ss.upper_wick_ratio_min
    passes_body = body_ratio <= ss.body_ratio_max
    passes_lower = lower_ratio <= ss.lower_wick_ratio_max

    passing = sum([passes_upper, passes_body, passes_lower])
    if passing < 2:
        return

    if not passes_upper:
        g = _gap(upper_ratio, ss.upper_wick_ratio_min)
        if abs(g) <= gap_thr:
            out.append(NearMiss("WEAK-1", "upper_wick_ratio just below shooting star min", round(upper_ratio, 4), ss.upper_wick_ratio_min, round(g, 4)))

    if not passes_body:
        g = _gap(body_ratio, ss.body_ratio_max)
        if abs(g) <= gap_thr:
            out.append(NearMiss("WEAK-1", "body_ratio just above shooting star max", round(body_ratio, 4), ss.body_ratio_max, round(g, 4)))

    if not passes_lower:
        g = _gap(lower_ratio, ss.lower_wick_ratio_max)
        if abs(g) <= gap_thr:
            out.append(NearMiss("WEAK-1", "lower_wick_ratio just above shooting star max", round(lower_ratio, 4), ss.lower_wick_ratio_max, round(g, 4)))
