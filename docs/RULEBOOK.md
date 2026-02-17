# VPA Rulebook (Legacy)

Last updated: 2026-02-17

> **SUPERSEDED**: The canonical actionable rules are now in [`docs/vpa-ck/vpa_actionable_rules.md`](vpa-ck/vpa_actionable_rules.md).  
> Rule IDs and setup IDs are governed by [`docs/vpa/VPA_RULE_REGISTRY.yaml`](vpa/VPA_RULE_REGISTRY.yaml).  
> This file is kept for historical reference. If there is any conflict, the canonical docs win.  
> See [`docs/vpa/VPA_DOC_INDEX.md`](vpa/VPA_DOC_INDEX.md) for the full reading order.

Canonical list of VPA setups from *A Complete Guide to Volume Price Analysis* (Anna Coulling). Each setup must be documented here **before** implementation in code. No invented rules; fidelity to the book.

---

## Rulebook structure (per setup)

For every setup we document:

- **Preconditions** — Context (e.g. uptrend, range, after weakness).
- **Candle characteristics** — Spread, body, close location.
- **Volume characteristics** — Relative volume, climactic, etc.
- **Confirmation rules** — What confirms the setup.
- **Invalidation rules** — What cancels the setup or trade.
- **Entry / stop / target** — Logic for TradePlan.

---

## No Demand (bearish / weakness)

*Reference: book’s treatment of “no demand” — up move on low or declining volume.*

### Id

`no_demand`

### Preconditions

- **Context**: Uptrend or bounce; price has moved up over recent bars.
- **Background**: We are assessing whether demand is present or absent.

### Candle characteristics

- **Current bar**: Price closes up (close > open) or at least the bar is an up bar (close > prior close).
- **Spread**: Not restricted for basic no demand; narrow spread with up close can emphasize lack of effort.
- **Close location**: Close in upper portion of bar is common; the key is that the **volume** is low relative to the move.

### Volume characteristics

- **Relative volume**: **Low** (below recent baseline) or **declining** vs prior bar(s).
- Interpretation: Buyers are not participating; effort (volume) does not support the result (up move). “No demand” for the stock at these prices.

### Confirmation rules

- At least one up bar (close > open or close > prior close) with clearly low or declining volume.
- Optional (if book specifies): Consecutive up bars on declining volume strengthen the signal.

### Invalidation rules

- Next bar shows high volume and strong up move (demand appears) — no-demand interpretation is invalidated for that level.
- Price breaks meaningfully below the no-demand bar low (weakness confirmed; trade idea may be “short” or “avoid long” rather than “long”).

### Entry / stop / target (TradePlan)

- **Direction**: Short or avoid long; no demand is a bearish/weakness setup.
- **Entry**: As per book — e.g. next bar open, or close below no-demand bar low. *(To be refined from book.)*
- **Stop**: Above the no-demand bar high (or above a defined structure high). *(To be refined from book.)*
- **Invalidation**: As above; also if strong demand appears (high volume up bar) before entry.
- **Target**: Book-defined; optional in MVP (e.g. next support or measured move).

### Rationale template

“No demand: up bar(s) on low/declining volume in [context]. Effort does not support result; buyers not in control. Rulebook: no_demand.”

---

## Other setups (to be added from the book)

Document in the same structure before implementing:

- **No Supply** — Down move on low/declining volume (bullish/strength).
- **Stopping Volume** — High volume that halts a move (potential reversal).
- **Test for Supply** — Price returns to prior high/supply and holds.
- **Test for Demand** — Price returns to prior low/demand and holds.

Add others only as the book is followed; do not invent or optimize.
