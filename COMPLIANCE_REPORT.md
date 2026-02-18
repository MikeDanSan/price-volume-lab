# COMPLIANCE_REPORT.md
**VPA Canonical System — Compliance Report**
- Date: 2026-02-18 (updated after Phase F)
- Code version: 0.1.0 (pyproject.toml)
- Config version: 0.1 (vpa.default.json)
- Commits since initial audit: 29

---

## 1) Executive summary
- **Overall status: PASS (canonical pipeline + live paper trading)**
- Blocking issues: 0 (all 7 original blockers resolved)
- Drift issues: 0
- Implemented rules: 8 atomic rules, 2 setups, 3 context gates (all OK)
- Tests: 312 passing, 0 failures

The system has a fully functional canonical pipeline (Features → Rules → Gates → Composer → Risk → Execution) with real context analysis (trend, location, congestion), config-driven thresholds, deterministic backtest execution, and a live paper-trading scheduler. All CLI commands (`scan`, `paper`, `backtest`, `status`, `ingest`) use the canonical pipeline.

### Completed since last report
- **Phase E (commits 22–27):** Paper command migration, real Context Engine (trend + location + congestion), CTX-2 policy-driven gate, CTX-3 congestion gate, golden-fixture runner.
- **Phase F (commits 28–29):** dotenv loading, alpaca-py v0.43 compat, IEX free-tier feed, live paper-trading scheduler with market-hours awareness.
- Test count: 244 → 312 (+68 tests)

### Remaining work (non-blocking)
- 13 rule/setup IDs defined in docs but not yet implemented (trend-level, climax, short-side)
- Multi-timeframe dominant alignment not yet computed (returns UNKNOWN)
- No holiday/low-liquidity filter
- IEX volume thresholds may need recalibration vs SIP

---

## 2) Vocabulary drift (docs + code comments)

### Status: CONTROLLED
- `scripts/vpa_vocab_lint.py` exists and enforces blacklist scanning
- All canonical code (`src/vpa_core/`) free of blacklisted terms
- Zero violations in code files or canonical docs

---

## 3) Registry coverage (VPA_RULE_REGISTRY.yaml)

### Registered AND implemented (OK) — 13 items

| ID | Type | Impl | Tests |
|----|------|------|-------|
| VAL-1 | Atomic rule | `rule_engine.py::detect_val_1` | 7 tests |
| ANOM-1 | Atomic rule | `rule_engine.py::detect_anom_1` | 6 tests |
| ANOM-2 | Atomic rule | `rule_engine.py::detect_anom_2` | 9 tests |
| STR-1 | Atomic rule | `rule_engine.py::detect_str_1` | 9 tests |
| WEAK-1 | Atomic rule | `rule_engine.py::detect_weak_1` | 9 tests |
| CONF-1 | Atomic rule | `rule_engine.py::detect_conf_1` | 9 tests |
| AVOID-NEWS-1 | Atomic rule | `rule_engine.py::detect_avoid_news_1` | 10 tests |
| TEST-SUP-1 | Atomic rule | `rule_engine.py::detect_test_sup_1` | 7 tests |
| CTX-1 | Context gate | `context_gates.py::_check_ctx_1` | 10 tests |
| CTX-2 | Context gate | `context_gates.py::_check_ctx_2` + `risk_engine.py` | 10 tests |
| CTX-3 | Context gate | `context_gates.py::_check_ctx_3` | 11 tests |
| ENTRY-LONG-1 | Setup | `setup_composer.py::SetupComposer` | 8 tests |
| ENTRY-LONG-2 | Setup | `setup_composer.py::SetupComposer` | 9 tests |

### Defined in docs but not yet implemented (MISSING) — 13 items
- Trend-level rules: TREND-VAL-1, TREND-ANOM-1, TREND-ANOM-2
- Additional validation/strength/weakness: VAL-2, WEAK-2, STR-2
- Tests: TEST-SUP-2, TEST-DEM-1
- Climax: CLIMAX-SELL-1, CLIMAX-SELL-2
- Avoidance: AVOID-TRAP-1, AVOID-COUNTER-1
- Confirmation: CONF-2
- Setups: ENTRY-SHORT-1, ENTRY-SHORT-2

### EXTRA items
- None.

---

## 4) Traceability matrix status

| Status | Count | Details |
|--------|-------|---------|
| OK | 13 | VAL-1, ANOM-1, ANOM-2, STR-1, WEAK-1, CONF-1, AVOID-NEWS-1, TEST-SUP-1, CTX-1, CTX-2, CTX-3, ENTRY-LONG-1, ENTRY-LONG-2 |
| PARTIAL | 0 | — |
| MISSING | 13 | Trend-level, climax, short-side rules and setups |
| DRIFT | 0 | — |
| EXTRA | 0 | — |

See `docs/vpa/VPA_TRACEABILITY.md` for the full matrix.

---

## 5) Pipeline compliance (VPA_SIGNAL_FLOW.md)

### Required stage ordering
```
Ingest → Resample → Features → Relative Measures → Structure → Context →
Rule Engine → Context Gates → Setup Composer → Risk → Execution → Journal
```

### Status: PASS

| Stage | Status | Implementation |
|-------|--------|---------------|
| Ingest | OK | `AlpacaBarFetcher` → `BarStore` (SQLite), IEX free-tier feed |
| Resample | N/A | Single-timeframe only (MTF is future work) |
| Features | OK | `feature_engine.py::extract_features` → `CandleFeatures` |
| Relative Measures | OK | `vol_rel`, `spread_rel` with SMA baselines, config-driven windows |
| Structure | OK | `context_engine.py::_detect_location` + `_detect_congestion` |
| Context | OK | `context_engine.py::analyze` → `ContextSnapshot` (trend, location, congestion) |
| Rule Engine | OK | 8 detectors, pure functions, `SignalEvent[]` only |
| Context Gates | OK | CTX-1 + CTX-2 (policy-driven) + CTX-3 (congestion awareness) |
| Setup Composer | OK | Data-driven `_SETUP_DEFS`; 2 setups; state machine |
| Risk Engine | OK | Stop placement, position sizing, CTX-2 REDUCE_RISK, hard rejects |
| Execution | OK | Backtest: next-bar-open; Paper: `submit_intent()` with risk-computed size |
| Journal | OK | `JournalWriter` with trade + signal events |

### Layer separation: PASS
- Rule Engine emits `SignalEvent[]` only (no orders, no sizing)
- Setup Composer matches sequences only (no sizing, no stops)
- Risk Engine owns stops, sizing, and rejects
- All CLI commands use canonical pipeline

---

## 6) Determinism and config compliance

### Status: PASS
- All thresholds config-driven via `VPAConfig` frozen dataclass tree
- JSON schema validation on load (`vpa_config.schema.json`)
- Context engine parameters configurable: `window_K`, `location_lookback`, `congestion_window`, `congestion_pct`
- Candle pattern thresholds: hammer, shooting star, long-legged doji
- Volume/spread classification: 4-state / 3-state with config boundaries
- No magic numbers in canonical rule engine, context engine, or pipeline

### Spread definition: RESOLVED
- Canonical: `spread = |close - open|` (candle body)
- `bar_range = high - low` (full extent)

---

## 7) Backtest anti-lookahead checks

| Check | Status | Details |
|-------|--------|---------|
| Bar-close evaluation enforced | **PASS** | `run_pipeline()` called on completed bars only |
| Next-bar execution enforced | **PASS** | Entry fill at `bars[i+1].open` |
| Stop fill model deterministic | **PASS** | Stop checked against next-bar range |
| Config-driven execution semantics | **PASS** | `signal_eval: BAR_CLOSE_ONLY`, `entry_timing: NEXT_BAR_OPEN` |
| Paper command alignment | **PASS** | Migrated to canonical pipeline (Commit 23) |

---

## 8) Tests + fixtures

### Test suite: 312 tests, 0 failures

| Test File | Count | Coverage |
|-----------|-------|----------|
| `test_rule_engine.py` | 78 | All 8 rules + orchestrator |
| `test_context_gates.py` | 31 | CTX-1, CTX-2 (3 policies), CTX-3, gate interactions |
| `test_vpa_config.py` | 24 | Config loading, validation, overrides |
| `test_scheduler.py` | 23 | Market hours, bar alignment, weekend handling |
| `test_classification.py` | 19 | Volume + spread classifiers |
| `test_context_engine.py` | 18 | Trend, location, congestion detection |
| `test_setup_composer.py` | 17 | Both setups + invalidation + expiration |
| `test_canonical_models.py` | 15 | Data model construction + immutability |
| `test_risk_engine.py` | 15 | Sizing, stops, rejects, CTX-2 policy |
| `test_vpa_core_features.py` | 12 | Candle anatomy functions |
| `test_golden_fixtures.py` | 10 | End-to-end pipeline replay from JSON |
| `test_backtest.py` | 9 | Backtest runner + execution semantics |
| `test_pipeline.py` | 8 | Integration: bars → TradeIntent |
| `test_feature_engine.py` | 8 | Feature extraction pipeline |
| `test_vocab_lint.py` | 8 | Vocabulary enforcement |
| `test_cli.py` | 5 | CLI commands (scan, backtest, status, paper) |
| Others | 12 | Config loader, bar store, fetcher, etc. |

### Golden fixtures
- `FXT-ANOM-1-basic.json` — atomic rule replay
- `FXT-VAL-1-basic.json` — atomic rule replay
- `FXT-INTEG-anom1-no-setup.json` — integration (signal but no setup match)
- `FXT-INTEG-neutral-bar.json` — integration (no signals expected)

---

## 9) Original blocking items — all resolved

| # | Issue | Resolution |
|---|-------|------------|
| B-1 | Data models don't match spec | Commit 2: canonical models match VPA_SYSTEM_SPEC §3.3 |
| B-2 | VAL-1 not implemented | Commit 7: `detect_val_1` with 7 tests |
| B-3 | ANOM-1 not implemented | Commit 7: `detect_anom_1` with 6 tests |
| B-4 | ENTRY-LONG-1 not implemented | Commit 9: SetupComposer with 8 tests |
| B-5 | `no_demand` EXTRA in code | Commit 13: removed |
| B-6 | Pipeline conflates stages | Commit 11: separate stages per VPA_SIGNAL_FLOW.md |
| B-7 | Hardcoded thresholds | Commits 3-4: all via `VPAConfig` |

---

## 10) Live trading readiness

| Capability | Status |
|------------|--------|
| Data ingestion (Alpaca IEX) | OK |
| Bar storage (SQLite) | OK |
| One-shot scan (`vpa scan`) | OK |
| Backtest (`vpa backtest`) | OK |
| Paper trading (`vpa paper`) | OK |
| Live scheduler (`vpa paper --live`) | OK |
| Market-hours awareness | OK |
| Position/status tracking (`vpa status`) | OK |
| Journal logging | OK |
