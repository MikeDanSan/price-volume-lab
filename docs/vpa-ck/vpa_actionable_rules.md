# VPA_ACTIONABLE_RULES.md
**Project:** Volume Price Analysis (VPA) — Canonical System  
**Phase:** 2 — Actionable Rules Extraction (Executable / detectable)  
**Source of truth:** *A Complete Guide to Volume Price Analysis (2013)* — Anna Couling  
**Constraint:** Rules must be deterministic, context-aware, explicitly scoped (Couling terminology & logic).

---

## 0) Rule format (standard)
Each rule is specified as:

- **Rule ID / Name**
- **Scope:** instrument-agnostic; timeframe; session (if relevant)
- **Context prerequisites:** where we are in the trend + structure
- **Detection (deterministic):** explicit conditions on candle + volume + sequence
- **Output:** signal classification (Strength / Weakness / Confirmation / Avoid)
- **Notes:** why it matters in Couling’s logic (with citations)

> Canonical reminder: VPA is a constant search for **validation or anomaly**; validation implies continuation bias, anomaly implies potential change. :contentReference[oaicite:0]{index=0}

---

## 1) Deterministic measurement layer (implementation mapping)
Couling uses **relative** volume terms (below/above/high/ultra-high). To make execution deterministic, we map these to parameters.

### 1.1 Volume state (parameterized but deterministic)
- `VolAvg = SMA(volume, N)` (default N=20; configurable)
- `VolRel = volume / VolAvg`
- **VolumeState thresholds (defaults; tuneable):**
  - `LOW`        : VolRel < 0.8
  - `AVERAGE`    : 0.8 ≤ VolRel ≤ 1.2
  - `HIGH`       : 1.2 < VolRel ≤ 1.8
  - `ULTRA_HIGH` : VolRel > 1.8

### 1.2 Candle anatomy (deterministic fields)
- `Spread = abs(close - open)`
- `Range  = high - low`
- `UpperWick = high - max(open, close)`
- `LowerWick = min(open, close) - low`
- `BodyPos = (close - open)` (sign = bull/bear)

### 1.3 Spread classification (relative, deterministic)
- `SpreadAvg = SMA(Spread, M)` (default M=20)
- `SpreadRel = Spread / SpreadAvg`
- Defaults:
  - `NARROW` : SpreadRel < 0.8
  - `WIDE`   : SpreadRel > 1.2

> Why we still do this: Couling’s logic is “effort vs result” (volume vs price outcome). We’re just quantizing her qualitative labels for execution. :contentReference[oaicite:1]{index=1}

---

## 2) Mandatory context gates (do these *before* any entry logic)

### CTX-1 — Trend-location-first gate
- **Scope:** all timeframes
- **Context prerequisite:** when any anomaly is detected, **first determine where we are in the trend** (top/bottom/mid), using structure tools (support/resistance, patterns, trend lines).  
- **Detection:** if `Anomaly == true`, then require `TrendContext != UNKNOWN` before taking any action.
- **Output:** `GATE_REQUIRED`
- **Notes:** Couling: “first point of reference is always where we are in the trend… we get our bearings first… bring in support/resistance and other tools.” :contentReference[oaicite:2]{index=2}

### CTX-2 — Dominant-trend risk gate (multi-timeframe)
- **Scope:** trading timeframe + slower “benchmark” timeframe
- **Detection:**
  - compute `DominantTrend` on slower timeframe
  - compute `TradeDirection` on trading timeframe
- **Output:**
  - if `TradeDirection == DominantTrend` → `RISK_LOWER`
  - else → `RISK_HIGHER` + `HOLD_TIME_SHORTER_EXPECTED`
- **Notes:** Couling: trading with dominant trend reduces risk; counter-trend increases risk and reduces expected hold time. :contentReference[oaicite:3]{index=3}

### CTX-3 — “Ripple” confirmation flow
- **Scope:** fast / primary / dominant (3 timeframes)
- **Detection:** treat fast timeframe signals as **early**, require subsequent confirmation on primary, then dominant for “fully established”.
- **Output:** `EARLY_SIGNAL` vs `CONFIRMED_SIGNAL`
- **Notes:** Couling: potential change appears on fast chart first, then ripples to primary and dominant. :contentReference[oaicite:4]{index=4}

---

## 3) Core rule atoms (single-bar and multi-bar, executable)

### VAL-1 — Single-bar validation (bullish drive)
- **Scope:** any timeframe
- **Context:** none (but significance increases near structure)
- **Detection:**
  - Candle: `WIDE` up bar (close > open) with small wicks (optional strictness)
  - Volume: `HIGH or ULTRA_HIGH`
- **Output:** `VALIDATION_BULL`
- **Implication:** move is genuine; maintain long bias **until anomaly appears**.
- **Notes:** wide spread + well above average volume validates price; continue until anomaly. :contentReference[oaicite:5]{index=5}

### VAL-2 — Single-bar validation (small progress)
- **Scope:** any timeframe
- **Detection:**
  - Candle: `NARROW` up bar
  - Volume: `LOW`
- **Output:** `VALIDATION_NEUTRAL_TO_BULL`
- **Notes:** small result should require small effort; volume still validates. :contentReference[oaicite:6]{index=6}

### ANOM-1 — “Big result, little effort” trap-up anomaly
- **Scope:** any timeframe (often early session on equities)
- **Detection:**
  - Candle: `WIDE` up bar
  - Volume: `LOW`
- **Output:** `ANOMALY_TRAP_UP_WARNING`
- **Notes:** Couling: anomaly; “alarm bells”; could be a trap / “feel out” move. :contentReference[oaicite:7]{index=7}

### ANOM-2 — “Big effort, little result” (absorption/weakness)
- **Scope:** any timeframe
- **Detection:**
  - Volume: `HIGH or ULTRA_HIGH`
  - Candle spread: NOT wide (e.g., `NARROW` or only marginally wider than prior)
- **Output:** `ANOMALY_WEAKNESS_OR_ABSORPTION`
- **Notes:** Couling: high effort not producing expected result → insiders selling out at this level (weakness). :contentReference[oaicite:8]{index=8}

---

## 4) Trend-level rule atoms (multi-bar validation/anomaly)

### TREND-VAL-1 — Uptrend validation (rising prices + rising volume)
- **Scope:** any timeframe (evaluate over last K bars; default K=3..10)
- **Detection:**
  - Price trend up over K bars
  - Volume trend rising over K bars
- **Output:** `TREND_VALID_UP`
- **Notes:** Couling: validation operates at candle level and trend level; rising prices with rising volume validates. :contentReference[oaicite:9]{index=9}

### TREND-ANOM-1 — Uptrend weakness (rising prices + falling volume)
- **Scope:** any timeframe
- **Detection:**
  - Price trend up over K bars
  - Volume trend falling over K bars
- **Output:** `TREND_ANOM_WEAK_UPTREND`
- **Notes:** Couling: rising markets should be associated with rising volume, **not falling**; alarm bells. :contentReference[oaicite:10]{index=10}

### TREND-ANOM-2 — Sequential anomaly cluster (escalating warning)
- **Scope:** any timeframe
- **Detection:** within last K bars (default 4), count anomalies:
  - (a) high volume + modest spread, OR
  - (b) wide spread + volume lower than prior high-effort bar, OR
  - (c) trend rising while volume declines
  - Trigger when `AnomalyCount >= 2`
- **Output:** `WEAKNESS_CLUSTER_HIGH_PRIORITY`
- **Notes:** Couling’s multi-bar example: repeated anomalies add confirmation; “alarm bells ringing loud and clear.” :contentReference[oaicite:11]{index=11}

---

## 5) Strength vs Weakness “premier candle” atoms (Couling)

### STR-1 — Hammer = strength (candidate reversal or temporary strength)
- **Scope:** any timeframe
- **Context prerequisite:** typically after decline; confirm via CTX-1
- **Detection (hammer):**
  - Session falls then recovers to close back near open
  - (Implementation proxy) `LowerWick` large vs Spread, and `abs(close-open)` small
- **Output:** `STRENGTH_HAMMER`
- **Notes:** Couling: hammer signals selling absorbed; strength, powerful with VPA. :contentReference[oaicite:12]{index=12}

### WEAK-1 — Shooting star = weakness (and demand-test behavior)
- **Scope:** any timeframe
- **Context prerequisite:** confirm trend/phase (CTX-1)
- **Detection (shooting star):**
  - Marked higher then falls back to close at/near open (deep upper wick; narrow body)
- **Output:** `WEAKNESS_SHOOTING_STAR`
- **Notes:** Couling: in downtrends it confirms weakness; after selling climax it can be a **test of demand** as market moves lower. :contentReference[oaicite:13]{index=13}

### WEAK-2 — Shooting star + LOW volume = “no demand” confirmation
- **Scope:** any timeframe
- **Context:** following distribution / selling climax or post-congestion
- **Detection:**
  - WEAK-1 candle
  - VolumeState = `LOW`
- **Output:** `TEST_DEMAND_CONFIRMED_LOW`
- **Notes:** Couling: shooting star shows market pushed higher but “no demand”, confirmed by low volume. :contentReference[oaicite:14]{index=14}

---

## 6) Campaign-phase executable rules (Accumulation/Distribution mechanisms)

### TEST-SUP-1 — Test of supply (post-accumulation breakout readiness)
- **Scope:** any timeframe
- **Context prerequisite:** accumulation/congestion area identified; confirm with CTX-1
- **Detection:**
  - A “re-test” bar into/near congestion
  - VolumeState = `LOW`
  - (Optional strictness) bar closes stable / not collapsing through range
- **Output:** `SUPPLY_REMOVED_TEST_PASS`
- **Implication:** market about to break out and move higher (breakout readiness).
- **Notes:** Couling: repeated tests; low-volume test confirms selling pressure removed; “one of the most powerful signals.” :contentReference[oaicite:15]{index=15}

### TEST-SUP-2 — Failed test of supply (expect return to congestion)
- **Scope:** any timeframe
- **Detection:**
  - TEST-SUP setup bar occurs
  - VolumeState = `HIGH/ULTRA_HIGH` (supply still present)
- **Output:** `SUPPLY_TEST_FAIL_RETURN_TO_RANGE`
- **Notes:** Couling: on failed test expect insiders take market back into congestion to flush selling pressure, then test again. :contentReference[oaicite:16]{index=16}

### TEST-DEM-1 — Test of demand (post-distribution markdown readiness)
- **Scope:** any timeframe
- **Context prerequisite:** distribution phase / recent high-demand area; confirm CTX-1
- **Detection:**
  - Market is marked higher (often with “news” catalyst)
  - Candle closes back near open
  - VolumeState = `LOW` (“no demand”)
- **Output:** `DEMAND_REMOVED_TEST_PASS`
- **Implication:** safe to start moving market lower, fast.
- **Notes:** Couling: test demand; “closes back near the open, with very low volume… safe to start moving the market lower, and fast.” :contentReference[oaicite:17]{index=17}

---

## 7) Climactic action rules (end-of-phase / “fireworks”)

### CLIMAX-SELL-1 — Selling climax (end of distribution; fast move likely)
- **Scope:** any timeframe
- **Context prerequisite:** distribution phase / mature up move; confirm CTX-1
- **Detection:**
  - Repeated surges higher that **close back at/near open**
  - Deep upper wick + narrow body
  - VolumeState = `HIGH or ULTRA_HIGH`
  - Repetition count ≥ 2 within window W (default W=10 bars)
- **Output:** `SELLING_CLIMAX_TOPPING`
- **Implication:** “next leg is opposite direction”; prepare for fast markdown.
- **Notes:** Couling: repeated action; deep upper wick + high/ultra-high volume is one of the most powerful combinations; signals ready to move fast. :contentReference[oaicite:18]{index=18}

### CLIMAX-SELL-2 — Upper-wick repetition emphasis (body color irrelevant)
- **Scope:** any timeframe
- **Detection refinement:**
  - Ignore candle body color
  - Require: wick height + repeated nature + high volume
- **Output:** `SELLING_PRESSURE_DOMINANT`
- **Notes:** Couling: body color unimportant; wick height + repetition + high volume is what matters. :contentReference[oaicite:19]{index=19}

---

## 8) “What not to trade” (explicit avoidance rules)

### AVOID-NEWS-1 — Long-legged doji on LOW volume = manipulation / stop hunting
- **Scope:** any timeframe; especially around scheduled news
- **Detection:**
  - Long-legged doji behavior: wide two-sided range, closes near open
  - VolumeState = `LOW`  (anomaly: big result, no effort)
- **Output:** `AVOID_TRADE_WAIT`
- **Notes:** Couling: low volume here is anomaly; insiders “racking” price/stop hunting; “we stay out, and wait for further candles.” :contentReference[oaicite:20]{index=20}

### AVOID-TRAP-1 — Trap-up anomaly (ANOM-1) without confirmation
- **Scope:** any timeframe
- **Detection:** ANOM-1 triggered AND no subsequent validation bar appears within next X bars (default X=3)
- **Output:** `AVOID_LONGS_UNTIL_CONFIRMED`
- **Notes:** Couling: wide spread up on low volume = alarm bells; without volume support it’s not genuine. :contentReference[oaicite:21]{index=21}

### AVOID-COUNTER-1 — Counter-dominant trend entries (unless explicitly “countertrend mode”)
- **Scope:** multi-timeframe trading
- **Detection:** CTX-2 says `RISK_HIGHER`
- **Output:** `AVOID_OR_REDUCE_SIZE_SHORT_HOLD`
- **Notes:** Couling: counter-trend = higher risk; unlikely long hold. :contentReference[oaicite:22]{index=22}

---

## 9) Confirmation logic (how signals become executable)

### CONF-1 — “Wait for response” after suspected stopping volume / hammer
- **Scope:** any timeframe
- **Context:** after sharp decline / waterfall
- **Detection:**
  - Candidate strength appears (e.g., hammer on very high/ultra-high volume)
  - Require next candle(s) to show **positive response**, not immediate weakness
- **Output:** `CONFIRM_REQUIRED`
- **Notes:** Couling: “Is this stopping volume – perhaps, and we wait for the next candle…”; lack of positive response is not bullish. :contentReference[oaicite:23]{index=23}

### CONF-2 — Two-level agreement (candle-level + trend-level)
- **Scope:** any timeframe
- **Detection:**
  - At least one candle-level validation/anomaly present
  - And trend-level validation/anomaly computed over K bars
- **Output:** `CONFIRMED` only when both levels align
- **Notes:** Couling: validation/anomaly exists at two levels (individual candle, and group/trend). :contentReference[oaicite:24]{index=24}

---

## 10) Entry conditions (composite “recipes”)
These are **explicitly scoped** setups built from rule atoms. Each recipe outputs “ENTRY_OK” only if all gates pass.

### ENTRY-LONG-1 — Post-accumulation breakout (Test supply → confirmation)
- **Scope:** any timeframe; best with multi-timeframe stack
- **Prerequisites:**
  - CTX-1 satisfied (trend/structure known)
  - Congestion/accumulation present (range-bound region)
- **Trigger sequence (deterministic):**
  1) `SUPPLY_REMOVED_TEST_PASS` (TEST-SUP-1) occurs :contentReference[oaicite:25]{index=25}
  2) Within next X bars (default X=5), a bullish validation bar occurs:
     - `VALIDATION_BULL` (VAL-1) :contentReference[oaicite:26]{index=26}
- **Output:** `ENTRY_OK_LONG`
- **Stop logic (deterministic):**
  - Initial protective stop under the low of the test bar or under structural support (implementation choice)

### ENTRY-SHORT-1 — Post-distribution markdown (Test demand → breakdown)
- **Scope:** any timeframe; strongest after distribution context
- **Prerequisites:**
  - CTX-1 satisfied
  - `DEMAND_REMOVED_TEST_PASS` (TEST-DEM-1) occurs :contentReference[oaicite:27]{index=27}
- **Trigger sequence:**
  1) demand-test pass prints
  2) next bearish drive validates with higher effort (trend validation building)
- **Output:** `ENTRY_OK_SHORT`
- **Notes:** Couling: low demand test means safe to move lower, fast. :contentReference[oaicite:28]{index=28}

### ENTRY-LONG-2 — Reversal long (Hammer strength + confirmation)
- **Scope:** any timeframe; best near support
- **Prerequisites:**
  - CTX-1 satisfied (likely bottom / support zone)
  - `STRENGTH_HAMMER` detected :contentReference[oaicite:29]{index=29}
- **Confirmation:**
  - CONF-1 satisfied (positive response candle(s)) :contentReference[oaicite:30]{index=30}
- **Output:** `ENTRY_OK_LONG`
- **Stop placement (Couling-specific):**
  - Stop loss below the hammer wick (market sets level). :contentReference[oaicite:31]{index=31}

### ENTRY-SHORT-2 — Reversal short (Selling climax / repeated upper-wick weakness)
- **Scope:** any timeframe; strongest after mature up-move/distribution
- **Prerequisites:**
  - `SELLING_CLIMAX_TOPPING` detected (CLIMAX-SELL-1) :contentReference[oaicite:32]{index=32}
- **Confirmation:**
  - Trend-level weakness begins (TREND-ANOM / breakdown)
- **Output:** `ENTRY_OK_SHORT`
- **Notes:** Couling: repeated upper-wick + high volume is a “clear signal” market ready to move fast. :contentReference[oaicite:33]{index=33}

---

## 11) Weakness vs strength signal catalog (quick reference)
**Strength signals**
- `STRENGTH_HAMMER` (absorption; candidate reversal) :contentReference[oaicite:34]{index=34}
- `SUPPLY_REMOVED_TEST_PASS` (breakout readiness) :contentReference[oaicite:35]{index=35}
- `TREND_VALID_UP` (rising prices + rising volume) :contentReference[oaicite:36]{index=36}

**Weakness signals**
- `WEAKNESS_SHOOTING_STAR` (mark up then fail) :contentReference[oaicite:37]{index=37}
- `DEMAND_REMOVED_TEST_PASS` (markdown readiness) :contentReference[oaicite:38]{index=38}
- `SELLING_CLIMAX_TOPPING` (distribution end; fast move likely) :contentReference[oaicite:39]{index=39}
- `TREND_ANOM_WEAK_UPTREND` (rising prices + falling volume) :contentReference[oaicite:40]{index=40}
- `ANOMALY_TRAP_UP_WARNING` (wide up, low vol) :contentReference[oaicite:41]{index=41}

**Avoid / stand aside**
- `AVOID_TRADE_WAIT` (long-legged doji + low vol = stop hunting) :contentReference[oaicite:42]{index=42}
- `AVOID_OR_REDUCE_SIZE_SHORT_HOLD` (counter-dominant trend) :contentReference[oaicite:43]{index=43}

---

## 12) Optional structural overlay (VAP as executable context)
### VAP-CTX-1 — Breakout-from-volume-density context flag
- **Scope:** any timeframe with VAP available
- **Detection:** price breaks out of a high-volume-density region (implementation-defined)
- **Output:** `NEW_TREND_POSSIBLE` (requires VPA confirmation)
- **Notes:** Couling: VAP shows density; breakout from such regions means a new trend; when confirmed with VPA. :contentReference[oaicite:44]{index=44}

---

## Phase 2 exit criteria (met)
- Deterministic rule atoms defined (validation/anomaly; trend-level; tests; premier candles; climaxes).
- Context gates enforced (trend-location-first; dominant-trend risk; ripple confirmation).
- Composite entry recipes expressed as explicit sequences.
- Explicit “do not trade / stand aside” rules captured (news/stop hunting; trap anomalies; countertrend risk).
