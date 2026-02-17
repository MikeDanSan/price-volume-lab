# VPA_SIGNAL_FLOW.md
**Project:** Volume Price Analysis (VPA) — Canonical System  
**Doc:** Signal Pipeline + Flow (engineering clarity)  
**Goal:** Show the exact processing order, dependencies, and state transitions from raw OHLCV to executable trade intents.

---

## 1) Signal pipeline (end-to-end)

### 1.1 Flowchart
```mermaid
flowchart LR
  A[OHLCV Ingest] --> B[Resample: fast/primary/dominant]
  B --> C[Feature Engine: candle anatomy]
  C --> D[Relative Measures: volRel, spreadRel]
  D --> E[Structure Engine: swings, S/R, congestion]
  E --> F[Context Engine: trend, location, dominant alignment]
  F --> G[Rule Engine: atomic VPA signals]
  G --> H[Context Gates: CTX-1/2/3]
  H --> I[Setup Composer: entry recipes]
  I --> J[Risk Engine: stop, size, rejects]
  J --> K[Trade Intent]
  K --> L[Execution Adapter]
  L --> M[Journal + Metrics]
2) Processing order (deterministic)
Stage 0 — Data acceptance
Inputs:

raw bars must be sorted, gap-checked, volume validated
Outputs:

canonical bar stream

Stage 1 — Multi-timeframe build
Build/align: fast_tf, primary_tf, dominant_tf

Ensure timestamp alignment rules are consistent (close-confirmed)

Stage 2 — Feature engine (per bar, per timeframe)
Compute:

spread, range, wicks

volAvg/volRel/volState

spreadAvg/spreadRel/spreadState

Stage 3 — Structure engine (per timeframe)
Compute:

swing highs/lows (deterministic fractal or pivot algorithm)

congestion detection (range tightness + duration threshold)

support/resistance zones from swings + congestion boundaries

optional VAP zones (volume density at price)

Stage 4 — Context engine (per timeframe)
Compute:

trend: UP/DOWN/RANGE/UNKNOWN (based on swing direction + range state)

trend location: TOP/BOTTOM/MIDDLE/UNKNOWN (relative to recent structure)

dominant alignment: WITH/AGAINST/UNKNOWN (primary vs dominant)

Stage 5 — Rule engine emits atomic signals
Atomic detections include:

Candle validation vs anomaly (effort vs result)

Trend-level validation/anomaly (over window K)

Tests: supply / demand

Climaxes: selling climax patterns

Premier candle shapes (hammer, shooting star)

Avoidance signatures (stop-hunt / manipulation)

Output:

SignalEvent[] with evidence payloads

Stage 6 — Context gates filter actionability
If anomaly/phase signal and trendLocation == UNKNOWN → mark requiresContextGate=true and block action.

If counter-dominant and policy says reduce risk or disallow → annotate/reject.

Stage 7 — Setup composer matches sequences
Examples:

TEST-SUP-PASS → within X bars → VALIDATION_BULL → yields ENTRY-LONG-1 READY

HAMMER → POSITIVE_RESPONSE → yields ENTRY-LONG-2 READY

SELLING_CLIMAX → TREND_WEAKNESS → yields ENTRY-SHORT-2 READY

Output:

TradeIntent candidates, each with explicit rationale chain

Stage 8 — Risk engine finalizes or rejects
Computes stop rule (setup-scoped)

Computes size from risk budget

Applies hard rejects (avoidance, gaps, max positions, daily loss limit)

Output:

Final TradeIntent READY → Execution Adapter

3) Signal dependency graph (what depends on what)
graph TD
  CF[CandleFeatures] --> VA[Validation/Anomaly]
  CF --> PC[Premier Candle Types]
  CF --> TL[TrendLevel Metrics]
  SR[Structure: S/R + Congestion] --> CX[Context Snapshot]
  TL --> CX
  VA --> GATES[Context Gates]
  PC --> GATES
  TESTS[Supply/Demand Tests] --> GATES
  CLIMAX[Climax Signals] --> GATES
  GATES --> SETUPS[Setup Composer]
  SETUPS --> RISK[Risk Engine]
  RISK --> INTENT[Trade Intent]
4) State machine interactions (market ↔ setups ↔ trades)
4.1 Market interpretation state updates
Market state updates are triggered by:

congestion detection

test pass/fail sequences

repeated anomaly clusters

climax signals + follow-through

4.2 Setup states
Each setup ID has its own mini-state:

INACTIVE

CANDIDATE (trigger condition detected)

PENDING_CONFIRM (waiting for response/confirmation bar)

READY (actionable)

INVALIDATED (context breaks or opposite signal)

EXPIRED (time window exceeded)

Mermaid (setup state):

stateDiagram-v2
  [*] --> INACTIVE
  INACTIVE --> CANDIDATE: trigger_detected
  CANDIDATE --> PENDING_CONFIRM: confirmation_required
  PENDING_CONFIRM --> READY: confirm_ok_within_window
  PENDING_CONFIRM --> INVALIDATED: opposing_signal or context_fail
  CANDIDATE --> READY: trigger_is_self_confirming
  READY --> EXPIRED: not_executed_within_window
  READY --> INVALIDATED: context_break
  INVALIDATED --> INACTIVE
  EXPIRED --> INACTIVE
4.3 Trade lifecycle uses setup outputs
READY → creates TradeIntent

Intent becomes order only after risk approval

5) Inputs/Outputs at each stage (IO tables)
5.1 Stage IO summary
Stage	Inputs	Outputs
0	Raw OHLCV	Canonical OHLCV
1	Canonical OHLCV	Aligned bars per timeframe
2	Bars	CandleFeatures
3	Bars + Features	StructureSnapshot
4	Structure + Features	ContextSnapshot
5	Features + Context	SignalEvent[]
6	Signals + Context	ActionableSignals / BlockedSignals
7	ActionableSignals	TradeIntent candidates
8	TradeIntents + RiskConfig	Approved intents / Rejections
9	Approved intents	Orders / Fills / Positions
10	Everything	Journal + Metrics
6) Backtest flow specifics (to avoid “cheating”)
Evaluation point: bar close (signal truth computed only after bar completes)

Entry fill model: next bar open (with slippage/fees)

Stop model: if stop is inside next bar range, assume fill at stop +/- slippage (deterministic rule)

VAP model: VAP computed only from historical bars up to decision point

7) Example: End-to-end signal → intent trace
Structure: range detected → RANGE_CONGESTION

Rule engine: TEST-SUP-1 (low-volume supply test) → emits signal

Gates: CTX-1 OK (trendLocation known) + CTX-3 OK (range-aware)

Setup composer: transitions ENTRY-LONG-1 to PENDING_CONFIRM

Next bar: VAL-1 bullish validation → setup becomes READY

Risk engine: stop below test bar low, size computed, passes max positions

Execution: market-at-open entry, journal logs full rationale chain

8) Operational hooks (DevOps-minded)
Every stage emits an event with:

configHash, codeVersion, datasetId, barTs, tf, entityId

Deterministic replay:

rerun with same dataset + configHash → identical event stream and trades
