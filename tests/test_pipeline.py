"""Integration tests: synthetic bars through the full VPA pipeline."""

from datetime import datetime, timezone, timedelta

import pytest

from config.vpa_config import load_vpa_config, VPAConfig
from vpa_core.contracts import (
    Bar,
    CandleFeatures,
    CandleType,
    Congestion,
    ContextSnapshot,
    DominantAlignment,
    SignalClass,
    SignalEvent,
    SpreadState,
    TradeIntent,
    TradeIntentStatus,
    Trend,
    TrendLocation,
    TrendStrength,
    VolumeState,
)
from vpa_core.pipeline import PipelineResult, run_pipeline
from vpa_core.risk_engine import AccountState
from vpa_core.setup_composer import SetupComposer, SetupCandidate, SetupMatch, SetupState


BASE_TS = datetime(2026, 2, 17, 9, 30, tzinfo=timezone.utc)


@pytest.fixture()
def cfg() -> VPAConfig:
    return load_vpa_config()


def _context(
    location: TrendLocation = TrendLocation.BOTTOM,
    alignment: DominantAlignment = DominantAlignment.WITH,
) -> ContextSnapshot:
    return ContextSnapshot(
        tf="15m", trend=Trend.UP, trend_strength=TrendStrength.MODERATE,
        trend_location=location, congestion=Congestion(active=False),
        dominant_alignment=alignment,
    )


def _account() -> AccountState:
    return AccountState(equity=100_000.0)


def _baseline_bar(i: int) -> Bar:
    """Produce a neutral up bar with avg volume ~1000 and spread ~1.0."""
    ts = BASE_TS + timedelta(minutes=15 * i)
    return Bar(
        timestamp=ts, open=100.0, high=102.0, low=99.0,
        close=101.0, volume=1000, symbol="TEST",
    )


def _baseline_bars(count: int = 20) -> list[Bar]:
    return [_baseline_bar(i) for i in range(count)]


# ---------------------------------------------------------------------------
# 1. VAL-1 fires and passes gates (no setup match yet)
# ---------------------------------------------------------------------------


class TestPartialPipeline:
    """Bars that trigger rule signals but don't complete a full setup."""

    def test_val_1_signal_no_setup(self, cfg: VPAConfig) -> None:
        """A wide up bar on ultra-high volume fires VAL-1 but without a
        prior TEST-SUP-1 the setup composer has nothing to match."""
        bars = _baseline_bars(20)
        signal_bar = Bar(
            timestamp=BASE_TS + timedelta(minutes=15 * 20),
            open=100.0, high=108.0, low=99.0,
            close=107.0, volume=2500, symbol="TEST",
        )
        bars.append(signal_bar)

        composer = SetupComposer(cfg)
        result = run_pipeline(bars, bar_index=20, context=_context(),
                              account=_account(), config=cfg, composer=composer)

        assert result.features is not None
        assert result.features.candle_type == CandleType.UP
        assert result.features.vol_state in (VolumeState.HIGH, VolumeState.ULTRA_HIGH)
        assert result.features.spread_state == SpreadState.WIDE

        signal_ids = {s.id for s in result.signals}
        assert "VAL-1" in signal_ids

        assert result.gate_result is not None
        assert any(s.id == "VAL-1" for s in result.gate_result.actionable)
        assert len(result.gate_result.blocked) == 0

        assert result.matches == []
        assert result.intents == []

    def test_anom_1_blocked_by_gate(self, cfg: VPAConfig) -> None:
        """Wide up bar on low volume fires ANOM-1, but CTX-1 blocks it
        when trend location is UNKNOWN."""
        bars = _baseline_bars(20)
        signal_bar = Bar(
            timestamp=BASE_TS + timedelta(minutes=15 * 20),
            open=100.0, high=108.0, low=99.0,
            close=107.0, volume=100, symbol="TEST",
        )
        bars.append(signal_bar)

        composer = SetupComposer(cfg)
        ctx = _context(location=TrendLocation.UNKNOWN)
        result = run_pipeline(bars, bar_index=20, context=ctx,
                              account=_account(), config=cfg, composer=composer)

        assert len(result.signals) == 1
        assert result.signals[0].id == "ANOM-1"

        assert len(result.gate_result.blocked) == 1
        assert len(result.gate_result.actionable) == 0

        assert result.matches == []
        assert result.intents == []

    def test_empty_bars_returns_empty_result(self, cfg: VPAConfig) -> None:
        composer = SetupComposer(cfg)
        result = run_pipeline([], bar_index=0, context=_context(),
                              account=_account(), config=cfg, composer=composer)
        assert result.features is None
        assert result.signals == []
        assert result.intents == []


# ---------------------------------------------------------------------------
# 2. Full pipeline: pre-seeded composer -> TradeIntent
# ---------------------------------------------------------------------------


class TestFullPipeline:
    """Pre-seed the composer with a TEST-SUP-1 candidate, then feed a bar
    that triggers VAL-1 to complete ENTRY-LONG-1 and produce a TradeIntent."""

    def _seed_composer(self, cfg: VPAConfig) -> SetupComposer:
        """Create a composer with an active ENTRY-LONG-1 candidate
        (as if TEST-SUP-1 was seen at bar 18)."""
        composer = SetupComposer(cfg)
        test_signal = SignalEvent(
            id="TEST-SUP-1", name="TestSupport", tf="15m",
            ts=BASE_TS + timedelta(minutes=15 * 18),
            signal_class=SignalClass.TEST, direction_bias="BULLISH",
            evidence={"bar_low": 98.5},
        )
        composer._candidates.append(SetupCandidate(
            setup_id="ENTRY-LONG-1",
            direction="LONG",
            state=SetupState.CANDIDATE,
            signals=[test_signal],
            started_at_bar=18,
            expires_at_bar=18 + cfg.setup.window_X,
        ))
        return composer

    def test_full_flow_to_trade_intent(self, cfg: VPAConfig) -> None:
        bars = _baseline_bars(20)
        signal_bar = Bar(
            timestamp=BASE_TS + timedelta(minutes=15 * 20),
            open=100.0, high=108.0, low=99.0,
            close=107.0, volume=2500, symbol="TEST",
        )
        bars.append(signal_bar)

        composer = self._seed_composer(cfg)
        result = run_pipeline(bars, bar_index=20, context=_context(),
                              account=_account(), config=cfg, composer=composer)

        signal_ids = {s.id for s in result.signals}
        assert "VAL-1" in signal_ids

        assert len(result.matches) == 1
        assert result.matches[0].setup_id == "ENTRY-LONG-1"
        assert result.matches[0].direction == "LONG"

        assert len(result.intents) == 1
        intent = result.intents[0]
        assert intent.status == TradeIntentStatus.READY
        assert intent.setup == "ENTRY-LONG-1"
        assert intent.direction == "LONG"
        assert intent.risk_plan.stop == 98.5
        assert intent.risk_plan.size > 0
        assert intent.entry_plan.timing == "NEXT_BAR_OPEN"

    def test_full_flow_rejected_max_positions(self, cfg: VPAConfig) -> None:
        bars = _baseline_bars(20)
        signal_bar = Bar(
            timestamp=BASE_TS + timedelta(minutes=15 * 20),
            open=100.0, high=108.0, low=99.0,
            close=107.0, volume=2500, symbol="TEST",
        )
        bars.append(signal_bar)

        composer = self._seed_composer(cfg)
        account = AccountState(equity=100_000.0, open_position_count=1)
        result = run_pipeline(bars, bar_index=20, context=_context(),
                              account=account, config=cfg, composer=composer)

        assert len(result.intents) == 1
        assert result.intents[0].status == TradeIntentStatus.REJECTED
        assert "Max concurrent" in result.intents[0].reject_reason

    def test_countertrend_reduces_size(self, cfg: VPAConfig) -> None:
        bars = _baseline_bars(20)
        signal_bar = Bar(
            timestamp=BASE_TS + timedelta(minutes=15 * 20),
            open=100.0, high=108.0, low=99.0,
            close=107.0, volume=2500, symbol="TEST",
        )
        bars.append(signal_bar)

        composer_with = self._seed_composer(cfg)
        result_with = run_pipeline(
            bars, bar_index=20, context=_context(alignment=DominantAlignment.WITH),
            account=_account(), config=cfg, composer=composer_with,
        )

        composer_against = self._seed_composer(cfg)
        result_against = run_pipeline(
            list(bars), bar_index=20,
            context=_context(alignment=DominantAlignment.AGAINST),
            account=_account(), config=cfg, composer=composer_against,
        )

        assert result_with.intents[0].risk_plan.size > result_against.intents[0].risk_plan.size


# ---------------------------------------------------------------------------
# 3. Multi-bar sequencing through the same composer
# ---------------------------------------------------------------------------


class TestMultiBarSequence:
    """Process multiple bars through the pipeline with a persistent composer."""

    def test_quiet_bars_produce_no_signals(self, cfg: VPAConfig) -> None:
        """20 neutral bars should produce no signals."""
        composer = SetupComposer(cfg)
        bars = _baseline_bars(20)

        for i in range(len(bars)):
            result = run_pipeline(
                bars[:i + 1], bar_index=i, context=_context(),
                account=_account(), config=cfg, composer=composer, tf="15m",
            )
            assert result.intents == []
        assert composer.active_candidates == 0

    def test_pipeline_result_is_frozen(self, cfg: VPAConfig) -> None:
        bars = _baseline_bars(20)
        bars.append(Bar(
            timestamp=BASE_TS + timedelta(minutes=15 * 20),
            open=100.0, high=108.0, low=99.0, close=107.0, volume=2500, symbol="TEST",
        ))
        composer = SetupComposer(cfg)
        result = run_pipeline(bars, bar_index=20, context=_context(),
                              account=_account(), config=cfg, composer=composer)
        with pytest.raises(AttributeError):
            result.bar_index = 99  # type: ignore[misc]
