# VPA_TRACEABILITY.md
**Project:** VPA — Canonical System  
**Purpose:** Ensure every canonical rule/setup is implemented and tested exactly as specified (Couling 2013).  
**Last updated:** 2026-02-17 (Commit 13)

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
| CTX-2 | Dominant alignment risk gate | VPA_ACTIONABLE_RULES §2 | `src/vpa_core/risk_engine.py` (countertrend multiplier) | `tests/test_risk_engine.py::TestCountertrend` | **PARTIAL** | Risk reduction applied via `countertrend_multiplier` when alignment==AGAINST. Full multi-TF alignment not yet computed. NOT IN REGISTRY. |
| CTX-3 | Congestion awareness gate | VPA_ACTIONABLE_RULES §2 | — | — | **MISSING** | `Congestion` dataclass exists in contracts but no detection logic. NOT IN REGISTRY. |

### 3.2 Atomic Rules (registered in YAML)
| ID | Name | Spec Source | Code Location | Test Location | Status | Notes |
|----|------|-------------|---------------|---------------|--------|-------|
| VAL-1 | Single-bar validation (bullish drive) | VPA_RULE_REGISTRY.yaml | `src/vpa_core/rule_engine.py::detect_val_1` | `tests/test_rule_engine.py::TestVAL1` (7 tests) | **OK** | Wide up bar + HIGH/ULTRA_HIGH volume. Evidence payload populated. No gate required. |
| ANOM-1 | Big result, little effort (trap-up) | VPA_RULE_REGISTRY.yaml | `src/vpa_core/rule_engine.py::detect_anom_1` | `tests/test_rule_engine.py::TestANOM1` (6 tests) | **OK** | Wide up bar + LOW volume. Requires CTX-1 gate. Priority=2. |

### 3.3 Atomic Rules (in VPA_ACTIONABLE_RULES.md, NOT yet in registry)
| ID | Name | Spec Source | Code Location | Test Location | Status | Notes |
|----|------|-------------|---------------|---------------|--------|-------|
| VAL-2 | Single-bar validation (small progress) | VPA_ACTIONABLE_RULES §3 | — | — | **MISSING** | NOT IN REGISTRY. |
| ANOM-2 | Big effort, little result (absorption) | VPA_ACTIONABLE_RULES §3 | — | — | **MISSING** | NOT IN REGISTRY. |
| TREND-VAL-1 | Uptrend validation | VPA_ACTIONABLE_RULES §4 | — | — | **MISSING** | NOT IN REGISTRY. |
| TREND-ANOM-1 | Uptrend weakness | VPA_ACTIONABLE_RULES §4 | — | — | **MISSING** | NOT IN REGISTRY. |
| TREND-ANOM-2 | Sequential anomaly cluster | VPA_ACTIONABLE_RULES §4 | — | — | **MISSING** | NOT IN REGISTRY. |
| STR-1 | Hammer = strength | VPA_ACTIONABLE_RULES §5 | — | — | **MISSING** | NOT IN REGISTRY. |
| WEAK-1 | Shooting star = weakness | VPA_ACTIONABLE_RULES §5 | — | — | **MISSING** | NOT IN REGISTRY. |
| WEAK-2 | Shooting star + LOW vol = no demand | VPA_ACTIONABLE_RULES §5 | — | — | **MISSING** | NOT IN REGISTRY. |
| TEST-SUP-1 | Test of supply (pass) | VPA_ACTIONABLE_RULES §6 | — | — | **MISSING** | NOT IN REGISTRY. Used as setup trigger in ENTRY-LONG-1 but no standalone detector yet. |
| TEST-SUP-2 | Failed test of supply | VPA_ACTIONABLE_RULES §6 | — | — | **MISSING** | NOT IN REGISTRY. |
| TEST-DEM-1 | Test of demand (pass) | VPA_ACTIONABLE_RULES §6 | — | — | **MISSING** | NOT IN REGISTRY. |
| CLIMAX-SELL-1 | Selling climax (topping) | VPA_ACTIONABLE_RULES §7 | — | — | **MISSING** | NOT IN REGISTRY. |
| CLIMAX-SELL-2 | Upper-wick repetition emphasis | VPA_ACTIONABLE_RULES §7 | — | — | **MISSING** | NOT IN REGISTRY. |
| AVOID-NEWS-1 | Long-legged doji / stop hunting | VPA_ACTIONABLE_RULES §8 | — | — | **MISSING** | NOT IN REGISTRY. |
| AVOID-TRAP-1 | Trap-up anomaly without confirmation | VPA_ACTIONABLE_RULES §8 | — | — | **MISSING** | NOT IN REGISTRY. |
| AVOID-COUNTER-1 | Counter-dominant entries | VPA_ACTIONABLE_RULES §8 | — | — | **MISSING** | NOT IN REGISTRY. |
| CONF-1 | Wait for response | VPA_ACTIONABLE_RULES §9 | — | — | **MISSING** | NOT IN REGISTRY. |
| CONF-2 | Two-level agreement | VPA_ACTIONABLE_RULES §9 | — | — | **MISSING** | NOT IN REGISTRY. |

### 3.4 Setups (registered in YAML)
| ID | Name | Spec Source | Code Location | Test Location | Status | Notes |
|----|------|-------------|---------------|---------------|--------|-------|
| ENTRY-LONG-1 | Post-accumulation breakout | VPA_RULE_REGISTRY.yaml | `src/vpa_core/setup_composer.py::SetupComposer` | `tests/test_setup_composer.py` (8 tests) | **OK** | Sequence: TEST-SUP-1 → VAL-1 within window_X bars. State machine with expiration and invalidation. |

### 3.5 Setups (in VPA_ACTIONABLE_RULES.md, NOT yet in registry)
| ID | Name | Spec Source | Code Location | Test Location | Status | Notes |
|----|------|-------------|---------------|---------------|--------|-------|
| ENTRY-SHORT-1 | Post-distribution markdown | VPA_ACTIONABLE_RULES §10 | — | — | **MISSING** | NOT IN REGISTRY. |
| ENTRY-LONG-2 | Reversal long (hammer + confirm) | VPA_ACTIONABLE_RULES §10 | — | — | **MISSING** | NOT IN REGISTRY. |
| ENTRY-SHORT-2 | Reversal short (selling climax) | VPA_ACTIONABLE_RULES §10 | — | — | **MISSING** | NOT IN REGISTRY. |

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

**Current summary: 4 OK (VAL-1, ANOM-1, CTX-1, ENTRY-LONG-1), 1 PARTIAL (CTX-2), 21 MISSING, 0 DRIFT, 0 EXTRA.**
