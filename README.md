# vpa-engine

Last updated: 2026-02-17

Volume Price Analysis (VPA) engine implementing the methodology from *A Complete Guide to Volume Price Analysis* by Anna Coulling. Deterministic, rulebook-driven signals; no ML; **paper trading and backtesting only**. **Stocks-only MVP; single symbol and timeframe.**

## Status

- **MVP / Active development**: Core rules engine (vpa-core), data layer, backtest, paper execution, journal, config loader, and CLI are implemented. Alpaca integration for bar data is live. Paper trading is local simulation (Phase 1). See [PAPER_TO_LIVE](docs/PAPER_TO_LIVE.md) for the three-phase path from backtest to live.

## Goals

- Encode VPA rules from the book; produce **deterministic, explainable** trade signals and TradePlans.
- Support backtesting and paper trading with full traceability (rationale + rulebook_ref).
- **Not a black box**: every CLI command shows the VPA reasoning behind its actions.
- Modular monolith, single-writer execution, safety-first.

## Non-goals (MVP)

- No ML or AI that decides trades. No indicator optimization. No live capital. No multi-symbol or multi-timeframe logic. No Alpaca live execution (Phase 3, future).

## Philosophy

- **Price and volume are primary**; indicators secondary or absent.
- Every signal and trade is **traceable to the rulebook** and explainable in plain English.
- **vpa-core** is a pure library (no I/O, no network); fully deterministic and testable.

See [docs/PROJECT_CONTEXT.md](docs/PROJECT_CONTEXT.md) for full intent and constraints.

## High-level architecture

Modular monolith: **vpa_core** (pure rules engine) has no I/O; **data**, **backtest**, **execution**, **journal**, **config**, and **cli** depend on it. Execution is single-writer (one process per state file). See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for diagrams and boundaries.

- **vpa_core** -- Rules engine: candle features, relative volume, context, VPA setup detection (e.g. No Demand), TradePlan generation.
- **data** -- Fetch bars from Alpaca (`AlpacaBarFetcher`) and store in SQLite (`BarStore`), provide context windows for vpa-core.
- **config** -- YAML config loader with env var resolution for API secrets.
- **cli** -- `click`-based CLI: `vpa ingest`, `vpa scan`, `vpa backtest`, `vpa paper`, `vpa status`.
- **backtest** -- Event-driven bar replay, vpa-core evaluation, fill/slippage/commission simulation, metrics.
- **execution** -- Paper only: TradePlan -> order, single-writer state, risk limits.
- **journal** -- Append-only log of signals and trades with rationale and rulebook reference.

## Quickstart

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,data]"
pytest tests/ -v

# Set Alpaca API keys (get free keys at https://alpaca.markets)
export APCA_API_KEY_ID="your-key"
export APCA_API_SECRET_KEY="your-secret"

# Copy and edit config
cp config.example.yaml config.yaml

# Fetch bars, scan, backtest
vpa ingest --days 30
vpa scan
vpa backtest
vpa paper
vpa status
```

See [docs/RUNBOOK.md](docs/RUNBOOK.md) for full installation, config, and usage details.

## CLI commands

| Command | Purpose |
|---------|---------|
| `vpa ingest` | Fetch bars from Alpaca and store locally |
| `vpa scan` | One-shot VPA analysis with full reasoning |
| `vpa backtest` | Run backtest with trade-by-trade reasoning |
| `vpa paper` | Paper trade (local simulation) |
| `vpa status` | Show position, cash, recent fills |

All commands accept `--config path` (default: `config.yaml`). All output includes VPA reasoning.

## Documentation index

### Canonical VPA docs (source of truth -- read these first)

| Doc | Purpose |
|-----|---------|
| [CANONICAL_CONTRACT](CANONICAL_CONTRACT.md) | One-page guardrails: source of truth, vocabulary, reasoning order, engineering separation. |
| [VPA_DOC_INDEX](docs/vpa/VPA_DOC_INDEX.md) | **Start here for AI agents.** Full reading order and change control. |
| [VPA_AI_CONTEXT](docs/vpa-ck/vpa_ai_context.md) | AI behavior contract: do/don't rules, compliance checklist. |
| [VPA_GLOSSARY](docs/vpa-ck/vpa_glossary.md) | Canonical vocabulary whitelist (Couling terms only). |
| [VPA_CANONICAL_MODEL](docs/vpa-ck/vpa_canonical_model.md) | Concepts, relationships, axioms (no rules yet). |
| [VPA_ACTIONABLE_RULES](docs/vpa-ck/vpa_actionable_rules.md) | Deterministic rule atoms + composite setups. |
| [VPA_SYSTEM_SPEC](docs/vpa-ck/vpa_system_spec.md) | Engineering spec: pipeline, state machines, data models, risk, backtest. |
| [VPA_SIGNAL_FLOW](docs/vpa-ck/vpa_signal_flow.md) | Signal pipeline stages and dependency graph. |
| [VPA_CONFIG](docs/vpa/VPA_CONFIG.md) | All tunable parameters + change control. |
| [VPA_RULE_REGISTRY](docs/vpa/VPA_RULE_REGISTRY.yaml) | Rule/setup IDs -- register before implementing. |
| [VPA_TRACEABILITY](docs/vpa/VPA_TRACEABILITY.md) | Doc-to-code-to-test mapping. |
| [VPA_TEST_FIXTURES](docs/vpa/VPA_TEST_FIXTURES.md) | Golden fixture format and naming conventions. |

### Project and engineering docs

| Doc | Purpose |
|-----|---------|
| [PROJECT_CONTEXT](docs/PROJECT_CONTEXT.md) | Philosophy, scope, non-goals. |
| [ARCHITECTURE](docs/ARCHITECTURE.md) | Module map, dependencies, data flow, single-writer rule. |
| [RUNBOOK](docs/RUNBOOK.md) | **How to run**: install, config, Alpaca setup, CLI commands, safety, troubleshooting. |
| [TUNING_GUIDE](docs/TUNING_GUIDE.md) | What to tune, what not to tune, safe tuning. |
| [PAPER_TO_LIVE](docs/PAPER_TO_LIVE.md) | Three-phase Alpaca path: backtest -> paper -> live. |
| [DATA_MODEL](docs/DATA_MODEL.md) | Bar, Signal, TradePlan, Order, Fill (being aligned to canonical spec). |
| [DECISIONS](docs/DECISIONS.md) | Decision log (ADR-style). |

### Legacy / educational docs

| Doc | Purpose |
|-----|---------|
| [VPA_METHODOLOGY](docs/VPA_METHODOLOGY.md) | Educational VPA reference (uses Wyckoff terminology; see canonical docs for implementation). |
| [RULEBOOK](docs/RULEBOOK.md) | Legacy rulebook (superseded by VPA_ACTIONABLE_RULES + VPA_RULE_REGISTRY). |
| [GLOSSARY](docs/GLOSSARY.md) | Legacy glossary (superseded by canonical VPA_GLOSSARY). |

## License

MIT.
