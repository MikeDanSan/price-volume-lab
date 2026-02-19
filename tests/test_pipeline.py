"""Integration tests: synthetic bars through the full VPA pipeline.

Includes multi-timeframe tests with daily_context parameter.
"""

from datetime import datetime, timezone, timedelta
from pathlib import Path

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
    """Produce a neutral up bar with avg volume ~100_000 and spread ~1.0."""
    ts = BASE_TS + timedelta(minutes=15 * i)
    return Bar(
        timestamp=ts, open=100.0, high=102.0, low=99.0,
        close=101.0, volume=100_000, symbol="TEST",
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
            close=107.0, volume=250_000, symbol="TEST",
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
            close=107.0, volume=1_000, symbol="TEST",
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
            close=107.0, volume=250_000, symbol="TEST",
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
            close=107.0, volume=250_000, symbol="TEST",
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
            close=107.0, volume=250_000, symbol="TEST",
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
            open=100.0, high=108.0, low=99.0, close=107.0, volume=250_000, symbol="TEST",
        ))
        composer = SetupComposer(cfg)
        result = run_pipeline(bars, bar_index=20, context=_context(),
                              account=_account(), config=cfg, composer=composer)
        with pytest.raises(AttributeError):
            result.bar_index = 99  # type: ignore[misc]


# ---------------------------------------------------------------------------
# 4. Low-liquidity volume guard
# ---------------------------------------------------------------------------


def _low_volume_bar(i: int) -> Bar:
    """Produce a bar with very low volume (simulates holiday thin trading)."""
    ts = BASE_TS + timedelta(minutes=15 * i)
    return Bar(
        timestamp=ts, open=100.0, high=102.0, low=99.0,
        close=101.0, volume=50, symbol="TEST",
    )


def _cfg_with_volume_guard(tmp_path: Path, *, enabled: bool, min_avg: int) -> VPAConfig:
    """Load config with a specific volume_guard setting."""
    import json
    from config.vpa_config import DEFAULT_CONFIG_PATH
    with open(DEFAULT_CONFIG_PATH) as f:
        data = json.load(f)
    data["volume_guard"] = {"enabled": enabled, "min_avg_volume": min_avg}
    p = tmp_path / "vol_guard_cfg.json"
    p.write_text(json.dumps(data))
    return load_vpa_config(config_path=p)


class TestVolumeGuard:
    """Pipeline skips evaluation when average volume < min_avg_volume."""

    def test_low_volume_blocks_signals(self, tmp_path: Path) -> None:
        """Thin-volume bars should produce no signals even if shape triggers rules."""
        cfg = _cfg_with_volume_guard(tmp_path, enabled=True, min_avg=10_000)
        bars = [_low_volume_bar(i) for i in range(20)]
        bars.append(Bar(
            timestamp=BASE_TS + timedelta(minutes=15 * 20),
            open=100.0, high=108.0, low=99.0,
            close=107.0, volume=125, symbol="TEST",
        ))
        composer = SetupComposer(cfg)
        result = run_pipeline(bars, bar_index=20, context=_context(),
                              account=_account(), config=cfg, composer=composer)
        assert result.features is not None
        assert result.signals == []
        assert result.intents == []

    def test_normal_volume_passes(self, tmp_path: Path) -> None:
        """Bars above the threshold produce signals normally."""
        cfg = _cfg_with_volume_guard(tmp_path, enabled=True, min_avg=10_000)
        bars = _baseline_bars(20)
        bars.append(Bar(
            timestamp=BASE_TS + timedelta(minutes=15 * 20),
            open=100.0, high=108.0, low=99.0,
            close=107.0, volume=250_000, symbol="TEST",
        ))
        composer = SetupComposer(cfg)
        result = run_pipeline(bars, bar_index=20, context=_context(),
                              account=_account(), config=cfg, composer=composer)
        assert len(result.signals) >= 1

    def test_guard_disabled_allows_low_volume(self, tmp_path: Path) -> None:
        """When guard is disabled, low volume bars still get evaluated."""
        cfg = _cfg_with_volume_guard(tmp_path, enabled=False, min_avg=10_000)
        bars = [_low_volume_bar(i) for i in range(20)]
        bars.append(Bar(
            timestamp=BASE_TS + timedelta(minutes=15 * 20),
            open=100.0, high=108.0, low=99.0,
            close=107.0, volume=125, symbol="TEST",
        ))
        composer = SetupComposer(cfg)
        result = run_pipeline(bars, bar_index=20, context=_context(),
                              account=_account(), config=cfg, composer=composer)
        assert len(result.signals) >= 1

    def test_features_still_computed_when_guarded(self, tmp_path: Path) -> None:
        """Even when guard trips, features are computed (for journaling/diagnostics)."""
        cfg = _cfg_with_volume_guard(tmp_path, enabled=True, min_avg=10_000)
        bars = [_low_volume_bar(i) for i in range(20)]
        composer = SetupComposer(cfg)
        result = run_pipeline(bars, bar_index=19, context=_context(),
                              account=_account(), config=cfg, composer=composer)
        assert result.features is not None
        assert result.features.vol_rel > 0

    def test_guard_threshold_boundary(self, tmp_path: Path) -> None:
        """Average volume exactly at threshold should pass."""
        cfg = _cfg_with_volume_guard(tmp_path, enabled=True, min_avg=100_000)
        bars = _baseline_bars(20)
        composer = SetupComposer(cfg)
        result = run_pipeline(bars, bar_index=19, context=_context(),
                              account=_account(), config=cfg, composer=composer)
        assert result.gate_result is not None


# ---------------------------------------------------------------------------
# 5. Multi-timeframe: daily_context parameter
# ---------------------------------------------------------------------------


def _daily_ctx(trend: Trend = Trend.UP) -> ContextSnapshot:
    return ContextSnapshot(
        tf="1d", trend=trend, trend_strength=TrendStrength.MODERATE,
        trend_location=TrendLocation.MIDDLE, congestion=Congestion(active=False),
    )


def _cfg_with_disallow_policy(tmp_path: Path) -> VPAConfig:
    """Load config with ctx2_dominant_alignment_policy = DISALLOW."""
    import json
    from config.vpa_config import DEFAULT_CONFIG_PATH
    with open(DEFAULT_CONFIG_PATH) as f:
        data = json.load(f)
    data["gates"]["ctx2_dominant_alignment_policy"] = "DISALLOW"
    p = tmp_path / "disallow_cfg.json"
    p.write_text(json.dumps(data))
    return load_vpa_config(config_path=p)


class TestMultiTimeframe:
    """Pipeline with daily_context for multi-timeframe dominant alignment."""

    def test_no_daily_context_unchanged(self, cfg: VPAConfig) -> None:
        """Without daily_context, pipeline behaves exactly as before."""
        bars = _baseline_bars(20)
        bars.append(Bar(
            timestamp=BASE_TS + timedelta(minutes=15 * 20),
            open=100.0, high=108.0, low=99.0,
            close=107.0, volume=250_000, symbol="TEST",
        ))
        composer = SetupComposer(cfg)
        result = run_pipeline(bars, bar_index=20, context=_context(),
                              account=_account(), config=cfg, composer=composer)
        assert len(result.signals) >= 1
        assert result.gate_result is not None

    def test_daily_up_passes_bullish_signal(self, tmp_path: Path) -> None:
        """Bullish VAL-1 + daily UP → WITH → passes CTX-2 DISALLOW."""
        cfg = _cfg_with_disallow_policy(tmp_path)
        bars = _baseline_bars(20)
        bars.append(Bar(
            timestamp=BASE_TS + timedelta(minutes=15 * 20),
            open=100.0, high=108.0, low=99.0,
            close=107.0, volume=250_000, symbol="TEST",
        ))
        composer = SetupComposer(cfg)
        ctx = _context(alignment=DominantAlignment.UNKNOWN)
        daily = _daily_ctx(Trend.UP)
        result = run_pipeline(bars, bar_index=20, context=ctx,
                              account=_account(), config=cfg, composer=composer,
                              daily_context=daily)

        bullish_signals = [s for s in result.signals if "BULLISH" in s.direction_bias]
        bullish_actionable = [s for s in result.gate_result.actionable
                              if "BULLISH" in s.direction_bias]
        assert len(bullish_signals) >= 1
        assert len(bullish_actionable) >= 1

    def test_daily_up_blocks_bearish_gated_signal(self, tmp_path: Path) -> None:
        """ANOM-1 (BEARISH, gated) + daily UP → AGAINST → blocked by DISALLOW.

        Wide-spread low-volume bar triggers ANOM-1 (direction_bias=BEARISH_OR_WAIT,
        requires_context_gate=True). Daily trend is UP, so BEARISH is AGAINST.
        """
        cfg = _cfg_with_disallow_policy(tmp_path)
        bars = _baseline_bars(20)
        bars.append(Bar(
            timestamp=BASE_TS + timedelta(minutes=15 * 20),
            open=100.0, high=108.0, low=99.0,
            close=107.0, volume=1_000, symbol="TEST",
        ))
        composer = SetupComposer(cfg)
        ctx = _context(alignment=DominantAlignment.UNKNOWN)
        daily = _daily_ctx(Trend.UP)
        result = run_pipeline(bars, bar_index=20, context=ctx,
                              account=_account(), config=cfg, composer=composer,
                              daily_context=daily)

        gated_bearish = [s for s in result.signals
                         if s.requires_context_gate and "BEARISH" in s.direction_bias]
        assert len(gated_bearish) >= 1
        blocked_bearish = [s for s in result.gate_result.blocked
                           if "BEARISH" in s.direction_bias]
        assert len(blocked_bearish) >= 1
        assert any("CTX-2" in r for r in result.gate_result.block_reasons.values())

    def test_daily_context_does_not_affect_reduce_risk_policy(self, cfg: VPAConfig) -> None:
        """Default REDUCE_RISK policy passes all signals regardless of daily trend."""
        bars = _baseline_bars(20)
        bars.append(Bar(
            timestamp=BASE_TS + timedelta(minutes=15 * 20),
            open=100.0, high=108.0, low=99.0,
            close=107.0, volume=250_000, symbol="TEST",
        ))
        composer = SetupComposer(cfg)
        ctx = _context(alignment=DominantAlignment.UNKNOWN)
        daily = _daily_ctx(Trend.DOWN)
        result = run_pipeline(bars, bar_index=20, context=ctx,
                              account=_account(), config=cfg, composer=composer,
                              daily_context=daily)

        assert len(result.gate_result.blocked) == 0
