"""
Human-readable VPA reasoning output for the terminal.

The system must explain itself at every step -- not a black box.
Every CLI command uses these formatters. Journal receives the same data.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from vpa_core.contracts import Bar, ContextWindow, Signal, TradePlan
from vpa_core.context import detect_context
from vpa_core.features import bar_range, close_location, spread
from vpa_core.relative_volume import average_volume, relative_volume_for_bar

if TYPE_CHECKING:
    from vpa_core.contracts import CandleFeatures, ContextSnapshot, SignalEvent, TradeIntent
    from vpa_core.pipeline import PipelineResult


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


def format_pipeline_scan(
    bar: Bar,
    features: CandleFeatures,
    context: ContextSnapshot,
    result: PipelineResult,
    symbol: str,
    timeframe: str,
) -> str:
    """Format a full pipeline scan result showing VPA reasoning at every stage."""
    lines: list[str] = []

    lines.append(f"=== VPA Pipeline Scan: {symbol} {timeframe} @ {bar.timestamp.isoformat()} ===")
    lines.append("")

    bar_type = "UP" if bar.close >= bar.open else "DOWN"
    lines.append(f"  Bar     : {bar_type} | O {bar.open:.2f}  H {bar.high:.2f}  L {bar.low:.2f}  C {bar.close:.2f}  V {_fmt_volume(bar.volume)}")
    lines.append(f"  Spread  : {features.spread:.2f} (rel {features.spread_rel:.2f}x → {features.spread_state.value})")
    lines.append(f"  Range   : {features.range:.2f}  |  Upper wick: {features.upper_wick:.2f}  |  Lower wick: {features.lower_wick:.2f}")
    lines.append(f"  Volume  : rel {features.vol_rel:.2f}x → {features.vol_state.value}")
    lines.append(f"  Context : trend={context.trend.value}  location={context.trend_location.value}  strength={context.trend_strength.value}")

    if context.dominant_alignment:
        lines.append(f"  Dominant: {context.dominant_alignment.value}")

    lines.append("")

    if result.signals:
        lines.append(f"  Signals fired ({len(result.signals)}):")
        for sig in result.signals:
            gate_tag = " [needs gate]" if sig.requires_context_gate else ""
            lines.append(f"    → {sig.id} ({sig.signal_class.value}) bias={sig.direction_bias} pri={sig.priority}{gate_tag}")
    else:
        lines.append("  Signals fired: none")

    if result.gate_result:
        if result.gate_result.blocked:
            lines.append(f"  Blocked  ({len(result.gate_result.blocked)}):")
            for sig in result.gate_result.blocked:
                reason = result.gate_result.block_reasons.get(sig.id, "unknown")
                lines.append(f"    ✗ {sig.id}: {reason}")

    if result.matches:
        lines.append("")
        for m in result.matches:
            chain = " → ".join(s.id for s in m.signals)
            lines.append(f"  SETUP MATCH: {m.setup_id} ({m.direction}) — {chain}")

    if result.intents:
        lines.append("")
        for intent in result.intents:
            if intent.status.value == "READY":
                lines.append(f"  TRADE INTENT: {intent.setup} {intent.direction}")
                lines.append(f"    Entry : {intent.entry_plan.timing} ({intent.entry_plan.order_type})")
                lines.append(f"    Stop  : {intent.risk_plan.stop:.2f}")
                lines.append(f"    Size  : {intent.risk_plan.size} shares (risk {intent.risk_plan.risk_pct:.3%})")
                lines.append(f"    Chain : {' → '.join(intent.rationale)}")
            else:
                lines.append(f"  TRADE REJECTED: {intent.setup} — {intent.reject_reason}")

    if not result.signals:
        lines.append("")
        lines.append("  No VPA setups detected on this bar.")

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
