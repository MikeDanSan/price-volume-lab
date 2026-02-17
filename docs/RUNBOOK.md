# vpa-engine — Runbook

Last updated: 2026-02-17

> For VPA rules, glossary, and pipeline details see [`docs/vpa/VPA_DOC_INDEX.md`](vpa/VPA_DOC_INDEX.md).

Step-by-step guide to run backtesting and paper trading. **Stocks-only MVP; paper trading first; single symbol and timeframe.**

---

## 1. Prerequisites

- **OS**: macOS, Linux, or Windows (WSL recommended on Windows).
- **Python**: 3.11 or 3.12. Check with `python3 --version`.
- **Alpaca account** (free): Sign up at <https://alpaca.markets>, create a paper-trading API key pair.
- **Docker**: Not used. All runs are local.

---

## 2. Installation

```bash
cd /path/to/price-volume-lab

python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# Install with base deps (click, pyyaml) and dev deps (pytest)
pip install -e ".[dev]"

# Install data extras (alpaca-py, pandas) for real bar fetching
pip install -e ".[data]"
```

Verify:

```bash
pytest tests/ -v
vpa --help
```

---

## 3. Configuration

### Config file

Copy `config.example.yaml` to `config.yaml` at the repo root:

```bash
cp config.example.yaml config.yaml
```

Edit `symbol`, `timeframe`, paths, and risk limits as needed. See the example file for all options.

Every CLI command accepts `--config path` (default: `config.yaml`).

### Environment variables (required for Alpaca)

| Variable | Required | Purpose |
|----------|----------|---------|
| `APCA_API_KEY_ID` | Yes (for `ingest`) | Alpaca API key (from your paper trading account) |
| `APCA_API_SECRET_KEY` | Yes (for `ingest`) | Alpaca API secret |

Set them before running:

```bash
export APCA_API_KEY_ID="your-key-here"
export APCA_API_SECRET_KEY="your-secret-here"
```

These are never stored in config files. They follow Alpaca's standard env var names.

### Selecting symbol and timeframe

In `config.yaml`:

```yaml
symbol: SPY
timeframe: "15m"
```

Supported timeframes: `1m`, `5m`, `15m`, `30m`, `1h`, `1d`.

**Free tier note**: Alpaca's free tier provides IEX data. Real-time SIP data requires Algo Trader Plus subscription ($99/month). For backtesting and paper trading, IEX historical bars are sufficient.

---

## 4. Data setup

### How bars are stored

- **Bar store**: SQLite database (default: `data/bars.db`). Created automatically on first use.
- Schema: `bars` table with `symbol`, `timeframe`, `ts_utc`, OHLCV. All timestamps UTC.

### Ingesting bars from Alpaca

```bash
# Fetch last 30 calendar days (default)
vpa ingest

# Fetch specific range
vpa ingest --days 60
vpa ingest --start 2024-06-01 --end 2024-09-01
```

Output:

```
Fetching SPY 15m bars from 2024-08-01 to 2024-09-01 ...
Stored 1247 bars in data/bars.db
  Range: 2024-08-01T09:30:00+00:00 -> 2024-09-01T16:00:00+00:00
```

---

## 5. How to run

### Scan (read the market)

One-shot VPA analysis of the latest bars. Shows context, volume, and any detected setups with full reasoning. This is the "read the market" command -- always explains itself.

```bash
vpa scan
vpa scan --window 30   # smaller context window
```

Example output:

```
--- VPA Analysis: SPY 15m @ 2024-08-15T14:30:00+00:00 ---
Bar          : up | O 102.00  H 103.00  L 101.50  C 102.80
Spread       : 1.50
Close loc.   : upper third
Context      : uptrend
Rel. volume  : low (current 400K vs 20-bar avg 1.05M = 0.38x)

  Setup detected: NO DEMAND  [rulebook: no_demand]
  Direction    : short
  Rationale    : No demand: up bar(s) on low/declining volume in uptrend. ...
  Entry        : next_bar_open_or_close_below_no_demand_low
  Stop         : 103.0
  Invalidation : next_bar_high_volume_up_move
  Invalidation : close_above_no_demand_high
---
```

### Backtest

Run backtest on stored bars with VPA reasoning for each trade:

```bash
vpa backtest
vpa backtest --start 2024-06-01 --end 2024-09-01
```

### Paper trade

Evaluate latest bars; if a VPA setup is detected, submit a simulated paper order:

```bash
vpa paper
```

Shows the same VPA reasoning as `scan`, plus order submission details. All orders are simulated locally (no broker connection in Phase 1).

### Status

Show current position, cash, and recent fills:

```bash
vpa status
vpa status --fills 10   # show more recent fills
```

### Where logs go

- **Journal**: Append-only JSONL file (default: `data/journal.jsonl`). Each line is a JSON object with `event` type, `rationale`, `rulebook_ref`, and event-specific fields.
- **Application logs**: Python `logging` at INFO level to stderr. VPA reasoning goes to stdout.

### Where results / trades / signals are recorded

- **Backtest**: Printed to stdout with full VPA reasoning per trade. Also written to journal if configured.
- **Paper**: Orders and fills in SQLite at `execution.state_path` (default: `data/paper_state.db`). Viewable with `vpa status`. Journal events logged to JSONL.

---

## 6. Safety

### Kill switch / stopping the system

- **Phase 1 (current)**: No live broker. Stop by pressing Ctrl+C or killing the process.
- **Single writer**: Only one process should write to the same state file. Do not run two instances of `vpa paper` against the same `paper_state.db`.

### Max risk limits

- Enforced in `PaperExecutor`: `max_position_pct`, `max_cash_per_trade_pct`, `initial_cash`.
- Enforced in `run_backtest`: `risk_pct_per_trade` sizes positions by risk per trade.
- Orders that would exceed limits are rejected (logged to stdout).

### Stopping safely

- Stop the process (Ctrl+C). SQLite state is committed per operation; no special shutdown required.
- Do not delete or move `paper_state.db` while a process is using it.

---

## 7. Troubleshooting

| Issue | Cause | Fix |
|-------|--------|-----|
| `ModuleNotFoundError: vpa_core` | Package not installed | `pip install -e ".[dev]"` from repo root |
| `ModuleNotFoundError: alpaca` | Data extras not installed | `pip install -e ".[data]"` |
| `Alpaca API key ... required` | Env vars not set | `export APCA_API_KEY_ID=... APCA_API_SECRET_KEY=...` |
| `No bars in store` | Haven't ingested yet | Run `vpa ingest --days 30` |
| Backtest returns 0 trades | No VPA setup triggered in bar series | Normal if conditions from the canonical rules are not met |
| `vpa paper` says "Order rejected" | Risk limit or existing position | Check `vpa status`; review risk limits in config |
| SQLite locked | Two processes writing to same DB | Use only one process per state path |
| Config file not found | Wrong path | `vpa --config /path/to/config.yaml scan` |

---

## Summary

```
vpa ingest              # Fetch bars from Alpaca
vpa scan                # Read the market (VPA analysis with reasoning)
vpa backtest            # Run backtest with trade-by-trade reasoning
vpa paper               # Paper trade (local simulation)
vpa status              # Show position, cash, fills
```

All commands load config from `config.yaml` (or `--config path`). All commands print human-readable VPA reasoning. Nothing is a black box.
