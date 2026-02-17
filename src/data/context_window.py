"""
Provide rolling context window (last N bars) for vpa-core.
"""

from datetime import datetime, timezone

from vpa_core.contracts import ContextWindow

from data.bar_store import BarStore


def get_context_window(
    store: BarStore,
    symbol: str,
    timeframe: str,
    *,
    window_size: int = 50,
    end_time: str | None = None,
) -> ContextWindow | None:
    """
    Load the last `window_size` bars (ascending time) and return a ContextWindow.
    If `end_time` is given (ISO UTC), load bars up to that time; else use latest.
    Returns None if no bars.
    """
    from datetime import datetime, timezone

    until = datetime.fromisoformat(end_time.replace("Z", "+00:00")) if end_time else None
    if until is not None and until.tzinfo is None:
        until = until.replace(tzinfo=timezone.utc)
    bars = store.get_last_bars(symbol, timeframe, window_size, until=until)
    if not bars:
        return None
    return ContextWindow(bars=bars, symbol=symbol, timeframe=timeframe)
