"""
Live paper-trading scheduler: market-aware loop that ingests bars and
runs the VPA pipeline at each bar close.

US equity regular session: 9:30 AM – 4:00 PM Eastern.
Sleeps overnight and on weekends.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import click

from config.loader import AppConfig

logger = logging.getLogger("vpa.scheduler")

ET = ZoneInfo("America/New_York")

MARKET_OPEN_H, MARKET_OPEN_M = 9, 30
MARKET_CLOSE_H, MARKET_CLOSE_M = 16, 0
BAR_BUFFER_SECONDS = 30


def parse_tf_minutes(timeframe: str) -> int:
    """Convert a timeframe string like '15m' or '1h' to minutes."""
    tf = timeframe.strip().lower()
    if tf.endswith("m"):
        return int(tf[:-1])
    if tf.endswith("h"):
        return int(tf[:-1]) * 60
    raise ValueError(f"Unsupported timeframe for live mode: {timeframe!r} (use e.g. '15m', '1h')")


def _market_open_time(day: datetime) -> datetime:
    return day.replace(hour=MARKET_OPEN_H, minute=MARKET_OPEN_M, second=0, microsecond=0)


def _market_close_time(day: datetime) -> datetime:
    return day.replace(hour=MARKET_CLOSE_H, minute=MARKET_CLOSE_M, second=0, microsecond=0)


def is_market_open(now: datetime) -> bool:
    """True if *now* (ET-aware) falls within regular market hours on a weekday."""
    if now.weekday() >= 5:
        return False
    return _market_open_time(now) <= now < _market_close_time(now)


def next_market_open(now: datetime) -> datetime:
    """Return the next market-open datetime (ET-aware), skipping weekends."""
    today_open = _market_open_time(now)
    if now < today_open and now.weekday() < 5:
        return today_open

    candidate = now + timedelta(days=1)
    candidate = _market_open_time(candidate)
    while candidate.weekday() >= 5:
        candidate += timedelta(days=1)
    return _market_open_time(candidate)


def next_bar_close(
    now: datetime,
    tf_minutes: int,
    market_open: datetime,
    market_close: datetime,
) -> datetime:
    """
    Return the next bar-close timestamp aligned to *tf_minutes* intervals
    starting from market open, capped at market close.
    """
    elapsed = (now - market_open).total_seconds()
    interval = tf_minutes * 60
    bars_elapsed = int(elapsed // interval) + 1
    candidate = market_open + timedelta(seconds=bars_elapsed * interval)
    if candidate > market_close:
        return market_close
    return candidate


def _ingest_latest(cfg: AppConfig) -> int:
    """Fetch last 1 day of bars into the store. Returns number of bars stored."""
    from data import get_alpaca_fetcher
    from data.bar_store import BarStore

    fetcher = get_alpaca_fetcher(cfg.data.api_key, cfg.data.api_secret)
    store = BarStore(cfg.data.bar_store_path)
    end = datetime.now(ET)
    start = end - timedelta(days=1)
    result = fetcher.fetch(cfg.symbol, cfg.timeframe, start=start, end=end)
    if result.bars:
        store.write_bars(cfg.symbol, cfg.timeframe, result.bars)
    return len(result.bars)


def _run_paper_cycle(cfg: AppConfig, window: int) -> None:
    """Single paper-trading evaluation cycle (ingest + pipeline + submit)."""
    from cli.output import format_pipeline_scan
    from config.vpa_config import load_vpa_config
    from data.bar_store import BarStore
    from execution import PaperExecutor
    from journal import JournalWriter
    from vpa_core.context_engine import analyze as analyze_context
    from vpa_core.pipeline import run_pipeline
    from vpa_core.risk_engine import AccountState
    from vpa_core.setup_composer import SetupComposer

    now_et = datetime.now(ET)
    bar_count = _ingest_latest(cfg)
    click.echo(f"[{now_et:%H:%M:%S} ET] Ingested {bar_count} bar(s).")

    store = BarStore(cfg.data.bar_store_path)
    bars = store.get_bars(cfg.symbol, cfg.timeframe)
    if not bars or len(bars) < 2:
        click.echo(f"[{now_et:%H:%M:%S} ET] Not enough bars in store. Skipping cycle.")
        return

    bars = bars[-window:]
    vpa_cfg = load_vpa_config()
    composer = SetupComposer(vpa_cfg)
    bar_index = len(bars) - 1
    context = analyze_context(bars, vpa_cfg, cfg.timeframe)

    account = AccountState(equity=cfg.execution.initial_cash)
    result = run_pipeline(
        bars, bar_index=bar_index, context=context,
        account=account, config=vpa_cfg, composer=composer, tf=cfg.timeframe,
    )

    click.echo(format_pipeline_scan(
        bar=bars[-1], features=result.features, context=context,
        result=result, symbol=cfg.symbol, timeframe=cfg.timeframe,
    ))

    ready_intents = [i for i in result.intents if i.status.value == "READY"]
    if not ready_intents:
        return

    executor = PaperExecutor(
        cfg.execution.state_path,
        max_position_pct=cfg.execution.max_position_pct,
        max_cash_per_trade_pct=cfg.execution.max_cash_per_trade_pct,
        initial_cash=cfg.execution.initial_cash,
    )
    journal = JournalWriter(cfg.journal.path, echo_stdout=cfg.journal.echo_stdout)

    for intent in ready_intents:
        order = executor.submit_intent(cfg.symbol, intent, bars[-1].close)
        if order:
            rationale_str = " -> ".join(intent.rationale)
            journal.signal(intent.setup, intent.direction, rationale_str, intent.setup)
            click.echo(f"  Paper order submitted: {order.side} {order.qty} {order.symbol} @ market")
            click.echo(f"  Setup: {intent.setup}  Stop: {intent.risk_plan.stop:.2f}")
        else:
            click.echo(f"  Order rejected (risk limit or existing position for {cfg.symbol}).")
        break


def run_live_loop(cfg: AppConfig, window: int) -> None:
    """
    Main loop: sleep until each bar close, ingest, evaluate, repeat.
    Ctrl+C for graceful shutdown.
    """
    tf_minutes = parse_tf_minutes(cfg.timeframe)
    cycles = 0

    click.echo(f"Live paper trading started: {cfg.symbol} {cfg.timeframe}")
    click.echo(f"Market hours: {MARKET_OPEN_H}:{MARKET_OPEN_M:02d}–"
               f"{MARKET_CLOSE_H}:{MARKET_CLOSE_M:02d} ET  |  Ctrl+C to stop\n")

    try:
        while True:
            now = datetime.now(ET)

            if not is_market_open(now):
                nxt = next_market_open(now)
                wait = (nxt - now).total_seconds()
                click.echo(f"[{now:%H:%M:%S} ET] Market closed. "
                           f"Sleeping until {nxt:%Y-%m-%d %H:%M} ET ({wait / 3600:.1f}h)")
                time.sleep(wait)
                continue

            m_open = _market_open_time(now)
            m_close = _market_close_time(now)
            nxt_bar = next_bar_close(now, tf_minutes, m_open, m_close)
            wake_at = nxt_bar + timedelta(seconds=BAR_BUFFER_SECONDS)
            wait = max(0, (wake_at - now).total_seconds())

            click.echo(f"[{now:%H:%M:%S} ET] Next bar close: {nxt_bar:%H:%M:%S} ET "
                       f"(sleeping {wait:.0f}s)")
            if wait > 0:
                time.sleep(wait)

            _run_paper_cycle(cfg, window)
            cycles += 1

    except KeyboardInterrupt:
        click.echo(f"\n\nShutting down after {cycles} cycle(s). Goodbye.")
