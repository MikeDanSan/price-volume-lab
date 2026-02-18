# COMPLIANCE_REPORT.md
**VPA Canonical System — Compliance Report**
- Date: 2026-02-18 (updated from initial audit 2026-02-17)
- Code version: 0.1.0 (pyproject.toml)
- Config version: 0.1 (vpa.default.json)
- Commits since audit: 21

---

## 1) Executive summary
- **Overall status: PASS (core pipeline)**
- Blocking issues: 0 (all 7 original blockers resolved)
- Drift issues: 0 (spread definition resolved, data models aligned)
- Implemented rules: 8 atomic rules, 2 setups, 3 context gates (1 partial)
- Tests: 244 passing, 0 failures

The system has a fully functional canonical pipeline (Features → Rules → Gates → Composer → Risk → Execution) with 8 Couling-aligned atomic rules, 2 long-entry setups, config-driven thresholds, and deterministic backtest execution. The CLI scan command displays full pipeline reasoning.

### Remaining work (non-blocking)
- 14 rule/setup IDs defined in docs but not yet implemented (trend-level, climax, short-side)
- Context Engine is stubbed (uses simple trend detector, not full structure analysis)
- `paper` CLI command still uses deprecated `evaluate()` path
- No multi-timeframe support yet

---

## 2) Vocabulary drift (docs + code comments)

### Status: CONTROLLED
- `scripts/vpa_vocab_lint.py` exists and enforces blacklist scanning (Commit 5)
- `docs/VPA_METHODOLOGY.md` added to `VPA_VOCAB_EXCEPTIONS.txt` as legacy/educational content
- All canonical code (`src/vpa_core/`) is free of blacklisted terms
- Exception-listed governance files reference terms only to prohibit them

### Vocab lint results
- Zero violations in code files (`*.py`)
- Zero violations in canonical docs (`docs/vpa-ck/`, `docs/vpa/`)
- Legacy docs in exceptions list: `VPA_METHODOLOGY.md`, `DECISIONS.md`, `README.md`, etc.

---

## 3) Registry coverage (VPA_RULE_REGISTRY.yaml)

### Registered AND implemented (OK)

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
| CTX-1 | Context gate | `context_gates.py::apply_gates` | 10 tests |
| ENTRY-LONG-1 | Setup | `setup_composer.py::SetupComposer` | 8 tests |
| ENTRY-LONG-2 | Setup | `setup_composer.py::SetupComposer` | 9 tests |

### Defined in docs but not yet implemented (MISSING)
- Trend-level rules: TREND-VAL-1, TREND-ANOM-1, TREND-ANOM-2
- Additional strength/weakness: WEAK-2, STR-2, VAL-2
- Tests: TEST-SUP-2, TEST-DEM-1
- Climax: CLIMAX-SELL-1, CLIMAX-SELL-2
- Avoidance: AVOID-TRAP-1, AVOID-COUNTER-1
- Confirmation: CONF-2
- Context gates: CTX-2 (PARTIAL), CTX-3
- Setups: ENTRY-SHORT-1, ENTRY-SHORT-2

### EXTRA items
- None. Legacy `no_demand` removed in Commit 13.

---

## 4) Traceability matrix status

| Status | Count | Details |
|--------|-------|---------|
| OK | 11 | VAL-1, ANOM-1, ANOM-2, STR-1, WEAK-1, CONF-1, AVOID-NEWS-1, TEST-SUP-1, CTX-1, ENTRY-LONG-1, ENTRY-LONG-2 |
| PARTIAL | 1 | CTX-2 (dominant alignment check in Risk Engine, not a full gate) |
| MISSING | 14 | Trend-level, climax, short-side rules and setups |
| DRIFT | 0 | All resolved |
| EXTRA | 0 | `no_demand` removed |

See `docs/vpa/VPA_TRACEABILITY.md` for the full matrix.

---

## 5) Pipeline compliance (VPA_SIGNAL_FLOW.md)

### Required stage ordering
```
Ingest → Resample → Features → Relative Measures → Structure → Context →
Rule Engine → Context Gates → Setup Composer → Risk → Execution → Journal
```

### Status: PASS (implemented stages)

| Stage | Status | Implementation |
|-------|--------|---------------|
| Ingest | OK | `AlpacaBarFetcher` → `BarStore` (SQLite) |
| Resample | N/A | Single-timeframe only (MTF is future work) |
| Features | OK | `feature_engine.py::extract_features` → `CandleFeatures` |
| Relative Measures | OK | `vol_rel`, `spread_rel` with SMA baselines, config-driven windows |
| Structure | STUB | Simple trend detector; full swing/S-R not yet built |
| Context | STUB | `_build_context()` bridges to `ContextSnapshot`; full engine future |
| Rule Engine | OK | 8 detectors, pure functions, `SignalEvent[]` only |
| Context Gates | OK | CTX-1 implemented; CTX-2 partial (in Risk Engine) |
| Setup Composer | OK | Data-driven `_SETUP_DEFS`; 2 setups; state machine |
| Risk Engine | OK | Stop placement, position sizing, CTX-2, hard rejects |
| Execution | OK | Backtest: next-bar-open; Paper: needs migration |
| Journal | OK | `JournalWriter` with trade + signal events |

### Layer separation: PASS
- Rule Engine emits `SignalEvent[]` only (no orders, no sizing)
- Setup Composer matches sequences only (no sizing, no stops)
- Risk Engine owns stops, sizing, and rejects
- Old `signals.evaluate()` deprecated; returns empty list

---

## 6) Determinism and config compliance

### Status: PASS (canonical pipeline)
- All thresholds config-driven via `VPAConfig` frozen dataclass tree
- JSON schema validation on load (`vpa_config.schema.json`)
- Candle pattern thresholds: hammer, shooting star, long-legged doji
- Volume/spread classification: 4-state / 3-state with config boundaries
- No magic numbers in canonical rule engine or pipeline

### Legacy code (deprecated path)
- `relative_volume.py::classify_relative_volume()` still has default args (3-state) — DEPRECATED
- `context.py::detect_context()` has default lookback — used as bridge only
- These are not called by the canonical pipeline

### Spread definition: RESOLVED
- Canonical: `spread = |close - open|` (candle body)
- `bar_range = high - low` (full extent)
- Code, tests, and docs all aligned since Commit 1

---

## 7) Backtest anti-lookahead checks

| Check | Status | Details |
|-------|--------|---------|
| Bar-close evaluation enforced | **PASS** | `run_pipeline()` called on completed bars only |
| Next-bar execution enforced | **PASS** | Entry fill at `bars[i+1].open` |
| Stop fill model deterministic | **PASS** | Stop checked against next-bar range |
| Config-driven execution semantics | **PASS** | `signal_eval: BAR_CLOSE_ONLY`, `entry_timing: NEXT_BAR_OPEN` |
| Lookahead risks | **WARN** | `paper` command still uses legacy path with current-bar fill |

---

## 8) Tests + fixtures

### Test suite: 244 tests, 0 failures

| Test File | Count | Coverage |
|-----------|-------|----------|
| `test_rule_engine.py` | 78 | All 8 rules + orchestrator |
| `test_vpa_config.py` | 24 | Config loading, validation, overrides |
| `test_canonical_models.py` | 15 | Data model construction + immutability |
| `test_classification.py` | 19 | Volume + spread classifiers |
| `test_feature_engine.py` | 8 | Feature extraction pipeline |
| `test_context_gates.py` | 10 | CTX-1 gate logic |
| `test_setup_composer.py` | 17 | Both setups + invalidation + expiration |
| `test_risk_engine.py` | 13 | Sizing, stops, rejects, CTX-2 |
| `test_pipeline.py` | 8 | Integration: bars → TradeIntent |
| `test_backtest.py` | 9 | Backtest runner + execution semantics |
| `test_vpa_core_features.py` | 12 | Candle anatomy functions |
| `test_vocab_lint.py` | 8 | Vocabulary enforcement |
| `test_cli.py` | 5 | CLI commands (scan, backtest, status, paper) |
| Others | 18 | Config loader, bar store, fetcher, etc. |

---

## 9) Original blocking items — resolution status

| # | Issue | Status | Resolution |
|---|-------|--------|------------|
| B-1 | Data models don't match spec | **RESOLVED** (Commit 2) | `CandleFeatures`, `ContextSnapshot`, `SignalEvent`, `TradeIntent` match VPA_SYSTEM_SPEC §3.3 |
| B-2 | VAL-1 not implemented | **RESOLVED** (Commit 7) | `detect_val_1` with 7 tests |
| B-3 | ANOM-1 not implemented | **RESOLVED** (Commit 7) | `detect_anom_1` with 6 tests |
| B-4 | ENTRY-LONG-1 not implemented | **RESOLVED** (Commit 9) | SetupComposer with 8 tests |
| B-5 | `no_demand` EXTRA in code | **RESOLVED** (Commit 13) | Removed; all detection in canonical pipeline |
| B-6 | Pipeline conflates stages | **RESOLVED** (Commit 11) | Separate stages per VPA_SIGNAL_FLOW.md |
| B-7 | Hardcoded thresholds | **RESOLVED** (Commit 3-4) | All canonical thresholds via `VPAConfig` |
