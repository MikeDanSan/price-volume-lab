# FIX_PLAN.md
**VPA Canonical System — Fix Plan**
- Date: 2026-02-17 (updated 2026-02-17, Phase I complete)
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

## Phase H — Multi-timeframe + stop optimization ✅

|| Commit | Description | Status |
||--------|-------------|--------|
|| 37 | Daily bar storage + ingestion (BarStore + AlpacaBarFetcher multi-TF) | ✅ Done |
|| 38 | Daily trend analyzer (`daily_context.py`) | ✅ Done |
|| 39 | CTX-2 dominant alignment from daily trend (pipeline + gates wiring) | ✅ Done |
|| 40 | ATR computation + config (`atr.py`, `AtrConfig`) | ✅ Done |
|| 41 | ATR-based stop placement (risk engine: bar-based + ATR fallback) | ✅ Done |
|| 42 | Per-symbol config support (`vpa.{SYMBOL}.json` deep-merge overrides) | ✅ Done |
|| 43 | Phase H doc update | ✅ Done |

### Phase H checkpoint: PASSED ✅
- CTX-2 dominant alignment computed from daily trend (not UNKNOWN)
- ATR-based stops available (config-driven, fallback to bar-based)
- Per-symbol config: `vpa.{SYMBOL}.json` overrides with deep-merge
- Daily + intraday bar ingestion and storage
- 443 tests passing

---

## Phase I — Extended rule coverage ✅

|| Commit | Description | Status |
||--------|-------------|--------|
|| 44 | TEST-SUP-2 (failed supply test) + TEST-DEM-1 (demand test) | ✅ Done |
|| 45 | TREND-VAL-1 (validated uptrend) + TREND-ANOM-1 (uptrend divergence) + VolumeTrend enum | ✅ Done |
|| 46 | TREND-ANOM-2 (sequential anomaly cluster, multi-bar rule) | ✅ Done |
|| 47 | CONF-2 (two-level agreement meta-rule) | ✅ Done |
|| 48 | AVOID-TRAP-1 (trap-up warning) + AVOID-COUNTER-1 (counter-trend warning) | ✅ Done |
|| 49 | ENTRY-SHORT-2 (reversal short: climax → trend weakness) | ✅ Done |
|| 50 | Phase I checkpoint: registry + traceability + compliance update | ✅ Done |

### Phase I checkpoint: PASSED ✅
- 8 new rules across 4 levels: bar-level (TEST-SUP-2, TEST-DEM-1), trend-level (TREND-VAL-1, TREND-ANOM-1), cluster-level (TREND-ANOM-2), meta-level (CONF-2), avoidance (AVOID-TRAP-1, AVOID-COUNTER-1)
- 1 new setup: ENTRY-SHORT-2 (shares CLIMAX-SELL-1 trigger with SHORT-1)
- Setup composer refined: hard vs soft avoidance invalidation
- Only 3 rule IDs remain MISSING (VAL-2, STR-2, CLIMAX-SELL-2) — non-blocking
- 555 tests passing, 0 drift, 0 extra

---

## Phase J — Production readiness

|| Commit | Description | Status |
||--------|-------------|--------|
|| 51 | Dockerfile + .dockerignore (slim Python 3.12, `vpa` CLI entrypoint) | ✅ Done |
|| 52 | docker-compose for per-symbol containers (SPY + QQQ template) | ✅ Done |
|| 53 | Health check CLI command + Docker HEALTHCHECK | ✅ Done |
|| 54 | Structured JSON logging + alerting hooks | |
|| 55 | Kill switch + max daily loss safety limits | |
|| 56 | Phase J checkpoint: PAPER_TO_LIVE.md update + compliance | |

### Phase J checkpoint criteria
- `docker build` + `docker compose up` works for multi-symbol deployment
- Health checks detect unhealthy containers (DB missing, config invalid)
- Structured JSON log events for signal/trade/error (foundation for Grafana/Loki)
- Kill switch + daily loss limit enforce safety before any real-money path
- PAPER_TO_LIVE.md Phase 1 checklist items marked complete

---

## Future phases (not yet planned in detail)

### Phase K — Remaining rules (optional)
- VAL-2 (single-bar validation, small progress)
- STR-2 (additional strength pattern)
- CLIMAX-SELL-2 (upper-wick repetition emphasis)
