"""
Data contracts for vpa-core: Bar, ContextWindow, Signal, TradePlan.

Canonical data models: docs/vpa-ck/vpa_system_spec.md §3.3.
vpa-core consumes Bar/ContextWindow and produces Signal/TradePlan.
No I/O; these are plain dataclasses.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Sequence


# ---------------------------------------------------------------------------
# Legacy enum (kept for backward compat; use VolumeState for new code)
# ---------------------------------------------------------------------------


class RelativeVolume(str, Enum):
    """Relative volume classification vs recent baseline. DEPRECATED: use VolumeState."""

    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"


# ---------------------------------------------------------------------------
# Canonical enums (VPA_SYSTEM_SPEC / VPA_ACTIONABLE_RULES)
# ---------------------------------------------------------------------------


class VolumeState(str, Enum):
    """4-state volume classification via VolRel = volume / SMA(volume, N)."""

    LOW = "LOW"
    AVERAGE = "AVERAGE"
    HIGH = "HIGH"
    ULTRA_HIGH = "ULTRA_HIGH"


class SpreadState(str, Enum):
    """3-state spread classification via SpreadRel = spread / SMA(spread, M)."""

    NARROW = "NARROW"
    NORMAL = "NORMAL"
    WIDE = "WIDE"


class CandleType(str, Enum):
    """Direction of the candle based on close vs open."""

    UP = "UP"
    DOWN = "DOWN"


class Trend(str, Enum):
    """Trend direction from context engine."""

    UP = "UP"
    DOWN = "DOWN"
    RANGE = "RANGE"
    UNKNOWN = "UNKNOWN"


class TrendStrength(str, Enum):
    """Strength of the detected trend."""

    WEAK = "WEAK"
    MODERATE = "MODERATE"
    STRONG = "STRONG"


class TrendLocation(str, Enum):
    """Where price is relative to recent structure."""

    TOP = "TOP"
    BOTTOM = "BOTTOM"
    MIDDLE = "MIDDLE"
    UNKNOWN = "UNKNOWN"


class VolumeTrend(str, Enum):
    """Volume trend direction over a lookback window."""

    RISING = "RISING"
    FALLING = "FALLING"
    FLAT = "FLAT"
    UNKNOWN = "UNKNOWN"


class DominantAlignment(str, Enum):
    """Alignment of trade direction with dominant (slower) timeframe trend."""

    WITH = "WITH"
    AGAINST = "AGAINST"
    UNKNOWN = "UNKNOWN"


class SignalClass(str, Enum):
    """Classification of a signal event."""

    VALIDATION = "VALIDATION"
    ANOMALY = "ANOMALY"
    STRENGTH = "STRENGTH"
    WEAKNESS = "WEAKNESS"
    AVOIDANCE = "AVOIDANCE"
    CONFIRMATION = "CONFIRMATION"
    TEST = "TEST"


class TradeIntentStatus(str, Enum):
    """Status of a trade intent from setup composer + risk engine."""

    READY = "READY"
    PENDING_CONFIRM = "PENDING_CONFIRM"
    REJECTED = "REJECTED"


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


# ---------------------------------------------------------------------------
# Canonical data models (VPA_SYSTEM_SPEC §3.3)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CandleFeatures:
    """Computed features for a single bar. Output of Feature Engine (stage 2).

    Per VPA_SYSTEM_SPEC §3.3 — CandleFeatures.
    """

    ts: datetime
    tf: str
    spread: float          # |close - open| (body)
    range: float           # high - low
    upper_wick: float      # high - max(open, close)
    lower_wick: float      # min(open, close) - low
    spread_rel: float      # spread / SMA(spread, M)
    vol_rel: float         # volume / SMA(volume, N)
    vol_state: VolumeState
    spread_state: SpreadState
    candle_type: CandleType


@dataclass(frozen=True)
class Congestion:
    """Congestion/range zone within a ContextSnapshot."""

    active: bool
    range_high: float | None = None
    range_low: float | None = None


@dataclass(frozen=True)
class ContextSnapshot:
    """Context for a timeframe at a point in time. Output of Context Engine (stage 4).

    Per VPA_SYSTEM_SPEC §3.3 — ContextSnapshot.
    """

    tf: str
    trend: Trend
    trend_strength: TrendStrength
    trend_location: TrendLocation
    congestion: Congestion
    dominant_alignment: DominantAlignment = DominantAlignment.UNKNOWN
    volume_trend: VolumeTrend = VolumeTrend.UNKNOWN


@dataclass(frozen=True)
class SignalEvent:
    """Atomic signal emitted by Rule Engine (stage 5). No orders, no sizing.

    Per VPA_SYSTEM_SPEC §3.3 — SignalEvent.
    """

    id: str                        # rule ID, e.g. "ANOM-1"
    name: str                      # human-readable, e.g. "BigResultLittleEffort_TrapUpWarning"
    tf: str                        # timeframe
    ts: datetime                   # bar timestamp
    signal_class: SignalClass      # VALIDATION, ANOMALY, etc.
    direction_bias: str            # e.g. "BULLISH", "BEARISH_OR_WAIT"
    priority: int = 1
    evidence: dict[str, Any] = field(default_factory=dict)
    requires_context_gate: bool = False


@dataclass(frozen=True)
class EntryPlan:
    """Entry timing and order type within a TradeIntent."""

    timing: str = "NEXT_BAR_OPEN"  # per config: execution.entry_timing
    order_type: str = "MARKET"


@dataclass(frozen=True)
class RiskPlan:
    """Stop, size, and risk parameters within a TradeIntent."""

    stop: float
    risk_pct: float
    size: int


@dataclass(frozen=True)
class TradeIntent:
    """Output of Risk Engine (stage 8). Approved or rejected trade candidate.

    Per VPA_SYSTEM_SPEC §3.3 — TradeIntent.
    """

    intent_id: str
    direction: str                 # "LONG" | "SHORT"
    tf: str
    setup: str                     # setup ID, e.g. "ENTRY-LONG-1"
    status: TradeIntentStatus
    entry_plan: EntryPlan
    risk_plan: RiskPlan
    rationale: list[str] = field(default_factory=list)  # chain of signal IDs + gate results
    reject_reason: str | None = None


# ---------------------------------------------------------------------------
# Legacy models (kept for backward compat with existing pipeline)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Signal:
    """DEPRECATED: Use SignalEvent for new code.

    Output of setup matching: one per detected VPA setup.
    """

    setup_type: str
    direction: str  # "long" | "short"
    bar_index: int
    timestamp: datetime
    rationale: str
    rulebook_ref: str
    strength: str | None = None


@dataclass(frozen=True)
class TradePlan:
    """DEPRECATED: Use TradeIntent for new code.

    Trading intent from a signal; execution layer converts to orders.
    """

    signal_id: str
    setup_type: str
    direction: str  # "long" | "short"
    entry_condition: str | dict[str, Any]
    stop_level: float | str
    invalidation_rules: list[str] | str
    rationale: str
    rulebook_ref: str
    target_logic: str | None = None
