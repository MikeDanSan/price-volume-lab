"""Tests for Setup Composer: ENTRY-LONG-1 sequence matching.

FXT-ENTRY-LONG-1-seq equivalent: TEST-SUP-1 -> VAL-1 within X bars.
"""

from datetime import datetime, timedelta, timezone

import pytest

from config.vpa_config import load_vpa_config, VPAConfig
from vpa_core.contracts import (
    Congestion,
    ContextSnapshot,
    SignalClass,
    SignalEvent,
    Trend,
    TrendLocation,
    TrendStrength,
)
from vpa_core.setup_composer import SetupComposer, SetupMatch, SetupState


TS = datetime(2026, 2, 17, 14, 30, tzinfo=timezone.utc)


@pytest.fixture()
def cfg() -> VPAConfig:
    return load_vpa_config()


@pytest.fixture()
def composer(cfg: VPAConfig) -> SetupComposer:
    return SetupComposer(cfg)


def _context() -> ContextSnapshot:
    return ContextSnapshot(
        tf="15m",
        trend=Trend.UP,
        trend_strength=TrendStrength.MODERATE,
        trend_location=TrendLocation.BOTTOM,
        congestion=Congestion(active=False),
    )


def _test_sup_1(bar_offset: int = 0) -> SignalEvent:
    return SignalEvent(
        id="TEST-SUP-1",
        name="SupplyRemovedTestPass",
        tf="15m",
        ts=TS + timedelta(minutes=bar_offset * 15),
        signal_class=SignalClass.TEST,
        direction_bias="BULLISH",
        priority=1,
        evidence={"vol_state": "LOW"},
        requires_context_gate=True,
    )


def _val_1(bar_offset: int = 0) -> SignalEvent:
    return SignalEvent(
        id="VAL-1",
        name="SingleBarValidation_BullishDrive",
        tf="15m",
        ts=TS + timedelta(minutes=bar_offset * 15),
        signal_class=SignalClass.VALIDATION,
        direction_bias="BULLISH",
        priority=1,
        evidence={"vol_state": "HIGH", "spread_state": "WIDE"},
        requires_context_gate=False,
    )


def _anom_high_priority(bar_offset: int = 0) -> SignalEvent:
    return SignalEvent(
        id="ANOM-1",
        name="BigResultLittleEffort_TrapUpWarning",
        tf="15m",
        ts=TS + timedelta(minutes=bar_offset * 15),
        signal_class=SignalClass.ANOMALY,
        direction_bias="BEARISH_OR_WAIT",
        priority=2,
        evidence={},
        requires_context_gate=True,
    )


# ---------------------------------------------------------------------------
# ENTRY-LONG-1: complete sequence
# ---------------------------------------------------------------------------


class TestEntryLong1Complete:
    """TEST-SUP-1 on bar N, VAL-1 on bar N+k (k <= window_X) -> READY."""

    def test_immediate_follow(self, composer: SetupComposer) -> None:
        """TEST-SUP-1 bar 0, VAL-1 bar 1 -> match on bar 1."""
        ctx = _context()
        composer.process_signals([_test_sup_1()], bar_index=0, context=ctx)
        assert composer.active_candidates == 1

        matches = composer.process_signals([_val_1(1)], bar_index=1, context=ctx)
        assert len(matches) == 1
        assert matches[0].setup_id == "ENTRY-LONG-1"
        assert matches[0].direction == "LONG"
        assert len(matches[0].signals) == 2
        assert matches[0].signals[0].id == "TEST-SUP-1"
        assert matches[0].signals[1].id == "VAL-1"
        assert matches[0].matched_at_bar == 1

    def test_delayed_follow_within_window(self, composer: SetupComposer, cfg: VPAConfig) -> None:
        """VAL-1 arrives on the last allowed bar."""
        ctx = _context()
        window = cfg.setup.window_X  # 5
        composer.process_signals([_test_sup_1()], bar_index=0, context=ctx)

        for i in range(1, window):
            matches = composer.process_signals([], bar_index=i, context=ctx)
            assert matches == []

        matches = composer.process_signals([_val_1(window)], bar_index=window, context=ctx)
        assert len(matches) == 1
        assert matches[0].setup_id == "ENTRY-LONG-1"

    def test_match_is_frozen(self, composer: SetupComposer) -> None:
        ctx = _context()
        composer.process_signals([_test_sup_1()], bar_index=0, context=ctx)
        matches = composer.process_signals([_val_1(1)], bar_index=1, context=ctx)
        with pytest.raises(AttributeError):
            matches[0].setup_id = "HACKED"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Expiration
# ---------------------------------------------------------------------------


class TestExpiration:
    def test_expired_after_window(self, composer: SetupComposer, cfg: VPAConfig) -> None:
        """VAL-1 arrives one bar too late -> no match."""
        ctx = _context()
        window = cfg.setup.window_X  # 5
        composer.process_signals([_test_sup_1()], bar_index=0, context=ctx)

        for i in range(1, window + 1):
            composer.process_signals([], bar_index=i, context=ctx)

        matches = composer.process_signals([_val_1(window + 1)], bar_index=window + 1, context=ctx)
        assert matches == []
        assert composer.active_candidates == 0


# ---------------------------------------------------------------------------
# Invalidation
# ---------------------------------------------------------------------------


class TestInvalidation:
    def test_opposing_anomaly_invalidates_candidate(self, composer: SetupComposer) -> None:
        """High-priority anomaly on bar 1 invalidates the LONG candidate."""
        ctx = _context()
        composer.process_signals([_test_sup_1()], bar_index=0, context=ctx)
        assert composer.active_candidates == 1

        matches = composer.process_signals([_anom_high_priority(1)], bar_index=1, context=ctx)
        assert matches == []
        assert composer.active_candidates == 0


# ---------------------------------------------------------------------------
# No-signal bars
# ---------------------------------------------------------------------------


class TestNoSignals:
    def test_no_signals_no_candidates(self, composer: SetupComposer) -> None:
        ctx = _context()
        matches = composer.process_signals([], bar_index=0, context=ctx)
        assert matches == []
        assert composer.active_candidates == 0

    def test_val_1_without_prior_test_does_nothing(self, composer: SetupComposer) -> None:
        """VAL-1 alone doesn't start or complete a setup."""
        ctx = _context()
        matches = composer.process_signals([_val_1()], bar_index=0, context=ctx)
        assert matches == []
        assert composer.active_candidates == 0


# ---------------------------------------------------------------------------
# Duplicate prevention
# ---------------------------------------------------------------------------


class TestDuplicates:
    def test_second_test_sup_1_does_not_duplicate(self, composer: SetupComposer) -> None:
        """Only one ENTRY-LONG-1 candidate active at a time."""
        ctx = _context()
        composer.process_signals([_test_sup_1()], bar_index=0, context=ctx)
        composer.process_signals([_test_sup_1(1)], bar_index=1, context=ctx)
        assert composer.active_candidates == 1
