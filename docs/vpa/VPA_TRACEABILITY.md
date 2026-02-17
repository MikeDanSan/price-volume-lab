# VPA_TRACEABILITY.md
**Project:** VPA — Canonical System  
**Purpose:** Ensure every canonical rule/setup is implemented and tested exactly as specified (Couling 2013).  
**Audit date:** 2026-02-17

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
> Rule IDs and Setup IDs must match the registry exactly.
> IDs from VPA_ACTIONABLE_RULES.md that are **not yet in the registry** are listed with note "NOT IN REGISTRY".

### 3.1 Context Gates
| ID | Name | Spec Source | Code Location | Test Location | Status | Notes |
|----|------|-------------|---------------|---------------|--------|-------|
| CTX-1 | Trend-location-first gate | VPA_ACTIONABLE_RULES §2, VPA_RULE_REGISTRY.yaml | — | — | **MISSING** | No formal gate implementation. `no_demand` does informal context check but not CTX-1 logic. |
| CTX-2 | Dominant alignment risk gate | VPA_ACTIONABLE_RULES §2 | — | — | **MISSING** | No multi-timeframe alignment implemented. NOT IN REGISTRY. |
| CTX-3 | Congestion awareness gate | VPA_ACTIONABLE_RULES §2 | — | — | **MISSING** | No congestion detection. NOT IN REGISTRY. |

### 3.2 Atomic Rules (registered in YAML)
| ID | Name | Spec Source | Code Location | Test Location | Status | Notes |
|----|------|-------------|---------------|---------------|--------|-------|
| VAL-1 | Single-bar validation (bullish drive) | VPA_RULE_REGISTRY.yaml | — | — | **MISSING** | No implementation. Fixture `FXT-VAL-1-basic` referenced in registry but file does not exist. |
| ANOM-1 | Big result, little effort (trap-up) | VPA_RULE_REGISTRY.yaml | — | — | **MISSING** | No implementation. Fixture `FXT-ANOM-1-basic` exists at `docs/config/fixtures/vpa/atomic/` but no runner. |

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
| TEST-SUP-1 | Test of supply (pass) | VPA_ACTIONABLE_RULES §6 | — | — | **MISSING** | NOT IN REGISTRY. |
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
| ENTRY-LONG-1 | Post-accumulation breakout | VPA_RULE_REGISTRY.yaml | — | — | **MISSING** | Fixture `FXT-ENTRY-LONG-1-seq` exists but no implementation or runner. |

### 3.5 Setups (in VPA_ACTIONABLE_RULES.md, NOT yet in registry)
| ID | Name | Spec Source | Code Location | Test Location | Status | Notes |
|----|------|-------------|---------------|---------------|--------|-------|
| ENTRY-SHORT-1 | Post-distribution markdown | VPA_ACTIONABLE_RULES §10 | — | — | **MISSING** | NOT IN REGISTRY. |
| ENTRY-LONG-2 | Reversal long (hammer + confirm) | VPA_ACTIONABLE_RULES §10 | — | — | **MISSING** | NOT IN REGISTRY. |
| ENTRY-SHORT-2 | Reversal short (selling climax) | VPA_ACTIONABLE_RULES §10 | — | — | **MISSING** | NOT IN REGISTRY. |

### 3.6 EXTRA signals (in code, not in registry)
| Code ID | Code Location | Description | Status | Notes |
|---------|---------------|-------------|--------|-------|
| `no_demand` | `src/vpa_core/setups/no_demand.py` + `src/vpa_core/signals.py` | Up bar on low/declining volume in uptrend | **EXTRA** | Predates registry. Not registered. Maps loosely to WEAK-2 / "no demand" concept but conditions differ from any registered rule. Must be registered or removed. |

## 4) Pipeline compliance checkpoints
- [ ] Rule Engine emits SignalEvents only (no orders) — **VIOLATED**: `signals.py:evaluate()` emits `(Signal, TradePlan)` tuples directly
- [ ] Setup Composer matches sequences only (no sizing) — **VIOLATED**: no separate Setup Composer; `signals.py` conflates all stages
- [ ] Risk Engine owns stop/size/rejects — **VIOLATED**: sizing done in `backtest/runner.py`; stop set in `signals.py`
- [ ] Backtest is bar-close evaluated, next-bar execution by default — **PARTIAL**: backtest runner fills at next-bar open (correct), but paper executor fills immediately (incorrect)

## 5) Data model alignment
| Canonical Model | Spec Location | Code Equivalent | Status |
|-----------------|---------------|-----------------|--------|
| `CandleFeatures` | VPA_SYSTEM_SPEC §3.3 | — | **MISSING** |
| `ContextSnapshot` | VPA_SYSTEM_SPEC §3.3 | — | **MISSING** |
| `SignalEvent` | VPA_SYSTEM_SPEC §3.3 | `Signal` (different schema) | **DRIFT** |
| `TradeIntent` | VPA_SYSTEM_SPEC §3.3 | `TradePlan` (different schema) | **DRIFT** |

## 6) "Stop the line" policy
If any ID is **MISSING/PARTIAL/DRIFT/EXTRA**, create a TODO with:
- acceptance criteria
- tests required
- smallest commit plan

**Current summary: 0 OK, 0 PARTIAL, 22+ MISSING, 2 DRIFT, 1 EXTRA.**
