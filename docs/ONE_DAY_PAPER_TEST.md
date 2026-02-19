# One-Day Paper Trading Test via Docker Compose

Last updated: 2026-02-19

Run both SPY and QQQ paper traders for a full market day using docker-compose, then review the results. **Zero real money at risk** -- all trades are simulated locally.

---

## Prerequisites

| Requirement | Check |
|-------------|-------|
| Docker & Docker Compose installed | `docker compose version` |
| Alpaca paper-trading API keys | [Generate here](https://app.alpaca.markets/paper/dashboard/overview) |
| `.env` file at repo root with keys set | See Step 1 below |

---

## Morning: Start the Test

### Step 1 -- Verify your `.env` file

```bash
# If you haven't created .env yet:
cp .env.example .env
# Then edit .env and paste in your Alpaca PAPER trading keys
```

Your `.env` should contain:

```
APCA_API_KEY_ID=PK...
APCA_API_SECRET_KEY=...
```

### Step 2 -- Build the Docker image

```bash
docker compose build
```

### Step 3 -- Ingest historical bars (needed for VPA context)

Each symbol needs ~60 days of 15-minute bars so VPA has enough context to detect setups.

```bash
docker compose run --rm vpa-spy ingest --days 60
docker compose run --rm vpa-qqq ingest --days 60
```

### Step 4 -- Start live paper trading

```bash
docker compose up -d
```

This starts both `vpa-spy` and `vpa-qqq` in detached mode. Each service runs `vpa paper --live`, which continuously evaluates bars during market hours (9:30 AM -- 4:00 PM ET) and submits simulated orders when VPA setups trigger.

### Step 5 -- Confirm services are healthy

```bash
docker compose ps
```

You should see both containers with status `Up` and health `healthy`.

---

## During the Day: Monitor (Optional)

### Watch live signals in real time

```bash
docker compose logs -f
```

Press `Ctrl+C` to stop following (the containers keep running).

### Watch one symbol only

```bash
docker compose logs -f vpa-spy
docker compose logs -f vpa-qqq
```

### Check container health

```bash
docker compose ps
```

---

## End of Day: Review Results

### 1. View current positions and cash

```bash
# SPY
docker compose run --rm vpa-spy status

# QQQ
docker compose run --rm vpa-qqq status

# Show more fill history
docker compose run --rm vpa-spy status --fills 20
docker compose run --rm vpa-qqq status --fills 20
```

### 2. Read the full trade journal

Every signal, trade plan, fill, and invalidation is logged with timestamps and rationale.

```bash
# SPY journal (pretty-printed if you have jq)
cat data/SPY/journal.jsonl | jq .

# QQQ journal
cat data/QQQ/journal.jsonl | jq .

# Without jq, the raw JSONL is still readable
cat data/SPY/journal.jsonl
cat data/QQQ/journal.jsonl
```

### 3. Query the paper trading database directly

```bash
# SPY -- recent fills
sqlite3 data/SPY/paper_state.db "SELECT * FROM fills ORDER BY ts_utc DESC;"

# SPY -- current positions
sqlite3 data/SPY/paper_state.db "SELECT * FROM positions;"

# SPY -- cash balance
sqlite3 data/SPY/paper_state.db "SELECT * FROM cash;"

# QQQ -- same queries
sqlite3 data/QQQ/paper_state.db "SELECT * FROM fills ORDER BY ts_utc DESC;"
sqlite3 data/QQQ/paper_state.db "SELECT * FROM positions;"
sqlite3 data/QQQ/paper_state.db "SELECT * FROM cash;"
```

### 4. Review the full day's Docker logs

```bash
# All output from both services
docker compose logs > today_logs.txt

# Per symbol
docker compose logs vpa-spy > today_spy.txt
docker compose logs vpa-qqq > today_qqq.txt
```

### 5. Run a VPA scan to see the final market read

```bash
docker compose run --rm vpa-spy scan
docker compose run --rm vpa-qqq scan
```

---

## End of Day: Stop the Test

```bash
docker compose down
```

This stops and removes both containers. Your data is preserved in the `data/` directory (SQLite DBs and journal files persist on the host).

---

## Quick Reference

| Action | Command |
|--------|---------|
| Build image | `docker compose build` |
| Ingest bars | `docker compose run --rm vpa-spy ingest --days 60` |
| Start trading | `docker compose up -d` |
| Check status | `docker compose ps` |
| Follow logs | `docker compose logs -f` |
| View positions/cash | `docker compose run --rm vpa-spy status` |
| Read journal | `cat data/SPY/journal.jsonl \| jq .` |
| Query fills | `sqlite3 data/SPY/paper_state.db "SELECT * FROM fills;"` |
| Final scan | `docker compose run --rm vpa-spy scan` |
| Stop everything | `docker compose down` |

---

## What to Look For

When reviewing the day's results, pay attention to:

- **Number of signals vs trades** -- Did the engine detect setups? Did it act on them?
- **Rationale quality** -- Every journal entry has a `rationale` field explaining why the signal fired (or didn't). Read these to verify the logic matches VPA rules.
- **Cash and P&L** -- Starting cash is $100,000 per symbol. Compare ending cash to see net impact.
- **Rejected orders** -- Check logs for "Order rejected" messages, which indicate risk limits were hit.
- **No activity** -- If zero trades occurred, that's normal. VPA setups don't fire every day. Run `vpa scan` to see the engine's read of the market.

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Container exits immediately | `docker compose logs vpa-spy` -- check for missing env vars or config errors |
| "No bars in store" | Re-run the ingest step: `docker compose run --rm vpa-spy ingest --days 60` |
| Health check failing | `docker compose run --rm vpa-spy health` to see the error |
| SQLite locked | Only one process per symbol should write to the same state DB. Stop containers before querying with `sqlite3` if you get lock errors |
| No `.env` file | `cp .env.example .env` and add your Alpaca paper-trading keys |
