# VPA_TEST_FIXTURES.md
**Project:** VPA — Canonical System  
**Purpose:** Standardize golden fixtures so every rule/setup can be tested deterministically and audited by any AI.

## 1) Principles
- Fixtures are **deterministic** and **portable** (no external data required).
- Fixtures are **small** (minimal bars needed to trigger the rule).
- Every fixture declares:
  - the rule/setup ID(s) it targets
  - config overrides (if any)
  - expected SignalEvents/Setup state transitions with evidence payload

## 2) Fixture types
### 2.1 Atomic rule fixture
- Targets exactly one atomic Rule ID (e.g., ANOM-1).
- Includes OHLCV bars required for:
  - rolling averages (vol/spread) OR
  - explicit precomputed feature inputs (choose one approach and stick to it).

### 2.2 Setup sequence fixture
- Targets exactly one Setup ID (e.g., ENTRY-LONG-1).
- Provides a sequence of SignalEvents (or bars) and expects setup state transitions:
  - INACTIVE → CANDIDATE → PENDING_CONFIRM → READY/INVALIDATED/EXPIRED

### 2.3 Integration fixture
- Small dataset (or synthetic bars) that exercises the pipeline:
  Ingest → Features → Context → Rules → Setups → Risk → (paper) execution
- Verifies event stream ordering and trade intent creation.

## 3) Standard format (JSON)
All fixtures are JSON files with this envelope:

{
  "fixtureId": "FXT-ANOM-1-basic",
  "type": "atomic|setup|integration",
  "targets": ["ANOM-1"],
  "timeframe": "15m",
  "configOverrides": { },
  "inputs": { ... },
  "expected": { ... }
}

## 4) Evidence payload standard
Expected signals must include `evidence` fields matching code output:
- spreadState, volState, candleType, wick metrics, etc.
If evidence changes, update fixture + bump version.

## 5) Naming conventions
- atomic:  fixtures/vpa/atomic/FXT-<RULE_ID>-<name>.json
- setup:   fixtures/vpa/setup/FXT-<SETUP_ID>-<name>.json
- integ:   fixtures/vpa/integration/FXT-INTEG-<name>.json
