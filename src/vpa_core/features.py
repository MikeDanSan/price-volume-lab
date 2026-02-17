"""
Candle feature extraction: spread, bar_range, body, close location, wicks.

Pure functions; no I/O.

Per canonical glossary (vpa_glossary.md):
  spread = |close - open|  (candle body; proxy for "result" in effort vs result)
  range  = high - low      (full extent of the candle)
"""

from vpa_core.contracts import Bar


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
    """
    Where the close sits within the bar's range: upper / middle / lower third.
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
