"""
Setup Composer: match signal sequences into trade setups.

Stateful stage that tracks active candidates across bar evaluations.
When a sequence completes, it emits a SetupMatch for the Risk Engine.

**Separation contract:** No sizing, no stop calculation, no orders.
This stage only matches sequences and tracks state.

Currently implemented:
    ENTRY-LONG-1: TEST-SUP-1 -> VAL-1 within X bars.
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
    # ENTRY-LONG-1: TEST-SUP-1 -> VAL-1 within X bars
    # ------------------------------------------------------------------

    def _open_new_candidates(self, signals: list[SignalEvent], bar_index: int) -> None:
        """Start new ENTRY-LONG-1 candidates from TEST-SUP-1 signals."""
        for sig in signals:
            if sig.id == "TEST-SUP-1":
                already_tracking = any(
                    c.setup_id == "ENTRY-LONG-1" and c.state == SetupState.CANDIDATE
                    for c in self._candidates
                )
                if not already_tracking:
                    self._candidates.append(SetupCandidate(
                        setup_id="ENTRY-LONG-1",
                        direction="LONG",
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
            if candidate.setup_id == "ENTRY-LONG-1":
                for sig in signals:
                    if sig.id == "VAL-1":
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

    def _invalidate_candidates(self, signals: list[SignalEvent]) -> None:
        """Invalidate candidates if opposing high-priority anomaly appears."""
        has_opposing_anomaly = any(
            sig.signal_class == SignalClass.ANOMALY and sig.priority >= 2
            for sig in signals
        )
        if has_opposing_anomaly:
            for candidate in self._candidates:
                if candidate.state == SetupState.CANDIDATE and candidate.direction == "LONG":
                    candidate.state = SetupState.INVALIDATED
            self._candidates = [c for c in self._candidates if c.state == SetupState.CANDIDATE]

    @property
    def active_candidates(self) -> int:
        """Number of currently active (CANDIDATE state) setups being tracked."""
        return sum(1 for c in self._candidates if c.state == SetupState.CANDIDATE)
