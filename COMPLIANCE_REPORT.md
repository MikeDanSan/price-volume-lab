# COMPLIANCE_REPORT.md
**VPA Canonical System — Compliance Report**
- Date: 2026-02-17
- Code version: 0.1.0 (pyproject.toml)
- Config version: 0.1 (vpa.default.json)
- Dataset: N/A (audit only; no backtest run)

---

## 1) Executive summary
- **Overall status: FAIL**
- Blocking issues: 7
- Drift issues: 5
- Missing implementations: 22+ rule/setup IDs
- Missing tests: all VPA rules (0 rule-level tests exist)

The repo has solid governance scaffolding (canonical docs, registry, config schema, fixture format, blacklist/whitelist, templates) but the **implementation is still at MVP-0**: only one pre-registry setup (`no_demand`) exists in code, the pipeline stages are conflated, and no registered Rule IDs have implementations or tests.

---

## 2) Vocabulary drift (docs + code comments)

### Blacklist hits

| File | Lines | Blacklisted Term(s) | Context |
|------|-------|---------------------|---------|
| `docs/VPA_METHODOLOGY.md` | 24, 26, 502, 504 | **wyckoff** | Section headers and explanatory prose ("The Three Wyckoff Laws", "The Wyckoff Market Cycle") |
| `docs/VPA_METHODOLOGY.md` | 393, 409, 441, 456, 474, 541, 545, 668, 681 | **upthrust** | Setup name and references throughout |
| `docs/VPA_METHODOLOGY.md` | 416, 418, 441, 474, 515, 518, 669, 682 | **spring**, **shakeout** | Setup name and references |
| `docs/VPA_METHODOLOGY.md` | 409 | **stop run** | "…trigger buying (breakout traders, stop runs)…" |
| `docs/vpa-ck/vpa_canonical_model.md` | 61 | **wyckoff** | "Effort vs Result (Wyckoff law used inside VPA)" — explanatory |
| `docs/vpa-ck/vpa_system_spec.md` | 234 | **wyckoff** | "This is not Wyckoff labeling" — disclaimer |

### Exceptions applied
- Hits in `vpa_canonical_model.md`, `vpa_system_spec.md`, `vpa_ai_context.md` are in the `VPA_VOCAB_EXCEPTIONS.txt` list (used in "we do NOT do this" context). Acceptable.
- Hits in governance files (`CANONICAL_CONTRACT.md`, `VPA_DOC_INDEX.md`) reference terms only to prohibit them. Acceptable.

### Non-exception violations requiring action
- **`docs/VPA_METHODOLOGY.md`** contains 30+ occurrences of blacklisted terms (`wyckoff`, `upthrust`, `spring`, `shakeout`, `stop run`). This file is **NOT** in exceptions. It was written before the canonical docs and uses Wyckoff/VSA terminology freely.

### Recommended replacements
| Blacklisted Term | Couling-canonical Replacement |
|------------------|-------------------------------|
| wyckoff | (remove or rephrase as "Couling's framework" / "effort vs result law") |
| upthrust | "failed breakout at resistance" or define as new glossary entry if Couling uses it |
| spring / shakeout | "failed breakdown at support" / "stop-hunt probe" or define if Couling uses it |
| stop run | "stop-hunt / manipulation probe" (see AVOID-NEWS-1) |

### Additional vocabulary note
- `docs/VPA_METHODOLOGY.md` uses "smart money" (lines 518, 545) — not blacklisted, but not in the whitelist. Couling's glossary term is **"insiders"**. Recommend replacing for consistency.

### Scripts
- `scripts/vpa_vocab_lint.*` does **NOT exist** yet. The blacklist/whitelist/exceptions files exist but there is no automated linter. This is a gap.

---

## 3) Registry coverage (VPA_RULE_REGISTRY.yaml)

### Registered
- Atomic rules: **2** (VAL-1, ANOM-1)
- Setups: **1** (ENTRY-LONG-1)

### Defined in VPA_ACTIONABLE_RULES.md but NOT yet registered
- Atomic rules: ~18 (VAL-2, ANOM-2, TREND-VAL-1, TREND-ANOM-1, TREND-ANOM-2, STR-1, WEAK-1, WEAK-2, TEST-SUP-1, TEST-SUP-2, TEST-DEM-1, CLIMAX-SELL-1, CLIMAX-SELL-2, AVOID-NEWS-1, AVOID-TRAP-1, AVOID-COUNTER-1, CONF-1, CONF-2)
- Context gates: 3 (CTX-1, CTX-2, CTX-3)
- Setups: 3 (ENTRY-SHORT-1, ENTRY-LONG-2, ENTRY-SHORT-2)

### IDs in code missing from registry ("EXTRA")
- `no_demand` — `src/vpa_core/setups/no_demand.py` + `src/vpa_core/signals.py`

### IDs in registry missing from code ("MISSING")
- **All 3 registered IDs** (VAL-1, ANOM-1, ENTRY-LONG-1) have zero implementation.

---

## 4) Traceability matrix status (VPA_TRACEABILITY.md)

| Status | Count | Details |
|--------|-------|---------|
| OK | 0 | — |
| PARTIAL | 0 | — |
| MISSING | 22+ | All registered and spec'd rules/setups |
| DRIFT | 2 | `Signal` vs `SignalEvent` schema; `TradePlan` vs `TradeIntent` schema |
| EXTRA | 1 | `no_demand` setup in code, not registered |

---

## 5) Pipeline compliance (VPA_SIGNAL_FLOW.md)

### Required stage ordering
```
Ingest → Resample → Features → Relative Measures → Structure → Context →
Rule Engine → Context Gates → Setup Composer → Risk → Execution → Journal
```

### Stage ordering violations

| # | Violation | Location | Details |
|---|-----------|----------|---------|
| P-1 | **No stage separation** | `src/vpa_core/signals.py` | `evaluate()` conflates Rule Engine + Context Gates + Setup Composer into one function. Returns `(Signal, TradePlan)` directly. |
| P-2 | **No Structure Engine** | — | Swing detection, congestion, S/R zones are not implemented. |
| P-3 | **No Resample / MTF** | — | No fast/primary/dominant timeframe stack; single-timeframe only. |
| P-4 | **No CandleFeatures stage** | — | Features are computed ad-hoc inside setup functions, not as a discrete stage producing `CandleFeatures` objects. |

### Layer separation violations

| # | Violation | Location | Details |
|---|-----------|----------|---------|
| L-1 | **Rule engine produces TradePlan** | `src/vpa_core/signals.py:evaluate()` | Should emit atomic `SignalEvent[]` only. TradePlan/TradeIntent is Risk Engine output. |
| L-2 | **Backtest runner does sizing** | `src/backtest/runner.py` lines 83-94 | `risk_pct_per_trade`, `qty` calculation belongs in Risk Engine. |
| L-3 | **Stop level set by signal function** | `src/vpa_core/signals.py` line 42 | Stop is set to `current.high` inside signal evaluation. Stops belong to Risk Engine. |

### Context gate enforcement violations

| # | Violation | Details |
|---|-----------|---------|
| G-1 | **CTX-1 not implemented** | No `trendLocation != UNKNOWN` check before acting on anomalies. The `no_demand` setup checks `detect_context == CONTEXT_UPTREND` but this is not the CTX-1 gate (which requires trend *location*: TOP/BOTTOM/MIDDLE). |
| G-2 | **CTX-2 not implemented** | No dominant-trend alignment check. |
| G-3 | **CTX-3 not implemented** | No congestion awareness check. |

---

## 6) Determinism and config compliance

### Hardcoded thresholds found

| # | Location | Parameter | Hardcoded Value | Config Key (should use) |
|---|----------|-----------|-----------------|-------------------------|
| D-1 | `src/vpa_core/relative_volume.py:classify_relative_volume()` | `high_threshold` | `1.2` (default arg) | `vol.thresholds.high_gt` |
| D-2 | `src/vpa_core/relative_volume.py:classify_relative_volume()` | `low_threshold` | `0.8` (default arg) | `vol.thresholds.low_lt` |
| D-3 | `src/vpa_core/relative_volume.py:relative_volume_for_bar()` | `lookback` | `20` (default arg) | `vol.avg_window_N` |
| D-4 | `src/vpa_core/context.py:detect_context()` | `lookback` | `5` (default arg) | `trend.window_K` |
| D-5 | `src/vpa_core/setups/no_demand.py:check_no_demand()` | `context_lookback` | `3` (default arg, differs from D-4!) | `trend.window_K` |
| D-6 | `src/vpa_core/setups/no_demand.py:check_no_demand()` | `volume_lookback` | `20` (default arg) | `vol.avg_window_N` |
| D-7 | `src/backtest/runner.py:run_backtest()` | `slippage_bps` | `5.0` (default arg) | `slippage.value` |

**Note**: `vpa.default.json` and `vpa_config.schema.json` exist and define correct parameters, but they are **not loaded or consumed** by any rule-engine code. The `config/loader.py` loads `config.yaml` for CLI/backtest settings only (AppConfig) — it does not load VPA rule parameters.

### Config/schema mismatches
- `RelativeVolume` enum has 3 states (`HIGH`, `NORMAL`, `LOW`) but spec requires 4 (`LOW`, `AVERAGE`, `HIGH`, `ULTRA_HIGH`). Missing `ULTRA_HIGH` state.
- No `SpreadState` enum or classification exists in code (spec requires `NARROW`, `NORMAL`, `WIDE`).

### Non-deterministic behavior found
- None confirmed. All code paths are deterministic given inputs. However, the parameter defaults mean different runs could use different thresholds if defaults are changed, since config isn't loaded.

### Spread definition conflict
- **`docs/VPA_METHODOLOGY.md`** and **`docs/GLOSSARY.md`** define spread = `high - low` (range).
- **`docs/vpa-ck/vpa_glossary.md`** and **`VPA_ACTIONABLE_RULES.md`** define spread = `abs(close - open)` (body).
- **Code** (`features.py`, `Bar.spread()`) implements spread = `high - low` (follows old docs, not canonical).
- **Status**: DRIFT from canonical spec. **UNKNOWN / NEEDS BOOK CHECK** on Couling's actual definition.

---

## 7) Backtest anti-lookahead checks

| Check | Status | Details |
|-------|--------|---------|
| Bar-close evaluation enforced | **PASS** (backtest) | `runner.py` iterates completed bars; signals computed on `bars[:i+1]` |
| Next-bar execution enforced | **PASS** (backtest) | Entry fill at `bars[i+1].open` with slippage |
| Stop fill model deterministic | **PASS** | Stop checked against next-bar range; fills at stop +/- slippage |
| Lookahead risks found | **WARN** (paper mode) | `cli/main.py:paper()` calls `executor.submit(…, current_bar.close)` — fills immediately at current bar close, NOT next-bar open. This violates the `NEXT_BAR_OPEN` contract in paper mode. |

---

## 8) Tests + fixtures

### Fixture runner status
- **No fixture runner exists**. Fixtures are JSON files (`FXT-ANOM-1-basic.json`, `FXT-ENTRY-LONG-1-seq.json`) but no code loads or validates them.

### Missing fixtures for rules/setups
- `FXT-VAL-1-basic` — referenced in registry but file does not exist.
- All other rules/setups lack fixtures entirely.

### Integration replay status
- No integration test exists.

### Existing tests (unrelated to VPA rules)
- `tests/test_alpaca_fetcher.py` — Alpaca SDK adapter (mocked)
- `tests/test_cli.py` — CLI smoke tests
- `tests/test_config.py` — Config loader

---

## 9) Required actions (blocking items)

| # | ID | File(s) | Issue | Acceptance Criteria | Tests to Add |
|---|----|---------|-------|---------------------|--------------|
| B-1 | — | `src/vpa_core/contracts.py` | Data models don't match spec (`SignalEvent`, `CandleFeatures`, `ContextSnapshot`, `TradeIntent`) | Models match VPA_SYSTEM_SPEC §3.3 exactly | Unit tests for serialization + field validation |
| B-2 | VAL-1 | `src/vpa_core/` (new) | No implementation of any registered atomic rule | VAL-1 passes `FXT-VAL-1-basic` fixture | Golden-fixture test |
| B-3 | ANOM-1 | `src/vpa_core/` (new) | No implementation of any registered atomic rule | ANOM-1 passes `FXT-ANOM-1-basic` fixture | Golden-fixture test |
| B-4 | ENTRY-LONG-1 | `src/vpa_core/` (new) | No implementation of registered setup | ENTRY-LONG-1 passes `FXT-ENTRY-LONG-1-seq` fixture | Setup-sequence test |
| B-5 | `no_demand` | `src/vpa_core/setups/no_demand.py` | EXTRA: exists but not registered; must be registered or removed | Either: (a) map to registered ID + add to registry, or (b) remove | Update tests to match |
| B-6 | — | `src/vpa_core/signals.py` | Pipeline conflates Rule Engine + Setup Composer + partial Risk | Separate stages per VPA_SIGNAL_FLOW.md | Integration pipeline test |
| B-7 | — | `src/vpa_core/relative_volume.py`, `context.py`, `no_demand.py` | Hardcoded thresholds; VPA config not loaded | All thresholds read from loaded VPA config | Config-override fixture test |
