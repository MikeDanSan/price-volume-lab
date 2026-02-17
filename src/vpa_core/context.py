"""
Context detection: trend vs range (background strength/weakness).

Signals are interpreted in context (per book). Simple MVP: infer from
recent bar closes. Pure functions; no I/O.
"""

from vpa_core.contracts import Bar

# Simple labels for MVP; can extend (e.g. S/R) later.
CONTEXT_UPTREND = "uptrend"
CONTEXT_DOWNTREND = "downtrend"
CONTEXT_RANGE = "range"


def detect_context(bars: list[Bar], lookback: int = 5) -> str:
    """
    Detect market context from recent bars: uptrend, downtrend, or range.

    Uptrend: majority of last `lookback` bars close higher than prior close.
    Downtrend: majority close lower. Else: range.
    """
    if not bars or len(bars) < lookback + 1:
        return CONTEXT_RANGE
    window = bars[-lookback - 1 : -1]
    ups = sum(1 for i in range(1, len(window)) if window[i].close > window[i - 1].close)
    downs = sum(
        1 for i in range(1, len(window)) if window[i].close < window[i - 1].close
    )
    if ups > downs and ups >= (lookback // 2) + 1:
        return CONTEXT_UPTREND
    if downs > ups and downs >= (lookback // 2) + 1:
        return CONTEXT_DOWNTREND
    return CONTEXT_RANGE
