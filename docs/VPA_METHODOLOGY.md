# VPA Methodology — A Complete Guide to Volume Price Analysis (Legacy / Educational)

Last updated: 2026-02-17

> **LEGACY / EDUCATIONAL**: This document was written before the canonical doc system and uses  
> Wyckoff/VSA terminology (e.g. "upthrust", "spring", "Wyckoff phases") for educational context.  
> **For implementation and AI agents, use the canonical docs instead:**  
> - Glossary: [`docs/vpa-ck/vpa_glossary.md`](vpa-ck/vpa_glossary.md)  
> - Rules: [`docs/vpa-ck/vpa_actionable_rules.md`](vpa-ck/vpa_actionable_rules.md)  
> - System spec: [`docs/vpa-ck/vpa_system_spec.md`](vpa-ck/vpa_system_spec.md)  
> - Full reading order: [`docs/vpa/VPA_DOC_INDEX.md`](vpa/VPA_DOC_INDEX.md)  
>  
> If there is any conflict between this file and the canonical docs, **the canonical docs win**.  
> Vocabulary in this file is NOT governed by `VPA_VOCAB_BLACKLIST.txt` (see exceptions list).

A faithful reference for the Volume Price Analysis (VPA) methodology as taught in *A Complete Guide to Volume Price Analysis* by Anna Coulling. This document defines the analytical framework that `vpa-core` implements. All rules are deterministic and book-driven; no ML, no invented indicators. See [RULEBOOK.md](RULEBOOK.md) for per-setup implementation specifications, and [GLOSSARY.md](GLOSSARY.md) for term definitions.

---

## 1. Foundation: Why Volume and Price

VPA rests on a single premise: **volume and price are the only two leading indicators**. Everything else — moving averages, oscillators, RSI — is derived from price and therefore lagging.

- **Price** tells you *what* happened.
- **Volume** tells you *how much effort* was behind it.
- **The relationship between the two** tells you *who is in control* — buyers or sellers — and whether the current move is genuine or likely to fail.

Volume reveals the activity of professional operators (institutional money, market makers, specialists). These participants cannot hide their activity because large positions require large volume. By reading volume alongside price action, bar by bar, we can infer their intent.

> **Simple example — the moving truck analogy:**
> Imagine you are watching a street. A moving truck (volume) pulls up to a house. The "For Sale" sign (price) comes down. That truck tells you *something real happened* — someone moved in. Now imagine the "For Sale" sign comes down but there is no truck. That is suspicious — the sign changed (price moved) but nothing real backed it up (no volume). VPA is the practice of always checking for the truck.

---

## 2. The Three Wyckoff Laws

VPA is rooted in the work of Richard Wyckoff. Coulling frames the analysis around three laws that govern every market, on every timeframe.

### 2.1 The Law of Supply and Demand

- When **demand exceeds supply**, prices rise.
- When **supply exceeds demand**, prices fall.
- When supply and demand are in balance, prices move sideways (consolidation/range).

VPA uses volume to determine *which side is dominant right now*. A rising price on rising volume means demand is in control. A rising price on falling volume means demand is drying up — even though price is still going up, the move is hollow.

> **Simple example — auction:**
> At an auction, two people bid on a painting. The price goes up because demand (two eager bidders) exceeds supply (one painting). Now imagine only one bidder shows up — the auctioneer drops the price until someone bites. The number of bidders is volume; the hammer price is price. VPA reads both together.

### 2.2 The Law of Cause and Effect

Every move in price has a cause that is proportional to the effect.

- **Cause** = accumulation or distribution (a period of sideways activity where professionals build or unload positions).
- **Effect** = the subsequent trending move (markup after accumulation, markdown after distribution).
- The *size* of the cause (how long and how much volume the sideways range contains) determines the *magnitude* of the effect.

> **Simple example — spring analogy:**
> A coiled spring. The more you compress it (longer accumulation, more volume absorbed), the further it will fly when released (bigger trending move). A quick, shallow compression gives a small bounce. VPA measures the compression (cause) to estimate the flight (effect).

### 2.3 The Law of Effort vs Result

This is the most important law for bar-by-bar analysis. **The effort (volume) should match the result (price movement).** When they disagree, something is wrong.

- **Effort matches result:** High volume + wide price spread in the same direction = genuine move, likely to continue.
- **Effort does NOT match result:** High volume + narrow price spread = effort was absorbed; the move is being opposed. Or: wide price spread on low volume = the move lacks conviction and is likely to fail.

> **Simple example — pushing a car:**
> You push a car (effort = volume) and it rolls forward a block (result = price movement). Effort matches result — normal. Now imagine ten people push the car (huge effort/volume) but it barely moves an inch (tiny price spread). Something is blocking it — maybe the handbrake is on. In VPA, that "handbrake" is professional operators absorbing the move. Conversely, if the car rolls a whole block but nobody pushed it (low volume), it is rolling downhill on momentum alone and will stop soon.

---

## 3. Reading the Candle (Price Action)

Every bar (candle) has four data points: Open, High, Low, Close. From these, VPA extracts three key characteristics.

### 3.1 Spread

**Spread = High minus Low** (the full range of the bar).

- **Wide spread**: Large range; significant activity or volatility.
- **Narrow spread**: Small range; lack of interest, indecision, or absorption.
- Spread is always judged **relative to recent bars**, not in absolute terms.

> **Simple example:**
> If the last five bars each moved about $1, and today's bar moved $3, that is a wide spread (relatively). If today's bar moved $0.30, that is narrow. The dollar amount alone does not matter — what matters is whether this bar's range is bigger or smaller than its neighbors.

### 3.2 Body

**Body = |Close minus Open|** (the filled or hollow portion of the candle).

- A **large body** relative to the spread means the close was far from the open — conviction.
- A **small body** relative to the spread means the close was near the open — indecision or reversal.

> **Simple example:**
> A bar opens at $100 and closes at $104, with a high of $105 and low of $99. Spread is $6, body is $4 — a solid body. Now imagine it opens at $100 and closes at $100.50 with the same $6 spread. Body is only $0.50 — price traveled far during the bar but ended up nearly where it started. That small body signals a tug-of-war.

### 3.3 Close Location

Where the close sits within the bar's range is the single most important piece of the candle:

| Close location | What it means |
|----------------|---------------|
| **Upper third** (close near the high) | Buyers won the bar; bullish. |
| **Lower third** (close near the low) | Sellers won the bar; bearish. |
| **Middle third** | Neither side won; indecision. |

> **Simple example:**
> Think of a bar as a tug-of-war rope. The high is one end, the low is the other. Where the close lands tells you who was winning at the bell. Close near the high = buyers pulled the rope to their side. Close near the low = sellers pulled it to theirs. Close in the middle = a draw.

### 3.4 Wicks (Shadows)

Wicks (upper and lower shadows) reveal intra-bar rejection:

- **Long upper wick**: Price tried to go higher but was rejected — supply (selling) appeared at the top.
- **Long lower wick**: Price tried to go lower but was rejected — demand (buying) appeared at the bottom.
- **No wick (marubozu)**: Strong conviction in one direction; no intra-bar rejection.

> **Simple example:**
> A bar goes up to $110 (high) but closes at $103 (close), leaving a $7 upper wick. Buyers pushed to $110 but sellers slammed it back down. That upper wick is the footprint of supply pushing price back. The longer the wick, the stronger the rejection.

---

## 4. Reading Volume

Volume is **always relative**, never absolute. 1 million shares on SPY is normal; 1 million shares on a small cap is extreme. VPA classifies volume relative to a recent baseline.

### 4.1 Relative Volume Classification

| Level | Meaning |
|-------|---------|
| **Ultra high** | Far above average; climactic; rare event — exhaustion, reversal, or breakout. |
| **High** | Above average; significant interest or professional activity. |
| **Average** | Normal participation. |
| **Low** | Below average; lack of interest. |
| **Ultra low** | Far below average; very thin participation; holiday-type. |

The baseline is typically a moving average of volume over the last N bars (e.g., 20 bars). The exact N is configurable — see [TUNING_GUIDE.md](TUNING_GUIDE.md).

> **Simple example:**
> If the average volume over the last 20 bars is 500,000 shares, then:
> - 1,200,000 shares = ultra high
> - 750,000 shares = high
> - 480,000 shares = average
> - 250,000 shares = low
> - 80,000 shares = ultra low
>
> The actual thresholds are set in configuration, but the principle is constant: judge this bar's volume against its recent neighbors.

### 4.2 Volume Trend (Rising or Declining)

Beyond classifying a single bar's volume, VPA looks at whether volume is **rising or declining** across a sequence of bars. This reveals whether participation is growing or shrinking as a price move continues.

- **Rising volume over consecutive bars** = increasing participation and conviction.
- **Declining volume over consecutive bars** = fading participation; the move is losing steam.

> **Simple example:**
> A stock rises for four bars: $100, $101, $102, $103. Volume on those bars: 600K, 500K, 400K, 300K. Price is going up but fewer and fewer people are buying each bar. That declining volume on rising prices is a classic warning: the rally is running out of fuel.

---

## 5. The Core Analytical Framework: Validation vs Anomaly

This is the heart of VPA. Every bar is either **validated** by its volume or presents an **anomaly**. Anomalies are where signals live.

### 5.1 Validation (Volume Confirms Price)

Volume confirms the price move — the move is genuine and likely to continue:

| Price action | Volume | Interpretation |
|--------------|--------|----------------|
| Price rises | Volume rises | Healthy demand; uptrend confirmed. |
| Price falls | Volume rises | Healthy supply; downtrend confirmed. |

> **Simple example:**
> A stock climbs from $50 to $55 over three bars and volume increases each bar. More and more buyers are showing up at higher prices. This is a healthy, validated uptrend — demand is real and growing.

### 5.2 Anomaly (Volume Contradicts Price)

Volume does NOT confirm the price move — something is wrong; the move is suspect:

| Price action | Volume | Interpretation | VPA signal type |
|--------------|--------|----------------|-----------------|
| Price rises | Volume falls / low | Rally lacks demand; likely to fail. | **No Demand** (weakness) |
| Price falls | Volume falls / low | Decline lacks supply; likely to reverse. | **No Supply** (strength) |
| Price rises sharply | Volume is ultra high | Possible buying exhaustion / climax. | **Buying Climax** (weakness) |
| Price falls sharply | Volume is ultra high | Possible selling exhaustion / climax. | **Selling Climax** (strength) |
| High volume | Little price movement | Effort absorbed; professionals opposing the move. | **Absorption** |

> **Simple example — "No Demand":**
> A stock ticks up from $50.00 to $50.20. But volume on that bar is half the recent average. The price went up, but almost nobody showed up to buy. That is "no demand." It is like a shop raising prices but having zero customers — the price increase will not stick.
>
> **Simple example — "Selling Climax":**
> A stock plunges $5 on the heaviest volume seen in months. Panic selling. But the very next bar barely falls and volume drops. The huge selling wave exhausted itself — everyone who wanted to sell already did. The "climax" is over. This is often the footprint of professionals absorbing all that panicked supply, building positions at the bottom.

---

## 6. The VPA Setups (Signals)

Each setup below is a specific pattern of candle characteristics + volume characteristics + context that signals a probable directional move. These are the building blocks that `vpa-core` detects.

### 6.1 No Demand (Bearish / Weakness)

**What it is:** An up bar on low or declining volume. The market went up, but buyers did not participate. Demand is absent.

**Candle:**
- Up bar (close > open, or close > prior close).
- Spread can be any size but narrow spread with up close strengthens the signal.
- Close typically in upper portion of bar.

**Volume:**
- Low relative volume (below baseline), OR volume declining vs prior bars.

**Context:**
- Most meaningful after an uptrend or bounce — it signals the uptrend is losing fuel.
- In a downtrend, no demand on a bounce confirms that sellers are still in control.

**Interpretation:**
- Buyers are not present at these prices. The up move is hollow.
- Do not buy. If already long, consider exiting or tightening stops.

> **Simple example:**
> SPY has been rising for five bars. Bar 6 closes slightly higher, but volume is 40% below the 20-bar average. The rally moved prices up, but almost nobody bought. No demand. The next bar gaps down — the rally was on borrowed time.

---

### 6.2 No Supply (Bullish / Strength)

**What it is:** A down bar on low or declining volume. The market went down, but sellers did not participate. Supply is absent.

**Candle:**
- Down bar (close < open, or close < prior close).
- Narrow spread with down close strengthens the signal.
- Close typically in lower portion.

**Volume:**
- Low relative volume (below baseline), OR volume declining vs prior bars.

**Context:**
- Most meaningful after a downtrend or dip — it signals selling pressure is exhausted.
- In an uptrend, no supply on a pullback confirms buyers are still in control.

**Interpretation:**
- Sellers are not present at these prices. The down move is hollow.
- The path of least resistance is up.

> **Simple example:**
> A stock has pulled back from $80 to $75 over three bars. On the third bar, it drops $0.30 to $74.70, but volume is the lowest in two weeks. Nobody is selling anymore. No supply. This is often the end of a pullback — smart money absorbed earlier selling and supply is now exhausted.

---

### 6.3 Stopping Volume (Potential Reversal)

**What it is:** High or ultra-high volume that halts a move. Typically seen at the end of a downtrend (stopping a decline) or uptrend (stopping a rally).

**Candle:**
- Wide spread bar in the direction of the existing move.
- Close moves *away* from the extreme — e.g., in a downtrend, the bar has a wide spread down but the close is in the upper half (buyers stepped in).
- A long lower wick (in a downtrend) or long upper wick (in an uptrend) strengthens the signal.

**Volume:**
- High or ultra-high — significantly above baseline.

**Context:**
- Must occur after a sustained move (trend). Stopping volume at the start of a move has no meaning.
- Often occurs at known support (in a downtrend) or resistance (in an uptrend).

**Interpretation:**
- Professionals are stepping in to oppose the existing move. In a downtrend, smart money is buying the panic. In an uptrend, smart money is selling into the euphoria.
- Stopping volume does NOT mean instant reversal — it means the current move has been "stopped." A period of consolidation or a test often follows before a reversal begins.

> **Simple example:**
> A stock has been falling for two weeks: $90 to $72. On one bar, it plunges to $70 intra-bar (wide spread down, huge volume) but closes at $73. The volume is three times the average. Someone bought all that panic selling. The move is "stopped." The next several bars go sideways as the market digests. Eventually, price moves up. The stopping volume bar was the footprint of professionals absorbing supply.

---

### 6.4 Buying Climax (Bearish / Weakness)

**What it is:** A wide-spread up bar on ultra-high volume near the top of an uptrend. It represents exhaustion of demand — the final burst of buying.

**Candle:**
- Wide spread up bar.
- Close near the high (buyers still felt in control during the bar).
- OR: close begins to pull back from the high (long upper wick) — even more bearish.

**Volume:**
- Ultra high — the highest in the recent sequence.

**Context:**
- After a sustained uptrend.
- Price is at or near a prior resistance level or all-time high.

**Interpretation:**
- This is the "blow-off top." Everyone who wants to buy has bought. Professionals use this euphoric volume to distribute (sell) their positions to late buyers. Supply is being handed to demand.
- The very next bars often show weakness: narrow spread, lower closes, or declining volume on up bars.

> **Simple example:**
> Tech stock XYZ has run from $150 to $200 over two months. On one bar, it surges $8 to $208 on volume that is 4x the average. Headlines are euphoric. But the next bar is flat, then the next bar is a small down bar. The climax bar was professionals selling to the crowd. Distribution has begun.

---

### 6.5 Selling Climax (Bullish / Strength)

**What it is:** A wide-spread down bar on ultra-high volume near the bottom of a downtrend. It represents exhaustion of supply — the final burst of panicked selling.

**Candle:**
- Wide spread down bar.
- Close near the low (sellers in control during the bar).
- OR: close pulls back up from the low (long lower wick) — even more bullish.

**Volume:**
- Ultra high — the highest in the recent sequence.

**Context:**
- After a sustained downtrend.
- Price is at or near a prior support level or significant low.

**Interpretation:**
- Panic selling. Everyone who wants to sell has sold. Professionals use this volume to accumulate (buy) positions cheaply. Demand is absorbing all the supply.
- Often followed by sideways consolidation (accumulation) before a reversal higher.

> **Simple example:**
> A stock crashes from $60 to $35 over six weeks on bad news. One bar plunges $4 to $31 on record volume, with a long lower wick closing back at $33. That is the selling climax. Weak holders have been shaken out. Over the next two weeks, the stock drifts sideways between $32 and $35 — accumulation. Then it starts climbing.

---

### 6.6 Test for Supply (Bullish)

**What it is:** After a period of accumulation or after stopping volume, price dips back down into a prior area of supply (a level where selling previously occurred). If volume is **low** on the dip, supply has been removed — the test is "successful" and bullish.

**Candle:**
- Down bar or dip that returns toward a prior low or demand zone.
- Narrow spread preferred (shows lack of selling pressure).
- Close in upper half preferred (buyers stepped in).

**Volume:**
- **Low** — the key characteristic. If volume is high, the test fails (supply is still present).

**Context:**
- Prior stopping volume or selling climax has occurred.
- Some accumulation / sideways action has taken place.
- Price dips back into or near the area of the prior high-volume low.

**Interpretation:**
- The dip is testing whether sellers are still active at these prices. Low volume means "no, they are gone." The path of least resistance is now up.
- A **successful test** (low volume) is one of the most reliable bullish signals in VPA.
- A **failed test** (high volume on the dip) means supply is still present — more work needed before a move up.

> **Simple example:**
> A stock hit $40 on a selling climax two weeks ago, then drifted up to $44. Now it dips back to $40.50. Volume on the dip bar is very low — barely 30% of average. Nobody wants to sell at $40 anymore. The supply at $40 was absorbed during the climax. This is a successful test. Price rallies from here.
>
> **Counter-example (failed test):** Same scenario, but the dip to $40.50 comes on heavy volume. Sellers are still active. The test fails. Do not buy — more selling is likely.

---

### 6.7 Test for Demand (Bearish)

**What it is:** After a period of distribution or after a buying climax, price rallies back up into a prior area of demand (a level where buying previously occurred). If volume is **low** on the rally, demand has been removed — the test is "successful" (from a bearish perspective) and confirms that the path down is clear.

**Candle:**
- Up bar or rally that returns toward a prior high or supply zone.
- Narrow spread preferred.
- Close in lower half preferred (sellers capping the rally).

**Volume:**
- **Low** — demand is no longer present at these higher prices.

**Context:**
- Prior buying climax or distribution has occurred.
- Price dips and then rallies back toward the area of the prior high.

**Interpretation:**
- The rally is testing whether buyers are still active at these prices. Low volume means "no, they have stepped away." The path of least resistance is now down.

> **Simple example:**
> A stock topped at $100 on a buying climax, then fell to $95. Now it rallies back to $99 but on volume that is 35% of average. Nobody is buying at $99 anymore. Demand is gone. This confirms distribution. The stock then falls through $95 and lower.

---

### 6.8 Absorption Volume

**What it is:** High volume with minimal price movement. The effort (volume) did not produce a proportional result (price change). One side is absorbing the other's pressure.

**Candle:**
- **Narrow spread** relative to recent bars.
- Close near open (small body) or close location varies.
- The key: the range is small despite heavy volume.

**Volume:**
- **High or ultra high** — well above average.

**Context:**
- In an uptrend: high volume + narrow spread = supply is being absorbed by demand. Professionals are buying everything sellers throw at them.
- In a downtrend: high volume + narrow spread = demand is being absorbed by supply. Professionals are selling into every buy attempt.

**Interpretation:**
- Think of it as an invisible wall. Price tried to move (as evidenced by the high volume) but was held in place. The side doing the absorbing is in control — they are quietly building or unloading positions without letting price move.

> **Simple example:**
> A stock is in a downtrend, falling from $50 to $42. At $42, one bar shows volume that is 3x average but the bar's spread is only $0.40 (open $42.10, close $42.30). Someone is buying every share that the panicked sellers are dumping — absorbing the supply — without letting the price fall further. This is accumulation happening in real time. After a few more bars of this, the downtrend is likely over.

---

### 6.9 Upthrust (Bearish Trap / Failed Breakout)

**What it is:** Price breaks above a resistance level (or makes a new high) but then closes back below it on high volume. The breakout was a trap.

**Candle:**
- High is above resistance or prior high.
- Close is back below resistance / prior high — preferably in the lower third of the bar.
- Long upper wick.

**Volume:**
- High volume — professionals used the breakout to sell into the buying frenzy.

**Context:**
- At resistance, top of range, or after distribution.

**Interpretation:**
- The breakout was engineered to trigger buying (breakout traders, stop runs) so that professionals could distribute at higher prices. The close back below resistance confirms supply overwhelmed the brief demand.

> **Simple example:**
> A stock has been stuck below $50 (resistance) for two weeks. One bar spikes to $51.50 on big volume — breakout traders pile in. But by the close, price is back at $49.20. The upper wick tells the story: smart money sold into the breakout frenzy. Anyone who bought the breakout is now trapped. Price drops to $46 over the next week.

---

### 6.10 Spring / Shakeout (Bullish Trap / Failed Breakdown)

**What it is:** The bullish mirror of an upthrust. Price breaks below a support level but then closes back above it. The breakdown was a trap to shake out weak holders and trigger stop losses.

**Candle:**
- Low is below support or prior low.
- Close is back above support — preferably in the upper third of the bar.
- Long lower wick.

**Volume:**
- Can be high (professionals buying the panic) or low (no real selling interest below support — just a vacuum).

**Context:**
- At support, bottom of range, or after accumulation.

**Interpretation:**
- The dip below support was designed to trigger panic selling and stop-loss orders. Professional operators bought those shares cheaply. The close back above support confirms demand is in control.

> **Simple example:**
> A stock has bounced off $30 support three times. One bar dips to $29.50, triggering stop losses. Volume spikes. But the close is $30.80 — back above support with a long lower wick. Weak holders sold their shares to smart money at $29.50. The stock rallies to $35 in the following week.

---

### 6.11 Pushing Through Supply / Pushing Through Demand

**What it is:** A wide-spread bar that breaks through a support or resistance level on high volume and **closes beyond it**. Unlike an upthrust or spring, this is a *genuine* breakout.

**Candle:**
- Wide spread.
- Close is well beyond the broken level (no long wick pulling back).

**Volume:**
- **High** — genuine effort behind the move.

**Interpretation:**
- Effort matches result. Volume is high and the price moved decisively through the level. This is a genuine breakout, not a trap.

> **Simple example:**
> A stock has been blocked at $50 resistance. One bar opens at $49.80, drives to $52.00, and closes at $51.70 — wide spread, close near the high, volume is 2.5x average. This is not a trap; it is real demand pushing through supply. The breakout is genuine.
>
> **How to tell a genuine breakout from an upthrust:** The close. If the bar closes *above* resistance with a strong close (upper third), on high volume, it is pushing through. If the bar pokes above resistance but closes *back below* it (long upper wick), it is an upthrust.

---

## 7. Context: Background Strength and Weakness

**No VPA signal is read in isolation.** Every bar must be interpreted against the "background" — the accumulated evidence of strength or weakness built up over prior bars.

### 7.1 Building the Background

The background is built bar by bar as signals accumulate:

| Signals that build background **strength** | Signals that build background **weakness** |
|---------------------------------------------|---------------------------------------------|
| Selling climax | Buying climax |
| Stopping volume (at bottom) | Stopping volume (at top) |
| No supply (on pullbacks) | No demand (on rallies) |
| Successful test for supply (low vol dip) | Successful test for demand (low vol rally) |
| Spring / shakeout | Upthrust |
| Absorption at support | Absorption at resistance |

> **Simple example:**
> Over 20 bars, you see: (1) a selling climax at $40, (2) sideways consolidation with absorption, (3) a test back to $40.50 on low volume. Each event adds to the background strength picture. Now, when you see a wide-spread up bar on high volume, you read it as a continuation of accumulation → markup. The background supports the signal.
>
> Contrast: if you see that same up bar on high volume with NO prior background strength (no climax, no test, no absorption), it could be a buying climax at the top. **Same bar, different background, opposite interpretation.**

### 7.2 Trend Identification

VPA identifies trend by reading price and volume together:

| Trend | Characteristics |
|-------|-----------------|
| **Uptrend (healthy)** | Higher highs and higher lows; up bars on rising volume, down bars (pullbacks) on declining/low volume. |
| **Uptrend (weakening)** | Price still making higher highs but up bars show declining volume; down bars show rising volume. |
| **Downtrend (healthy)** | Lower highs and lower lows; down bars on rising volume, up bars (bounces) on declining/low volume. |
| **Downtrend (weakening)** | Price still making lower lows but down bars show declining volume; up bars show rising volume. |
| **Sideways / range** | Price oscillates between support and resistance; volume may spike at extremes (tests, absorption). |

> **Simple example — healthy vs weakening uptrend:**
>
> **Healthy:** Bar 1: up $1, volume 600K. Bar 2: up $1.20, volume 700K. Bar 3: pullback $0.40, volume 300K. Bar 4: up $1.50, volume 800K. Volume rises on up bars, falls on pullbacks. Buyers are in control.
>
> **Weakening:** Bar 1: up $1, volume 600K. Bar 2: up $0.80, volume 450K. Bar 3: up $0.50, volume 350K. Price is still rising but each bar has less volume. Demand is fading. This is "no demand" building across multiple bars.

---

## 8. The Wyckoff Market Cycle

Coulling teaches the four-phase market cycle derived from Wyckoff. Every instrument, on every timeframe, moves through these phases. VPA identifies which phase the market is in.

### 8.1 Accumulation

**What:** Smart money is quietly buying after a downtrend. Price moves sideways in a range.

**VPA footprint:**
- Selling climax or stopping volume marks the beginning.
- Narrow-range bars on declining volume (no supply on dips).
- Absorption volume (high volume, little price movement) as professionals soak up remaining supply.
- Successful tests for supply (low-volume dips toward the bottom of the range).
- Springs / shakeouts near the bottom.

> **Simple example:**
> After a stock falls from $80 to $50, it stops falling (stopping volume at $50). For the next three weeks it trades between $50 and $55. Volume on down bars is light (no supply). Volume on certain bars is very high but price does not fall (absorption). A dip to $49.50 on tiny volume recovers immediately (spring + successful test). All of this is accumulation. Smart money is loading up.

### 8.2 Markup

**What:** The uptrend that follows accumulation. Demand exceeds supply; price rises.

**VPA footprint:**
- Breakout from the accumulation range on high volume (pushing through supply).
- Up bars on rising or healthy volume.
- Pullbacks are shallow and on low volume (no supply on dips — healthy retracements).
- No demand signals are absent.

> **Simple example:**
> The stock breaks above $55 on volume that is 2x average. It rises from $55 to $70 over several weeks. Each pullback ($2-3) comes on low volume — no supply. Each rally bar has solid volume — demand is present. This is the markup phase. Ride the trend.

### 8.3 Distribution

**What:** Smart money is quietly selling after an uptrend. Price moves sideways in a range at the top.

**VPA footprint:**
- Buying climax or stopping volume at the top marks the beginning.
- Up bars on declining volume (no demand on rallies).
- High-volume bars with little upside progress (absorption — professionals selling into buying).
- Upthrusts (failed breakouts above the range on high volume).
- Tests for demand that show low volume on rallies (buyers gone).

> **Simple example:**
> After rising from $50 to $90, the stock surges to $92 on 4x volume (buying climax). Over the next two weeks it trades between $85 and $92. Rallies toward $92 come on declining volume (no demand). A spike to $93 closes back at $89 (upthrust). Smart money is distributing — selling their positions to late buyers.

### 8.4 Markdown

**What:** The downtrend that follows distribution. Supply exceeds demand; price falls.

**VPA footprint:**
- Breakdown from the distribution range on high volume (pushing through demand).
- Down bars on rising or healthy volume.
- Bounces are shallow and on low volume (no demand on rallies — weak bounces).
- No supply signals are absent; supply dominates.

> **Simple example:**
> The stock breaks below $85 on heavy volume. It falls from $85 to $60 over several weeks. Each bounce ($2-3) comes on thin volume — no demand. Each down bar has solid volume — supply is present. This is the markdown phase. Stay out or be short.

---

## 9. Support, Resistance, and Volume

VPA treats support and resistance not as static lines but as **zones where prior volume activity occurred.** The more volume at a price level, the more significant it is.

### 9.1 Support

A level where demand previously overwhelmed supply (e.g., a selling climax, stopping volume, or absorption zone). When price returns to this level, VPA asks: **is demand still here?**

- Test on low volume → support holds (demand still present, supply exhausted).
- Test on high volume with price breaking through → support fails.

### 9.2 Resistance

A level where supply previously overwhelmed demand (e.g., a buying climax, distribution zone). When price returns, VPA asks: **is supply still here?**

- Test on low volume → resistance may break (supply exhausted).
- Test on high volume with price rejected → resistance holds.

> **Simple example:**
> A stock found stopping volume at $40 three weeks ago with 3x average volume. Now price returns to $41. Volume on the dip is ultra low. There is nobody left to sell at $40 — the stopping volume event absorbed all the supply. Support holds. The stock bounces.
>
> But if price returns to $41 and volume is very high with a wide-spread down bar closing below $40 — the demand that supported $40 has been overwhelmed. Support breaks.

---

## 10. Putting It All Together: The VPA Read

Reading the market with VPA follows a consistent process, applied to each new bar:

### Step 1: Classify the candle
- Spread (wide / average / narrow relative to recent bars).
- Body size and close location (upper / middle / lower third).
- Wicks (long upper wick = supply rejection; long lower wick = demand rejection).

### Step 2: Classify the volume
- Relative volume (ultra high / high / average / low / ultra low vs baseline).
- Volume trend (rising or declining across recent bars).

### Step 3: Apply effort vs result
- Does the volume match the price movement?
- If yes: validated move — continuation expected.
- If no: anomaly — identify which anomaly (no demand, no supply, absorption, climax, etc.).

### Step 4: Read in context
- What is the background? (Strength or weakness accumulated over prior bars.)
- What phase are we in? (Accumulation, markup, distribution, markdown.)
- Where are we relative to support / resistance?
- Is this bar confirming the background or contradicting it?

### Step 5: Identify the setup
- Does this bar (in context) match a specific VPA setup from the rulebook?
- If yes: generate a signal with rationale.
- If no: no signal — wait.

### Step 6: Require confirmation
- A single bar is a setup, not a complete signal for action.
- Confirmation comes from subsequent bars that support the interpretation.
- E.g., no demand is confirmed if the next bar closes lower or shows continued low volume on any rally.

> **Worked example — full read:**
>
> **Background:** Stock XYZ has been in a downtrend from $60 to $45 over three weeks. Two bars ago, there was a wide-spread down bar on ultra-high volume at $45 with a long lower wick closing at $46.50 (stopping volume — background strength event #1). Yesterday's bar: small range, $46.20 to $46.80, average volume (consolidation after climax).
>
> **Today's bar:**
> - Open: $46.50, High: $47.00, Low: $45.10, Close: $46.80
> - Spread: $1.90 (average for recent bars)
> - Close location: upper third (close near high)
> - Lower wick: $1.40 ($46.50 - $45.10) — long
> - Volume: low (60% of 20-bar average)
>
> **Read:**
> 1. Candle: Down dip intra-bar (low at $45.10 near the prior stopping volume zone) but closed back up near the high. Long lower wick = demand rejection of lower prices.
> 2. Volume: Low — during the dip, almost nobody sold.
> 3. Effort vs result: Price dipped to $45.10 (the result of selling effort) but volume was low (effort was minimal). Anomaly: no supply.
> 4. Context: We had stopping volume at $45 two bars ago (background strength event #1). Now a test back toward $45 on low volume (background strength event #2). Supply has been exhausted.
> 5. Setup: **Test for supply — successful**. Low-volume dip back to prior stopping volume zone, close in upper third.
> 6. Confirmation: Watch the next bar. If it closes higher on average or rising volume, the test is confirmed. If it plunges on high volume, the test failed and supply is not yet exhausted.

---

## 11. What VPA Is NOT

To maintain fidelity to the book:

- **VPA is not indicator-based.** No RSI, MACD, Bollinger Bands, or moving averages are required. Price and volume are sufficient.
- **VPA is not pattern matching in isolation.** A single bar never generates a signal without context. The background is essential.
- **VPA is not prediction.** It reads what professionals are *doing now*, not what will happen in the future. Signals express probability based on current evidence, not certainty.
- **VPA is not mechanical without judgment.** While `vpa-core` implements deterministic rules, the methodology in the book requires interpreting bars in context. The rulebook encodes the decision logic; it does not replace understanding the principles.
- **VPA does not use absolute volume.** Volume is always relative. Never compare raw volume numbers across different instruments or time periods without normalization.

---

## 12. Summary of Key VPA Setups

Quick-reference table of all setups, their bias, and what to look for:

| Setup | Bias | Candle | Volume | Context |
|-------|------|--------|--------|---------|
| No Demand | Bearish | Up bar, any spread | Low / declining | After uptrend or bounce |
| No Supply | Bullish | Down bar, any spread | Low / declining | After downtrend or dip |
| Stopping Volume | Reversal | Wide spread, close away from extreme, wicks | Ultra high / high | End of sustained move |
| Buying Climax | Bearish | Wide spread up, close near high | Ultra high | Top of uptrend |
| Selling Climax | Bullish | Wide spread down, close near low | Ultra high | Bottom of downtrend |
| Test for Supply | Bullish | Dip toward prior support, narrow spread | Low | After accumulation / stopping vol |
| Test for Demand | Bearish | Rally toward prior resistance, narrow spread | Low | After distribution / buying climax |
| Absorption | Depends | Narrow spread (any direction) | High / ultra high | At support (bullish) or resistance (bearish) |
| Upthrust | Bearish | Poke above resistance, close back below, upper wick | High | At resistance / top of range |
| Spring / Shakeout | Bullish | Dip below support, close back above, lower wick | High or low | At support / bottom of range |
| Pushing Through Supply | Bullish | Wide spread up through resistance, close above | High | Breakout from accumulation |
| Pushing Through Demand | Bearish | Wide spread down through support, close below | High | Breakdown from distribution |

---

## 13. Confirmation and Invalidation (General Rules)

These principles apply across all setups:

### Confirmation
- A setup is a *potential* signal. It becomes actionable when the next bar(s) support the interpretation.
- For bearish setups (no demand, buying climax, upthrust): confirmed if the next bar closes lower or shows continued weakness (low volume on any rally).
- For bullish setups (no supply, selling climax, spring): confirmed if the next bar closes higher or shows continued strength (low volume on any dip).
- Multiple setups in the same direction build cumulative evidence. E.g., stopping volume + absorption + successful test = strong case for reversal.

### Invalidation
- A setup is invalidated when the market does the opposite with conviction.
- For bearish setups: invalidated if the next bar shows high volume and a strong up close (real demand appeared).
- For bullish setups: invalidated if the next bar shows high volume and a strong down close (real supply appeared).
- One invalidating bar overrides a setup. Do not fight the evidence.

> **Simple example:**
> You identify "no demand" — an up bar on low volume. You expect weakness. But the very next bar is a wide-spread up bar on volume that is 2x average. Real demand has arrived. The no-demand reading is invalidated. Do not trade it.

---

## 14. Relationship to This Codebase

This document is the **conceptual foundation**. Here is how it maps to the system:

| Concept in this document | Where it lives in the codebase |
|--------------------------|-------------------------------|
| Candle characteristics (spread, body, close location, wicks) | `vpa_core` — candle feature extraction |
| Relative volume classification | `vpa_core` — relative volume module |
| Background strength/weakness, trend, phase | `vpa_core` — context detection |
| VPA setups (no demand, stopping vol, etc.) | `vpa_core` — setup matching; each setup defined in [RULEBOOK.md](RULEBOOK.md) |
| Confirmation and invalidation | `vpa_core` — confirmation logic per setup |
| Signal + rationale | `vpa_core` output: `Signal` dataclass |
| TradePlan (entry, stop, invalidation) | `vpa_core` output: `TradePlan` dataclass |
| Market cycle phases | Future: context detection (not in MVP) |

Every rule implemented in `vpa_core` must trace back to a concept in this document and a specific setup in [RULEBOOK.md](RULEBOOK.md). If a rule cannot be traced, it does not belong.

---

*This document is a reference, not a substitute for reading the book. For the definitive treatment, see: A Complete Guide to Volume Price Analysis by Anna Coulling.*
