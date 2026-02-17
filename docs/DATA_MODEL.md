# Data model and contracts

Last updated: 2026-02-17

> **Canonical data models**: The canonical `CandleFeatures`, `ContextSnapshot`, `SignalEvent`, and `TradeIntent`  
> schemas are defined in [`docs/vpa-ck/vpa_system_spec.md`](vpa-ck/vpa_system_spec.md) §3.3.  
> This file documents the current (legacy) code models. They will be aligned to the canonical spec  
> per the fix plan. If there is a conflict, the canonical spec wins.

Field names, types, and semantics for vpa-engine. Keeps vpa-core and callers aligned. See [PROJECT_CONTEXT.md](PROJECT_CONTEXT.md) and [ARCHITECTURE.md](ARCHITECTURE.md).

---

## Bar

OHLCV bar; no indicator fields required for core.

| Field | Type | Description |
|-------|------|-------------|
| `open` | float | Open price |
| `high` | float | High price |
| `low` | float | Low price |
| `close` | float | Close price |
| `volume` | int | Volume (trades/shares) |
| `timestamp` | datetime (UTC) | Bar start time; normalized to UTC |
| `symbol` | str | Instrument (e.g. `"SPY"`) |

Optional for downstream: `bar_index` (int, 0-based order in series) if the provider attaches it.

---

## Context window

Input to vpa-core for a given bar.

| Field | Type | Description |
|-------|------|-------------|
| `bars` | list[Bar] or sequence of bar-like dicts | Ordered list of bars, oldest first. Typically “current bar” is last; all are past (no lookahead). |
| `symbol` | str | Same as Bar.symbol |
| `timeframe` | str, optional | e.g. `"15m"`, `"1h"` |

Optional (for future use): prior swing highs/lows or structure metadata for “background strength/weakness”. MVP can use only `bars`.

---

## Relative volume classification

Output of relative-volume step; used by setup detection.

> **Canonical model** (from `VPA_ACTIONABLE_RULES.md`): 4-state `VolumeState` using `VolRel = volume / SMA(volume, N)`:
>
> | State | Condition (default thresholds) |
> |-------|-------------------------------|
> | `LOW` | VolRel < 0.8 |
> | `AVERAGE` | 0.8 <= VolRel <= 1.2 |
> | `HIGH` | 1.2 < VolRel <= 1.8 |
> | `ULTRA_HIGH` | VolRel > 1.8 |

**Current code** uses a 3-state enum (`HIGH`, `NORMAL`, `LOW`). This will be aligned to the 4-state canonical model per the fix plan.

Baseline definition (N-bar average) and thresholds must come from VPA config (`vpa.default.json`).

---

## Signal

Output of setup matching; one per detected setup.

| Field | Type | Description |
|-------|------|-------------|
| `setup_type` | str | e.g. `"no_demand"`, `"stopping_volume"`; must match rulebook id |
| `direction` | str | `"long"` or `"short"` |
| `bar_index` | int | Index of bar where signal occurred (in the window) |
| `timestamp` | datetime (UTC) | Bar timestamp |
| `rationale` | str | Plain-English explanation |
| `rulebook_ref` | str | Rule/setup id in rulebook (e.g. `"no_demand_01"`) |
| `strength` | str or None | Optional; if book defines strength (e.g. “strong” vs “weak” no demand) |

---

## TradePlan

Trading intent produced from a signal; not an order. Execution layer converts to orders.

| Field | Type | Description |
|-------|------|-------------|
| `signal_id` | str | Links to Signal (e.g. id or bar_index + timestamp) |
| `setup_type` | str | Same as Signal.setup_type |
| `direction` | str | `"long"` or `"short"` |
| `entry_condition` | str or structured | When to enter (e.g. “next bar open”, “close above X”) |
| `stop_level` | float or str | Stop price or rule (e.g. “below bar low”) |
| `invalidation_rules` | list[str] or str | Conditions that cancel the plan |
| `target_logic` | str or None | If from book (e.g. “first resistance”); optional in MVP |
| `rationale` | str | Same as Signal.rationale or expanded |
| `rulebook_ref` | str | Same as Signal.rulebook_ref |

---

## Order (paper execution)

| Field | Type | Description |
|-------|------|-------------|
| `id` | str | Unique order id |
| `symbol` | str | Instrument |
| `side` | str | `"buy"` or `"sell"` |
| `qty` | int or float | Quantity |
| `order_type` | str | e.g. `"market"`, `"limit"` |
| `limit_price` | float or None | If limit order |
| `timestamp` | datetime (UTC) | Creation time |
| `trade_plan_ref` | str or None | Link to TradePlan/signal |

---

## Fill (paper execution)

| Field | Type | Description |
|-------|------|-------------|
| `id` | str | Unique fill id |
| `order_id` | str | Parent order |
| `symbol` | str | Instrument |
| `side` | str | `"buy"` or `"sell"` |
| `qty` | int or float | Filled quantity |
| `price` | float | Fill price |
| `timestamp` | datetime (UTC) | Fill time |
| `slippage_bps` | float or None | Optional; for backtest/paper audit |

---

## Position (paper execution)

| Field | Type | Description |
|-------|------|-------------|
| `symbol` | str | Instrument |
| `side` | str | `"long"` or `"short"` |
| `qty` | int or float | Signed (long positive, short negative) or absolute with side |
| `avg_price` | float | Average entry price |
| `updated_at` | datetime (UTC) | Last update |

---

All timestamps in persistence and between modules use **UTC**. Rationale and rulebook_ref are required for every signal and trade for explainability and audit.
