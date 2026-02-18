"""Tests for Context Gates: CTX-1 trend-location-first gate."""

from datetime import datetime, timezone

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


def _context(*, trend_location: TrendLocation = TrendLocation.TOP) -> ContextSnapshot:
    return ContextSnapshot(
        tf="15m",
        trend=Trend.UP,
        trend_strength=TrendStrength.MODERATE,
        trend_location=trend_location,
        congestion=Congestion(active=False),
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
