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

## Phase E — Hardening + context gates (M3–M6) ✅

| Commit | Description | Status |
|--------|-------------|--------|
| 22 | Update compliance report + fix plan checkpoint | ✅ Done |
| 23 | Migrate CLI `paper` command to canonical pipeline | ✅ Done |
| 24 | Context engine: real trend, location, congestion detection | ✅ Done |
| 25 | CTX-2 full implementation (policy-driven dominant alignment gate) | ✅ Done |
| 26 | CTX-3 implementation (congestion awareness gate) | ✅ Done |
| 27 | Golden-fixture runner for end-to-end pipeline replay | ✅ Done |

### M6 checkpoint: PASSED ✅
- All 3 context gates (CTX-1, CTX-2, CTX-3) at OK status
- Context engine produces real trend + location + congestion
- Golden fixtures validate end-to-end pipeline
- CLI scan + paper + backtest all use canonical pipeline
- 8 rules, 2 setups, 3 gates — meaningful backtest
- 312 tests passing

---

## Phase F — Live data + environment + scheduler ✅

| Commit | Description | Status |
|--------|-------------|--------|
| 28 | Fix local environment: dotenv loading, alpaca-py v0.43 compat, IEX feed default | ✅ Done |
| 29 | Add live paper-trading scheduler with market-hours awareness (`vpa paper --live`) | ✅ Done |

### Phase F deliverables
- 1,226 SPY 15m bars ingested (IEX free tier)
- First backtest on real data: 3 trades, -2.96%
- Live scheduler: market-aware loop, bar-close alignment, graceful shutdown
- 312 tests passing

---

## Phase G — Short-side + tuning (next)

Priority-ordered based on backtest analysis of Phase F real-data run.

### Commit 30: WEAK-2 atomic rule (no demand — shooting star + LOW vol)
- **Scope:** Register WEAK-2 in YAML + implement in rule engine.
- **Rationale:** Required building block for short-side setups.
- **Files:** `VPA_RULE_REGISTRY.yaml`, `rule_engine.py`, `test_rule_engine.py`
- **Acceptance criteria:** WEAK-2 fires on shooting star with LOW volume. Traceability updated.
- **Tests:** 6+ tests covering fire/no-fire/config-driven thresholds.

### Commit 31: CLIMAX-SELL-1 atomic rule (selling climax at top)
- **Scope:** Register + implement climactic selling detection.
- **Rationale:** Core signal for identifying distribution tops.
- **Files:** `VPA_RULE_REGISTRY.yaml`, `rule_engine.py`, `test_rule_engine.py`
- **Acceptance criteria:** Ultra-high volume + wide spread at TOP location.
- **Tests:** 6+ tests.

### Commit 32: ENTRY-SHORT-1 setup (post-distribution markdown)
- **Scope:** Register + implement first short-side setup.
- **Rationale:** System currently cannot profit in downtrends.
- **Sequence:** CLIMAX-SELL-1 → WEAK-1 (or WEAK-2) within window.
- **Files:** `VPA_RULE_REGISTRY.yaml`, `setup_composer.py`, `test_setup_composer.py`
- **Acceptance criteria:** Setup matches short sequence, risk engine computes short stops.
- **Tests:** 8+ tests covering sequence, expiration, invalidation.

### Commit 33: Risk engine short-side support
- **Scope:** Extend risk engine to compute stop-above for short entries.
- **Files:** `risk_engine.py`, `test_risk_engine.py`
- **Acceptance criteria:** Short TradeIntents have stop above entry, correct sizing.
- **Tests:** 4+ tests for short stop placement and sizing.

### Commit 34: Backtest runner short-side support
- **Scope:** Extend backtest to handle short positions (entry, stop, exit).
- **Files:** `backtest/runner.py`, `test_backtest.py`
- **Acceptance criteria:** Short trades track correctly with negative PnL on adverse moves.
- **Tests:** 4+ tests for short trade lifecycle.

### Commit 35: Low-liquidity guard
- **Scope:** Add configurable minimum-volume filter to rule engine.
- **Rationale:** Phase F backtest losses all occurred during holiday thin trading.
- **Files:** `vpa.default.json`, `vpa_config.schema.json`, `vpa_config.py`, `pipeline.py`
- **Acceptance criteria:** Pipeline skips evaluation when avg volume < threshold.
- **Tests:** Pipeline returns no signals when volume guard trips.

### Commit 36: Golden fixtures for short-side + volume guard
- **Scope:** Add golden fixtures for ENTRY-SHORT-1 and low-liquidity scenarios.
- **Files:** `docs/config/fixtures/vpa/`
- **Acceptance criteria:** Fixtures replay successfully in `test_golden_fixtures.py`.

---

## Phase G checkpoint criteria (review before Phase H)
- At least 1 short-side setup operational
- Backtest shows both long and short trades
- Low-liquidity guard prevents holiday-period false signals
- Ready to discuss: MTF support, additional rules, stop optimization

---

## Future phases (not yet planned in detail)

### Phase H — Multi-timeframe + stop optimization
- Daily/hourly dominant alignment for CTX-2 (currently returns UNKNOWN)
- ATR-based stop tuning (wider for volatile symbols)
- Per-symbol config support (`config-SPY.yaml`, `config-AAPL.yaml`)

### Phase I — Extended rule coverage
- TREND-VAL-1, TREND-ANOM-1, TREND-ANOM-2 (trend-level rules)
- TEST-SUP-2 (failed test), TEST-DEM-1 (demand test)
- CONF-2 (two-level agreement)
- AVOID-TRAP-1, AVOID-COUNTER-1

### Phase J — Production readiness
- Dockerfile + docker-compose for per-symbol containers
- Health checks, alerting, dashboarding
- PAPER_TO_LIVE.md checklist completion
