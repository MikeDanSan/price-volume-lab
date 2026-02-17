"""
Candle feature extraction: spread, body, close location.

Pure functions; no I/O. Aligned with glossary: spread = high-low, body = |close-open|.
"""

from vpa_core.contracts import Bar


def spread(bar: Bar) -> float:
    """Range of the candle (high minus low)."""
    return bar.high - bar.low


def body(bar: Bar) -> float:
    """Absolute difference between open and close (real body)."""
    return abs(bar.close - bar.open)


def close_location(bar: Bar) -> str:
    """
    Where the close sits within the bar: upper / middle / lower third.
    Used to infer buyer/seller control.
    """
    if bar.high == bar.low:
        return "middle"
    range_ = bar.high - bar.low
    pos = (bar.close - bar.low) / range_
    if pos >= 2 / 3:
        return "upper"
    if pos <= 1 / 3:
        return "lower"
    return "middle"
