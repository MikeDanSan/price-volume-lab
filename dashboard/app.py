"""
VPA dashboard: position state, cash, and recent journal activity per symbol.
Run from repo root: streamlit run dashboard/app.py
Or with data dir: VPA_DASHBOARD_DATA_DIR=/path/to/data streamlit run dashboard/app.py
"""

import streamlit as st

from data_reader import (
    discover_symbols,
    get_cash,
    get_position,
    get_recent_fills,
    get_recent_journal_events,
    _data_dir,
)

st.set_page_config(page_title="VPA Dashboard", layout="wide")
st.title("VPA Paper Trading Dashboard")

data_dir = _data_dir()
symbols = discover_symbols(data_dir)

if not symbols:
    st.warning(f"No symbols found under: `{data_dir}`")
    st.caption("Expect subdirs like data/SPY/, data/QQQ/ each with at least one of: paper_state.db, journal.jsonl, or bars.db. Run ingest (and optionally paper) per symbol or use docker-compose.")
    st.stop()

# Refresh
col_refresh, col_auto = st.columns([1, 3])
with col_refresh:
    if st.button("Refresh"):
        st.rerun()
with col_auto:
    auto_refresh = st.checkbox("Auto-refresh every 60s", value=False)

for symbol in symbols:
    pos = get_position(symbol)
    cash = get_cash(symbol)
    state = "Flat"
    if pos:
        side = (pos["side"] or "").lower()
        state = "Long" if side in ("long", "buy") else "Short"

    with st.container():
        st.subheader(symbol)
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("Position", state)
            if pos:
                qty = pos["qty"]
                st.caption(f"{abs(qty):.0f} @ {pos['avg_price']:.2f}")
        with c2:
            cash_str = f"${cash:,.2f}" if cash is not None else "—"
            st.metric("Cash", cash_str)
        with c3:
            if pos and cash is not None:
                notional = abs(pos["qty"]) * pos["avg_price"]
                st.metric("Notional", f"${notional:,.2f}")
            else:
                st.metric("Notional", "—")

        signals = get_recent_journal_events(symbol, event_type="signal", limit=10)
        trade_plans = get_recent_journal_events(symbol, event_type="trade_plan", limit=10)
        fills = get_recent_fills(symbol, limit=15)
        invalidations = get_recent_journal_events(symbol, event_type="invalidation", limit=10)

        with st.expander("Recent signals", expanded=False):
            if not signals:
                st.caption("No signals yet.")
            else:
                for e in signals:
                    ts = e.get("ts_utc", "")[:19]
                    setup = e.get("setup_type", "")
                    direction = e.get("direction", "")
                    rationale = (e.get("rationale") or "")[:120]
                    st.text(f"{ts}  {setup}  {direction}")
                    if rationale:
                        st.caption(rationale + ("..." if len(e.get("rationale", "")) > 120 else ""))

        with st.expander("Recent trade plans", expanded=False):
            if not trade_plans:
                st.caption("No trade plans yet.")
            else:
                for e in trade_plans:
                    ts = e.get("ts_utc", "")[:19]
                    setup = e.get("setup_type", "")
                    direction = e.get("direction", "")
                    rationale = (e.get("rationale") or "")[:120]
                    st.text(f"{ts}  {setup}  {direction}")
                    if rationale:
                        st.caption(rationale + ("..." if len(e.get("rationale", "")) > 120 else ""))

        with st.expander("Recent fills", expanded=False):
            if not fills:
                st.caption("No fills yet.")
            else:
                for f in fills:
                    ts = (f.get("ts_utc") or "")[:19]
                    st.text(f"{ts}  {f.get('side')}  {f.get('qty')} @ {f.get('price')}")

        with st.expander("Invalidations", expanded=False):
            if not invalidations:
                st.caption("No invalidations yet.")
            else:
                for e in invalidations:
                    ts = e.get("ts_utc", "")[:19]
                    reason = e.get("reason", "")
                    setup = e.get("setup_type", "")
                    st.text(f"{ts}  {setup}: {reason}")

    st.divider()

if auto_refresh:
    import time
    time.sleep(60)
    st.rerun()
