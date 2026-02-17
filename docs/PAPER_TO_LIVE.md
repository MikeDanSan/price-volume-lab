# vpa-engine — Paper to Live: the Alpaca path

Last updated: 2026-02-17

How to run with **zero financial risk** and the concrete path from backtest to paper to live using **Alpaca** as the data and execution provider. Every phase uses the same VPA rules from the book -- only the execution layer changes; the signal logic never becomes a black box.

---

## Phase 1: Backtest + local paper execution (current)

**Risk: $0.** No broker connection in execution layer.

What you do:

1. **Sign up for Alpaca** (free) at <https://alpaca.markets>. Generate paper-trading API keys.
2. Set env vars: `APCA_API_KEY_ID` and `APCA_API_SECRET_KEY`.
3. **Ingest historical bars** from Alpaca's free IEX data:

```bash
vpa ingest --days 60
```

4. **Run backtest** on stored bars:

```bash
vpa backtest
```

5. **Scan** the latest bars for VPA setups (read the market, not a black box):

```bash
vpa scan
```

6. **Paper trade locally**: signals trigger simulated fills via `PaperExecutor` (SQLite state, no broker connection):

```bash
vpa paper
```

What happens under the hood:

- `AlpacaBarFetcher` calls Alpaca Market Data API to download OHLCV bars.
- `vpa-core` evaluates each bar using only VPA rules from the rulebook (e.g., No Demand).
- `PaperExecutor` simulates fills locally with slippage. No money leaves your account.
- Every signal and trade is logged to `journal.jsonl` with `rationale` and `rulebook_ref`.

**Free tier note**: Alpaca's free tier provides IEX data (15-minute delayed for market data, but historical bars are fine for backtesting and end-of-day paper). SIP (real-time) requires Algo Trader Plus ($99/month) and is not needed for Phase 1.

### Phase 1 readiness checklist

- [ ] Backtest produces reasonable results on 30+ days of data.
- [ ] `vpa scan` output shows correct context, volume, and setup reasoning.
- [ ] Paper trades logged with rationale and rulebook_ref in journal.
- [ ] System restarts cleanly (SQLite state is restart-safe).
- [ ] Tests pass: `pytest tests/ -v` (all green).

---

## Phase 2: Alpaca paper trading API (next)

**Risk: $0.** Alpaca paper accounts use fake money (starts at $100K, can be reset).

What changes:

- Replace `PaperExecutor` with a new `AlpacaPaperExecutor` that calls `alpaca.trading.TradingClient(paper=True).submit_order()`.
- Real order lifecycle: market/limit orders, partial fills, rejections, order status callbacks.
- Same VPA rules, same `evaluate()` call, same journal logging.
- Paper account on Alpaca is completely separate from any live account.

### Phase 2 readiness checklist

- [ ] `AlpacaPaperExecutor` implemented and tested with Alpaca's paper endpoint.
- [ ] Orders appear in Alpaca dashboard (paper) matching journal entries.
- [ ] Reconciliation: Alpaca's positions/fills match local journal and state.
- [ ] Run for 2+ weeks without crashes, missed signals, or state drift.
- [ ] Consistent behavior across process restarts.
- [ ] Risk limits enforced: `max_position_pct`, `max_cash_per_trade_pct` work correctly.
- [ ] All trades explainable: every fill can be traced to a VPA setup and rulebook entry.

---

## Phase 3: Alpaca live trading (future)

**Risk: Real money.** Only proceed after Phase 2 is proven stable.

What changes:

- Same `TradingClient` but with `paper=False` and live API keys.
- Config switch: `APCA_API_KEY_ID` / `APCA_API_SECRET_KEY` point to live keys; `execution.mode: live` in config (not yet implemented).
- Use a **separate** state DB path for live (never share with paper state).

### Steps to go live

1. **Prove Phase 2**: At least 4 weeks of stable paper trading, reconciled daily.
2. **Tighten risk limits**:
   - `max_cash_per_trade_pct`: 1-2% (not 5%).
   - `risk_pct_per_trade`: 0.5% initially.
   - Max 2-3 trades per day.
3. **Start tiny**: 1 share per trade. Run for 1-2 weeks.
4. **Monitor constantly**: Check Alpaca dashboard and journal after every trade.
5. **Scale gradually**: Increase size only after consistent, explainable results.

### Live safety requirements

- [ ] Kill switch: config flag or env var that disables order submission instantly.
- [ ] Max daily loss limit: stop trading if daily PnL drops below threshold.
- [ ] Market hours enforcement: no orders outside regular session unless intentional.
- [ ] Broker permissions verified: account approved for equity trading (and margin if used).
- [ ] Separate live state DB from paper state DB.
- [ ] Real-time monitoring of positions vs expectations.

---

## Warnings

- **The VPA rules engine is deterministic and rule-based.** It is not ML and does not optimize. But markets are unpredictable. Past backtest performance does not predict future results.
- **Single writer**: Only one process writes to a given execution state file. Never run two live writers.
- **Never risk more than you can afford to lose.** Start with the smallest possible position.
- **Every trade must be explainable.** If the system takes a trade you don't understand, stop and investigate. The journal and CLI output always show the rationale and rulebook reference.

---

## Summary

| Phase | Execution | Money at risk | Data source |
|-------|-----------|---------------|-------------|
| 1 (current) | `PaperExecutor` (local SQLite) | $0 | Alpaca IEX (free) |
| 2 (next) | `AlpacaPaperExecutor` (API, paper=True) | $0 | Alpaca IEX or SIP |
| 3 (future) | `TradingClient(paper=False)` | Real money | Alpaca SIP (recommended) |

All phases use the **same VPA rules from the book**. The signal logic is identical; only the execution layer changes.
