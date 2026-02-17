# vpa-engine — Tuning and extensibility guide

Last updated: 2026-02-17

> **Canonical config reference**: [`docs/vpa/VPA_CONFIG.md`](vpa/VPA_CONFIG.md), default values in
> [`docs/config/vpa.default.json`](config/vpa.default.json), schema in [`docs/config/vpa_config.schema.json`](config/vpa_config.schema.json).
> All VPA thresholds (volume, spread, trend windows, gates, execution timing) are defined there.
> This file provides guidance on safe tuning practices. If there is a conflict, the canonical config docs win.

What you can tune safely, what you should not change lightly, and how to extend the system without breaking fidelity to Anna Coulling's VPA. **Stocks-only MVP; paper first.**

---

## 1. Parameters designed to be tuned

These are implementation or environment choices that do not change the *meaning* of VPA rules from the book.

All VPA-specific parameters (volume/spread thresholds, trend windows, gate policies, execution timing) are defined in
[`docs/vpa/VPA_CONFIG.md`](vpa/VPA_CONFIG.md) and must be loaded from config at runtime -- not hardcoded in rule logic.

| Parameter | Config key | Purpose | Safe range |
|-----------|------------|---------|------------|
| **Volume lookback** | `vol.avg_window_N` | Number of bars for average-volume baseline. | 10-50; match book if specified. |
| **Volume thresholds** | `vol.thresholds.low_lt`, `high_gt`, `ultra_high_gt` | Relative volume state boundaries. | Keep near 0.8 / 1.2 / 1.8 unless book specifies otherwise. |
| **Spread lookback** | `spread.avg_window_M` | Number of bars for average-spread baseline. | 10-50. |
| **Spread thresholds** | `spread.thresholds.narrow_lt`, `wide_gt` | Relative spread state boundaries. | Keep near 0.8 / 1.2. |
| **Trend window** | `trend.window_K` | Bars used for trend-level validation/anomaly. | 3-10. |
| **Setup window** | `setup.window_X` | Max bars for setup confirmation sequence. | 3-10. |
| **Slippage** | `slippage.value` | Simulated execution cost (BPS or ticks). | 0-20 bps typical for liquid stocks. |
| **Costs** | `costs.fee_value` | Fee per trade (BPS or per-trade). | Set to your broker's fee. |
| **Risk per trade** | `risk.risk_pct_per_trade` | Position sizing. | 0.25%-1.0%. |
| **Session / market hours** | Not in MVP | Filter bars to regular session. | Future. |

---

## 2. What should NOT be tuned lightly

These encode the book's logic. Changing them can break fidelity and explainability.

- **Rule definitions** -- Preconditions, candle/volume conditions, confirmation, invalidation, and entry/stop logic for each rule/setup must match the canonical rules in [`docs/vpa-ck/vpa_actionable_rules.md`](vpa-ck/vpa_actionable_rules.md). Do not relax or tighten rules to improve backtest stats.
- **Setup detection logic** -- Only change when the book or an updated registry entry justifies it.
- **Rationale and evidence** -- Every signal must include evidence payload. Do not remove or make optional.
- **Context gate enforcement** -- Gates (CTX-1/2/3) must not be disabled to increase signal count.

If you need to refine a rule, update the registry (`VPA_RULE_REGISTRY.yaml`) and traceability first, then the code.

---

## 3. How to tune safely

- **Walk-forward**: Reserve out-of-sample periods; run backtest on one window, then "forward" on the next. Avoid reusing the same period for tuning and evaluation.
- **Avoid overfitting**: Prefer few, simple parameters (e.g. one lookback, one threshold band). Do not optimize many knobs to maximize a single metric.
- **Compare results**: Use the same bar data and same config hash when comparing before/after. Document parameter changes and outcome (e.g. in DECISIONS.md).
- **Paper before live**: After any tuning, run paper trading for a while and confirm behavior and logs match expectations before considering live (see [PAPER_TO_LIVE](PAPER_TO_LIVE.md)).

---

## 4. Future extensions (ideas only)

Labelled as **future work**; not part of MVP.

- **Multi-symbol scanning** -- Run vpa-core on multiple symbols; same rules, one symbol at a time or parallel workers. Execution stays single-writer per account/symbol as designed.
- **Multi-timeframe confirmation** (CTX-2, CTX-3, ripple logic) -- Use higher-timeframe context to filter or confirm signals on a lower timeframe. Defined in canonical spec.
- **Additional VPA setups** -- Each must be registered in `VPA_RULE_REGISTRY.yaml` with fixtures before implementation.
- **Dashboards / visualization** -- Charts of bars, signals, and equity; no change to core logic.
- **Alerts** -- Notifications when a signal or trade occurs; read from journal or events.
- **Live trading readiness** -- Checklist and safeguards in [PAPER_TO_LIVE](PAPER_TO_LIVE.md); no live execution in MVP.

These are directions only; implement when needed and keep docs and registry updated.
