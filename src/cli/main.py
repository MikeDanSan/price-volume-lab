"""
CLI entry point: vpa ingest | backtest | scan | paper | status.

Every command loads config from --config (default config.yaml),
prints human-readable VPA reasoning, and logs to journal.
"""

import logging
import sys
from datetime import datetime, timedelta, timezone

import click

from config import load_config

logger = logging.getLogger("vpa")


def _setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s  %(message)s",
        stream=sys.stderr,
    )


@click.group()
@click.option("--config", "config_path", default="config.yaml", help="Path to config file.")
@click.pass_context
def cli(ctx: click.Context, config_path: str) -> None:
    """vpa-engine: Volume Price Analysis (Anna Coulling) — deterministic, explainable signals."""
    _setup_logging()
    ctx.ensure_object(dict)
    ctx.obj["config_path"] = config_path


# ---------- vpa ingest ----------


@cli.command()
@click.option("--days", default=30, help="Number of calendar days to fetch.")
@click.option("--start", "start_str", default=None, help="Start date (ISO, e.g. 2024-01-01).")
@click.option("--end", "end_str", default=None, help="End date (ISO, e.g. 2024-02-01).")
@click.pass_context
def ingest(ctx: click.Context, days: int, start_str: str | None, end_str: str | None) -> None:
    """Fetch bars from Alpaca and store locally."""
    cfg = load_config(ctx.obj["config_path"])
    from data import get_alpaca_fetcher
    from data.bar_store import BarStore

    fetcher = get_alpaca_fetcher(cfg.data.api_key, cfg.data.api_secret)
    store = BarStore(cfg.data.bar_store_path)

    end_dt = datetime.fromisoformat(end_str).replace(tzinfo=timezone.utc) if end_str else datetime.now(timezone.utc)
    start_dt = datetime.fromisoformat(start_str).replace(tzinfo=timezone.utc) if start_str else end_dt - timedelta(days=days)

    click.echo(f"Fetching {cfg.symbol} {cfg.timeframe} bars from {start_dt.date()} to {end_dt.date()} ...")
    result = fetcher.fetch(cfg.symbol, cfg.timeframe, start=start_dt, end=end_dt)
    if result.bars:
        store.write_bars(cfg.symbol, cfg.timeframe, result.bars)
        click.echo(f"Stored {len(result.bars)} bars in {cfg.data.bar_store_path}")
        click.echo(f"  Range: {result.bars[0].timestamp.isoformat()} -> {result.bars[-1].timestamp.isoformat()}")
    else:
        click.echo("No bars returned. Check symbol, timeframe, date range, and API keys.")


# ---------- vpa backtest ----------


@cli.command()
@click.option("--start", "start_str", default=None, help="Start date filter (ISO).")
@click.option("--end", "end_str", default=None, help="End date filter (ISO).")
@click.pass_context
def backtest(ctx: click.Context, start_str: str | None, end_str: str | None) -> None:
    """Run backtest on stored bars and show VPA reasoning for each trade."""
    cfg = load_config(ctx.obj["config_path"])
    from backtest import run_backtest
    from cli.output import format_backtest_summary
    from data.bar_store import BarStore
    from journal import JournalWriter

    store = BarStore(cfg.data.bar_store_path)
    since = datetime.fromisoformat(start_str).replace(tzinfo=timezone.utc) if start_str else None
    until = datetime.fromisoformat(end_str).replace(tzinfo=timezone.utc) if end_str else None
    bars = store.get_bars(cfg.symbol, cfg.timeframe, since=since, until=until)
    if not bars:
        click.echo("No bars in store. Run 'vpa ingest' first.")
        return

    journal = JournalWriter(cfg.journal.path, echo_stdout=cfg.journal.echo_stdout)

    def on_event(event_type: str, payload: dict) -> None:
        if event_type == "exit":
            t = payload["trade"]
            rationale_str = " -> ".join(t.rationale) if isinstance(t.rationale, list) else str(t.rationale)
            journal.trade(t.symbol, t.direction, t.entry_price, t.exit_price, t.qty, t.pnl, rationale_str, t.setup)
        elif event_type == "signal":
            intent = payload.get("intent")
            if intent:
                journal.signal(intent.setup, intent.direction, " -> ".join(intent.rationale), intent.setup)

    click.echo(f"Running backtest: {cfg.symbol} {cfg.timeframe}, {len(bars)} bars ...")
    result = run_backtest(
        bars,
        cfg.symbol,
        cfg.timeframe,
        initial_cash=cfg.backtest.initial_cash,
        slippage_bps=cfg.backtest.slippage_bps,
        journal_callback=on_event,
    )
    click.echo(format_backtest_summary(result))


# ---------- vpa scan ----------


@cli.command()
@click.option("--window", default=50, help="Context window size (number of bars).")
@click.pass_context
def scan(ctx: click.Context, window: int) -> None:
    """One-shot VPA analysis: show context, volume, and any detected setups with reasoning."""
    cfg = load_config(ctx.obj["config_path"])
    from cli.output import format_pipeline_scan
    from config.vpa_config import load_vpa_config
    from data.bar_store import BarStore
    from vpa_core.contracts import (
        Congestion,
        ContextSnapshot,
        DominantAlignment,
        Trend,
        TrendLocation,
        TrendStrength,
    )
    from vpa_core.context import CONTEXT_DOWNTREND, CONTEXT_UPTREND, detect_context
    from vpa_core.pipeline import run_pipeline
    from vpa_core.risk_engine import AccountState
    from vpa_core.setup_composer import SetupComposer

    store = BarStore(cfg.data.bar_store_path)
    bars = store.get_bars(cfg.symbol, cfg.timeframe)
    if not bars or len(bars) < 2:
        click.echo("Not enough bars in store. Run 'vpa ingest' first.")
        return

    bars = bars[-window:]
    vpa_cfg = load_vpa_config()
    composer = SetupComposer(vpa_cfg)
    bar_index = len(bars) - 1

    trend_str = detect_context(bars, lookback=vpa_cfg.trend.window_K)
    if trend_str == CONTEXT_UPTREND:
        trend, location = Trend.UP, TrendLocation.BOTTOM
    elif trend_str == CONTEXT_DOWNTREND:
        trend, location = Trend.DOWN, TrendLocation.TOP
    else:
        trend, location = Trend.RANGE, TrendLocation.MIDDLE

    context = ContextSnapshot(
        tf=cfg.timeframe,
        trend=trend,
        trend_strength=TrendStrength.MODERATE,
        trend_location=location,
        congestion=Congestion(active=False),
        dominant_alignment=DominantAlignment.WITH,
    )

    account = AccountState(equity=100_000.0)
    result = run_pipeline(
        bars, bar_index=bar_index, context=context,
        account=account, config=vpa_cfg, composer=composer, tf=cfg.timeframe,
    )

    click.echo(format_pipeline_scan(
        bar=bars[-1], features=result.features, context=context,
        result=result, symbol=cfg.symbol, timeframe=cfg.timeframe,
    ))


# ---------- vpa paper ----------


@cli.command()
@click.option("--window", default=50, help="Context window size.")
@click.pass_context
def paper(ctx: click.Context, window: int) -> None:
    """Evaluate latest window; if signal found, submit paper order. Shows full reasoning."""
    cfg = load_config(ctx.obj["config_path"])
    from cli.output import format_scan_result, format_signal
    from data.bar_store import BarStore
    from data.context_window import get_context_window
    from execution import PaperExecutor
    from journal import JournalWriter
    from vpa_core.signals import evaluate

    store = BarStore(cfg.data.bar_store_path)
    ctx_window = get_context_window(store, cfg.symbol, cfg.timeframe, window_size=window)
    if ctx_window is None:
        click.echo("No bars in store. Run 'vpa ingest' first.")
        return

    results = evaluate(ctx_window)
    click.echo(format_scan_result(ctx_window, results))

    if not results:
        return

    executor = PaperExecutor(
        cfg.execution.state_path,
        max_position_pct=cfg.execution.max_position_pct,
        max_cash_per_trade_pct=cfg.execution.max_cash_per_trade_pct,
        initial_cash=cfg.execution.initial_cash,
    )
    journal = JournalWriter(cfg.journal.path, echo_stdout=cfg.journal.echo_stdout)
    current_bar = ctx_window.current_bar()
    if current_bar is None:
        return

    for signal, plan in results:
        order = executor.submit(cfg.symbol, plan, current_bar.close)
        if order:
            journal.signal(signal.setup_type, signal.direction, signal.rationale, signal.rulebook_ref)
            journal.trade_plan(plan.signal_id, plan.setup_type, plan.direction, plan.rationale, plan.rulebook_ref)
            click.echo(f"\n  Paper order submitted: {order.side} {order.qty} {order.symbol} @ market")
            click.echo(f"  Trade plan ref: {order.trade_plan_ref}")
        else:
            click.echo(f"\n  Order rejected (risk limit or existing position for {cfg.symbol}).")
        break  # single position


# ---------- vpa status ----------


@cli.command()
@click.option("--fills", default=5, help="Number of recent fills to show.")
@click.pass_context
def status(ctx: click.Context, fills: int) -> None:
    """Show current position, cash, and recent fills."""
    cfg = load_config(ctx.obj["config_path"])
    from cli.output import format_position
    from execution import PaperExecutor

    executor = PaperExecutor(
        cfg.execution.state_path,
        max_position_pct=cfg.execution.max_position_pct,
        max_cash_per_trade_pct=cfg.execution.max_cash_per_trade_pct,
        initial_cash=cfg.execution.initial_cash,
    )
    pos = executor.get_position(cfg.symbol)
    cash = executor._get_cash()
    click.echo(format_position(pos, cash))

    recent_fills = executor.list_fills(symbol=cfg.symbol, limit=fills)
    if recent_fills:
        click.echo(f"\nRecent fills ({len(recent_fills)}):")
        for f in recent_fills:
            click.echo(f"  {f.side} {f.qty} {f.symbol} @ {f.price:.2f}  {f.timestamp.isoformat()}")
    else:
        click.echo("\nNo fills yet.")
