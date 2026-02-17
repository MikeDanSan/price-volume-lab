# FIX_PLAN.md
**VPA Canonical System — Fix Plan**
- Date: 2026-02-17
- Goal: Bring repo from FAIL to PASS on compliance gates with smallest safe commits.
- Reference: `COMPLIANCE_REPORT.md` (same date)

## Rules
- One commit per focused change.
- Tests in same commit.
- No new VPA terms, no new rules unless explicitly added to registry + docs.
- Couling (2013) is the only authority.

---

## Phase A — Foundation alignment (contracts + config + vocabulary)

### Commit 1: Resolve spread definition conflict
- **Scope:** Settle whether `spread` means body (`|close-open|`) or range (`high-low`) per Couling.
- **Files:** `docs/vpa-ck/vpa_glossary.md`, `docs/vpa-ck/vpa_actionable_rules.md`, `docs/vpa-ck/vpa_canonical_model.md`, `docs/GLOSSARY.md`, `src/vpa_core/features.py`, `src/vpa_core/contracts.py`
- **Acceptance criteria:**
  - All docs agree on one definition (book-verified).
  - Code `spread()` matches the settled definition.
  - A second function (e.g. `range_()` or `body()`) exists for the other measure.
  - If NEEDS BOOK CHECK: document explicitly and pick one pending verification.
- **Tests:** Unit test asserting `spread()` and `body()` / `range()` produce correct values for known bar.

### Commit 2: Align data models to canonical spec
- **Scope:** Introduce `CandleFeatures`, `ContextSnapshot`, `SignalEvent`, `TradeIntent` matching VPA_SYSTEM_SPEC §3.3.
- **Files:** `src/vpa_core/contracts.py` (add new models), `src/vpa_core/features.py` (produce `CandleFeatures`)
- **Acceptance criteria:**
  - New dataclasses/frozen classes match spec fields exactly.
  - `SignalEvent` has `id`, `name`, `tf`, `ts`, `class`, `directionBias`, `priority`, `evidence`, `requiresContextGate`.
  - Old `Signal`/`TradePlan` remain temporarily for backward compat; marked `@deprecated`.
- **Tests:** Construction + serialization tests for each new model.

### Commit 3: VPA config loader + schema validation
- **Scope:** Load `vpa.default.json` (or override) and validate against `vpa_config.schema.json`. Make config available to rule engine.
- **Files:** `src/config/vpa_config.py` (new), `src/config/__init__.py`, `docs/config/vpa.default.json`
- **Acceptance criteria:**
  - `load_vpa_config(path) -> VPAConfig` returns frozen dataclass with all params from schema.
  - Schema validation runs on load; raises on invalid.
  - All thresholds accessible: `config.vol.thresholds.low_lt`, etc.
- **Tests:** Load default config; load with overrides; reject invalid config.

### Commit 4: Volume + spread classification aligned to spec
- **Scope:** 4-state `VolumeState` (LOW/AVERAGE/HIGH/ULTRA_HIGH) + 3-state `SpreadState` (NARROW/NORMAL/WIDE), all config-driven.
- **Files:** `src/vpa_core/relative_volume.py` (refactor), `src/vpa_core/features.py` (add spread classification), `src/vpa_core/contracts.py` (enums)
- **Acceptance criteria:**
  - `classify_volume(vol_rel, config) -> VolumeState` with 4 states.
  - `classify_spread(spread_rel, config) -> SpreadState` with 3 states.
  - No hardcoded thresholds; all from VPA config.
  - Old `RelativeVolume` enum deprecated.
- **Tests:** Boundary tests for each threshold; config-override test.

### Commit 5: Vocabulary lint script + VPA_METHODOLOGY.md cleanup
- **Scope:** Create `scripts/vpa_vocab_lint.py`; fix or quarantine `docs/VPA_METHODOLOGY.md`.
- **Files:** `scripts/vpa_vocab_lint.py` (new), `docs/VPA_METHODOLOGY.md`
- **Acceptance criteria:**
  - Script scans `*.py`, `*.md`, `*.yaml` (excluding `.venv`, exceptions file entries).
  - Reports file:line for any blacklist hit not in an exception-listed file.
  - `docs/VPA_METHODOLOGY.md` either: (a) cleaned of blacklist terms, OR (b) added to exceptions with a "legacy/pre-canonical" header disclaimer. Recommend (b) for now since it's educational content.
  - Script exits non-zero on violations (CI-ready).
- **Tests:** Run script on repo; assert zero violations after fix.
- **Notes:** Blacklist terms "upthrust" and "spring" may need BOOK CHECK to decide if Couling uses them. If she does, add to whitelist with Couling-specific definitions. If not, replace with Couling-canonical alternatives.

---

## Phase B — Pipeline skeleton (stage separation)

### Commit 6: Feature engine stage (produces CandleFeatures per bar)
- **Scope:** Create `src/vpa_core/feature_engine.py` that takes `Bar` + `VPAConfig` → `CandleFeatures`.
- **Files:** `src/vpa_core/feature_engine.py` (new)
- **Acceptance criteria:**
  - Computes: spread, range, wicks, bodyRel, spreadRel, volRel, volState, spreadState, candleType.
  - All relative measures use rolling averages from config windows.
  - Pure function; no side effects.
- **Tests:** Golden-bar fixture asserting all computed fields.

### Commit 7: Rule engine stage (emits SignalEvent[] only)
- **Scope:** Create `src/vpa_core/rule_engine.py` with one function per registered atomic rule. Each returns `SignalEvent | None`.
- **Files:** `src/vpa_core/rule_engine.py` (new)
- **Acceptance criteria:**
  - `detect_val_1(features, config) -> SignalEvent | None` — implements VAL-1 per registry conditions.
  - `detect_anom_1(features, config) -> SignalEvent | None` — implements ANOM-1 per registry conditions.
  - Rule engine function collects all atomic signals: `evaluate_rules(features[], config) -> SignalEvent[]`.
  - **No TradePlan, no orders, no sizing.**
- **Tests:** `FXT-VAL-1-basic` fixture test; `FXT-ANOM-1-basic` fixture test. Create `FXT-VAL-1-basic.json`.

### Commit 8: Context gate stage
- **Scope:** Implement CTX-1 (trend-location-first gate) as a filter on SignalEvent[].
- **Files:** `src/vpa_core/context_gates.py` (new)
- **Acceptance criteria:**
  - `apply_gates(signals, context, config) -> (actionable[], blocked[])`.
  - CTX-1: if signal.class == ANOMALY and context.trendLocation == UNKNOWN → block.
  - Returns both lists for observability.
- **Tests:** Signal with UNKNOWN location blocked; signal with known location passes.

### Commit 9: Setup composer stage (sequence matcher)
- **Scope:** Create `src/vpa_core/setup_composer.py` implementing ENTRY-LONG-1 as first recipe.
- **Files:** `src/vpa_core/setup_composer.py` (new)
- **Acceptance criteria:**
  - Listens to SignalEvent stream + ContextSnapshot.
  - ENTRY-LONG-1: TEST-SUP-1 → VAL-1 within X bars → gates pass → READY.
  - Setup state machine: INACTIVE → CANDIDATE → PENDING_CONFIRM → READY / INVALIDATED / EXPIRED.
  - **No sizing, no stop calculation, no orders.**
- **Tests:** `FXT-ENTRY-LONG-1-seq` fixture test.

### Commit 10: Risk engine stage (stop + size + reject)
- **Scope:** Create `src/vpa_core/risk_engine.py` that takes READY setup + config → TradeIntent (approved or rejected).
- **Files:** `src/vpa_core/risk_engine.py` (new)
- **Acceptance criteria:**
  - Computes stop per setup-scoped rules (e.g., ENTRY-LONG-1 stop below test bar low).
  - Computes size from risk budget (`risk_pct_per_trade`, `countertrend_multiplier`).
  - Applies hard rejects (max positions, daily loss limit, avoidance signals).
  - Returns `TradeIntent` with status READY or REJECTED + reason.
- **Tests:** Size calculation test; reject on max positions; reject on avoidance.

---

## Phase C — Integration + backtest alignment

### Commit 11: Pipeline orchestrator (wire stages together)
- **Scope:** Create `src/vpa_core/pipeline.py` that chains: Features → Rules → Gates → Composer → Risk.
- **Files:** `src/vpa_core/pipeline.py` (new), refactor `src/vpa_core/signals.py` to delegate
- **Acceptance criteria:**
  - `run_pipeline(bars, config) -> PipelineResult` with events at each stage.
  - Old `evaluate()` wrapper calls pipeline internally.
  - Event journal emits stage-level events.
- **Tests:** Integration test: synthetic bars → expected SignalEvents + TradeIntents.

### Commit 12: Backtest runner aligned to pipeline
- **Scope:** Refactor `src/backtest/runner.py` to use pipeline; remove inline sizing.
- **Files:** `src/backtest/runner.py`
- **Acceptance criteria:**
  - Backtest calls `run_pipeline()` per bar.
  - Sizing delegated to Risk Engine (via pipeline).
  - Entry at next-bar open preserved.
  - Paper executor fill timing fixed to next-bar open.
- **Tests:** Regression test: same bars + config → same trades (snapshot test).

### Commit 13: `no_demand` disposition
- **Scope:** Either register `no_demand` as a canonical rule (map to appropriate ID, e.g., register new ID or map to WEAK-2 variant) or remove it.
- **Files:** `docs/vpa/VPA_RULE_REGISTRY.yaml`, `src/vpa_core/setups/no_demand.py`, `src/vpa_core/signals.py`
- **Acceptance criteria:**
  - If registered: add to registry YAML with conditions matching Couling, add fixture, add to traceability.
  - If removed: delete file, remove from `signals.py`, update CLI.
  - No EXTRA status in traceability.
- **Tests:** If registered: golden-fixture test. If removed: verify pipeline still works.

---

## Phase D — Expand rule coverage (incremental)

### Commit 14+: Add rules one at a time
For each new rule (VAL-2, ANOM-2, STR-1, WEAK-1, TEST-SUP-1, etc.):
1. Add to `VPA_RULE_REGISTRY.yaml` (if not already there).
2. Implement detection function in `rule_engine.py`.
3. Create golden-fixture JSON.
4. Add fixture test.
5. Update `VPA_TRACEABILITY.md`.

Priority order (for first-version backtest):
1. TEST-SUP-1 (needed for ENTRY-LONG-1)
2. VAL-1 (needed for ENTRY-LONG-1) — already in commit 7
3. ANOM-1 — already in commit 7
4. CONF-1 (wait-for-response confirmation)
5. STR-1 (hammer)
6. WEAK-1 (shooting star)
7. AVOID-NEWS-1 (stand-aside)

---

## Commit dependency graph

```
1 (spread def) → 2 (data models) → 3 (VPA config) → 4 (vol+spread classify)
                                                       ↓
5 (vocab lint) ─────────────────────────────────── (independent)
                                                       ↓
                                    6 (feature engine) → 7 (rule engine) → 8 (gates)
                                                                              ↓
                                                                    9 (setup composer) → 10 (risk engine)
                                                                                              ↓
                                                                                   11 (pipeline) → 12 (backtest)
                                                                                                      ↓
                                                                                            13 (no_demand) → 14+ (expand)
```
