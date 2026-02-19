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

## Phase G — Short-side + tuning ✅

| Commit | Description | Status |
|--------|-------------|--------|
| 30 | WEAK-2 atomic rule (no demand — shooting star + LOW vol) | ✅ Done |
| 31 | CLIMAX-SELL-1 atomic rule (selling climax at top) | ✅ Done |
| 32 | ENTRY-SHORT-1 setup (CLIMAX-SELL-1 → WEAK-1/WEAK-2, OR-completers) | ✅ Done |
| 33 | Risk engine short-side support (stop above, bidirectional sizing) | ✅ Done |
| 34 | Backtest runner short-side tests (fill, PnL, stop-out, journal) | ✅ Done |
| 35 | Low-liquidity volume guard (config-driven, pipeline early-return) | ✅ Done |
| 36 | Golden fixtures for CLIMAX-SELL-1, WEAK-2, ENTRY-SHORT-1, volume guard | ✅ Done |

### Phase G checkpoint: PASSED ✅
- ENTRY-SHORT-1 operational (post-distribution short)
- Backtest proves both long and short trade lifecycle
- Low-liquidity guard blocks holiday thin-trading false signals
- Symmetric setup invalidation (bullish kills shorts, anomaly/avoidance kills longs)
- 375 tests passing, 9 golden fixtures

---

## Phase H — Multi-timeframe + stop optimization (next)

CTX-2 dominant alignment currently returns UNKNOWN because there is no
higher-timeframe trend to compare against. This phase adds daily bar
ingestion, a daily trend overlay, and ATR-based stop optimization.

### Commit 37: Daily bar storage + ingestion
- **Scope:** Extend BarStore and AlpacaBarFetcher to handle daily bars alongside intraday.
- **Rationale:** Daily trend is required for CTX-2 dominant alignment.
- **Files:** `bar_store.py`, `alpaca_fetcher.py`, `cli/main.py` (ingest --timeframe 1d)
- **Acceptance criteria:** `vpa ingest --timeframe 1d` fetches and stores daily bars.
- **Tests:** Bar store handles multiple timeframes; fetcher returns daily bars.

### Commit 38: Daily trend analyzer
- **Scope:** Compute daily trend (direction + strength) from daily bars.
- **Rationale:** Feed into dominant alignment for CTX-2.
- **Files:** `context_engine.py`, new `daily_context.py` or extend existing.
- **Acceptance criteria:** Given 20+ daily bars, returns Trend + TrendStrength.
- **Tests:** Daily trend detection with known bar sequences.

### Commit 39: CTX-2 dominant alignment from daily trend
- **Scope:** Wire daily trend into ContextSnapshot.dominant_alignment.
- **Rationale:** CTX-2 REDUCE_RISK policy finally activates in live/backtest.
- **Files:** `pipeline.py`, `context_engine.py`, `backtest/runner.py`
- **Acceptance criteria:** When 15m trade direction opposes daily trend, alignment=AGAINST.
- **Tests:** Pipeline produces AGAINST/WITH alignment; risk reduction triggers.

### Commit 40: ATR computation + config
- **Scope:** Add Average True Range (ATR) computation from bar history.
- **Rationale:** ATR-based stops adapt to volatility instead of using static bar high/low.
- **Files:** new `atr.py` or extend `feature_engine.py`, `vpa.default.json`
- **Acceptance criteria:** ATR(14) computed from bars; value available to risk engine.
- **Tests:** ATR calculation against known values.

### Commit 41: ATR-based stop placement
- **Scope:** Risk engine uses ATR multiplier for stop distance when configured.
- **Rationale:** Static stops (bar high/low) are too tight in volatile markets.
- **Files:** `risk_engine.py`, `vpa.default.json`, `vpa_config.schema.json`
- **Acceptance criteria:** Stop = entry ± (ATR × multiplier). Fallback to bar-based if ATR unavailable.
- **Tests:** ATR stop vs bar-based stop; sizing adjusts to wider stop.

### Commit 42: Per-symbol config support
- **Scope:** Allow `config-SPY.yaml`, `config-AAPL.yaml` overrides.
- **Rationale:** Different symbols need different volume thresholds and ATR multipliers.
- **Files:** `vpa_config.py`, `cli/main.py`
- **Acceptance criteria:** CLI `--symbol SPY` loads symbol-specific overrides if present.
- **Tests:** Symbol override merges correctly with defaults.

### Phase H checkpoint criteria
- CTX-2 dominant alignment computed from daily trend (not UNKNOWN)
- Backtest with daily overlay shows fewer counter-trend losses
- ATR-based stops reduce stop-out rate vs bar-based stops
- Per-symbol config available for multi-ticker deployment

---

## Future phases (not yet planned in detail)

### Phase I — Extended rule coverage
- TREND-VAL-1, TREND-ANOM-1, TREND-ANOM-2 (trend-level rules)
- TEST-SUP-2 (failed test), TEST-DEM-1 (demand test)
- CONF-2 (two-level agreement)
- AVOID-TRAP-1, AVOID-COUNTER-1
- ENTRY-SHORT-2 (reversal short from selling climax)

### Phase J — Production readiness
- Dockerfile + docker-compose for per-symbol containers
- Health checks, alerting, dashboarding
- PAPER_TO_LIVE.md checklist completion
