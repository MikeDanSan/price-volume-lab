"""
Setup Composer: match signal sequences into trade setups.

Stateful stage that tracks active candidates across bar evaluations.
When a sequence completes, it emits a SetupMatch for the Risk Engine.

**Separation contract:** No sizing, no stop calculation, no orders.
This stage only matches sequences and tracks state.

Currently implemented:
    ENTRY-LONG-1:  TEST-SUP-1 -> VAL-1 within X bars.
    ENTRY-LONG-2:  STR-1 -> CONF-1 within X bars (hammer + confirmation).
    ENTRY-SHORT-1: CLIMAX-SELL-1 -> WEAK-1|WEAK-2 within X bars.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from config.vpa_config import VPAConfig
from vpa_core.contracts import ContextSnapshot, SignalClass, SignalEvent


class SetupState(str, Enum):
    INACTIVE = "INACTIVE"
    CANDIDATE = "CANDIDATE"
    READY = "READY"
    INVALIDATED = "INVALIDATED"
    EXPIRED = "EXPIRED"


@dataclass
class SetupCandidate:
    """Tracks an in-progress setup sequence."""
    setup_id: str
    direction: str
    state: SetupState
    signals: list[SignalEvent] = field(default_factory=list)
    started_at_bar: int = 0
    expires_at_bar: int = 0


@dataclass(frozen=True)
class SetupMatch:
    """A completed setup sequence ready for the risk engine.

    No sizing, no stops — just the match result and the evidence chain.
    """
    setup_id: str
    direction: str
    signals: list[SignalEvent]
    matched_at_bar: int
    tf: str


class SetupComposer:
    """Stateful setup sequence matcher.

    Call ``process_signals`` once per bar with that bar's actionable signals.
    Returns any setups that completed on this bar.
    """

    def __init__(self, config: VPAConfig) -> None:
        self._config = config
        self._window_x = config.setup.window_X
        self._candidates: list[SetupCandidate] = []

    def process_signals(
        self,
        signals: list[SignalEvent],
        bar_index: int,
        context: ContextSnapshot,
    ) -> list[SetupMatch]:
        """Process one bar's worth of actionable signals.

        Parameters
        ----------
        signals:
            Actionable signals (already passed through context gates).
        bar_index:
            Sequential bar counter (monotonically increasing).
        context:
            Current ContextSnapshot (for future gate checks).

        Returns
        -------
        list[SetupMatch]
            Any setups that completed on this bar (usually 0 or 1).
        """
        self._expire_candidates(bar_index)
        self._invalidate_candidates(signals)

        matches: list[SetupMatch] = []

        matches.extend(self._check_completions(signals, bar_index))

        self._open_new_candidates(signals, bar_index)

        return matches

    # ------------------------------------------------------------------
    # Setup definitions (trigger signal -> completion signal)
    # ------------------------------------------------------------------

    _SETUP_DEFS: dict[str, dict] = {
        "ENTRY-LONG-1": {"trigger": "TEST-SUP-1", "completers": ["VAL-1"], "direction": "LONG"},
        "ENTRY-LONG-2": {"trigger": "STR-1", "completers": ["CONF-1"], "direction": "LONG"},
        "ENTRY-SHORT-1": {"trigger": "CLIMAX-SELL-1", "completers": ["WEAK-1", "WEAK-2"], "direction": "SHORT"},
    }

    def _open_new_candidates(self, signals: list[SignalEvent], bar_index: int) -> None:
        """Start new candidates when a trigger signal appears."""
        for sig in signals:
            for setup_id, defn in self._SETUP_DEFS.items():
                if sig.id == defn["trigger"]:
                    already_tracking = any(
                        c.setup_id == setup_id and c.state == SetupState.CANDIDATE
                        for c in self._candidates
                    )
                    if not already_tracking:
                        self._candidates.append(SetupCandidate(
                            setup_id=setup_id,
                            direction=defn["direction"],
                            state=SetupState.CANDIDATE,
                            signals=[sig],
                            started_at_bar=bar_index,
                            expires_at_bar=bar_index + self._window_x,
                        ))

    def _check_completions(self, signals: list[SignalEvent], bar_index: int) -> list[SetupMatch]:
        """Check if any active candidates complete with this bar's signals."""
        matches: list[SetupMatch] = []
        for candidate in self._candidates:
            if candidate.state != SetupState.CANDIDATE:
                continue
            defn = self._SETUP_DEFS.get(candidate.setup_id)
            if defn is None:
                continue
            completers = defn["completers"]
            for sig in signals:
                if sig.id in completers:
                    candidate.signals.append(sig)
                    candidate.state = SetupState.READY
                    matches.append(SetupMatch(
                        setup_id=candidate.setup_id,
                        direction=candidate.direction,
                        signals=list(candidate.signals),
                        matched_at_bar=bar_index,
                        tf=sig.tf,
                    ))
                    break
        return matches

    def _expire_candidates(self, bar_index: int) -> None:
        """Expire candidates that have exceeded their window."""
        for candidate in self._candidates:
            if candidate.state == SetupState.CANDIDATE and bar_index > candidate.expires_at_bar:
                candidate.state = SetupState.EXPIRED
        self._candidates = [c for c in self._candidates if c.state == SetupState.CANDIDATE]

    _HARD_AVOIDANCE = {"AVOID-NEWS-1"}

    def _invalidate_candidates(self, signals: list[SignalEvent]) -> None:
        """Invalidate candidates if opposing signals appear.

        LONG candidates invalidated by: high-priority anomalies or hard-block
        avoidance signals (e.g. AVOID-NEWS-1). Soft avoidance signals like
        AVOID-COUNTER-1 are handled by the risk engine (size reduction), not
        by setup invalidation.
        SHORT candidates invalidated by: strong bullish validation or strength.
        """
        should_invalidate_longs = any(
            (sig.signal_class == SignalClass.ANOMALY and sig.priority >= 2)
            or (sig.signal_class == SignalClass.AVOIDANCE and sig.id in self._HARD_AVOIDANCE)
            for sig in signals
        )
        should_invalidate_shorts = any(
            sig.signal_class == SignalClass.VALIDATION
            or sig.signal_class == SignalClass.STRENGTH
            for sig in signals
        )
        for candidate in self._candidates:
            if candidate.state != SetupState.CANDIDATE:
                continue
            if candidate.direction == "LONG" and should_invalidate_longs:
                candidate.state = SetupState.INVALIDATED
            elif candidate.direction == "SHORT" and should_invalidate_shorts:
                candidate.state = SetupState.INVALIDATED
        self._candidates = [c for c in self._candidates if c.state == SetupState.CANDIDATE]

    @property
    def active_candidates(self) -> int:
        """Number of currently active (CANDIDATE state) setups being tracked."""
        return sum(1 for c in self._candidates if c.state == SetupState.CANDIDATE)
