# VPA_AI_CONTEXT.md
**Project:** Volume Price Analysis (VPA) — Canonical System  
**Purpose:** Provide a *portable, AI-safe contract* so future agents implement and discuss VPA exactly as **Anna Couling (2013)** intends—without drifting into Wyckoff/VSA/other interpretations.

---

## 1) Source of truth (non-negotiable)
- **Authoritative reference:** *A Complete Guide to Volume Price Analysis (2013)* — Anna Couling.
- **If there’s a conflict** between any agent’s suggestion and Couling’s framing/terminology → **Couling wins**.
- **No substitutions** (Wyckoff/VSA/SMC/etc.) unless the user explicitly requests comparison.

---

## 2) Canonical core (what VPA is)
VPA answers: **“Where is price going next?”** by reading:
1) **Price action** (candle anatomy: spread + wicks)
2) **Validated (or contradicted) by volume**
3) **Inside context** (trend location + structure + timeframe)

VPA is a constant search for:
- **Validation** (volume agrees with price action)
- **Anomaly** (effort vs result mismatch)

---

## 3) Vocabulary constraints (term whitelist)
Agents must only use terms defined in **VPA_GLOSSARY.md** when making claims about VPA logic.

### Allowed terms (examples; see glossary for full list)
- VPA, VAP
- validation, anomaly
- effort vs result
- spread, wick, hammer, shooting star
- accumulation, distribution
- tests (test of supply, test of demand)
- stopping volume, topping out volume
- buying climax, selling climax
- congestion/range
- dominant trend / benchmark chart / ripples

### Disallowed (unless user explicitly requests)
- “Wyckoff phases A–E”, “springs/upthrusts” (unless mapped explicitly and requested)
- “VSA” reinterpretations and label sets
- “SMC”, “order blocks”, “liquidity grabs” terminology
- any invented Couling “rules” that aren’t grounded in her concepts

---

## 4) Canonical reasoning order (AI must follow)
When interpreting markets or building logic, follow this strict sequence:

1) **Candle first**  
   - Determine candle anatomy: spread + wicks + close location.
2) **Then volume**  
   - Decide: is volume **validating** the candle or creating an **anomaly**?
3) **Then context gates**  
   - Where are we in the trend (top/bottom/middle)?  
   - What structure is nearby (support/resistance, congestion boundaries, optional VAP zones)?
4) **Then confirmation / response**  
   - Many VPA signals require waiting for the *next candle(s) response*.
5) **Only then** propose action (setup → confirmation → entry → stop placement).

If an agent skips context (trend location + structure) and jumps to entries → **reject**.

---

## 5) Determinism policy (for engineering)
Couling uses *relative* terms (low/high/ultra-high volume, narrow/wide spread).  
To make rules executable, we quantize them:

- Volume states via `VolRel = volume / SMA(volume, N)`
- Spread states via `SpreadRel = spread / SMA(spread, M)`

**Important:** thresholds are configurable, but once configured, decisions must be deterministic.

---

## 6) AI Do / Don’t rules (hard guardrails)

### DO
- Use Couling’s conceptual primitives: **validation vs anomaly**, **effort vs result**, **tests**, **climaxes**, **multi-timeframe ripples**.
- Explicitly declare **scope** (timeframe, market, session assumptions).
- Separate:  
  **(a) detection** (signal) from **(b) action** (trade intent) from **(c) risk** (size/stop).
- When unsure: say **“Unknown under Couling without book verification”** and request the exact excerpt/page.

### DON’T
- Don’t invent “new Couling rules” or rename terms.
- Don’t recommend indicator stacks as decision drivers.
- Don’t treat candle patterns as standalone truths (must be volume + context).
- Don’t equate VPA to VAP. (VAP is supportive structure; VPA is price+volume analysis.)
- Don’t generalize: “this always means reversal” without context gates and confirmation logic.

---

## 7) AI compliance checklist (must appear in complex outputs)
For any agent output that proposes logic or trades, the agent must include:

- [ ] Terms used are in **VPA_GLOSSARY.md**
- [ ] Candle → Volume → Context → Confirmation order followed
- [ ] Validation vs anomaly explicitly stated
- [ ] Trend-location gate enforced for anomalies
- [ ] Setup scope stated (tf, instrument assumptions)
- [ ] Backtest lookahead avoided (bar-close evaluation, next-bar entry by default)
- [ ] “What not to trade” conditions enumerated

---

## 8) Context refresh pack (what an agent should read first)
Agents should load, in order:
1) `VPA_AI_CONTEXT.md` (this file)
2) `VPA_GLOSSARY.md`
3) `VPA_CANONICAL_MODEL.md`
4) `VPA_ACTIONABLE_RULES.md`
5) `VPA_SYSTEM_SPEC.md` + `VPA_SIGNAL_FLOW.md`

---

## 9) Change control (long-term correctness)
- Every change to rules/spec must include:
  - reason for change
  - impacted rule IDs
  - updated tests/fixtures
  - version bump of documentation set
- Avoid “drift”: glossary and vocabulary whitelist are the stabilizers.

---
