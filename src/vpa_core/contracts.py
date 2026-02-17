"""
Data contracts for vpa-core: Bar, ContextWindow, Signal, TradePlan.

Canonical data models: docs/vpa-ck/vpa_system_spec.md §3.3.
vpa-core consumes Bar/ContextWindow and produces Signal/TradePlan.
No I/O; these are plain dataclasses.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Sequence


class RelativeVolume(str, Enum):
    """Relative volume classification vs recent baseline."""

    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"


@dataclass(frozen=True)
class Bar:
    """OHLCV bar; timestamps in UTC. No indicator fields."""

    open: float
    high: float
    low: float
    close: float
    volume: int
    timestamp: datetime
    symbol: str
    bar_index: int | None = None

    def spread(self) -> float:
        """Candle body magnitude: |close - open|.

        Per canonical glossary (vpa_glossary.md): spread is the candle body,
        used as a proxy for 'result' in effort vs result.
        """
        return abs(self.close - self.open)

    def body(self) -> float:
        """Alias for spread(): absolute difference between open and close."""
        return abs(self.close - self.open)

    def bar_range(self) -> float:
        """Full extent of the candle: high - low."""
        return self.high - self.low

    def is_up(self) -> bool:
        """Close greater than open."""
        return self.close > self.open


@dataclass(frozen=True)
class ContextWindow:
    """Input to vpa-core: ordered bars (oldest first), no lookahead."""

    bars: Sequence[Bar]
    symbol: str
    timeframe: str | None = None

    def current_bar(self) -> Bar | None:
        """Last bar in the window (current bar)."""
        if not self.bars:
            return None
        return self.bars[-1]


@dataclass(frozen=True)
class Signal:
    """Output of setup matching: one per detected VPA setup."""

    setup_type: str
    direction: str  # "long" | "short"
    bar_index: int
    timestamp: datetime
    rationale: str
    rulebook_ref: str
    strength: str | None = None


@dataclass(frozen=True)
class TradePlan:
    """Trading intent from a signal; execution layer converts to orders."""

    signal_id: str
    setup_type: str
    direction: str  # "long" | "short"
    entry_condition: str | dict[str, Any]
    stop_level: float | str
    invalidation_rules: list[str] | str
    rationale: str
    rulebook_ref: str
    target_logic: str | None = None
