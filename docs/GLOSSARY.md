# VPA Glossary (Legacy)

Last updated: 2026-02-17

> **SUPERSEDED**: The canonical glossary is now [`docs/vpa-ck/vpa_glossary.md`](vpa-ck/vpa_glossary.md).  
> This file is kept for historical reference. If there is any conflict, the canonical glossary wins.  
> See [`docs/vpa/VPA_DOC_INDEX.md`](vpa/VPA_DOC_INDEX.md) for the full reading order.

Terms from *A Complete Guide to Volume Price Analysis* (Anna Coulling). Use these consistently in code, logs, and documentation.

---

## Price and candle

- **Spread** — The candle body magnitude: `|close - open|`. Used as a proxy for "result" in effort vs result. *(Note: earlier versions of this file defined spread as `high - low`; the canonical glossary defines it as body magnitude.)*
- **Range** — `high - low` of a bar (full extent of the candle).
- **Body** — Same as Spread: absolute difference between Open and Close (real body).
- **Close location** — Where the close sits within the bar: upper/middle/lower portion; used to infer buyer/seller control.
- **Effort** — Volume on a bar (or over a move).
- **Result** — Price movement (e.g. spread or close relative to open). Compare effort vs result to infer efficiency and who is in control.

---

## Volume

- **Relative volume** — Volume compared to a recent baseline (e.g. average over N bars). Volume is always interpreted relatively, not in absolute terms.
- **Climactic volume** — Unusually high volume often associated with exhaustion or reversal (e.g. stopping volume).
- **Stopping volume** — High volume that halts a move (e.g. down move stops on high volume); can signal potential reversal or support.
- **Absorption** — High volume with limited price movement; suggests professional activity (supply or demand being absorbed).

---

## Supply and demand (VPA)

- **No demand** — Up move (e.g. up bar or higher close) on low or declining volume; suggests lack of buying interest, potential weakness.
- **No supply** — Down move on low or declining volume; suggests lack of selling pressure, potential strength.
- **Test for supply** — Price returns to a prior area (e.g. high or breakout level) and holds; tests whether supply remains.
- **Test for demand** — Price returns to a prior area (e.g. low or breakdown level) and holds; tests whether demand remains.

---

## Context

- **Background strength / weakness** — Underlying condition of the market (e.g. uptrend, downtrend, range) inferred from price and volume over recent bars.
- **Context** — The environment in which a bar or setup appears: trend, range, support/resistance. Signals are interpreted in context.
- **Who is in control** — Central question: buyers or sellers? Inferred from effort vs result, absorption, and tests.

---

## System usage

- **Rulebook** — Canonical document(s) that define each VPA setup: preconditions, candle/volume traits, confirmation, invalidation, entry/stop. Code must follow the rulebook. **Canonical source: [`docs/vpa-ck/vpa_actionable_rules.md`](vpa-ck/vpa_actionable_rules.md).**
- **TradePlan** — Intent only (entry condition, stop, invalidation, rationale). Not an order; execution layer converts TradePlans to orders. **Canonical model: `TradeIntent` in [`docs/vpa-ck/vpa_system_spec.md`](vpa-ck/vpa_system_spec.md).**
- **Rationale** — Human-readable explanation of why a signal or trade was generated; must reference the rulebook and be deterministic.
