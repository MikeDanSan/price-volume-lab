# COMPLIANCE_REPORT.md
**VPA Canonical System — Compliance Report**
- Date: 2026-02-17 (updated after Phase I)
- Code version: 0.1.0 (pyproject.toml)
- Config version: 0.1 (vpa.default.json)
- Commits since initial audit: 50

---

## 1) Executive summary
- **Overall status: PASS (full canonical pipeline + multi-timeframe + extended rules)**
- Blocking issues: 0 (all 7 original blockers resolved)
- Drift issues: 0
- Implemented rules: 18 atomic/trend/cluster/meta/avoidance rules, 4 setups, 3 context gates (all OK)
- Tests: 555 passing, 0 failures

The system has a fully functional canonical pipeline (Features → Rules → Gates → Composer → Risk → Execution) with real context analysis (trend, location, congestion, volume trend), multi-timeframe dominant alignment (daily trend), ATR-based stop optimization, per-symbol configuration, config-driven thresholds, deterministic backtest execution, bidirectional trading (long + short), avoidance rules, a low-liquidity volume guard, and a live paper-trading scheduler. All CLI commands (`scan`, `paper`, `backtest`, `status`, `ingest`) use the canonical pipeline.

### Completed since last report
- **Phase H (commits 37–43):** Daily bar ingestion + storage, daily trend analyzer, CTX-2 dominant alignment from daily trend, ATR computation + config, ATR-based stop placement, per-symbol config support (`vpa.{SYMBOL}.json` overrides).
- **Phase I (commits 44–49):** TEST-SUP-2 + TEST-DEM-1 (supply/demand tests), TREND-VAL-1 + TREND-ANOM-1 (trend-level rules), TREND-ANOM-2 (cluster rule), CONF-2 (two-level agreement meta-rule), AVOID-TRAP-1 + AVOID-COUNTER-1 (avoidance rules), ENTRY-SHORT-2 (reversal short from climax + trend weakness).
- Test count: 375 → 555 (+180 tests across Phases H-I)

### Remaining work (non-blocking)
- 3 rule IDs defined in docs but not yet implemented (VAL-2, STR-2, CLIMAX-SELL-2)
- IEX volume thresholds may need recalibration vs SIP
- Production readiness (Docker, health checks, alerting)

---

## 2) Vocabulary drift (docs + code comments)

### Status: CONTROLLED
- `scripts/vpa_vocab_lint.py` exists and enforces blacklist scanning
- All canonical code (`src/vpa_core/`) free of blacklisted terms
- Zero violations in code files or canonical docs

---

## 3) Registry coverage (VPA_RULE_REGISTRY.yaml)

### Registered AND implemented (OK) — 25 items

| ID | Type | Impl | Tests |
|----|------|------|-------|
| VAL-1 | Atomic rule | `rule_engine.py::detect_val_1` | 7 tests |
| ANOM-1 | Atomic rule | `rule_engine.py::detect_anom_1` | 6 tests |
| ANOM-2 | Atomic rule | `rule_engine.py::detect_anom_2` | 9 tests |
| STR-1 | Atomic rule | `rule_engine.py::detect_str_1` | 9 tests |
| WEAK-1 | Atomic rule | `rule_engine.py::detect_weak_1` | 9 tests |
| WEAK-2 | Atomic rule | `rule_engine.py::detect_weak_2` | 8 tests |
| CLIMAX-SELL-1 | Atomic rule | `rule_engine.py::detect_climax_sell_1` | 9 tests |
| CONF-1 | Atomic rule | `rule_engine.py::detect_conf_1` | 9 tests |
| AVOID-NEWS-1 | Atomic rule | `rule_engine.py::detect_avoid_news_1` | 10 tests |
| TEST-SUP-1 | Atomic rule | `rule_engine.py::detect_test_sup_1` | 7 tests |
| TEST-SUP-2 | Atomic rule | `rule_engine.py::detect_test_sup_2` | 10 tests |
| TEST-DEM-1 | Atomic rule | `rule_engine.py::detect_test_dem_1` | 9 tests |
| TREND-VAL-1 | Trend rule | `rule_engine.py::detect_trend_val_1` | 8 tests |
| TREND-ANOM-1 | Trend rule | `rule_engine.py::detect_trend_anom_1` | 6 tests |
| TREND-ANOM-2 | Cluster rule | `rule_engine.py::detect_trend_anom_2` | 11 tests |
| CONF-2 | Meta rule | `rule_engine.py::detect_conf_2` | 11 tests |
| AVOID-TRAP-1 | Avoidance rule | `rule_engine.py::detect_avoid_trap_1` | 6 tests |
| AVOID-COUNTER-1 | Avoidance rule | `rule_engine.py::detect_avoid_counter_1` | 5 tests |
| CTX-1 | Context gate | `context_gates.py::_check_ctx_1` | 10 tests |
| CTX-2 | Context gate | `context_gates.py::_check_ctx_2` + `risk_engine.py` | 10 tests |
| CTX-3 | Context gate | `context_gates.py::_check_ctx_3` | 11 tests |
| ENTRY-LONG-1 | Setup | `setup_composer.py::SetupComposer` | 8 tests |
| ENTRY-LONG-2 | Setup | `setup_composer.py::SetupComposer` | 9 tests |
| ENTRY-SHORT-1 | Setup | `setup_composer.py::SetupComposer` | 13 tests |
| ENTRY-SHORT-2 | Setup | `setup_composer.py::SetupComposer` | 12 tests |

### Defined in docs but not yet implemented (MISSING) — 3 items
- VAL-2 (single-bar validation, small progress)
- STR-2 (additional strength pattern)
- CLIMAX-SELL-2 (upper-wick repetition emphasis)

### EXTRA items
- None.

---

## 4) Traceability matrix status

| Status | Count | Details |
|--------|-------|---------|
| OK | 25 | All 18 rules + 3 gates + 4 setups |
| PARTIAL | 0 | — |
| MISSING | 3 | VAL-2, STR-2, CLIMAX-SELL-2 |
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
| Ingest | OK | `AlpacaBarFetcher` → `BarStore` (SQLite), IEX free-tier feed, daily + intraday |
| Resample | OK | Daily bars stored separately; multi-timeframe pipeline support |
| Features | OK | `feature_engine.py::extract_features` → `CandleFeatures` |
| Relative Measures | OK | `vol_rel`, `spread_rel` with SMA baselines, config-driven windows |
| Structure | OK | `context_engine.py::_detect_location` + `_detect_congestion` |
| Context | OK | `context_engine.py::analyze` → `ContextSnapshot` (trend, location, congestion, volume trend) |
| Rule Engine | OK | 18 detectors across 4 levels (bar, trend, cluster, meta) + 2 avoidance; pure functions, `SignalEvent[]` only |
| Context Gates | OK | CTX-1 + CTX-2 (policy-driven, daily alignment) + CTX-3 (congestion awareness) |
| Setup Composer | OK | Data-driven `_SETUP_DEFS`; 4 setups (2 long, 2 short); state machine with OR-completers, shared triggers |
| Risk Engine | OK | Bidirectional stops (bar-based + ATR), position sizing, CTX-2 REDUCE_RISK, hard rejects |
| Execution | OK | Backtest: next-bar-open; Paper: `submit_intent()` with risk-computed size |
| Journal | OK | `JournalWriter` with trade + signal events |

### Layer separation: PASS
- Rule Engine emits `SignalEvent[]` only (no orders, no sizing)
- Setup Composer matches sequences only (no sizing, no stops)
- Risk Engine owns stops, sizing, and rejects
- Avoidance rules are informational (soft) or invalidation-triggering (hard), per canonical intent
- All CLI commands use canonical pipeline

---

## 6) Determinism and config compliance

### Status: PASS
- All thresholds config-driven via `VPAConfig` frozen dataclass tree
- JSON schema validation on load (`vpa_config.schema.json`)
- Context engine parameters configurable: `window_K`, `location_lookback`, `congestion_window`, `congestion_pct`
- Candle pattern thresholds: hammer, shooting star, long-legged doji
- Volume/spread classification: 4-state / 3-state with config boundaries
- ATR parameters: period, stop_multiplier, enabled flag
- Per-symbol configuration: `vpa.{SYMBOL}.json` overrides with deep-merge
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
| Daily overlay no-lookahead | **PASS** | Daily context computed from bars prior to current intraday bar (Commit 39) |

---

## 8) Tests + fixtures

### Test suite: 555 tests, 0 failures

| Test File | Count | Coverage |
|-----------|-------|----------|
| `test_rule_engine.py` | 170 | All 18 rules + orchestrators + mutual exclusion |
| `test_setup_composer.py` | 42 | 4 setups + invalidation + expiration + cross-direction + shared triggers |
| `test_vpa_config.py` | 40 | Config loading, validation, deep-merge, per-symbol overrides |
| `test_context_gates.py` | 37 | CTX-1, CTX-2 (3 policies), CTX-3, gate interactions |
| `test_risk_engine.py` | 34 | Bidirectional sizing, bar + ATR stops, rejects, CTX-2 policy |
| `test_backtest.py` | 26 | Backtest runner: long + short lifecycle, fill, stop-out, journal |
| `test_context_engine.py` | 23 | Trend, location, congestion, volume trend detection |
| `test_scheduler.py` | 23 | Market hours, bar alignment, weekend handling |
| `test_daily_context.py` | 21 | Daily trend analyzer, alignment computation |
| `test_classification.py` | 19 | Volume + spread classifiers |
| `test_atr.py` | 17 | ATR calculation + config integration |
| `test_pipeline.py` | 17 | Integration: bars → TradeIntent + volume guard + multi-TF |
| `test_canonical_models.py` | 15 | Data model construction + immutability |
| `test_vpa_core_features.py` | 14 | Candle anatomy functions |
| `test_golden_fixtures.py` | 9 | End-to-end pipeline replay from JSON (9 fixtures) |
| `test_feature_engine.py` | 8 | Feature extraction pipeline |
| `test_vocab_lint.py` | 8 | Vocabulary enforcement |
| `test_data_pipeline.py` | 7 | Data pipeline (store + fetch) |
| `test_daily_helper.py` | 6 | Daily bar helpers |
| `test_cli.py` | 6 | CLI commands (scan, backtest, status, paper) |
| `test_config.py` | 4 | Base config loader |
| Others | 9 | Context helpers, fetcher, execution, journal |

### Golden fixtures (9 total)
- `FXT-VAL-1-basic.json` — atomic: bullish drive validation
- `FXT-ANOM-1-basic.json` — atomic: trap-up anomaly
- `FXT-CLIMAX-SELL-1-basic.json` — atomic: selling climax distribution
- `FXT-WEAK-2-basic.json` — atomic: no-demand shooting star
- `FXT-ENTRY-LONG-1-seq.json` — setup: TEST-SUP-1 → VAL-1 sequence
- `FXT-ENTRY-SHORT-1-seq.json` — setup: CLIMAX-SELL-1 → WEAK-1 sequence
- `FXT-INTEG-anom1-no-setup.json` — integration: signal but no setup match
- `FXT-INTEG-neutral-bar.json` — integration: no signals expected
- `FXT-INTEG-vol-guard.json` — integration: low-liquidity guard blocks signals

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
| Data ingestion (Alpaca IEX, daily + intraday) | OK |
| Bar storage (SQLite, multi-timeframe) | OK |
| One-shot scan (`vpa scan`) | OK |
| Backtest (`vpa backtest`) | OK |
| Paper trading (`vpa paper`) | OK |
| Live scheduler (`vpa paper --live`) | OK |
| Market-hours awareness | OK |
| Multi-timeframe analysis (daily → intraday) | OK |
| ATR-based stop optimization | OK |
| Per-symbol configuration | OK |
| Position/status tracking (`vpa status`) | OK |
| Journal logging | OK |

---

## 11) Phase completion history

| Phase | Commits | Key Deliverables | Tests Added |
|-------|---------|------------------|-------------|
| A — Foundation | 1–5 | Models, config, vocabulary | +57 |
| B — Pipeline skeleton | 6–10 | 5 stages, VAL-1, ANOM-1, ENTRY-LONG-1 | +72 |
| C — Integration + backtest | 11–13 | Pipeline orchestrator, backtest runner, no_demand removed | +31 |
| D — Expand rules | 14–21 | 8 more rules, ENTRY-LONG-2, CLI scan | +96 |
| E — Hardening + gates | 22–27 | Context engine, CTX-2/CTX-3, golden fixtures | +56 |
| F — Live data + scheduler | 28–29 | Alpaca ingest, paper scheduler | +0 (infra) |
| G — Short-side + tuning | 30–36 | WEAK-2, CLIMAX-SELL-1, ENTRY-SHORT-1, volume guard | +63 |
| H — Multi-TF + stops | 37–43 | Daily trend, ATR stops, per-symbol config | +68 |
| I — Extended rules | 44–49 | 8 new rules, ENTRY-SHORT-2 | +112 |
