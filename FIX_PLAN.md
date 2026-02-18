# FIX_PLAN.md
**VPA Canonical System — Fix Plan**
- Date: 2026-02-17 (updated 2026-02-18)
- Goal: Bring repo from FAIL to PASS on compliance gates with smallest safe commits.
- Reference: `COMPLIANCE_REPORT.md`

## Rules
- One commit per focused change.
- Tests in same commit.
- No new VPA terms, no new rules unless explicitly added to registry + docs.
- Couling (2013) is the only authority.

---

## Phase A — Foundation alignment (contracts + config + vocabulary) ✅

| Commit | Description | Status |
|--------|-------------|--------|
| 1 | Resolve spread definition conflict | ✅ Done |
| 2 | Align data models to canonical spec | ✅ Done |
| 3 | VPA config loader + schema validation | ✅ Done |
| 4 | Volume + spread classification aligned to spec | ✅ Done |
| 5 | Vocabulary lint script + VPA_METHODOLOGY.md cleanup | ✅ Done |

---

## Phase B — Pipeline skeleton (stage separation) ✅

| Commit | Description | Status |
|--------|-------------|--------|
| 6 | Feature engine stage (CandleFeatures per bar) | ✅ Done |
| 7 | Rule engine stage (VAL-1 + ANOM-1, SignalEvent[] only) | ✅ Done |
| 8 | Context gate stage (CTX-1) | ✅ Done |
| 9 | Setup composer stage (ENTRY-LONG-1) | ✅ Done |
| 10 | Risk engine stage (stop + size + reject) | ✅ Done |

---

## Phase C — Integration + backtest alignment ✅

| Commit | Description | Status |
|--------|-------------|--------|
| 11 | Pipeline orchestrator (wire stages together) | ✅ Done |
| 12 | Backtest runner aligned to pipeline | ✅ Done |
| 13 | `no_demand` disposition (removed) | ✅ Done |

---

## Phase D — Expand rule coverage (incremental) ✅

| Commit | Description | Status |
|--------|-------------|--------|
| 14 | TEST-SUP-1 (test of support) | ✅ Done |
| 15 | ANOM-2 (big effort, little result) | ✅ Done |
| 16 | STR-1 (hammer) | ✅ Done |
| 17 | WEAK-1 (shooting star) | ✅ Done |
| 18 | CONF-1 (positive response) | ✅ Done |
| 19 | AVOID-NEWS-1 (long-legged doji on low volume) | ✅ Done |
| 20 | ENTRY-LONG-2 (STR-1 → CONF-1 sequence) | ✅ Done |
| 21 | CLI scan command migrated to canonical pipeline | ✅ Done |

---

## Phase E — Hardening + next milestones (M3–M6)

### Commit 22: Update compliance report + fix plan checkpoint
- **Scope:** Bring `COMPLIANCE_REPORT.md` and `FIX_PLAN.md` current with 21 completed commits.
- **Files:** `COMPLIANCE_REPORT.md`, `FIX_PLAN.md`
- **Acceptance criteria:**
  - Report reflects 244 tests, 11 OK traceability items, 0 blocking issues.
  - Plan shows all completed phases + Phase E roadmap.

### Commit 23: Migrate CLI `paper` command to canonical pipeline
- **Scope:** Replace deprecated `evaluate()` call in `paper` command with `run_pipeline()`.
- **Files:** `src/cli/main.py`, `tests/test_cli.py`
- **Acceptance criteria:**
  - `paper` command uses canonical pipeline (same as `scan` and `backtest`).
  - Deprecation warning removed.
  - Paper executor respects `NEXT_BAR_OPEN` entry timing.
- **Tests:** CLI `paper` smoke test updated.

### Commit 24: Context engine stub → real trend detector
- **Scope:** Replace `_build_context()` bridge with a proper `ContextEngine` that produces `ContextSnapshot` from bar history.
- **Files:** `src/vpa_core/context_engine.py` (new), update `pipeline.py`, `cli/main.py`, `backtest/runner.py`
- **Acceptance criteria:**
  - `ContextEngine.analyze(bars, config) -> ContextSnapshot` with real trend, location, congestion fields.
  - Pipeline calls context engine instead of `_build_context()` stub.
  - Trend direction uses SMA crossover or swing analysis (config-driven window).
  - Location classification: TOP/BOTTOM/MIDDLE based on lookback range percentile.
- **Tests:** Known uptrend bars → UPTREND + MIDDLE; bars near recent high → TOP.

### Commit 25: CTX-2 full implementation (dominant alignment gate)
- **Scope:** Move CTX-2 from Risk Engine heuristic to proper context gate.
- **Files:** `src/vpa_core/context_gates.py`, `src/vpa_core/risk_engine.py`
- **Acceptance criteria:**
  - CTX-2 checks dominant timeframe alignment in `apply_gates()`.
  - Risk Engine no longer duplicates this check.
  - Traceability updated from PARTIAL to OK.
- **Tests:** Signal blocked when dominant trend opposes; passes when aligned.

### Commit 26: CTX-3 implementation (congestion awareness)
- **Scope:** Implement congestion detection and CTX-3 gate.
- **Files:** `src/vpa_core/context_engine.py`, `src/vpa_core/context_gates.py`
- **Acceptance criteria:**
  - Context engine detects congestion zones (tight range clusters).
  - CTX-3 blocks low-priority signals inside congestion unless breakout volume present.
- **Tests:** Narrow-range bars → congestion flagged; high-volume breakout bar → not blocked.

### Commit 27: Golden-fixture runner
- **Scope:** Create a runner that loads `fixtures/vpa/*.json` files and replays them against the pipeline.
- **Files:** `tests/test_golden_fixtures.py` (new), `scripts/run_fixtures.py` (optional)
- **Acceptance criteria:**
  - Each fixture specifies input bars + expected signals/setups/intents.
  - Runner asserts pipeline output matches expectations.
  - CI-ready (pytest discoverable).
- **Tests:** Self-referential: the fixtures ARE the tests.

---

## M6 checkpoint criteria (review with user before proceeding)
- All 3 context gates (CTX-1, CTX-2, CTX-3) at OK status
- Context engine produces real trend + location + congestion
- Golden fixtures validate end-to-end pipeline
- CLI scan + paper + backtest all use canonical pipeline
- 11+ rules, 2+ setups, 3 gates — enough for meaningful backtest
- Ready to discuss: short-side rules, MTF, live paper trading

---

## Commit dependency graph (Phase E)

```
22 (checkpoint) → 23 (paper migration) → 24 (context engine)
                                              ↓
                                    25 (CTX-2 gate) → 26 (CTX-3 gate)
                                                          ↓
                                                   27 (golden fixtures)
                                                          ↓
                                                    ═══ M6 review ═══
```
