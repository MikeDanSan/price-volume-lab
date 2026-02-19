# VPA_TRACEABILITY.md
**Project:** VPA — Canonical System  
**Purpose:** Ensure every canonical rule/setup is implemented and tested exactly as specified (Couling 2013).  
**Last updated:** 2026-02-18 (Phase G complete)

## 1) Non-negotiables
- Canonical source: Anna Couling (2013).
- IDs come from `VPA_RULE_REGISTRY.yaml` (not memory, not prose).
- No code may implement a "signal" that does not exist in the registry.
- Every rule/setup must have tests.

## 2) Status definitions
- **OK**: Implemented + unit tests + referenced by pipeline appropriately.
- **PARTIAL**: Implemented but missing tests OR missing gates OR missing evidence payload.
- **MISSING**: No implementation found.
- **DRIFT**: Implementation exists but conditions/gates differ from registry.
- **EXTRA**: Code contains signal/setup not registered (must be removed or registered).

## 3) Traceability Matrix

### 3.1 Context Gates
| ID | Name | Spec Source | Code Location | Test Location | Status | Notes |
|----|------|-------------|---------------|---------------|--------|-------|
| CTX-1 | Trend-location-first gate | VPA_ACTIONABLE_RULES §2, VPA_RULE_REGISTRY.yaml | `src/vpa_core/context_gates.py` | `tests/test_context_gates.py` | **OK** | Blocks anomaly signals when trendLocation==UNKNOWN. Configurable via `config.gates.ctx1_trend_location_required`. |
| CTX-2 | Dominant alignment gate | VPA_ACTIONABLE_RULES §2 | `src/vpa_core/context_gates.py::_check_ctx_2` + `src/vpa_core/risk_engine.py` | `tests/test_context_gates.py::TestCTX2*` + `tests/test_risk_engine.py::TestCountertrend` | **OK** | Policy-driven: DISALLOW blocks at gate; REDUCE_RISK adjusts sizing in Risk Engine; ALLOW disables. Multi-TF alignment not yet computed (returns UNKNOWN). |
| CTX-3 | Congestion awareness gate | VPA_ACTIONABLE_RULES §2 | `src/vpa_core/context_gates.py::_check_ctx_3` | `tests/test_context_gates.py::TestCTX3*` | **OK** | Blocks anomaly signals in congestion zones (ambiguous in range). Non-anomaly classes (VALIDATION, TEST, STRENGTH, WEAKNESS) pass through as potential breakout/boundary signals. Configurable via `config.gates.ctx3_congestion_awareness_required`. |

### 3.2 Atomic Rules (registered in YAML)
| ID | Name | Spec Source | Code Location | Test Location | Status | Notes |
|----|------|-------------|---------------|---------------|--------|-------|
| VAL-1 | Single-bar validation (bullish drive) | VPA_RULE_REGISTRY.yaml | `src/vpa_core/rule_engine.py::detect_val_1` | `tests/test_rule_engine.py::TestVAL1` (7 tests) | **OK** | Wide up bar + HIGH/ULTRA_HIGH volume. Evidence payload populated. No gate required. |
| ANOM-1 | Big result, little effort (trap-up) | VPA_RULE_REGISTRY.yaml | `src/vpa_core/rule_engine.py::detect_anom_1` | `tests/test_rule_engine.py::TestANOM1` (6 tests) | **OK** | Wide up bar + LOW volume. Requires CTX-1 gate. Priority=2. |
| ANOM-2 | Big effort, little result (absorption) | VPA_RULE_REGISTRY.yaml | `src/vpa_core/rule_engine.py::detect_anom_2` | `tests/test_rule_engine.py::TestANOM2` (9 tests) | **OK** | HIGH/ULTRA_HIGH volume + NARROW/NORMAL spread. Direction-agnostic. Requires CTX-1 gate. |
| STR-1 | Hammer (strength) | VPA_RULE_REGISTRY.yaml | `src/vpa_core/rule_engine.py::detect_str_1` | `tests/test_rule_engine.py::TestSTR1` (9 tests) | **OK** | Config-driven wick/body/range ratios. Requires CTX-1 gate. |
| WEAK-1 | Shooting star (weakness) | VPA_RULE_REGISTRY.yaml | `src/vpa_core/rule_engine.py::detect_weak_1` | `tests/test_rule_engine.py::TestWEAK1` (9 tests) | **OK** | Config-driven wick/body/range ratios. Inverse of STR-1. Requires CTX-1 gate. |
| CONF-1 | Positive response (confirmation) | VPA_RULE_REGISTRY.yaml | `src/vpa_core/rule_engine.py::detect_conf_1` | `tests/test_rule_engine.py::TestCONF1` (9 tests) | **OK** | UP bar + non-LOW volume + non-NARROW spread. No gate (prior signal's gate suffices). |
| AVOID-NEWS-1 | Long-legged doji on LOW vol (stand-aside) | VPA_RULE_REGISTRY.yaml | `src/vpa_core/rule_engine.py::detect_avoid_news_1` | `tests/test_rule_engine.py::TestAVOIDNEWS1` (10 tests) | **OK** | Config-driven body/wick ratios + LOW volume. Priority=0 (highest). No gate. |
| WEAK-2 | Shooting star + LOW vol (no demand) | VPA_RULE_REGISTRY.yaml | `src/vpa_core/rule_engine.py::detect_weak_2` | `tests/test_rule_engine.py::TestWEAK2` (8 tests) | **OK** | WEAK-1 shape + LOW volume. Higher priority than WEAK-1 (more decisive). Requires CTX-1 gate. |
| CLIMAX-SELL-1 | Selling climax bar | VPA_RULE_REGISTRY.yaml | `src/vpa_core/rule_engine.py::detect_climax_sell_1` | `tests/test_rule_engine.py::TestCLIMAXSELL1` (9 tests) | **OK** | Shooting star shape + HIGH/ULTRA_HIGH volume. Single-bar detection; repetition in Setup Composer. Requires CTX-1 gate. |
| TEST-SUP-1 | Test of supply (pass) | VPA_RULE_REGISTRY.yaml | `src/vpa_core/rule_engine.py::detect_test_sup_1` | `tests/test_rule_engine.py::TestTESTSUP1` (7 tests) | **OK** | LOW volume + NARROW/NORMAL spread. Requires CTX-1 gate. Bar_low enriched by pipeline for stop placement. |

### 3.3 Rules defined in docs but NOT yet implemented
| ID | Name | Spec Source | Status | Notes |
|----|------|-------------|--------|-------|
| VAL-2 | Single-bar validation (small progress) | VPA_ACTIONABLE_RULES §3 | **MISSING** | Planned Phase I. |
| TREND-VAL-1 | Uptrend validation | VPA_ACTIONABLE_RULES §4 | **MISSING** | Planned Phase I. |
| TREND-ANOM-1 | Uptrend weakness | VPA_ACTIONABLE_RULES §4 | **MISSING** | Planned Phase I. |
| TREND-ANOM-2 | Sequential anomaly cluster | VPA_ACTIONABLE_RULES §4 | **MISSING** | Planned Phase I. |
| STR-2 | Additional strength pattern | VPA_ACTIONABLE_RULES §5 | **MISSING** | Planned Phase I. |
| WEAK-2 | Shooting star + LOW vol = no demand | VPA_ACTIONABLE_RULES §5 / VPA_RULE_REGISTRY.yaml | **OK** | Implemented Commit 30. |
| TEST-SUP-2 | Failed test of supply | VPA_ACTIONABLE_RULES §6 | **MISSING** | Planned Phase I. |
| TEST-DEM-1 | Test of demand (pass) | VPA_ACTIONABLE_RULES §6 | **MISSING** | Planned Phase I. |
| CLIMAX-SELL-1 | Selling climax (topping) | VPA_ACTIONABLE_RULES §7 / VPA_RULE_REGISTRY.yaml | **OK** | Implemented Commit 31. Single-bar detection; repetition in Setup Composer. |
| CLIMAX-SELL-2 | Upper-wick repetition emphasis | VPA_ACTIONABLE_RULES §7 | **MISSING** | Planned Phase I. |
| AVOID-TRAP-1 | Trap-up anomaly without confirmation | VPA_ACTIONABLE_RULES §8 | **MISSING** | Planned Phase I. |
| AVOID-COUNTER-1 | Counter-dominant entries | VPA_ACTIONABLE_RULES §8 | **MISSING** | Planned Phase I. |
| CONF-2 | Two-level agreement | VPA_ACTIONABLE_RULES §9 | **MISSING** | Planned Phase I. |

### 3.4 Setups (registered in YAML)
| ID | Name | Spec Source | Code Location | Test Location | Status | Notes |
|----|------|-------------|---------------|---------------|--------|-------|
| ENTRY-LONG-1 | Post-accumulation breakout | VPA_RULE_REGISTRY.yaml | `src/vpa_core/setup_composer.py::SetupComposer` | `tests/test_setup_composer.py` (8 tests) | **OK** | Sequence: TEST-SUP-1 → VAL-1 within window_X bars. State machine with expiration and invalidation. |
| ENTRY-LONG-2 | Reversal long (hammer + confirm) | VPA_RULE_REGISTRY.yaml | `src/vpa_core/setup_composer.py::SetupComposer` | `tests/test_setup_composer.py` (9 tests) | **OK** | Sequence: STR-1 → CONF-1 within window_X bars. Stop below hammer wick. AVOID-NEWS-1 invalidates. |

| ENTRY-SHORT-1 | Post-distribution markdown | VPA_RULE_REGISTRY.yaml | `src/vpa_core/setup_composer.py::SetupComposer` | `tests/test_setup_composer.py` (13 tests) | **OK** | Sequence: CLIMAX-SELL-1 → WEAK-1 or WEAK-2 within window_X bars. OR-matching completers. Bullish validation/strength invalidates. |

### 3.5 Setups defined in docs but NOT yet implemented
| ID | Name | Spec Source | Status | Notes |
|----|------|-------------|--------|-------|
| ENTRY-SHORT-2 | Reversal short (selling climax) | VPA_ACTIONABLE_RULES §10 | **MISSING** | Planned Phase I. |

### 3.6 EXTRA signals (in code, not in registry)
| Code ID | Code Location | Description | Status | Notes |
|---------|---------------|-------------|--------|-------|
| *(none)* | — | — | — | Legacy `no_demand` removed in Commit 13. No EXTRA signals remain. |

## 4) Pipeline compliance checkpoints
- [x] Rule Engine emits SignalEvents only (no orders) — `src/vpa_core/rule_engine.py`
- [x] Setup Composer matches sequences only (no sizing) — `src/vpa_core/setup_composer.py`
- [x] Risk Engine owns stop/size/rejects — `src/vpa_core/risk_engine.py`
- [x] Backtest is bar-close evaluated, next-bar execution by default — `src/backtest/runner.py`
- [x] Pipeline orchestrator chains all stages — `src/vpa_core/pipeline.py`
- [x] All thresholds config-driven (no magic numbers) — `docs/config/vpa.default.json` + `vpa_config.schema.json`

## 5) Data model alignment
| Canonical Model | Spec Location | Code Location | Status |
|-----------------|---------------|---------------|--------|
| `CandleFeatures` | VPA_SYSTEM_SPEC §3.3 | `src/vpa_core/contracts.py` + `src/vpa_core/feature_engine.py` | **OK** |
| `ContextSnapshot` | VPA_SYSTEM_SPEC §3.3 | `src/vpa_core/contracts.py` | **OK** |
| `SignalEvent` | VPA_SYSTEM_SPEC §3.3 | `src/vpa_core/contracts.py` | **OK** |
| `TradeIntent` | VPA_SYSTEM_SPEC §3.3 | `src/vpa_core/contracts.py` | **OK** |

## 6) "Stop the line" policy
If any ID is **MISSING/PARTIAL/DRIFT/EXTRA**, create a TODO with:
- acceptance criteria
- tests required
- smallest commit plan

**Current summary: 16 OK (VAL-1, ANOM-1, ANOM-2, STR-1, WEAK-1, WEAK-2, CLIMAX-SELL-1, CONF-1, AVOID-NEWS-1, TEST-SUP-1, CTX-1, CTX-2, CTX-3, ENTRY-LONG-1, ENTRY-LONG-2, ENTRY-SHORT-1), 0 PARTIAL, 10 MISSING, 0 DRIFT, 0 EXTRA.**
