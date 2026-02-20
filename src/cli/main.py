"""
CLI entry point: vpa ingest | backtest | scan | paper | status.

Every command loads config from --config (default config.yaml),
prints human-readable VPA reasoning, and logs to journal.
"""

import logging
import sys
from datetime import datetime, timedelta, timezone

import click
from dotenv import load_dotenv

from config import load_config

load_dotenv()

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
@click.option("--days", default=None, type=int, help="Number of calendar days to fetch (default: 30 for intraday, 365 for daily).")
@click.option("--start", "start_str", default=None, help="Start date (ISO, e.g. 2024-01-01).")
@click.option("--end", "end_str", default=None, help="End date (ISO, e.g. 2024-02-01).")
@click.option("--timeframe", "tf_override", default=None, help="Override timeframe (e.g. 1d, 15m). Defaults to config value.")
@click.pass_context
def ingest(ctx: click.Context, days: int | None, start_str: str | None, end_str: str | None, tf_override: str | None) -> None:
    """Fetch bars from Alpaca and store locally.

    Use --timeframe 1d to ingest daily bars for multi-timeframe analysis.
    Daily bars default to 365 days of history; intraday defaults to 30.
    """
    cfg = load_config(ctx.obj["config_path"])
    from data import get_alpaca_fetcher
    from data.bar_store import BarStore

    fetcher = get_alpaca_fetcher(cfg.data.api_key, cfg.data.api_secret)
    store = BarStore(cfg.data.bar_store_path)

    tf = tf_override or cfg.timeframe
    if days is None:
        days = 365 if tf == "1d" else 30

    end_dt = datetime.fromisoformat(end_str).replace(tzinfo=timezone.utc) if end_str else datetime.now(timezone.utc)
    start_dt = datetime.fromisoformat(start_str).replace(tzinfo=timezone.utc) if start_str else end_dt - timedelta(days=days)

    click.echo(f"Fetching {cfg.symbol} {tf} bars from {start_dt.date()} to {end_dt.date()} ...")
    result = fetcher.fetch(cfg.symbol, tf, start=start_dt, end=end_dt)
    if result.bars:
        store.write_bars(cfg.symbol, tf, result.bars)
        click.echo(f"Stored {len(result.bars)} bars in {cfg.data.bar_store_path}")
        click.echo(f"  Range: {result.bars[0].timestamp.isoformat()} -> {result.bars[-1].timestamp.isoformat()}")
        total = store.count_bars(cfg.symbol, tf)
        click.echo(f"  Total {tf} bars in store: {total}")
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

    daily_bars = store.get_bars(cfg.symbol, "1d")
    if daily_bars:
        click.echo(f"Loaded {len(daily_bars)} daily bars for multi-timeframe analysis.")
    else:
        click.echo("No daily bars found. Run 'vpa ingest --timeframe 1d' for multi-timeframe.")

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
        daily_bars=daily_bars or None,
    )
    click.echo(format_backtest_summary(result))


# ---------- vpa scan ----------


@cli.command()
@click.option("--window", default=50, help="Context window size (number of bars).")
@click.pass_context
def scan(ctx: click.Context, window: int) -> None:
    """One-shot VPA analysis: show context, volume, and any detected setups with reasoning."""
    cfg = load_config(ctx.obj["config_path"])
    from cli.daily_helper import load_daily_context
    from cli.output import format_pipeline_scan
    from config.vpa_config import load_vpa_config
    from data.bar_store import BarStore
    from vpa_core.context_engine import analyze as analyze_context
    from vpa_core.pipeline import run_pipeline
    from vpa_core.risk_engine import AccountState
    from vpa_core.setup_composer import SetupComposer

    store = BarStore(cfg.data.bar_store_path)
    bars = store.get_bars(cfg.symbol, cfg.timeframe)
    if not bars or len(bars) < 2:
        click.echo("Not enough bars in store. Run 'vpa ingest' first.")
        return

    bars = bars[-window:]
    vpa_cfg = load_vpa_config(symbol=cfg.symbol)
    composer = SetupComposer(vpa_cfg)
    bar_index = len(bars) - 1

    context = analyze_context(bars, vpa_cfg, cfg.timeframe)
    daily_ctx = load_daily_context(store, cfg.symbol, vpa_cfg)

    account = AccountState(equity=100_000.0)
    result = run_pipeline(
        bars, bar_index=bar_index, context=context,
        account=account, config=vpa_cfg, composer=composer, tf=cfg.timeframe,
        daily_context=daily_ctx,
    )

    click.echo(format_pipeline_scan(
        bar=bars[-1], features=result.features, context=context,
        result=result, symbol=cfg.symbol, timeframe=cfg.timeframe,
    ))


# ---------- vpa paper ----------


@cli.command()
@click.option("--window", default=50, help="Context window size.")
@click.option("--live", is_flag=True, default=False, help="Run continuously, evaluating each bar close during market hours.")
@click.pass_context
def paper(ctx: click.Context, window: int, live: bool) -> None:
    """Evaluate latest window; if signal found, submit paper order. Shows full reasoning."""
    cfg = load_config(ctx.obj["config_path"])

    if live:
        from cli.scheduler import run_live_loop
        run_live_loop(cfg, window)
        return
    from cli.daily_helper import load_daily_context
    from cli.output import format_pipeline_scan
    from config.vpa_config import load_vpa_config
    from data.bar_store import BarStore
    from execution import PaperExecutor
    from journal import JournalWriter
    from vpa_core.context_engine import analyze as analyze_context
    from vpa_core.pipeline import run_pipeline
    from vpa_core.risk_engine import AccountState
    from vpa_core.setup_composer import SetupComposer

    store = BarStore(cfg.data.bar_store_path)
    bars = store.get_bars(cfg.symbol, cfg.timeframe)
    if not bars or len(bars) < 2:
        click.echo("Not enough bars in store. Run 'vpa ingest' first.")
        return

    bars = bars[-window:]
    vpa_cfg = load_vpa_config(symbol=cfg.symbol)
    composer = SetupComposer(vpa_cfg)
    bar_index = len(bars) - 1

    context = analyze_context(bars, vpa_cfg, cfg.timeframe)
    daily_ctx = load_daily_context(store, cfg.symbol, vpa_cfg)

    account = AccountState(equity=cfg.execution.initial_cash)
    result = run_pipeline(
        bars, bar_index=bar_index, context=context,
        account=account, config=vpa_cfg, composer=composer, tf=cfg.timeframe,
        daily_context=daily_ctx,
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
            click.echo(f"\n  Paper order submitted: {order.side} {order.qty} {order.symbol} @ market")
            click.echo(f"  Setup: {intent.setup}  Stop: {intent.risk_plan.stop:.2f}")
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


# ---------- vpa replay ----------


@cli.command()
@click.option("--window", default=50, help="Context window size.")
@click.option("--last", "last_n", default=None, type=int, help="Only replay the last N bars (default: all bars in store).")
@click.option("--sensitivity", is_flag=True, default=False, help="Include threshold proximity report (near-misses).")
@click.pass_context
def replay(ctx: click.Context, window: int, last_n: int | None, sensitivity: bool) -> None:
    """Replay stored bars through the pipeline and diagnose setup lifecycle.

    Shows which trigger signals opened candidates, whether they expired
    (missing completer), were invalidated, or completed into setups.
    Also reports gate blocks and a signal frequency summary.

    Use --sensitivity to see how close bars were to triggering rules
    that didn't fire (threshold proximity analysis).
    """
    cfg = load_config(ctx.obj["config_path"])
    from collections import Counter

    from cli.daily_helper import load_daily_context
    from config.vpa_config import load_vpa_config
    from data.bar_store import BarStore
    from vpa_core.context_engine import analyze as analyze_context
    from vpa_core.pipeline import run_pipeline
    from vpa_core.risk_engine import AccountState
    from vpa_core.sensitivity import NearMiss, compute_near_misses
    from vpa_core.setup_composer import SetupComposer

    store = BarStore(cfg.data.bar_store_path)
    bars = store.get_bars(cfg.symbol, cfg.timeframe)
    if not bars or len(bars) < 2:
        click.echo("Not enough bars in store. Run 'vpa ingest' first.")
        return

    if last_n is not None:
        bars = bars[-last_n:]

    vpa_cfg = load_vpa_config(symbol=cfg.symbol)
    composer = SetupComposer(vpa_cfg, record_events=True)
    daily_ctx = load_daily_context(store, cfg.symbol, vpa_cfg)
    account = AccountState(equity=100_000.0)

    signal_counter: Counter[str] = Counter()
    gate_blocks: Counter[str] = Counter()
    near_miss_counter: Counter[str] = Counter()
    near_miss_examples: list[tuple[int, NearMiss]] = []
    intent_count = 0
    bars_evaluated = 0

    for i in range(window, len(bars)):
        bar_slice = bars[i - window : i + 1]
        context = analyze_context(bar_slice, vpa_cfg, cfg.timeframe)
        result = run_pipeline(
            bar_slice,
            bar_index=i,
            context=context,
            account=account,
            config=vpa_cfg,
            composer=composer,
            tf=cfg.timeframe,
            daily_context=daily_ctx,
        )
        for sig in result.signals:
            signal_counter[sig.id] += 1
        if result.gate_result:
            for sig in result.gate_result.blocked:
                key = f"{sig.id}@{sig.ts.isoformat()}"
                reason = result.gate_result.block_reasons.get(key, "unknown")
                gate_blocks[reason] += 1
        intent_count += len(result.intents)
        bars_evaluated += 1

        if sensitivity and result.features:
            misses = compute_near_misses(result.features, vpa_cfg)
            for m in misses:
                near_miss_counter[m.condition] += 1
                if len(near_miss_examples) < 50:
                    near_miss_examples.append((i, m))

    # --- Output report ---
    click.echo(f"=== VPA Replay: {cfg.symbol} {cfg.timeframe} ===")
    click.echo(f"Bars evaluated   : {bars_evaluated}")
    click.echo(f"Period           : {bars[window].timestamp.isoformat()} → {bars[-1].timestamp.isoformat()}")
    if daily_ctx:
        click.echo(f"Daily context    : trend={daily_ctx.trend.value}  strength={daily_ctx.trend_strength.value}")
    else:
        click.echo("Daily context    : N/A (no daily bars)")
    click.echo("")

    # Signal frequency
    click.echo("--- Signal Frequency ---")
    if signal_counter:
        for sig_id, count in signal_counter.most_common():
            click.echo(f"  {sig_id:25s} {count:>4d} times")
    else:
        click.echo("  (none)")
    click.echo("")

    # Gate blocks
    click.echo("--- Gate Blocks ---")
    if gate_blocks:
        for reason, count in gate_blocks.most_common():
            click.echo(f"  {reason:40s} {count:>4d}")
    else:
        click.echo("  (none)")
    click.echo("")

    # Setup candidate lifecycle
    events = composer.event_log
    click.echo("--- Setup Candidate Lifecycle ---")
    if not events:
        click.echo("  No setup candidates were opened during the replay period.")
    else:
        opened = [e for e in events if e.event == "opened"]
        completed = [e for e in events if e.event == "completed"]
        expired = [e for e in events if e.event == "expired"]
        invalidated = [e for e in events if e.event == "invalidated"]

        click.echo(f"  Opened       : {len(opened)}")
        click.echo(f"  Completed    : {len(completed)}")
        click.echo(f"  Expired      : {len(expired)}")
        click.echo(f"  Invalidated  : {len(invalidated)}")
        click.echo("")

        for evt in events:
            bar_ts = bars[evt.bar_index].timestamp if evt.bar_index < len(bars) else "?"
            if evt.event == "opened":
                needed = " | ".join(evt.completer_needed)
                click.echo(f"  [{evt.event:11s}] bar {evt.bar_index} ({bar_ts}) "
                           f"{evt.setup_id} ({evt.direction}) "
                           f"trigger={evt.trigger_signal}  needs=[{needed}]")
            elif evt.event == "completed":
                click.echo(f"  [{evt.event:11s}] bar {evt.bar_index} ({bar_ts}) "
                           f"{evt.setup_id} ({evt.direction}) "
                           f"trigger={evt.trigger_signal}  got={evt.completer_got}")
            elif evt.event == "expired":
                needed = " | ".join(evt.completer_needed)
                click.echo(f"  [{evt.event:11s}] bar {evt.bar_index} ({bar_ts}) "
                           f"{evt.setup_id} ({evt.direction}) "
                           f"trigger={evt.trigger_signal}  missing=[{needed}]")
            elif evt.event == "invalidated":
                click.echo(f"  [{evt.event:11s}] bar {evt.bar_index} ({bar_ts}) "
                           f"{evt.setup_id} ({evt.direction}) "
                           f"trigger={evt.trigger_signal}")

    # Sensitivity report
    if sensitivity:
        click.echo("")
        click.echo("--- Threshold Sensitivity (Near-Misses) ---")
        if near_miss_counter:
            click.echo("  Frequency of near-miss conditions across all bars:")
            for cond, count in near_miss_counter.most_common(15):
                click.echo(f"    {cond:55s} {count:>4d} bars")
            click.echo("")
            click.echo("  Sample near-misses (first occurrences):")
            shown = set()
            for bar_idx, m in near_miss_examples:
                key = m.condition
                if key in shown:
                    continue
                shown.add(key)
                bar_ts = bars[bar_idx].timestamp if bar_idx < len(bars) else "?"
                direction = "below" if m.gap_pct < 0 else "above"
                click.echo(f"    bar {bar_idx} ({bar_ts})")
                click.echo(f"      {m.rule_id:15s} {m.condition}")
                click.echo(f"      actual={m.actual:.4f}  threshold={m.threshold:.4f}  "
                           f"({abs(m.gap_pct):.1%} {direction})")
        else:
            click.echo("  No near-misses detected (all conditions were either clearly met or clearly missed).")

    click.echo("")
    click.echo(f"Trade intents    : {intent_count}")
    click.echo("===")


# ---------- vpa health ----------


@cli.command()
@click.pass_context
def health(ctx: click.Context) -> None:
    """Check system health: config, VPA config, DB access, bar data.

    Exit code 0 = healthy, 1 = unhealthy. Designed for Docker HEALTHCHECK.
    """
    checks: list[tuple[str, bool, str]] = []

    try:
        cfg = load_config(ctx.obj["config_path"])
        checks.append(("config", True, f"loaded ({cfg.symbol} {cfg.timeframe})"))
    except Exception as e:
        checks.append(("config", False, str(e)))
        _print_health(checks)
        raise SystemExit(1)

    try:
        from config.vpa_config import load_vpa_config
        vpa_cfg = load_vpa_config(symbol=cfg.symbol)
        rule_count = len(vpa_cfg.vol.thresholds.__dataclass_fields__)
        checks.append(("vpa_config", True, f"validated (symbol={cfg.symbol})"))
    except Exception as e:
        checks.append(("vpa_config", False, str(e)))

    try:
        from data.bar_store import BarStore
        store = BarStore(cfg.data.bar_store_path)
        bar_count = store.count_bars(cfg.symbol, cfg.timeframe)
        daily_count = store.count_bars(cfg.symbol, "1d")
        if bar_count > 0:
            checks.append(("bars", True, f"{bar_count} {cfg.timeframe} bars, {daily_count} daily bars"))
        else:
            checks.append(("bars", False, f"no {cfg.timeframe} bars for {cfg.symbol}"))
    except Exception as e:
        checks.append(("bars", False, str(e)))

    _print_health(checks)
    healthy = all(ok for _, ok, _ in checks)
    raise SystemExit(0 if healthy else 1)


def _print_health(checks: list[tuple[str, bool, str]]) -> None:
    for name, ok, detail in checks:
        status = "OK" if ok else "FAIL"
        click.echo(f"  [{status}] {name}: {detail}")
    healthy = all(ok for _, ok, _ in checks)
    click.echo(f"\nHealth: {'HEALTHY' if healthy else 'UNHEALTHY'}")


if __name__ == "__main__":
    cli()
