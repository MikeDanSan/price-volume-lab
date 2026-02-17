# VPA_CONFIG.md
**Project:** VPA — Canonical System  
**Purpose:** Single source of truth for all tunable parameters used to quantize Couling’s relative terms and enforce deterministic behavior.

## 1) Non-negotiables
- Any “LOW/HIGH/ULTRA” volume or “NARROW/WIDE” spread decision MUST come from config.
- No hardcoded thresholds in rule logic.
- Backtest must be bar-close evaluated; entry defaults to next-bar open unless explicitly overridden.

## 2) Parameters

### 2.1 Relative volume (Effort)
- `vol.avg_window_N` (default 20)
- `vol.thresholds.low_lt` (default 0.8)
- `vol.thresholds.high_gt` (default 1.2)
- `vol.thresholds.ultra_high_gt` (default 1.8)

### 2.2 Relative spread (Result)
- `spread.avg_window_M` (default 20)
- `spread.thresholds.narrow_lt` (default 0.8)
- `spread.thresholds.wide_gt` (default 1.2)

### 2.3 Trend windows
- `trend.window_K` (default 5)

### 2.4 Setup windows
- `setup.window_X` (default 5)

### 2.5 Context gates
- `gates.ctx1_trend_location_required` (default true)
- `gates.ctx2_dominant_alignment_policy` ("ALLOW" | "REDUCE_RISK" | "DISALLOW")
- `gates.ctx3_congestion_awareness_required` (default true)

### 2.6 Execution semantics (anti-lookahead)
- `execution.signal_eval` ("BAR_CLOSE_ONLY")
- `execution.entry_timing` ("NEXT_BAR_OPEN")
- `execution.intrabar_allowed` (default false)

### 2.7 Costs + slippage (deterministic)
- `costs.fee_model` ("BPS" | "PER_TRADE")
- `costs.fee_value`
- `slippage.model` ("BPS" | "TICKS")
- `slippage.value`

### 2.8 Risk policy
- `risk.risk_pct_per_trade`
- `risk.max_concurrent_positions`
- `risk.countertrend_multiplier`
- `risk.daily_loss_limit_pct` (optional)

## 3) Change control
- Any config change requires:
  - version bump in config file
  - updated tests for at least one rule impacted
  - backtest regression snapshot update
