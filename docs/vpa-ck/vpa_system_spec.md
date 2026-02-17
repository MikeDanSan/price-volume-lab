# VPA_SYSTEM_SPEC.md
**Project:** Volume Price Analysis (VPA) — Canonical System  
**Doc:** Trading System Specification (engineering-level)  
**Source of truth:** Anna Couling — *A Complete Guide to Volume Price Analysis (2013)*  
**Goal:** Deterministic, context-aware execution of Couling-style VPA (validation vs anomaly, effort vs result, tests, climaxes, multi-timeframe “ripples”).

---

## 1) Scope and Non-Goals

### In scope
- Deterministic detection of VPA rule atoms and composite setups.
- Context gates (trend location, structure, dominant trend alignment).
- State machine for market interpretation + trade lifecycle.
- Risk/position logic with explicit stop placement rules.
- Backtesting harness assumptions and reproducibility requirements.

### Out of scope (by design)
- ML prediction, optimization-as-a-crutch, pattern-mining without VPA context.
- “Everything is a signal” indicator stacks. (Indicators may exist only as structure aids, not decision drivers.)
- Real-money brokerage specifics (adapters can be implemented later).

---

## 2) System Overview

### 2.1 High-level architecture
**Pipeline:** OHLCV(+optional VAP) → Features → Context → Rule Engine → Setup Composer → Risk Engine → Execution → Journal/Telemetry

Components:
1. **Market Data Ingestor**
2. **Timeframe Builder** (fast / primary / dominant)
3. **Feature Engine** (candle anatomy, relative volume, relative spread)
4. **Structure Engine** (support/resistance zones, swing points, congestion/range detection; optional VAP)
5. **Context Engine** (trend phase & location, dominant trend alignment)
6. **Rule Engine** (atomic signals: validation/anomaly, tests, climaxes, premier candles)
7. **Setup Composer** (entry recipes: sequences + confirmations)
8. **Risk Engine** (position sizing, stops, trade gating)
9. **Execution Adapter** (paper/backtest/live)
10. **Observability** (events, metrics, audit trail)

---

## 3) Inputs, Outputs, and Contracts

### 3.1 Inputs
**Required**
- `OHLCV` bars: `{ts_open, ts_close, open, high, low, close, volume}`
- Instrument metadata: `{symbol, tick_size, lot_size, session_calendar(optional)}`
- Timeframes config: `{fast_tf, primary_tf, dominant_tf}`

**Optional**
- `VAP` (Volume At Price) profile per session/rolling window (derived from bars)
- Corporate actions / roll schedule (equities/futures)

### 3.2 Outputs
1. **Signal Events** (atomic + composite)
2. **Trade Intents** (entry/exit, direction, confidence tier)
3. **Orders** (backtest/paper/live)
4. **Position State** (open risk, stop, size, PnL)
5. **Audit Journal** (why a decision occurred)

### 3.3 Canonical data models

#### CandleFeatures
```json
{
  "ts": "2026-02-17T14:30:00Z",
  "tf": "15m",
  "spread": 1.25,
  "range": 2.10,
  "upperWick": 0.70,
  "lowerWick": 0.15,
  "bodyRel": 1.34,
  "spreadRel": 1.22,
  "volRel": 1.65,
  "volState": "HIGH",
  "spreadState": "WIDE",
  "candleType": "UP"
}

#### ContextSnapshot
```json
{
  "tf": "15m",
  "trend": "UP|DOWN|RANGE|UNKNOWN",
  "trendStrength": "WEAK|MODERATE|STRONG",
  "trendLocation": "TOP|BOTTOM|MIDDLE|UNKNOWN",
  "congestion": {"active": true, "rangeHigh": 105.2, "rangeLow": 100.8},
  "dominantAlignment": "WITH|AGAINST|UNKNOWN",
  "vapZones": [{"price": 102.4, "density": "HIGH"}]
}
```

#### SignalEvent
````json
{
  "id": "ANOM-1",
  "name": "BigResultLittleEffort_TrapUpWarning",
  "tf": "15m",
  "ts": "2026-02-17T14:30:00Z",
  "class": "ANOMALY",
  "directionBias": "BEARISH_OR_WAIT",
  "priority": 2,
  "evidence": {"spreadState": "WIDE", "volState": "LOW"},
  "requiresContextGate": true
}
```

#### TradeIntent
```json
{
  "intentId": "TI-20260217-001",
  "direction": "LONG",
  "tf": "15m",
  "setup": "ENTRY-LONG-1",
  "status": "READY|PENDING_CONFIRM|REJECTED",
  "entryPlan": {"timing": "NEXT_BAR_OPEN", "orderType": "MARKET"},
  "riskPlan": {"stop": 100.6, "riskPct": 0.5, "size": 120},
  "rationale": ["TEST-SUP-1", "VAL-1", "CTX-1:OK", "CTX-2:WITH"]
}
```
4) Determinism Layer (Quantizing Couling’s relative terms)
4.1 Relative volume states (configurable)

VolAvg = SMA(volume, N=20)

VolRel = volume / VolAvg

Defaults:

LOW < 0.8

AVERAGE 0.8–1.2

HIGH 1.2–1.8

ULTRA_HIGH > 1.8

4.2 Relative spread states (configurable)

SpreadAvg = SMA(|close-open|, M=20)

SpreadRel = Spread / SpreadAvg

Defaults:

NARROW < 0.8

NORMAL 0.8–1.2

WIDE > 1.2

Note: these thresholds are parameters, but execution is deterministic once configured.

5) Timeframes and “Ripples” (Fast → Primary → Dominant)
5.1 Three-timeframe stack

Fast TF: earliest detection of change (the first “ripple”)

Primary TF: execution/decision timeframe

Dominant TF: risk bias gate (with-trend vs countertrend)

5.2 Multi-timeframe rules

Fast signals produce EARLY events.

Primary confirmation upgrades a setup to READY.

Dominant alignment adjusts risk policy (not the signal truth).

6) Rule Engine (Atomic Signals)

The Rule Engine emits atomic SignalEvents only (no orders). Examples:

Candle-level validation: VAL-1, VAL-2

Candle-level anomalies: ANOM-1, ANOM-2

Trend-level validation/anomaly: TREND-VAL-*, TREND-ANOM-*

Tests: TEST-SUP-*, TEST-DEM-*

Climaxes: CLIMAX-SELL-* (and later: buying climax variants)

Premier candles: STR-1 hammer, WEAK-1 shooting star, etc.

Avoidance: AVOID-NEWS-1, AVOID-TRAP-1

7) Context Gates (Mandatory)

Context gates are hard requirements for acting on anomalies and phase signals.

Gate CTX-1: Trend-location-first

If Signal.class == ANOMALY or phase-related → must have trendLocation != UNKNOWN.

Gate CTX-2: Dominant alignment risk gate

dominantAlignment == WITH → normal risk

dominantAlignment == AGAINST → reduced risk, shorter expected hold, stricter confirmations, or reject.

Gate CTX-3: Range/congestion awareness

If congestion active:

Prefer test-based setups (supply/demand tests).

Deprioritize “trend continuation” entries inside the range.

8) Setup Composer (Composite Entry Recipes)

The Setup Composer is a deterministic sequence matcher that listens to SignalEvents + ContextSnapshots.

Example recipes:

ENTRY-LONG-1: Test of supply pass → bull validation within X bars → context gates pass

ENTRY-SHORT-1: Test of demand pass → bearish follow-through → gates pass

ENTRY-LONG-2: Hammer strength → positive response confirmation → gates pass

ENTRY-SHORT-2: Selling climax/top weakness → trend-level weakness → gates pass

Each recipe yields:

PENDING_CONFIRM or READY or REJECTED

9) State Machines
9.1 Market Interpretation State (VPA-centric)

This is not Wyckoff labeling by guesswork; it’s a minimal state to enforce context-aware logic.

States:

UNKNOWN

RANGE_CONGESTION

ACCUMULATION_CANDIDATE

DISTRIBUTION_CANDIDATE

UPTREND_VALIDATED

DOWNTREND_VALIDATED

TRANSITION_RISK (anomaly clusters / climax evidence present)

Transitions (examples):

UNKNOWN → RANGE_CONGESTION when congestion detected (structure engine)

RANGE_CONGESTION → ACCUMULATION_CANDIDATE when repeated supply tests appear + strength signals

RANGE_CONGESTION → DISTRIBUTION_CANDIDATE when repeated demand failure / topping signals appear

UPTREND_VALIDATED → TRANSITION_RISK on anomaly cluster / climax signals

DOWNTREND_VALIDATED → TRANSITION_RISK on stopping-volume / strength cluster

Mermaid (market state):

stateDiagram-v2
  [*] --> UNKNOWN
  UNKNOWN --> RANGE_CONGESTION: congestion_detected
  RANGE_CONGESTION --> ACCUMULATION_CANDIDATE: supply_tests_pass + strength
  RANGE_CONGESTION --> DISTRIBUTION_CANDIDATE: demand_tests_pass + weakness
  ACCUMULATION_CANDIDATE --> UPTREND_VALIDATED: breakout_validation
  DISTRIBUTION_CANDIDATE --> DOWNTREND_VALIDATED: breakdown_validation
  UPTREND_VALIDATED --> TRANSITION_RISK: anomaly_cluster or climax
  DOWNTREND_VALIDATED --> TRANSITION_RISK: stopping_volume_cluster
  TRANSITION_RISK --> RANGE_CONGESTION: range_reforms
  TRANSITION_RISK --> UPTREND_VALIDATED: strength_confirmed
  TRANSITION_RISK --> DOWNTREND_VALIDATED: weakness_confirmed

9.2 Trade Lifecycle State

States:

FLAT

SETUP_TRACKING

PENDING_ENTRY

IN_POSITION

EXIT_PENDING

COOLDOWN

Mermaid (trade state):

stateDiagram-v2
  [*] --> FLAT
  FLAT --> SETUP_TRACKING: setup_candidate
  SETUP_TRACKING --> PENDING_ENTRY: setup_ready
  SETUP_TRACKING --> FLAT: setup_invalidated
  PENDING_ENTRY --> IN_POSITION: entry_filled
  PENDING_ENTRY --> FLAT: entry_canceled_or_rejected
  IN_POSITION --> EXIT_PENDING: exit_signal or stop_update
  EXIT_PENDING --> FLAT: exit_filled
  FLAT --> COOLDOWN: avoid_signal_high_priority
  COOLDOWN --> FLAT: cooldown_elapsed

10) Risk & Position Logic (Deterministic Policies)
10.1 Risk budget

riskPctPerTrade (default 0.25%–1.0% of equity)

maxConcurrentPositions

dailyLossLimitPct (optional hard stop)

counterTrendRiskMultiplier (e.g., 0.5x when CTX-2 == AGAINST)

10.2 Position sizing

risk$ = equity * riskPctPerTrade * alignmentMultiplier

stopDistance = |entryPrice - stopPrice|

size = floor(risk$ / stopDistance / pointValue) adjusted to lot/tick constraints

10.3 Stop placement rules (setup-scoped)

Stops are derived from Couling-style “market sets the level” logic:

Hammer long (ENTRY-LONG-2): stop below hammer wick low

Supply test long (ENTRY-LONG-1): stop below test bar low or below range floor (config strictness)

Selling climax short (ENTRY-SHORT-2): stop above climax wick high or above distribution ceiling

Demand test short (ENTRY-SHORT-1): stop above test bar high or above range ceiling

10.4 Exit rules (deterministic, VPA-consistent)

Primary exits should be “context breaks,” not arbitrary indicators:

Invalidation exit: opposing anomaly cluster against position direction

Structure exit: break of last swing / re-entry into congestion against thesis

Stop-loss exit: hard stop hit

Time stop (optional): if expected “fast move” fails to materialize within T bars after tests/climax

Optional scaling:

Conservative: no scaling; single entry/exit.

Moderate: partial take on first major opposing anomaly, remainder trail via structure.

10.5 “What not to trade” enforcement

Hard rejects:

AVOID-NEWS-1 (stop-hunt / manipulation signature)

Anomaly triggers without CTX-1 satisfied

Counter-dominant trades when policy set to DISALLOW_COUNTERTREND

11) Execution Semantics (Backtest/Paper/Live)
11.1 Decision timing

Deterministic timing choice (config):

Mode A (close-confirmed): signal evaluated at bar close; entry at next bar open

Mode B (intrabar): not allowed in backtest unless tick data exists (avoid lookahead)

Default: close-confirmed (Mode A).

11.2 Order types

Backtest: market-at-open with slippage model

Live: market/limit depending on venue; keep order abstraction

12) Backtesting Assumptions and Controls
12.1 No lookahead

All signals computed from completed candles only.

VAP zones computed only from historical bars up to decision point.

12.2 Data integrity

Volume must be real traded volume (or consistent proxy, explicitly declared).

Handle missing bars deterministically (fill policy: reject signals during gaps).

12.3 Costs and slippage

Fees: fee_per_trade or bps

Slippage: deterministic model (e.g., slippage_bps or half-spread)

For crypto/FX: include spread model

12.4 Corporate actions / futures

Equities: adjust OHLC for splits/dividends if needed (volume handling declared)

Futures: continuous contract + roll rules declared (or backtest per-contract)

12.5 Survivorship bias

If using equities universe, store delisted symbols; otherwise results are biased.

13) Observability (DevOps-grade)
13.1 Event journal (append-only)

Every step emits events:

bar_ingested, features_computed, context_built, signal_emitted,
setup_state_changed, trade_intent_created, order_sent, fill_received, position_updated

13.2 Metrics

Signal counts by type

Setup conversion rate (candidate→ready→filled)

Win rate, expectancy, max drawdown

Average hold time by setup

Countertrend vs with-trend performance

13.3 Deterministic replay

Given dataset + config hash, results must be identical.

14) Testing Strategy
14.1 Unit tests (rule atoms)

Golden-candle fixtures for each atomic rule (VAL/ANOM/TEST/CLIMAX)

Edge cases: equal open/close, zero volume bars, gap bars

14.2 Integration tests (pipeline)

Replay a known segment → verify event sequence and final positions

14.3 Regression tests

Snapshot key metrics under fixed seeds/configs

Fail CI if drift exceeds tolerance

15) Deployment & CI/CD (minimal baseline)

Containerized backtest runner (Docker)

CI steps:

lint/format

typecheck

unit tests

integration replay tests

smoke backtest on small dataset

Artifacts:

config hash

build hash

backtest report + journal