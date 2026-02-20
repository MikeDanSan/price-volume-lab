# VPA Dashboard

Simple Streamlit dashboard for paper trading state: position (Flat/Long/Short), cash, and recent journal activity per symbol.

## Run

From the repo root:

```bash
source .venv/bin/activate
pip install -e ".[dashboard]"
streamlit run dashboard/app.py
```

Or with a custom data directory:

```bash
VPA_DASHBOARD_DATA_DIR=/path/to/data streamlit run dashboard/app.py
```

## Data

The dashboard discovers symbols by looking for `data/<SYMBOL>/paper_state.db`. Each symbol shows:

- **Position**: Flat, Long, or Short (with qty and avg price)
- **Cash**: Current balance
- **Recent signals** / **trade plans** / **fills** / **invalidations** from the journal

Read-only; no writes to state or journal.
