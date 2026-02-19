"""Golden-fixture runner: load fixtures/vpa/*.json and replay through the pipeline.

Fixture types:
    atomic      — bars → features → rules → check expected signals
    setup       — signal events → setup composer → check expected matches
    integration — bars → full pipeline → check signals + setups + intents

Fixtures are discovered automatically via pytest parametrize.
See docs/vpa/VPA_TEST_FIXTURES.md for format spec.
"""

from __future__ import annotations

import copy
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest

from config.vpa_config import DEFAULT_CONFIG_PATH, VPAConfig, load_vpa_config
from vpa_core.contracts import (
    Bar,
    Congestion,
    ContextSnapshot,
    DominantAlignment,
    SignalClass,
    SignalEvent,
    Trend,
    TrendLocation,
    TrendStrength,
)
from vpa_core.context_engine import analyze as analyze_context
from vpa_core.feature_engine import extract_features
from vpa_core.pipeline import run_pipeline
from vpa_core.risk_engine import AccountState
from vpa_core.rule_engine import evaluate_rules
from vpa_core.setup_composer import SetupComposer

FIXTURES_ROOT = Path(__file__).resolve().parent.parent / "docs" / "config" / "fixtures" / "vpa"


def _discover_fixtures(fixture_type: str | None = None) -> list[Path]:
    """Find all fixture JSON files, optionally filtered by type subdirectory."""
    if not FIXTURES_ROOT.exists():
        return []
    paths = sorted(FIXTURES_ROOT.rglob("FXT-*.json"))
    if fixture_type:
        paths = [p for p in paths if fixture_type in p.parts]
    return paths


def _fixture_ids(paths: list[Path]) -> list[str]:
    return [p.stem for p in paths]


def _load_fixture(path: Path) -> dict[str, Any]:
    with open(path) as f:
        return json.load(f)


def _deep_merge(base: dict, overrides: dict) -> dict:
    """Recursively merge overrides into a copy of base."""
    result = copy.deepcopy(base)
    for key, value in overrides.items():
        if isinstance(value, dict) and key in result and isinstance(result[key], dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _build_config(overrides: dict[str, Any], tmp_path: Path) -> VPAConfig:
    """Load default config, apply fixture overrides, return validated VPAConfig."""
    with open(DEFAULT_CONFIG_PATH) as f:
        base = json.load(f)
    merged = _deep_merge(base, overrides)
    p = tmp_path / "fixture_config.json"
    p.write_text(json.dumps(merged))
    return load_vpa_config(config_path=p)


def _parse_bar(raw: dict) -> Bar:
    ts = datetime.fromisoformat(raw["ts"].replace("Z", "+00:00"))
    return Bar(
        open=raw["open"],
        high=raw["high"],
        low=raw["low"],
        close=raw["close"],
        volume=raw["volume"],
        timestamp=ts,
        symbol="TEST",
    )


def _parse_bars(raw_list: list[dict]) -> list[Bar]:
    return [_parse_bar(r) for r in raw_list]


# ---------------------------------------------------------------------------
# Atomic fixture runner
# ---------------------------------------------------------------------------

ATOMIC_PATHS = _discover_fixtures("atomic")


@pytest.mark.parametrize("fixture_path", ATOMIC_PATHS, ids=_fixture_ids(ATOMIC_PATHS))
def test_atomic_fixture(fixture_path: Path, tmp_path: Path) -> None:
    """Replay an atomic fixture: bars → features → rules → check signals."""
    data = _load_fixture(fixture_path)
    assert data["type"] == "atomic", f"Expected atomic fixture, got {data['type']}"

    cfg = _build_config(data.get("configOverrides", {}), tmp_path)
    bars = _parse_bars(data["inputs"]["bars"])
    tf = data.get("timeframe", "15m")

    features = extract_features(bars, cfg, tf)
    signals = evaluate_rules(features, cfg)

    expected_signals = data["expected"]["signals"]
    expected_ids = {s["id"] for s in expected_signals}
    actual_ids = {s.id for s in signals}

    assert expected_ids <= actual_ids, (
        f"Fixture {data['fixtureId']}: expected signals {expected_ids} "
        f"not found in actual {actual_ids}"
    )

    for expected in expected_signals:
        matching = [s for s in signals if s.id == expected["id"]]
        assert matching, f"Signal {expected['id']} not found"
        sig = matching[0]

        if "class" in expected:
            assert sig.signal_class.value == expected["class"], (
                f"{sig.id}: expected class {expected['class']}, got {sig.signal_class.value}"
            )
        if "directionBias" in expected:
            assert sig.direction_bias == expected["directionBias"], (
                f"{sig.id}: expected bias {expected['directionBias']}, got {sig.direction_bias}"
            )
        if "name" in expected:
            assert sig.name == expected["name"], (
                f"{sig.id}: expected name {expected['name']}, got {sig.name}"
            )
        if "evidence" in expected:
            for key, val in expected["evidence"].items():
                assert key in sig.evidence, f"{sig.id}: missing evidence key '{key}'"
                assert str(sig.evidence[key]) == str(val), (
                    f"{sig.id}: evidence[{key}] expected {val}, got {sig.evidence[key]}"
                )


# ---------------------------------------------------------------------------
# Setup fixture runner
# ---------------------------------------------------------------------------

SETUP_PATHS = _discover_fixtures("setup")


def _make_signal_event(raw: dict) -> SignalEvent:
    """Build a minimal SignalEvent from fixture shorthand."""
    ts = datetime.fromisoformat(raw["ts"].replace("Z", "+00:00"))
    sig_id = raw["signalId"]
    class_map = {
        "VAL-1": SignalClass.VALIDATION,
        "ANOM-1": SignalClass.ANOMALY,
        "ANOM-2": SignalClass.ANOMALY,
        "TEST-SUP-1": SignalClass.TEST,
        "STR-1": SignalClass.STRENGTH,
        "WEAK-1": SignalClass.WEAKNESS,
        "WEAK-2": SignalClass.WEAKNESS,
        "CLIMAX-SELL-1": SignalClass.WEAKNESS,
        "CONF-1": SignalClass.CONFIRMATION,
        "AVOID-NEWS-1": SignalClass.AVOIDANCE,
    }
    bearish_ids = {"WEAK-1", "WEAK-2", "CLIMAX-SELL-1"}
    return SignalEvent(
        id=sig_id,
        name=sig_id,
        tf=raw.get("tf", "15m"),
        ts=ts,
        signal_class=class_map.get(sig_id, SignalClass.VALIDATION),
        direction_bias="BEARISH" if sig_id in bearish_ids else "BULLISH",
        priority=2,
        evidence={"bar_low": 98.0, "bar_high": 102.0},
        requires_context_gate=False,
    )


def _parse_context(raw: dict | None) -> ContextSnapshot:
    if not raw:
        return ContextSnapshot(
            tf="15m", trend=Trend.UP, trend_strength=TrendStrength.MODERATE,
            trend_location=TrendLocation.BOTTOM, congestion=Congestion(active=False),
            dominant_alignment=DominantAlignment.WITH,
        )
    loc_map = {"TOP": TrendLocation.TOP, "BOTTOM": TrendLocation.BOTTOM,
               "MIDDLE": TrendLocation.MIDDLE, "UNKNOWN": TrendLocation.UNKNOWN}
    cong_raw = raw.get("congestion", {})
    return ContextSnapshot(
        tf="15m",
        trend=Trend.UP,
        trend_strength=TrendStrength.MODERATE,
        trend_location=loc_map.get(raw.get("trendLocation", "BOTTOM"), TrendLocation.BOTTOM),
        congestion=Congestion(
            active=cong_raw.get("active", False),
            range_high=cong_raw.get("range_high"),
            range_low=cong_raw.get("range_low"),
        ),
        dominant_alignment=DominantAlignment.WITH,
    )


@pytest.mark.parametrize("fixture_path", SETUP_PATHS, ids=_fixture_ids(SETUP_PATHS))
def test_setup_fixture(fixture_path: Path, tmp_path: Path) -> None:
    """Replay a setup fixture: signal events → composer → check matches."""
    data = _load_fixture(fixture_path)
    assert data["type"] == "setup", f"Expected setup fixture, got {data['type']}"

    cfg = _build_config(data.get("configOverrides", {}), tmp_path)
    composer = SetupComposer(cfg)
    context = _parse_context(data["inputs"].get("context"))

    events = [_make_signal_event(e) for e in data["inputs"]["events"]]
    all_matches = []
    for i, event in enumerate(events):
        matches = composer.process_signals([event], bar_index=i, context=context)
        all_matches.extend(matches)

    expected = data["expected"]
    if "tradeIntentCandidate" in expected:
        exp_intent = expected["tradeIntentCandidate"]
        assert len(all_matches) >= 1, (
            f"Fixture {data['fixtureId']}: expected at least 1 setup match, got 0"
        )
        match = all_matches[-1]
        assert match.setup_id == exp_intent["setupId"]
        assert match.direction == exp_intent["direction"]


# ---------------------------------------------------------------------------
# Integration fixture runner
# ---------------------------------------------------------------------------

INTEG_PATHS = _discover_fixtures("integration")


@pytest.mark.parametrize("fixture_path", INTEG_PATHS, ids=_fixture_ids(INTEG_PATHS))
def test_integration_fixture(fixture_path: Path, tmp_path: Path) -> None:
    """Replay an integration fixture: bars → full pipeline → check outputs."""
    data = _load_fixture(fixture_path)
    assert data["type"] == "integration", f"Expected integration fixture, got {data['type']}"

    cfg = _build_config(data.get("configOverrides", {}), tmp_path)
    bars = _parse_bars(data["inputs"]["bars"])
    tf = data.get("timeframe", "15m")
    composer = SetupComposer(cfg)
    context = analyze_context(bars, cfg, tf)
    account = AccountState(equity=100_000.0)

    result = run_pipeline(
        bars, bar_index=len(bars) - 1, context=context,
        account=account, config=cfg, composer=composer, tf=tf,
    )

    expected = data["expected"]

    if "signals" in expected:
        expected_ids = {s["id"] for s in expected["signals"]}
        actual_ids = {s.id for s in result.signals}
        assert expected_ids <= actual_ids, (
            f"Fixture {data['fixtureId']}: expected signals {expected_ids} "
            f"not found in actual {actual_ids}"
        )

    if "noSignals" in expected and expected["noSignals"]:
        assert len(result.signals) == 0, (
            f"Fixture {data['fixtureId']}: expected no signals, got {[s.id for s in result.signals]}"
        )

    if "intents" in expected:
        for exp_intent in expected["intents"]:
            matching = [i for i in result.intents if i.setup == exp_intent["setupId"]]
            assert matching, (
                f"Fixture {data['fixtureId']}: expected intent for {exp_intent['setupId']} not found"
            )
            intent = matching[0]
            if "status" in exp_intent:
                assert intent.status.value == exp_intent["status"]
            if "direction" in exp_intent:
                assert intent.direction == exp_intent["direction"]
