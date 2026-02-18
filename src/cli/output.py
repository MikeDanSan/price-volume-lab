"""
Human-readable VPA reasoning output for the terminal.

The system must explain itself at every step -- not a black box.
Every CLI command uses these formatters. Journal receives the same data.
"""

from vpa_core.contracts import Bar, ContextWindow, Signal, TradePlan
from vpa_core.context import detect_context
from vpa_core.features import bar_range, close_location, spread
from vpa_core.relative_volume import average_volume, relative_volume_for_bar


def _fmt_volume(vol: int | float) -> str:
    if vol >= 1_000_000:
        return f"{vol / 1_000_000:.2f}M"
    if vol >= 1_000:
        return f"{vol / 1_000:.0f}K"
    return str(int(vol))


def format_bar_analysis(window: ContextWindow) -> str:
    """Format the current bar's VPA analysis: context, volume, close location."""
    bars = list(window.bars)
    if not bars:
        return "No bars in context window."
    current = bars[-1]
    ctx = detect_context(bars, lookback=3)
    rel_vol = relative_volume_for_bar(bars)
    avg_vol = average_volume(bars, lookback=20)
    ratio = current.volume / avg_vol if avg_vol > 0 else 0.0
    cloc = close_location(current)
    bar_spread = spread(current)
    bar_rng = bar_range(current)
    bar_type = "up" if current.is_up() else "down"

    lines = [
        f"--- VPA Analysis: {window.symbol} {window.timeframe or ''} @ {current.timestamp.isoformat()} ---",
        f"Bar          : {bar_type} | O {current.open:.2f}  H {current.high:.2f}  L {current.low:.2f}  C {current.close:.2f}",
        f"Spread (body): {bar_spread:.2f}  |  Range: {bar_rng:.2f}",
        f"Close loc.   : {cloc} third",
        f"Context      : {ctx}",
        f"Rel. volume  : {rel_vol.value} (current {_fmt_volume(current.volume)} vs 20-bar avg {_fmt_volume(avg_vol)} = {ratio:.2f}x)",
    ]
    return "\n".join(lines)


def format_signal(signal: Signal, plan: TradePlan) -> str:
    """Format a detected VPA setup with full rationale."""
    lines = [
        "",
        f"  Setup detected: {signal.setup_type.upper().replace('_', ' ')}  [rulebook: {signal.rulebook_ref}]",
        f"  Direction    : {plan.direction}",
        f"  Rationale    : {plan.rationale}",
        f"  Entry        : {plan.entry_condition}",
        f"  Stop         : {plan.stop_level}",
    ]
    if isinstance(plan.invalidation_rules, list):
        for rule in plan.invalidation_rules:
            lines.append(f"  Invalidation : {rule}")
    else:
        lines.append(f"  Invalidation : {plan.invalidation_rules}")
    if plan.target_logic:
        lines.append(f"  Target       : {plan.target_logic}")
    return "\n".join(lines)


def format_no_setups() -> str:
    return "\n  No VPA setups detected on this bar."


def format_scan_result(window: ContextWindow, results: list[tuple[Signal, TradePlan]]) -> str:
    """Full scan output: bar analysis + any signals."""
    parts = [format_bar_analysis(window)]
    if results:
        for signal, plan in results:
            parts.append(format_signal(signal, plan))
    else:
        parts.append(format_no_setups())
    parts.append("---")
    return "\n".join(parts)


def format_backtest_summary(result) -> str:
    """Format backtest result summary."""
    lines = [
        f"=== Backtest: {result.symbol} {result.timeframe} ===",
        f"Period       : {result.start_time.isoformat()} -> {result.end_time.isoformat()}",
        f"Initial cash : ${result.initial_cash:,.2f}",
        f"Final cash   : ${result.final_cash:,.2f}",
        f"Return       : {result.total_return_pct:+.2f}%",
        f"Trades       : {len(result.trades)} (W:{result.win_count} / L:{result.loss_count})",
    ]
    if result.trades:
        lines.append("")
        for i, t in enumerate(result.trades, 1):
            lines.append(f"  Trade #{i}: {t.direction} | entry {t.entry_price:.2f} @ {t.entry_time.isoformat()}")
            lines.append(f"            exit  {t.exit_price:.2f} @ {t.exit_time.isoformat()} | PnL ${t.pnl:+.2f}")
            rationale_str = " -> ".join(t.rationale) if isinstance(t.rationale, list) else str(t.rationale)
            lines.append(f"            Rationale: {rationale_str}")
            lines.append(f"            Setup    : {t.setup}")
    lines.append("===")
    return "\n".join(lines)


def format_position(pos, cash: float) -> str:
    """Format current position and cash."""
    lines = [
        "=== Account Status ===",
        f"Cash         : ${cash:,.2f}",
    ]
    if pos:
        lines.append(f"Position     : {pos.symbol} {pos.side} {abs(pos.qty)} shares @ avg {pos.avg_price:.2f}")
        lines.append(f"Updated      : {pos.updated_at.isoformat()}")
    else:
        lines.append("Position     : flat (no open position)")
    lines.append("===")
    return "\n".join(lines)
