"""
Feature Engine: Bar + prior bars + VPAConfig -> CandleFeatures.

This is the canonical entry point for stage 2 of the pipeline
(Ingest -> Resample -> **Features** -> ...).

Pure function; no I/O, no side effects. All relative measures
use rolling averages from config-specified windows.
"""

from __future__ import annotations

from vpa_core.contracts import Bar, CandleFeatures, CandleType
from vpa_core.features import (
    average_spread,
    bar_range,
    classify_spread,
    lower_wick,
    spread,
    spread_rel,
    upper_wick,
)
from vpa_core.relative_volume import average_volume, classify_volume, vol_rel

from config.vpa_config import VPAConfig


def extract_features(bars: list[Bar], config: VPAConfig, tf: str) -> CandleFeatures:
    """Extract canonical CandleFeatures for the last bar in *bars*.

    Parameters
    ----------
    bars:
        Ordered bar history (oldest first). The last element is the current bar;
        prior bars supply the rolling averages for relative measures.
    config:
        VPA configuration with window sizes and classification thresholds.
    tf:
        Timeframe label (e.g. "15m", "1h").

    Returns
    -------
    CandleFeatures
        Frozen dataclass with all computed fields per VPA_SYSTEM_SPEC §3.3.

    Raises
    ------
    ValueError
        If *bars* is empty.
    """
    if not bars:
        raise ValueError("extract_features requires at least one bar")

    current = bars[-1]

    bar_spread = spread(current)
    bar_rng = bar_range(current)
    bar_upper_wick = upper_wick(current)
    bar_lower_wick = lower_wick(current)

    vol_avg = average_volume(bars, lookback=config.vol.avg_window_N)
    computed_vol_rel = vol_rel(current.volume, vol_avg) if vol_avg > 0 else 0.0

    spread_avg = average_spread(bars, lookback=config.spread.avg_window_M)
    computed_spread_rel = spread_rel(current, spread_avg) if spread_avg > 0 else 0.0

    vol_state = classify_volume(computed_vol_rel, config)
    spread_state = classify_spread(computed_spread_rel, config)

    candle_type = CandleType.UP if current.close >= current.open else CandleType.DOWN

    return CandleFeatures(
        ts=current.timestamp,
        tf=tf,
        spread=bar_spread,
        range=bar_rng,
        upper_wick=bar_upper_wick,
        lower_wick=bar_lower_wick,
        spread_rel=computed_spread_rel,
        vol_rel=computed_vol_rel,
        vol_state=vol_state,
        spread_state=spread_state,
        candle_type=candle_type,
    )
