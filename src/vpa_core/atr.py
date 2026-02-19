"""
Average True Range (ATR) computation.

ATR measures volatility by averaging the True Range over a lookback
window. Used by the Risk Engine for volatility-adaptive stop placement.

True Range = max(
    high - low,
    |high - prev_close|,
    |low  - prev_close|
)

ATR(n) = Simple Moving Average of True Range over the last n bars.

Pure function; no I/O.
"""

from __future__ import annotations

from vpa_core.contracts import Bar


def true_range(current: Bar, prev_close: float) -> float:
    """Compute the True Range for a single bar.

    The True Range accounts for gaps between bars by comparing
    the current bar's high/low against the previous close.
    """
    return max(
        current.high - current.low,
        abs(current.high - prev_close),
        abs(current.low - prev_close),
    )


def compute_atr(bars: list[Bar], period: int = 14) -> float:
    """Compute ATR over the last ``period`` bars using SMA.

    Parameters
    ----------
    bars:
        Ordered bar history (oldest first). At least ``period + 1``
        bars are recommended for a full-window calculation.
    period:
        Number of bars for the averaging window (default: 14).

    Returns
    -------
    float
        The ATR value. Returns 0.0 if fewer than 2 bars are provided.
    """
    if len(bars) < 2:
        return 0.0

    tr_values: list[float] = []
    for i in range(1, len(bars)):
        tr_values.append(true_range(bars[i], bars[i - 1].close))

    if not tr_values:
        return 0.0

    window = tr_values[-period:] if len(tr_values) >= period else tr_values
    return sum(window) / len(window)
