# vpa-engine — Project Context & Intent

Last updated: 2026-02-17

> **Canonical doc system**: For VPA-specific rules, glossary, pipeline, and config, see
> [`docs/vpa/VPA_DOC_INDEX.md`](vpa/VPA_DOC_INDEX.md) which defines the full reading order.
> This file covers project philosophy and engineering intent.

## 1. Purpose of This Project

This project, **vpa-engine**, is a programmatic trading system designed to implement
**Volume Price Analysis (VPA)** exactly as taught in the book:

> *A Complete Guide to Volume Price Analysis: Read the Book. Then Read the Market*  
> by **Anna Coulling**

The goal is NOT to invent a new strategy, optimize indicators, or use black-box AI
to decide trades.

The goal IS to:
- Encode the **rules, logic, and market-reading principles** from the book
- Produce **deterministic, explainable trade signals**
- Allow careful automation, backtesting, and paper trading
- Maintain full traceability: *why* a signal was generated

This system should be understandable to a human trader who has read the book.

---

## 2. Core Trading Philosophy (Non-Negotiable)

The system must strictly follow these principles from the book:

- **Price and Volume are primary**
- Indicators are secondary or excluded
- Signals are interpreted in **context** (“background strength/weakness”)
- Volume is **relative**, not absolute
- Professional activity is inferred via:
  - effort vs result
  - absorption
  - lack of demand / lack of supply
  - tests after strength or weakness
  - climactic action / stopping volume

The system should always answer:
> “Who is in control here — buyers or sellers?”

---

## 3. Scope (Initial MVP)

### Asset Class
- **Stocks only**
- Start with **a single, highly liquid symbol** (e.g., SPY or AAPL)

### Timeframe
- One timeframe only (e.g., 15m or 1h)
- No multi-timeframe logic in MVP

### Trading Mode
- Backtesting
- Paper trading only (no live capital)

---

## 4. Architectural Intent

This project is intentionally designed as a **modular monolith**, with clean boundaries
that can later be split into microservices if scaling requires it.

### Naming Conventions
- **Repository / System:** `vpa-engine`
- **Core rules engine:** `vpa-core`

### Key Design Rule
> `vpa-core` MUST be a pure library.
> - No broker APIs
> - No network calls
> - No side effects
> - Fully deterministic and unit-testable

---

## 5. High-Level Components

### vpa-core (Rules Engine)
Responsibilities:
- Candle feature extraction (spread, body, close location)
- Relative volume classification
- Context detection (trend, range, S/R)
- VPA setup detection
- TradePlan generation (intent, not execution)

Outputs:
- Signals
- TradePlans with:
  - entry logic
  - stop logic
  - invalidation rules
  - human-readable rationale

---

### Data Pipeline
Responsibilities:
- Fetch historical and latest OHLCV bars
- Normalize timestamps (UTC)
- Store bars locally
- Provide rolling context windows to vpa-core

---

### Backtesting Engine
Responsibilities:
- Replay historical bars honestly (no lookahead)
- Simulate fills, slippage, commissions
- Enforce risk rules
- Produce performance metrics

---

### Execution Layer (Paper Trading)
Responsibilities:
- Convert TradePlans into orders (paper: simulated fills; no broker in MVP)
- Track order lifecycle and positions in local state (SQLite)
- Enforce hard risk limits
- Maintain exactly-one execution authority (single writer)

Execution MUST remain:
- single-writer
- conservative
- restart-safe

---

### Journal & Observability
Responsibilities:
- Log every signal and trade with rationale
- Persist decisions for auditability
- Enable post-trade review

---

## 6. Explicit Non-Goals (Important)

This project is NOT:
- A machine-learning trading bot
- An indicator-optimization system
- A high-frequency trading engine
- A “predict the market” AI

AI may assist with:
- Planning
- Code generation
- Documentation
- Analysis and visualization

AI must NOT:
- Decide when to trade
- Alter core VPA rules without explicit human approval

---

## 7. Rules-as-Code Requirement

All VPA setups must be **registered** in [`docs/vpa/VPA_RULE_REGISTRY.yaml`](vpa/VPA_RULE_REGISTRY.yaml) **before implementation** in code.

Canonical rule definitions live in [`docs/vpa-ck/vpa_actionable_rules.md`](vpa-ck/vpa_actionable_rules.md).

Each rule/setup definition must include:
- Rule ID (from registry)
- Scope (timeframes, markets)
- Context prerequisites (gates required)
- Detection conditions (deterministic)
- Output (signal classification)
- Tests required (golden fixtures)

This prevents logic drift and preserves fidelity to the book.

---

## 8. Future Evolution

The system should be designed so that:
- Data ingestion
- Signal generation
can scale horizontally if that would make it better.
- agentic ai (agents trained to be the best at their task)

Execution should remain:
- tightly controlled
- low-concurrency
- safety-first

Microservices are optional and should only be introduced when justified by scale,
not by architecture fashion.

---

## 9. Intended Outcome

The final system should be able to:
- Read the market the way the book teaches
- Explain every trade in plain English
- Be trusted by a human who understands VPA
- Serve as a foundation for future expansion

The priority order is:
1. Correctness
2. Explainability
3. Safety
4. Performance
5. Scale (only if needed.)

---

## 10. Audience for This Document

This document is intended for:
- AI pair-programming assistants
- Human collaborators
- Future maintainers

Any system, plan, or code generated for this project must respect
the constraints and philosophy described above.
