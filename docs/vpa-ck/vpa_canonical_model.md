# VPA_CANONICAL_MODEL.md
**Project:** Volume Price Analysis (VPA) — Canonical System  
**Phase:** 1 — Canonical Knowledge Model (Understand before building)  
**Source of truth:** *A Complete Guide to Volume Price Analysis (2013)* by Anna Couling  
**Scope:** Concepts, definitions, relationships, participant roles, and cause→effect logic (NO trading rules yet).

---

## 0) Canonical stance (what VPA is)
### Concept: Volume Price Analysis (VPA)
- **Definition:** VPA is Anna Couling’s term for an analytical method that answers the trader’s core question: *“where is the price going next?”* by interpreting **price action validated (or contradicted) by volume**.:contentReference[oaicite:0]{index=0}
- **Conditions:** Works across markets and timeframes; interpretation is contextual.
- **Implications:** The model is not indicator-first; it is **price+volume-first**, with everything else used as supporting structure.

---

## 1) Observables (the raw inputs)

### 1.1 Concept: Candle anatomy (price action primitives)
- **Definition:** A candle is decomposed into **open, high, low, close, upper wick, lower wick, and spread** (body/open↔close).:contentReference[oaicite:1]{index=1}
- **Conditions:** Interpreted within the timeframe of the candle; same candle shape can mean different things depending on trend location.
- **Implications:** Candle interpretation is **not** pattern-memorization; it’s reading **sentiment + change** (wicks) and **conviction** (spread), then validating with volume.

#### Candle sub-primitives (canonical meanings)
- **Spread (body width)**
  - **Definition:** Wide spread = strong sentiment; narrow spread = weak sentiment.:contentReference[oaicite:2]{index=2}
  - **Implications:** Spread is the “result” component in effort vs result.

- **Wicks**
  - **Definition:** Wicks represent **change of sentiment during the session**; absence of wick signals strong sentiment in direction of close.:contentReference[oaicite:3]{index=3}:contentReference[oaicite:4]{index=4}
  - **Implications:** Wicks are a primary early-warning mechanism, but require volume to gauge significance.

### 1.2 Concept: Volume (effort primitive)
- **Definition:** Volume is the “effort” behind the price action and is the key to detecting professional/insider participation; *what cannot be hidden is volume.*:contentReference[oaicite:5]{index=5}
- **Conditions:** Always evaluated **relative** (above/below/ultra-high vs average) and **in context** (trend, congestion, phase).
- **Implications:** Volume is the validator and lie detector of price action.

### 1.3 Concept: Time (context primitive)
- **Definition:** The same VPA logic applies across timeframes; trend meaning is always relative to timeframe.:contentReference[oaicite:6]{index=6}
- **Conditions:** Major turns take time; “cause” is time+effort; “effect” is magnitude of move.:contentReference[oaicite:7]{index=7}:contentReference[oaicite:8]{index=8}
- **Implications:** The model must explicitly represent time as a first-class dimension, not an afterthought.

---

## 2) Core VPA axioms (the engine-room logic)

### 2.1 Concept: “Volume validates price”
- **Definition:** The canonical rule: start with the candle, then check whether volume **validates** or reveals an **anomaly** in the price action.:contentReference[oaicite:9]{index=9}
- **Conditions:** Applied at two levels:
  1) single candle validation/anomaly  
  2) multi-candle / trend validation/anomaly:contentReference[oaicite:10]{index=10}
- **Implications:** The system must model validation/anomaly as a binary *interpretation outcome* that drives next-step reasoning.

### 2.2 Concept: Validation vs Anomaly (the only two things we look for)
- **Definition:** VPA is a constant search for **validation or anomaly**: validation suggests continuation; anomaly suggests potential change.:contentReference[oaicite:11]{index=11}
- **Conditions:** Requires context: where we are in the trend/consolidation is the first reference point when an anomaly appears.:contentReference[oaicite:12]{index=12}
- **Implications:** Any AI/system must:
  - detect anomalies,
  - then immediately anchor them to **trend location + nearby structure** (support/resistance/congestion).

### 2.3 Concept: Effort vs Result (Wyckoff law used inside VPA)
- **Definition:** “Effort” = volume; “Result” = price outcome (often proxied by spread and progress). When effort and result mismatch, an **anomaly** is present.:contentReference[oaicite:13]{index=13}:contentReference[oaicite:14]{index=14}
- **Conditions:**
  - Applies to single candles and also to trends (groups of candles).:contentReference[oaicite:15]{index=15}
  - Markets require effort to rise *and* to fall; rising volume can validate down moves too.:contentReference[oaicite:16]{index=16}
- **Implications:** The canonical model must include:
  - a computed notion of “result” (spread/progress),
  - a relative notion of “effort” (volume vs average),
  - a mismatch detector (anomaly generator).

### 2.4 Concept: Cause and Effect (time as part of “cause”)
- **Definition:** The **longer** the market takes to prepare/turn (cause), the **greater** the eventual move (effect).:contentReference[oaicite:17]{index=17}
- **Conditions:** Varies by market structure and timeframe, but the principle holds.:contentReference[oaicite:18]{index=18}
- **Implications:** Consolidation/accumulation/distribution duration is not “dead time” — it is stored cause.

---

## 3) Market participants (roles + incentives)

### 3.1 Concept: Insiders (canonical role)
- **Definition:** “Insiders” is Couling’s umbrella term for specialists, market makers, large operators, professional money — modeled as merchants with warehouses: buy wholesale, sell retail.:contentReference[oaicite:19]{index=19}
- **Conditions:** Insiders run campaigns and manage inventory.
- **Implications:** VPA is written from the insiders’ perspective; we aim to follow their footprints via volume.

### 3.2 Concept: Public (canonical counterparty)
- **Definition:** The public (traders/investors/speculators) is induced to **sell in accumulation** and **buy in distribution** (from the insiders’ perspective).:contentReference[oaicite:20]{index=20}
- **Conditions:** Behavior is driven by fear/greed; insiders exploit this with “news” narratives.:contentReference[oaicite:21]{index=21}
- **Implications:** The model must treat sentiment-driven participation as predictable flow that insiders harvest.

---

## 4) Market cycle (campaign lifecycle model)

### 4.1 Concept: Accumulation phase
- **Definition:** Accumulation is the period where insiders **buy** to fill inventory (“warehouse”) before launching a markup campaign; it takes time.:contentReference[oaicite:22]{index=22}
- **Conditions:** Public is predominantly selling while insiders buy.:contentReference[oaicite:23]{index=23}
- **Implications:** Expect price to oscillate/congest while inventory is built; breakout readiness is assessed via “tests”.

### 4.2 Concept: Distribution phase
- **Definition:** Distribution is where insiders **sell** inventory at retail prices into public demand, often near target/overbought areas; public buys while insiders sell.:contentReference[oaicite:24]{index=24}:contentReference[oaicite:25]{index=25}
- **Conditions:** Momentum is cultivated; “good news” increases participation and demand.:contentReference[oaicite:26]{index=26}
- **Implications:** Expect narrow trading ranges near highs as inventory is offloaded; climax patterns can appear near end.

### 4.3 Concept: Buying climax (end of accumulation; start of bullish trend)
- **Definition:** Buying climax appears at the **bottom of a bearish trend** and reflects insiders **buying** during accumulation (Couling’s insider-perspective definition).:contentReference[oaicite:27]{index=27}
- **Conditions:** Often follows stopping volume and final “mopping up” of selling pressure.
- **Implications:** Signals the transition into markup / trend higher.

### 4.4 Concept: Selling climax (end of distribution; start of bearish move)
- **Definition:** Selling climax appears at the **top of a bullish trend** and reflects insiders **selling** during distribution (insider-perspective definition).:contentReference[oaicite:28]{index=28}
- **Conditions:** Characterized by repeated push-ups with closes back near open and high volume, trapping late buyers.:contentReference[oaicite:29]{index=29}
- **Implications:** A strong warning that the next leg is likely opposite (move down).

---

## 5) Cause→Effect tools insiders use (canonical mechanisms)

### 5.1 Concept: Tests (insider probing of supply/demand)
- **Definition:** Testing is a core insider tool used across markets/timeframes to confirm whether supply (selling pressure) or demand (buying pressure) has been removed/absorbed.:contentReference[oaicite:30]{index=30}
- **Conditions:**  
  - **Test for supply (post-accumulation):** successful when volume is low; failure when volume is high (sellers still present).:contentReference[oaicite:31]{index=31}  
  - **Test for demand (post-distribution):** successful when there is low demand (low volume) on a mark-up probe that closes back near open.:contentReference[oaicite:32]{index=32}
- **Implications:** Tests create explicit “go/no-go” confirmation moments for breakouts or markdown continuations.

### 5.2 Concept: Stopping volume (bear trend braking)
- **Definition:** Stopping volume is insiders/professional buying that **stops the market falling further** and precedes a potential reversal; it is a strength signal.:contentReference[oaicite:33]{index=33}
- **Conditions:** Appears after sharp declines; often seen as deep lower wicks as price recovers off lows with strong volume.:contentReference[oaicite:34]{index=34}
- **Implications:** Transition alert: bearish waterfall may be ending; accumulation process may be beginning.

### 5.3 Concept: Topping out volume (bull trend exhaustion)
- **Definition:** Topping out volume marks a market topping after a bullish run, as insiders sell into demand; often seen with deep upper wicks and high volume as upward progress becomes difficult.:contentReference[oaicite:35]{index=35}
- **Conditions:** Frequently appears before/into distribution and into the selling climax.
- **Implications:** Strength is failing; risk shifts from continuation to reversal.

---

## 6) Canonical interpretation patterns (NOT rules; just modelled constructs)
Each construct is stored as a reusable reasoning block.

### 6.1 Construct: Candle + Volume validation
- **Definition:** If spread/result and volume/effort “match”, the move is considered genuine (validated).:contentReference[oaicite:36]{index=36}:contentReference[oaicite:37]{index=37}
- **Conditions:** Example of validation logic:
  - wide spread + above-average volume = price validated
  - narrow spread + low volume = price validated (small result, small effort):contentReference[oaicite:38]{index=38}
- **Implications:** Continuation bias holds until an anomaly appears.

### 6.2 Construct: “Big result from little effort” anomaly (trap risk)
- **Definition:** Wide spread up candle with low volume is an anomaly (big result, little effort), often interpreted as a trap or probe rather than genuine buying.:contentReference[oaicite:39]{index=39}
- **Conditions:** Common around openings and during “feeling out” behavior; context dependent.
- **Implications:** Early warning: do not assume bullishness purely from price action.

### 6.3 Construct: “Little result from big effort” anomaly (absorption/weakness)
- **Definition:** Modest spread with high volume indicates effort not producing progress; suggests weakness/absorption at that level.:contentReference[oaicite:40]{index=40}
- **Conditions:** Often develops near tops/bottoms and at key levels.
- **Implications:** Signals a struggle; sets up potential reversal or congestion.

### 6.4 Construct: Wick-first reading (with volume for significance)
- **Definition:** Wick length is first focus; it reveals impending strength/weakness/indecision; volume determines significance.:contentReference[oaicite:41]{index=41}
- **Conditions:** Same wick candle can be minor pause or major reversal depending on volume + location in trend.:contentReference[oaicite:42]{index=42}
- **Implications:** The model must store candle shape + volume + location together (never in isolation).

---

## 7) Support/resistance as “volume memory” (Volume At Price, VAP)

### 7.1 Concept: Volume At Price (VAP)
- **Definition:** VAP is distinct from VPA: it visualizes the **density of traded volume at specific price levels**, highlighting where price is likely to find support/resistance (invisible barriers).:contentReference[oaicite:43]{index=43}:contentReference[oaicite:44]{index=44}
- **Conditions:** Significance increases with:
  - greater volume concentration,
  - longer time spent in congestion (more volume stored in range).:contentReference[oaicite:45]{index=45}
- **Implications:** Breakouts from dense regions imply a new trend; revisits test the strength of the “platform”.

---

## 8) Multi-timeframe logic (time as structure, not decoration)

### 8.1 Concept: Dominant trend / benchmark chart
- **Definition:** Using three timeframes gives a 3D view: a slower benchmark chart provides dominant trend bias; faster charts show early “ripples” of change first.:contentReference[oaicite:46]{index=46}
- **Conditions:** Trading with dominant trend lowers risk; counter-trend trading increases risk and usually reduces holding time.:contentReference[oaicite:47]{index=47}
- **Implications:** The canonical model must support:
  - signal emergence on fast TF,
  - confirmation on primary TF,
  - adoption into dominant TF.

---

## 9) Canonical relationship map (price ↔ volume ↔ time)

### 9.1 Entity graph (conceptual)
```mermaid
graph TD
  V[Volume (Effort)] --> VA[Validation/Anomaly]
  P[Price Action (Candle: spread+wicks)] --> VA
  T[Time/Timeframe] --> CEF[Cause→Effect]
  V --> CEF
  T --> Trend[Trend Context]
  Trend --> VA
  VA --> Phase[Campaign Phase: Accumulation/Distribution/etc]
  Phase --> Tests[Tests of Supply/Demand]
  Tests --> Next[Likely Next Move]
  VAP[VAP: Volume at Price] --> SR[Support/Resistance Barriers]
  SR --> Trend
  SR --> Phase
