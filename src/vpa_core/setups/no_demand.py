"""
No Demand setup (bearish/weakness): up move on low or declining volume.

Rulebook: docs/RULEBOOK.md — no_demand.
Preconditions: uptrend or bounce. Candle: up bar. Volume: low or declining.
"""

from vpa_core.contracts import Bar, RelativeVolume
from vpa_core.context import CONTEXT_UPTREND, detect_context
from vpa_core.relative_volume import relative_volume_for_bar


def _is_up_bar(bar: Bar, prior: Bar | None) -> bool:
    """Up bar: close > open, or at least close > prior close."""
    if prior is None:
        return bar.close > bar.open
    return bar.close > bar.open or bar.close > prior.close


def _volume_declining(bars: list[Bar]) -> bool:
    """Current bar volume less than prior bar (declining)."""
    if len(bars) < 2:
        return False
    return bars[-1].volume < bars[-2].volume


def check_no_demand(
    bars: list[Bar],
    *,
    volume_lookback: int = 20,
    context_lookback: int = 3,
) -> bool:
    """
    True if the last bar in `bars` qualifies as No Demand per rulebook.

    - Context: uptrend or bounce (we use uptrend for MVP).
    - Current bar: up bar (close > open or close > prior close).
    - Volume: low (vs baseline) or declining vs prior bar.
    """
    if not bars or len(bars) < 2:
        return False
    current = bars[-1]
    prior = bars[-2]
    if not _is_up_bar(current, prior):
        return False
    context = detect_context(bars, lookback=context_lookback)
    if context != CONTEXT_UPTREND:
        # Rulebook: uptrend or bounce; MVP we only accept uptrend
        return False
    rel_vol = relative_volume_for_bar(bars, lookback=volume_lookback)
    if rel_vol == RelativeVolume.LOW or _volume_declining(bars):
        return True
    return False
