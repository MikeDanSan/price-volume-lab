# Architecture decision records (ADR) / Decision log

Last updated: 2026-02-17

Short notes on key technical decisions. Helps future maintainers and AI assistants. Also referred to as the **decision log**.

---

## Canonical doc system (2026-02-17)

- **Canonical VPA docs** live in `docs/vpa-ck/` (knowledge model, glossary, rules, system spec, signal flow) and `docs/vpa/` (governance: registry, traceability, config, fixtures, vocab lists).
- Older docs (`docs/GLOSSARY.md`, `docs/RULEBOOK.md`, `docs/VPA_METHODOLOGY.md`) are now marked **legacy** and defer to canonical docs on any conflict.
- `docs/VPA_METHODOLOGY.md` uses Wyckoff/VSA terminology for educational context; it is in `VPA_VOCAB_EXCEPTIONS.txt`.
- All rule/setup IDs must be registered in `VPA_RULE_REGISTRY.yaml` before implementation.
- Reading order for AI agents: `CANONICAL_CONTRACT.md` -> `VPA_DOC_INDEX.md` -> follow the list.

---

## Language and runtime

- **Python 3.11+** — Readable, strong ecosystem for time series and backtesting; easy to keep vpa-core as a pure, dependency-light library; good for rulebook-as-doc and pair-programming.
- **vpa-core**: pure Python, no framework — Only stdlib + `dataclasses`/`typing`. No pandas inside core; accept/return simple structs so the core stays testable and portable.

---

## Data and storage

- **Bars**: SQLite (single symbol, MVP) — One file, simple, good for bars + journal. Created automatically by `BarStore`.
- **Data source**: **Alpaca** via `alpaca-py` SDK — Free tier (IEX) sufficient for backtesting and paper trading. SIP available with paid plan. Chosen over Polygon (Alpaca also provides brokerage for Phase 2+) and Yahoo Finance (unreliable, no official API).
- **Config**: single YAML file (`config.yaml`) loaded by `config.loader` — Symbol, timeframe, paths, risk limits. Parsed with `pyyaml`. API secrets via environment variables (`APCA_API_KEY_ID`, `APCA_API_SECRET_KEY`) following Alpaca's standard naming, never in config file.

---

## Backtesting

- **Event-driven, bar-by-bar** — Replay bars in order; call vpa-core at each bar with only past data (no lookahead). Simulate fills, slippage, commissions in a small, explicit module. Ensures honesty and matches how paper/live would see data.

---

## Execution (paper)

- **In-process module or single script** — Single writer to order/position state; file or SQLite-backed state for restart-safety. No distributed execution in MVP. Execution does not depend on backtest (separate use cases).

---

## Logging and journal

- **Structured logging** (JSON or key-value) to file + optional stdout — Append-only; every signal and trade with rationale and rulebook_ref for audit and post-trade review.

---

## Testing and types

- **pytest** — Unit tests for vpa-core (deterministic); integration tests for pipeline and backtest with fixture bars.
- **Full typing** in vpa-core and public APIs — Enforces contracts at boundaries and helps avoid logic drift.

---

## CLI

- **click** for CLI framework — Lightweight, composable, excellent for subcommands (`vpa ingest`, `vpa scan`, etc.). No need for heavier frameworks. Entry point via `[project.scripts]` in `pyproject.toml`.
- **Reasoning output to stdout** — Every CLI command prints human-readable VPA reasoning (context, volume, setup, rationale, rulebook ref). Operational logs go to stderr via Python `logging`. The system must never be a black box.

---

## Why Alpaca over alternatives

- **Free data**: IEX historical bars at no cost; sufficient for backtesting and paper trading.
- **Paper + live in one provider**: Alpaca offers paper trading API (fake money) and live trading with the same SDK. This means Phase 1 → Phase 2 → Phase 3 only changes the execution layer, not the data layer.
- **Official Python SDK**: `alpaca-py` is maintained by Alpaca; well-documented.
- **Standard env vars**: `APCA_API_KEY_ID` / `APCA_API_SECRET_KEY` are Alpaca's standard; no custom naming needed.

---

## Why YAML config with env var resolution

- YAML is human-readable and supports comments (unlike JSON).
- Config file holds non-secret values; secrets from env vars (12-factor app pattern).
- Single `load_config()` function returns a frozen dataclass tree — type-safe, no global mutable state.

---

## Out of scope (MVP)

- Message queues, Kubernetes, microservices, any ML/optimization of indicators or entries.
- Multi-symbol or multi-timeframe; live capital.
- Alpaca paper trading API execution (Phase 2) — `AlpacaPaperExecutor` is planned but not yet implemented.
