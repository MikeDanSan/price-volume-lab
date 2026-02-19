"""Tests for Context Gates: CTX-1, CTX-2, and CTX-3.

Includes per-signal dominant alignment via daily_context (multi-timeframe).
"""

from datetime import datetime, timezone

import pytest

from config.vpa_config import load_vpa_config, VPAConfig
from vpa_core.contracts import (
    Congestion,
    ContextSnapshot,
    DominantAlignment,
    SignalClass,
    SignalEvent,
    Trend,
    TrendLocation,
    TrendStrength,
)
from vpa_core.context_gates import GateResult, apply_gates


TS = datetime(2026, 2, 17, 14, 30, tzinfo=timezone.utc)


@pytest.fixture()
def cfg() -> VPAConfig:
    return load_vpa_config()


def _signal(
    *,
    rule_id: str = "ANOM-1",
    signal_class: SignalClass = SignalClass.ANOMALY,
    requires_gate: bool = True,
) -> SignalEvent:
    return SignalEvent(
        id=rule_id,
        name="TestSignal",
        tf="15m",
        ts=TS,
        signal_class=signal_class,
        direction_bias="BEARISH_OR_WAIT",
        priority=2,
        evidence={},
        requires_context_gate=requires_gate,
    )


def _context(
    *,
    trend_location: TrendLocation = TrendLocation.TOP,
    dominant_alignment: DominantAlignment = DominantAlignment.WITH,
    congestion: Congestion | None = None,
) -> ContextSnapshot:
    return ContextSnapshot(
        tf="15m",
        trend=Trend.UP,
        trend_strength=TrendStrength.MODERATE,
        trend_location=trend_location,
        congestion=congestion or Congestion(active=False),
        dominant_alignment=dominant_alignment,
    )


# ---------------------------------------------------------------------------
# CTX-1: anomaly + UNKNOWN location -> blocked
# ---------------------------------------------------------------------------


class TestCTX1:
    def test_anomaly_blocked_when_location_unknown(self, cfg: VPAConfig) -> None:
        signals = [_signal(requires_gate=True)]
        context = _context(trend_location=TrendLocation.UNKNOWN)
        result = apply_gates(signals, context, cfg)

        assert len(result.actionable) == 0
        assert len(result.blocked) == 1
        assert result.blocked[0].id == "ANOM-1"
        assert "CTX-1" in list(result.block_reasons.values())[0]

    def test_anomaly_passes_when_location_known_top(self, cfg: VPAConfig) -> None:
        signals = [_signal(requires_gate=True)]
        context = _context(trend_location=TrendLocation.TOP)
        result = apply_gates(signals, context, cfg)

        assert len(result.actionable) == 1
        assert len(result.blocked) == 0

    def test_anomaly_passes_when_location_known_bottom(self, cfg: VPAConfig) -> None:
        signals = [_signal(requires_gate=True)]
        context = _context(trend_location=TrendLocation.BOTTOM)
        result = apply_gates(signals, context, cfg)

        assert len(result.actionable) == 1
        assert len(result.blocked) == 0

    def test_anomaly_passes_when_location_known_middle(self, cfg: VPAConfig) -> None:
        signals = [_signal(requires_gate=True)]
        context = _context(trend_location=TrendLocation.MIDDLE)
        result = apply_gates(signals, context, cfg)

        assert len(result.actionable) == 1

    def test_validation_not_blocked_even_with_unknown_location(self, cfg: VPAConfig) -> None:
        """VAL-1 does not require context gate -> always passes."""
        signals = [_signal(rule_id="VAL-1", signal_class=SignalClass.VALIDATION, requires_gate=False)]
        context = _context(trend_location=TrendLocation.UNKNOWN)
        result = apply_gates(signals, context, cfg)

        assert len(result.actionable) == 1
        assert len(result.blocked) == 0


# ---------------------------------------------------------------------------
# Mixed signals
# ---------------------------------------------------------------------------


class TestMixedSignals:
    def test_mixed_batch_split_correctly(self, cfg: VPAConfig) -> None:
        """VAL-1 passes, ANOM-1 blocked when location UNKNOWN."""
        val = _signal(rule_id="VAL-1", signal_class=SignalClass.VALIDATION, requires_gate=False)
        anom = _signal(rule_id="ANOM-1", signal_class=SignalClass.ANOMALY, requires_gate=True)
        context = _context(trend_location=TrendLocation.UNKNOWN)

        result = apply_gates([val, anom], context, cfg)
        assert len(result.actionable) == 1
        assert result.actionable[0].id == "VAL-1"
        assert len(result.blocked) == 1
        assert result.blocked[0].id == "ANOM-1"

    def test_all_pass_when_location_known(self, cfg: VPAConfig) -> None:
        val = _signal(rule_id="VAL-1", signal_class=SignalClass.VALIDATION, requires_gate=False)
        anom = _signal(rule_id="ANOM-1", signal_class=SignalClass.ANOMALY, requires_gate=True)
        context = _context(trend_location=TrendLocation.TOP)

        result = apply_gates([val, anom], context, cfg)
        assert len(result.actionable) == 2
        assert len(result.blocked) == 0


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_empty_signals(self, cfg: VPAConfig) -> None:
        result = apply_gates([], _context(), cfg)
        assert result.actionable == []
        assert result.blocked == []

    def test_gate_disabled_in_config(self, tmp_path) -> None:
        """When ctx1_trend_location_required=false, nothing is blocked."""
        import json
        from config.vpa_config import load_vpa_config, DEFAULT_CONFIG_PATH

        with open(DEFAULT_CONFIG_PATH) as f:
            data = json.load(f)
        data["gates"]["ctx1_trend_location_required"] = False
        p = tmp_path / "no_gate.json"
        p.write_text(json.dumps(data))
        cfg = load_vpa_config(config_path=p)

        signals = [_signal(requires_gate=True)]
        context = _context(trend_location=TrendLocation.UNKNOWN)
        result = apply_gates(signals, context, cfg)

        assert len(result.actionable) == 1
        assert len(result.blocked) == 0

    def test_gate_result_is_frozen(self, cfg: VPAConfig) -> None:
        result = apply_gates([], _context(), cfg)
        with pytest.raises(AttributeError):
            result.actionable = []  # type: ignore[misc]


# ---------------------------------------------------------------------------
# CTX-2: dominant alignment gate
# ---------------------------------------------------------------------------


def _cfg_with_ctx2_policy(tmp_path, policy: str) -> VPAConfig:
    """Load config with a specific ctx2 policy."""
    import json
    from config.vpa_config import load_vpa_config, DEFAULT_CONFIG_PATH

    with open(DEFAULT_CONFIG_PATH) as f:
        data = json.load(f)
    data["gates"]["ctx2_dominant_alignment_policy"] = policy
    p = tmp_path / f"ctx2_{policy.lower()}.json"
    p.write_text(json.dumps(data))
    return load_vpa_config(config_path=p)


class TestCTX2Disallow:
    """When policy is DISALLOW, gated signals blocked if dominant_alignment == AGAINST."""

    def test_gated_signal_blocked_when_against(self, tmp_path) -> None:
        cfg = _cfg_with_ctx2_policy(tmp_path, "DISALLOW")
        signals = [_signal(requires_gate=True)]
        context = _context(dominant_alignment=DominantAlignment.AGAINST)
        result = apply_gates(signals, context, cfg)

        assert len(result.blocked) == 1
        assert len(result.actionable) == 0
        assert "CTX-2" in list(result.block_reasons.values())[0]

    def test_gated_signal_passes_when_with(self, tmp_path) -> None:
        cfg = _cfg_with_ctx2_policy(tmp_path, "DISALLOW")
        signals = [_signal(requires_gate=True)]
        context = _context(dominant_alignment=DominantAlignment.WITH)
        result = apply_gates(signals, context, cfg)

        assert len(result.actionable) == 1
        assert len(result.blocked) == 0

    def test_gated_signal_passes_when_unknown(self, tmp_path) -> None:
        cfg = _cfg_with_ctx2_policy(tmp_path, "DISALLOW")
        signals = [_signal(requires_gate=True)]
        context = _context(dominant_alignment=DominantAlignment.UNKNOWN)
        result = apply_gates(signals, context, cfg)

        assert len(result.actionable) == 1
        assert len(result.blocked) == 0

    def test_non_gated_signal_passes_even_when_against(self, tmp_path) -> None:
        cfg = _cfg_with_ctx2_policy(tmp_path, "DISALLOW")
        signals = [_signal(rule_id="VAL-1", signal_class=SignalClass.VALIDATION, requires_gate=False)]
        context = _context(dominant_alignment=DominantAlignment.AGAINST)
        result = apply_gates(signals, context, cfg)

        assert len(result.actionable) == 1
        assert len(result.blocked) == 0


class TestCTX2ReduceRisk:
    """When policy is REDUCE_RISK, gate passes all signals — Risk Engine handles sizing."""

    def test_against_signal_not_blocked(self, cfg: VPAConfig) -> None:
        """Default config policy is REDUCE_RISK."""
        assert cfg.gates.ctx2_dominant_alignment_policy == "REDUCE_RISK"
        signals = [_signal(requires_gate=True)]
        context = _context(dominant_alignment=DominantAlignment.AGAINST)
        result = apply_gates(signals, context, cfg)

        assert len(result.actionable) == 1
        assert len(result.blocked) == 0


class TestCTX2Allow:
    """When policy is ALLOW, gate passes all signals — CTX-2 fully disabled."""

    def test_against_signal_not_blocked(self, tmp_path) -> None:
        cfg = _cfg_with_ctx2_policy(tmp_path, "ALLOW")
        signals = [_signal(requires_gate=True)]
        context = _context(dominant_alignment=DominantAlignment.AGAINST)
        result = apply_gates(signals, context, cfg)

        assert len(result.actionable) == 1
        assert len(result.blocked) == 0


class TestCTX1AndCTX2Interaction:
    """Verify gate ordering: CTX-1 checked before CTX-2."""

    def test_ctx1_blocks_before_ctx2_checked(self, tmp_path) -> None:
        """If CTX-1 blocks (UNKNOWN location), CTX-2 reason doesn't appear."""
        cfg = _cfg_with_ctx2_policy(tmp_path, "DISALLOW")
        signals = [_signal(requires_gate=True)]
        context = _context(
            trend_location=TrendLocation.UNKNOWN,
            dominant_alignment=DominantAlignment.AGAINST,
        )
        result = apply_gates(signals, context, cfg)

        assert len(result.blocked) == 1
        reason = list(result.block_reasons.values())[0]
        assert "CTX-1" in reason

    def test_ctx2_blocks_when_ctx1_passes(self, tmp_path) -> None:
        """CTX-1 passes (known location), then CTX-2 blocks (DISALLOW + AGAINST)."""
        cfg = _cfg_with_ctx2_policy(tmp_path, "DISALLOW")
        signals = [_signal(requires_gate=True)]
        context = _context(
            trend_location=TrendLocation.TOP,
            dominant_alignment=DominantAlignment.AGAINST,
        )
        result = apply_gates(signals, context, cfg)

        assert len(result.blocked) == 1
        reason = list(result.block_reasons.values())[0]
        assert "CTX-2" in reason


# ---------------------------------------------------------------------------
# CTX-3: congestion awareness gate
# ---------------------------------------------------------------------------


CONGESTION_ACTIVE = Congestion(active=True, range_high=102.0, range_low=98.0)


class TestCTX3:
    """CTX-3 blocks anomaly signals inside congestion zones."""

    def test_anomaly_blocked_in_congestion(self, cfg: VPAConfig) -> None:
        assert cfg.gates.ctx3_congestion_awareness_required is True
        signals = [_signal(rule_id="ANOM-1", signal_class=SignalClass.ANOMALY, requires_gate=True)]
        context = _context(congestion=CONGESTION_ACTIVE)
        result = apply_gates(signals, context, cfg)

        assert len(result.blocked) == 1
        assert len(result.actionable) == 0
        assert "CTX-3" in list(result.block_reasons.values())[0]

    def test_anomaly_passes_when_no_congestion(self, cfg: VPAConfig) -> None:
        signals = [_signal(rule_id="ANOM-1", signal_class=SignalClass.ANOMALY, requires_gate=True)]
        context = _context(congestion=Congestion(active=False))
        result = apply_gates(signals, context, cfg)

        assert len(result.actionable) == 1
        assert len(result.blocked) == 0

    def test_validation_passes_in_congestion(self, cfg: VPAConfig) -> None:
        """VALIDATION (breakout candidate) not blocked by CTX-3."""
        signals = [_signal(rule_id="VAL-1", signal_class=SignalClass.VALIDATION, requires_gate=False)]
        context = _context(congestion=CONGESTION_ACTIVE)
        result = apply_gates(signals, context, cfg)

        assert len(result.actionable) == 1
        assert len(result.blocked) == 0

    def test_strength_passes_in_congestion(self, cfg: VPAConfig) -> None:
        """STRENGTH (hammer at range boundary) not blocked by CTX-3."""
        signals = [_signal(rule_id="STR-1", signal_class=SignalClass.STRENGTH, requires_gate=True)]
        context = _context(congestion=CONGESTION_ACTIVE)
        result = apply_gates(signals, context, cfg)

        assert len(result.actionable) == 1

    def test_weakness_passes_in_congestion(self, cfg: VPAConfig) -> None:
        """WEAKNESS (shooting star at range boundary) not blocked by CTX-3."""
        signals = [_signal(rule_id="WEAK-1", signal_class=SignalClass.WEAKNESS, requires_gate=True)]
        context = _context(congestion=CONGESTION_ACTIVE)
        result = apply_gates(signals, context, cfg)

        assert len(result.actionable) == 1

    def test_test_signal_passes_in_congestion(self, cfg: VPAConfig) -> None:
        """TEST (boundary probe) not blocked by CTX-3."""
        signals = [_signal(rule_id="TEST-SUP-1", signal_class=SignalClass.TEST, requires_gate=True)]
        context = _context(congestion=CONGESTION_ACTIVE)
        result = apply_gates(signals, context, cfg)

        assert len(result.actionable) == 1

    def test_non_gated_anomaly_passes_in_congestion(self, cfg: VPAConfig) -> None:
        """requires_context_gate=False bypasses CTX-3."""
        signals = [_signal(rule_id="ANOM-X", signal_class=SignalClass.ANOMALY, requires_gate=False)]
        context = _context(congestion=CONGESTION_ACTIVE)
        result = apply_gates(signals, context, cfg)

        assert len(result.actionable) == 1

    def test_mixed_signals_in_congestion(self, cfg: VPAConfig) -> None:
        """Anomaly blocked, validation and strength pass in congestion."""
        anom = _signal(rule_id="ANOM-1", signal_class=SignalClass.ANOMALY, requires_gate=True)
        val = _signal(rule_id="VAL-1", signal_class=SignalClass.VALIDATION, requires_gate=False)
        strn = _signal(rule_id="STR-1", signal_class=SignalClass.STRENGTH, requires_gate=True)
        context = _context(congestion=CONGESTION_ACTIVE)
        result = apply_gates([anom, val, strn], context, cfg)

        assert len(result.actionable) == 2
        assert {s.id for s in result.actionable} == {"VAL-1", "STR-1"}
        assert len(result.blocked) == 1
        assert result.blocked[0].id == "ANOM-1"


class TestCTX3Disabled:
    """When ctx3_congestion_awareness_required=false, CTX-3 is bypassed."""

    def test_anomaly_passes_when_gate_disabled(self, tmp_path) -> None:
        import json
        from config.vpa_config import load_vpa_config, DEFAULT_CONFIG_PATH

        with open(DEFAULT_CONFIG_PATH) as f:
            data = json.load(f)
        data["gates"]["ctx3_congestion_awareness_required"] = False
        p = tmp_path / "no_ctx3.json"
        p.write_text(json.dumps(data))
        cfg = load_vpa_config(config_path=p)

        signals = [_signal(rule_id="ANOM-1", signal_class=SignalClass.ANOMALY, requires_gate=True)]
        context = _context(congestion=CONGESTION_ACTIVE)
        result = apply_gates(signals, context, cfg)

        assert len(result.actionable) == 1
        assert len(result.blocked) == 0


class TestAllThreeGatesInteraction:
    """Verify full gate chain: CTX-1 → CTX-2 → CTX-3."""

    def test_ctx3_blocks_when_ctx1_and_ctx2_pass(self, cfg: VPAConfig) -> None:
        """Known location, WITH alignment, but in congestion → CTX-3 blocks anomaly."""
        signals = [_signal(rule_id="ANOM-2", signal_class=SignalClass.ANOMALY, requires_gate=True)]
        context = _context(
            trend_location=TrendLocation.TOP,
            dominant_alignment=DominantAlignment.WITH,
            congestion=CONGESTION_ACTIVE,
        )
        result = apply_gates(signals, context, cfg)

        assert len(result.blocked) == 1
        reason = list(result.block_reasons.values())[0]
        assert "CTX-3" in reason

    def test_ctx1_blocks_before_ctx3(self, cfg: VPAConfig) -> None:
        """UNKNOWN location + congestion: CTX-1 blocks first, not CTX-3."""
        signals = [_signal(rule_id="ANOM-1", signal_class=SignalClass.ANOMALY, requires_gate=True)]
        context = _context(
            trend_location=TrendLocation.UNKNOWN,
            congestion=CONGESTION_ACTIVE,
        )
        result = apply_gates(signals, context, cfg)

        assert len(result.blocked) == 1
        reason = list(result.block_reasons.values())[0]
        assert "CTX-1" in reason


# ---------------------------------------------------------------------------
# CTX-2 with daily_context (per-signal dominant alignment)
# ---------------------------------------------------------------------------


def _bullish_signal(*, requires_gate: bool = True) -> SignalEvent:
    return SignalEvent(
        id="VAL-1", name="Validation", tf="15m", ts=TS,
        signal_class=SignalClass.VALIDATION, direction_bias="BULLISH",
        requires_context_gate=requires_gate,
    )


def _bearish_signal(*, requires_gate: bool = True) -> SignalEvent:
    return SignalEvent(
        id="WEAK-1", name="Weakness", tf="15m", ts=TS,
        signal_class=SignalClass.WEAKNESS, direction_bias="BEARISH",
        requires_context_gate=requires_gate,
    )


def _daily_ctx(trend: Trend = Trend.UP) -> ContextSnapshot:
    return ContextSnapshot(
        tf="1d", trend=trend, trend_strength=TrendStrength.MODERATE,
        trend_location=TrendLocation.MIDDLE, congestion=Congestion(active=False),
    )


class TestCTX2WithDailyContext:
    """Per-signal alignment via daily_context parameter."""

    def test_bullish_with_daily_up_passes(self, tmp_path) -> None:
        """Bullish signal + daily UP → WITH → not blocked."""
        cfg = _cfg_with_ctx2_policy(tmp_path, "DISALLOW")
        context = _context(dominant_alignment=DominantAlignment.UNKNOWN)
        daily = _daily_ctx(Trend.UP)
        result = apply_gates([_bullish_signal()], context, cfg, daily_context=daily)

        assert len(result.actionable) == 1
        assert len(result.blocked) == 0

    def test_bullish_against_daily_down_blocked(self, tmp_path) -> None:
        """Bullish signal + daily DOWN → AGAINST → blocked by DISALLOW."""
        cfg = _cfg_with_ctx2_policy(tmp_path, "DISALLOW")
        context = _context(dominant_alignment=DominantAlignment.UNKNOWN)
        daily = _daily_ctx(Trend.DOWN)
        result = apply_gates([_bullish_signal()], context, cfg, daily_context=daily)

        assert len(result.blocked) == 1
        assert "CTX-2" in list(result.block_reasons.values())[0]

    def test_bearish_with_daily_down_passes(self, tmp_path) -> None:
        """Bearish signal + daily DOWN → WITH → not blocked."""
        cfg = _cfg_with_ctx2_policy(tmp_path, "DISALLOW")
        context = _context(dominant_alignment=DominantAlignment.UNKNOWN)
        daily = _daily_ctx(Trend.DOWN)
        result = apply_gates([_bearish_signal()], context, cfg, daily_context=daily)

        assert len(result.actionable) == 1

    def test_bearish_against_daily_up_blocked(self, tmp_path) -> None:
        """Bearish signal + daily UP → AGAINST → blocked."""
        cfg = _cfg_with_ctx2_policy(tmp_path, "DISALLOW")
        context = _context(dominant_alignment=DominantAlignment.UNKNOWN)
        daily = _daily_ctx(Trend.UP)
        result = apply_gates([_bearish_signal()], context, cfg, daily_context=daily)

        assert len(result.blocked) == 1
        assert "CTX-2" in list(result.block_reasons.values())[0]

    def test_mixed_signals_per_signal_alignment(self, tmp_path) -> None:
        """Bullish WITH + bearish AGAINST in same bar: bullish passes, bearish blocked."""
        cfg = _cfg_with_ctx2_policy(tmp_path, "DISALLOW")
        context = _context(dominant_alignment=DominantAlignment.UNKNOWN)
        daily = _daily_ctx(Trend.UP)
        signals = [_bullish_signal(), _bearish_signal()]
        result = apply_gates(signals, context, cfg, daily_context=daily)

        assert len(result.actionable) == 1
        assert result.actionable[0].id == "VAL-1"
        assert len(result.blocked) == 1
        assert result.blocked[0].id == "WEAK-1"

    def test_no_daily_context_falls_back_to_static(self, tmp_path) -> None:
        """Without daily_context, uses context's existing dominant_alignment."""
        cfg = _cfg_with_ctx2_policy(tmp_path, "DISALLOW")
        context = _context(dominant_alignment=DominantAlignment.AGAINST)
        result = apply_gates([_bullish_signal()], context, cfg, daily_context=None)

        assert len(result.blocked) == 1

    def test_daily_unknown_trend_gives_unknown_alignment(self, tmp_path) -> None:
        """Daily UNKNOWN trend → alignment UNKNOWN → not blocked even with DISALLOW."""
        cfg = _cfg_with_ctx2_policy(tmp_path, "DISALLOW")
        context = _context(dominant_alignment=DominantAlignment.UNKNOWN)
        daily = _daily_ctx(Trend.UNKNOWN)
        result = apply_gates([_bullish_signal()], context, cfg, daily_context=daily)

        assert len(result.actionable) == 1

    def test_reduce_risk_policy_passes_with_daily(self, cfg: VPAConfig) -> None:
        """REDUCE_RISK policy passes regardless of daily alignment."""
        daily = _daily_ctx(Trend.DOWN)
        context = _context(dominant_alignment=DominantAlignment.UNKNOWN)
        result = apply_gates([_bullish_signal()], context, cfg, daily_context=daily)

        assert len(result.actionable) == 1
