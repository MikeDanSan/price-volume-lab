"""Tests for Risk Engine: SetupMatch + account -> TradeIntent."""

import math
from datetime import datetime, timezone

import pytest

from config.vpa_config import load_vpa_config, VPAConfig
from vpa_core.contracts import (
    Congestion,
    ContextSnapshot,
    DominantAlignment,
    SignalClass,
    SignalEvent,
    TradeIntentStatus,
    Trend,
    TrendLocation,
    TrendStrength,
)
from vpa_core.risk_engine import AccountState, evaluate_risk
from vpa_core.setup_composer import SetupMatch


TS = datetime(2026, 2, 17, 14, 30, tzinfo=timezone.utc)


@pytest.fixture()
def cfg() -> VPAConfig:
    return load_vpa_config()


def _signal(
    rule_id: str = "TEST-SUP-1",
    bar_low: float | None = None,
    bar_high: float | None = None,
    direction_bias: str = "BULLISH",
    signal_class: SignalClass = SignalClass.TEST,
) -> SignalEvent:
    evidence: dict = {}
    if bar_low is not None:
        evidence["bar_low"] = bar_low
    if bar_high is not None:
        evidence["bar_high"] = bar_high
    return SignalEvent(
        id=rule_id, name="Test", tf="15m", ts=TS,
        signal_class=signal_class, direction_bias=direction_bias,
        evidence=evidence,
    )


def _match(bar_low: float | None = 98.0) -> SetupMatch:
    return SetupMatch(
        setup_id="ENTRY-LONG-1",
        direction="LONG",
        signals=[_signal("TEST-SUP-1", bar_low=bar_low), _signal("VAL-1")],
        matched_at_bar=5,
        tf="15m",
    )


def _short_match(bar_high: float | None = 102.0) -> SetupMatch:
    return SetupMatch(
        setup_id="ENTRY-SHORT-1",
        direction="SHORT",
        signals=[
            _signal("CLIMAX-SELL-1", bar_high=bar_high,
                    direction_bias="BEARISH", signal_class=SignalClass.WEAKNESS),
            _signal("WEAK-1", direction_bias="BEARISH",
                    signal_class=SignalClass.WEAKNESS),
        ],
        matched_at_bar=5,
        tf="15m",
    )


def _context(alignment: DominantAlignment = DominantAlignment.WITH) -> ContextSnapshot:
    return ContextSnapshot(
        tf="15m", trend=Trend.UP, trend_strength=TrendStrength.MODERATE,
        trend_location=TrendLocation.BOTTOM, congestion=Congestion(active=False),
        dominant_alignment=alignment,
    )


def _account(equity: float = 100_000.0, positions: int = 0, daily_pnl: float = 0.0) -> AccountState:
    return AccountState(equity=equity, open_position_count=positions, daily_realized_pnl=daily_pnl)


def _cfg_with_policy(tmp_path, policy: str) -> VPAConfig:
    """Load config with a specific ctx2_dominant_alignment_policy."""
    import json
    from config.vpa_config import DEFAULT_CONFIG_PATH

    with open(DEFAULT_CONFIG_PATH) as f:
        data = json.load(f)
    data["gates"]["ctx2_dominant_alignment_policy"] = policy
    p = tmp_path / f"risk_{policy.lower()}.json"
    p.write_text(json.dumps(data))
    return load_vpa_config(config_path=p)


# ---------------------------------------------------------------------------
# Sizing calculation
# ---------------------------------------------------------------------------


class TestSizing:
    def test_basic_size_calculation(self, cfg: VPAConfig) -> None:
        """size = (equity * risk_pct) / |entry - stop|
        = (100000 * 0.005) / |100 - 98| = 500 / 2 = 250 shares."""
        intent = evaluate_risk(_match(bar_low=98.0), 100.0, _account(), _context(), cfg)
        assert intent.status == TradeIntentStatus.READY
        assert intent.risk_plan.size == 250
        assert intent.risk_plan.stop == 98.0
        assert intent.risk_plan.risk_pct == 0.005

    def test_stop_from_test_bar_low(self, cfg: VPAConfig) -> None:
        intent = evaluate_risk(_match(bar_low=95.0), 100.0, _account(), _context(), cfg)
        assert intent.risk_plan.stop == 95.0
        # (100000 * 0.005) / |100 - 95| = 500 / 5 = 100
        assert intent.risk_plan.size == 100

    def test_fallback_stop_when_no_bar_low(self, cfg: VPAConfig) -> None:
        """When test signal has no bar_low evidence, fallback to 2% below price."""
        intent = evaluate_risk(_match(bar_low=None), 100.0, _account(), _context(), cfg)
        assert intent.risk_plan.stop == pytest.approx(98.0)

    def test_entry_plan_uses_config(self, cfg: VPAConfig) -> None:
        intent = evaluate_risk(_match(), 100.0, _account(), _context(), cfg)
        assert intent.entry_plan.timing == "NEXT_BAR_OPEN"
        assert intent.entry_plan.order_type == "MARKET"


# ---------------------------------------------------------------------------
# Countertrend risk reduction (CTX-2)
# ---------------------------------------------------------------------------


class TestCountertrend:
    """CTX-2 risk reduction — only active when policy is REDUCE_RISK."""

    def test_with_trend_full_risk(self, cfg: VPAConfig) -> None:
        """Default policy is REDUCE_RISK; WITH alignment gets full risk + annotation."""
        assert cfg.gates.ctx2_dominant_alignment_policy == "REDUCE_RISK"
        intent = evaluate_risk(_match(bar_low=98.0), 100.0, _account(), _context(DominantAlignment.WITH), cfg)
        assert intent.risk_plan.risk_pct == 0.005
        assert "CTX-2:WITH" in intent.rationale

    def test_against_trend_reduced_risk(self, cfg: VPAConfig) -> None:
        """Against dominant trend + REDUCE_RISK policy: risk_pct *= countertrend_multiplier (0.5)."""
        intent = evaluate_risk(_match(bar_low=98.0), 100.0, _account(), _context(DominantAlignment.AGAINST), cfg)
        assert intent.risk_plan.risk_pct == pytest.approx(0.0025)
        assert intent.risk_plan.size == 125
        assert "CTX-2:AGAINST(risk_reduced)" in intent.rationale

    def test_unknown_alignment_full_risk(self, cfg: VPAConfig) -> None:
        intent = evaluate_risk(_match(bar_low=98.0), 100.0, _account(), _context(DominantAlignment.UNKNOWN), cfg)
        assert intent.risk_plan.risk_pct == 0.005
        assert not any("CTX-2" in r for r in intent.rationale)

    def test_allow_policy_no_reduction(self, tmp_path) -> None:
        """ALLOW policy: AGAINST alignment does NOT reduce risk."""
        cfg = _cfg_with_policy(tmp_path, "ALLOW")
        intent = evaluate_risk(_match(bar_low=98.0), 100.0, _account(), _context(DominantAlignment.AGAINST), cfg)
        assert intent.risk_plan.risk_pct == 0.005
        assert not any("CTX-2" in r for r in intent.rationale)

    def test_disallow_policy_no_reduction(self, tmp_path) -> None:
        """DISALLOW policy: no risk reduction (gate already blocked the signal)."""
        cfg = _cfg_with_policy(tmp_path, "DISALLOW")
        intent = evaluate_risk(_match(bar_low=98.0), 100.0, _account(), _context(DominantAlignment.AGAINST), cfg)
        assert intent.risk_plan.risk_pct == 0.005
        assert not any("CTX-2" in r for r in intent.rationale)


# ---------------------------------------------------------------------------
# Hard rejects
# ---------------------------------------------------------------------------


class TestRejects:
    def test_reject_max_positions(self, cfg: VPAConfig) -> None:
        account = _account(positions=1)  # max_concurrent_positions = 1
        intent = evaluate_risk(_match(), 100.0, account, _context(), cfg)
        assert intent.status == TradeIntentStatus.REJECTED
        assert "Max concurrent positions" in intent.reject_reason

    def test_reject_daily_loss_limit(self, cfg: VPAConfig) -> None:
        """daily_loss_limit_pct=0.02, equity=100000 -> limit=$2000."""
        account = _account(daily_pnl=-2000.0)
        intent = evaluate_risk(_match(), 100.0, account, _context(), cfg)
        assert intent.status == TradeIntentStatus.REJECTED
        assert "Daily loss limit" in intent.reject_reason

    def test_passes_within_daily_loss_limit(self, cfg: VPAConfig) -> None:
        account = _account(daily_pnl=-1999.0)
        intent = evaluate_risk(_match(), 100.0, account, _context(), cfg)
        assert intent.status == TradeIntentStatus.READY

    def test_rejected_intent_has_zero_risk_plan(self, cfg: VPAConfig) -> None:
        account = _account(positions=1)
        intent = evaluate_risk(_match(), 100.0, account, _context(), cfg)
        assert intent.risk_plan.size == 0
        assert intent.risk_plan.stop == 0.0


# ---------------------------------------------------------------------------
# Rationale chain
# ---------------------------------------------------------------------------


class TestRationale:
    def test_rationale_includes_signal_ids(self, cfg: VPAConfig) -> None:
        intent = evaluate_risk(_match(), 100.0, _account(), _context(), cfg)
        assert "TEST-SUP-1" in intent.rationale
        assert "VAL-1" in intent.rationale

    def test_intent_id_format(self, cfg: VPAConfig) -> None:
        intent = evaluate_risk(_match(), 100.0, _account(), _context(), cfg)
        assert intent.intent_id == "TI-ENTRY-LONG-1-bar5"
        assert intent.setup == "ENTRY-LONG-1"
        assert intent.direction == "LONG"
        assert intent.tf == "15m"


# ---------------------------------------------------------------------------
# Short-side: ENTRY-SHORT-1 stop & sizing
# ---------------------------------------------------------------------------


class TestShortSizing:
    def test_basic_short_size_calculation(self, cfg: VPAConfig) -> None:
        """size = (equity * risk_pct) / |entry - stop|
        = (100000 * 0.005) / |100 - 102| = 500 / 2 = 250 shares."""
        intent = evaluate_risk(_short_match(bar_high=102.0), 100.0, _account(), _context(), cfg)
        assert intent.status == TradeIntentStatus.READY
        assert intent.direction == "SHORT"
        assert intent.risk_plan.size == 250
        assert intent.risk_plan.stop == 102.0
        assert intent.risk_plan.risk_pct == 0.005

    def test_stop_from_climax_bar_high(self, cfg: VPAConfig) -> None:
        """Stop placed above the climax bar's high."""
        intent = evaluate_risk(_short_match(bar_high=105.0), 100.0, _account(), _context(), cfg)
        assert intent.risk_plan.stop == 105.0
        # (100000 * 0.005) / |100 - 105| = 500 / 5 = 100
        assert intent.risk_plan.size == 100

    def test_fallback_stop_when_no_bar_high(self, cfg: VPAConfig) -> None:
        """When climax signal has no bar_high evidence, fallback to 2% above price."""
        intent = evaluate_risk(_short_match(bar_high=None), 100.0, _account(), _context(), cfg)
        assert intent.risk_plan.stop == pytest.approx(102.0)

    def test_short_entry_plan_uses_config(self, cfg: VPAConfig) -> None:
        intent = evaluate_risk(_short_match(), 100.0, _account(), _context(), cfg)
        assert intent.entry_plan.timing == "NEXT_BAR_OPEN"
        assert intent.entry_plan.order_type == "MARKET"


class TestShortCountertrend:
    """CTX-2 risk reduction applies to shorts the same way as longs."""

    def test_short_against_trend_reduced_risk(self, cfg: VPAConfig) -> None:
        intent = evaluate_risk(
            _short_match(bar_high=102.0), 100.0, _account(),
            _context(DominantAlignment.AGAINST), cfg,
        )
        assert intent.risk_plan.risk_pct == pytest.approx(0.0025)
        assert "CTX-2:AGAINST(risk_reduced)" in intent.rationale

    def test_short_with_trend_full_risk(self, cfg: VPAConfig) -> None:
        intent = evaluate_risk(
            _short_match(bar_high=102.0), 100.0, _account(),
            _context(DominantAlignment.WITH), cfg,
        )
        assert intent.risk_plan.risk_pct == 0.005
        assert "CTX-2:WITH" in intent.rationale


class TestShortRejects:
    def test_reject_short_max_positions(self, cfg: VPAConfig) -> None:
        account = _account(positions=1)
        intent = evaluate_risk(_short_match(), 100.0, account, _context(), cfg)
        assert intent.status == TradeIntentStatus.REJECTED
        assert "Max concurrent positions" in intent.reject_reason

    def test_reject_short_daily_loss_limit(self, cfg: VPAConfig) -> None:
        account = _account(daily_pnl=-2000.0)
        intent = evaluate_risk(_short_match(), 100.0, account, _context(), cfg)
        assert intent.status == TradeIntentStatus.REJECTED


class TestShortRationale:
    def test_short_rationale_includes_signal_ids(self, cfg: VPAConfig) -> None:
        intent = evaluate_risk(_short_match(), 100.0, _account(), _context(), cfg)
        assert "CLIMAX-SELL-1" in intent.rationale
        assert "WEAK-1" in intent.rationale

    def test_short_intent_id_format(self, cfg: VPAConfig) -> None:
        intent = evaluate_risk(_short_match(), 100.0, _account(), _context(), cfg)
        assert intent.intent_id == "TI-ENTRY-SHORT-1-bar5"
        assert intent.setup == "ENTRY-SHORT-1"
        assert intent.direction == "SHORT"
