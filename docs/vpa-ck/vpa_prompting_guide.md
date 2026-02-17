# VPA_PROMPTING_GUIDE.md
**Project:** VPA — Canonical System  
**Goal:** Safe prompting so any AI (Cursor/Copilot/Claude/etc.) stays canonical to Anna Couling and produces engineering-grade artifacts without drift.

---

## 1) Universal “Agent Contract” prompt (paste at top of any session)
Use this as the first message to any AI agent:

> You are working on the VPA Canonical System based ONLY on Anna Couling’s *A Complete Guide to Volume Price Analysis (2013)*.  
> You must follow `VPA_AI_CONTEXT.md` and only use terms from `VPA_GLOSSARY.md`.  
> Do NOT introduce Wyckoff/VSA/SMC terminology unless explicitly requested.  
> Always reason in order: Candle → Volume → Context (trend location + structure) → Confirmation/response → Action.  
> Every output must include: scope, context gates, deterministic conditions, and “what not to trade.”

---

## 2) Prompt templates (practical, reusable)

### 2.1 “Context refresh” prompt (prevents misinterpretation)
Use when starting a new chat or swapping models:

**Prompt**
- Read: `VPA_AI_CONTEXT.md`, `VPA_GLOSSARY.md`, `VPA_CANONICAL_MODEL.md`, `VPA_ACTIONABLE_RULES.md`, `VPA_SYSTEM_SPEC.md`, `VPA_SIGNAL_FLOW.md`.
- Restate in bullets:
  1) non-negotiable invariants (Couling stance)
  2) vocabulary whitelist
  3) the candle→volume→context→confirmation order
  4) the difference between VPA vs VAP
- Then propose next steps ONLY as:
  - small, testable increments
  - with acceptance criteria

### 2.2 “Implement one rule atom” prompt (engine work, small commits)
**Prompt**
- Implement rule `RULE_ID` exactly as specified in `VPA_ACTIONABLE_RULES.md`.
- Output:
  1) function signature + inputs/outputs
  2) deterministic detection logic
  3) unit tests (golden fixtures)
  4) event payload schema (evidence)
- Constraints:
  - no new terms
  - no new strategy rules
  - keep commit small and focused

### 2.3 “Add setup composer recipe” prompt
**Prompt**
- Implement setup `ENTRY-*` as a deterministic sequence matcher.
- Must include:
  - time window X bars (configurable)
  - invalidation rules
  - state transitions (CANDIDATE → PENDING_CONFIRM → READY → INVALIDATED/EXPIRED)
  - integration tests with synthetic event streams

### 2.4 “Backtest correctness” prompt (anti-lookahead)
**Prompt**
- Audit the backtest pipeline for lookahead bias.
- Enforce:
  - signals computed only on completed bars
  - next-bar execution
  - deterministic stop fill model
- Output:
  - list of lookahead risks found
  - patch plan
  - regression tests

### 2.5 “Documentation upkeep” prompt (Cursor/Copilot-friendly)
**Prompt**
- Scan all VPA docs for drift or inconsistencies.
- Verify:
  - glossary matches system spec terminology
  - rules reference only glossary terms
  - state machine names consistent across docs
- Output:
  - proposed edits as a diff-like summary
  - do not rewrite everything—only minimal corrections

---

## 3) Do / Don’t rules for prompting (high leverage)

### DO
- Ask for **one phase / one artifact / one rule** at a time.
- Require outputs in a strict schema: **Scope → Context → Conditions → Output → Tests → Edge cases**.
- Require the agent to list **which glossary terms were used**.
- Require the agent to explicitly mark anything “assumed” vs “from Couling”.

### DON’T
- Don’t ask “make it better” without constraints—agents will drift into other frameworks.
- Don’t ask for indicator recommendations as primary decision logic.
- Don’t ask for “all strategies” in one response (forces blob output and weak QA).

---

## 4) Safety rails for swapping AIs
When moving between models/tools, always carry these pinned files:
- `VPA_AI_CONTEXT.md` (contract)
- `VPA_GLOSSARY.md` (term whitelist)
- `VPA_ACTIONABLE_RULES.md` (rule truth)
- `VPA_SYSTEM_SPEC.md` + `VPA_SIGNAL_FLOW.md` (engineering truth)

**Swap protocol**
1) Paste the Universal Agent Contract.
2) Run “Context refresh” prompt.
3) Ask the agent to confirm:
   - it will not introduce non-glossary terms
   - it will not create new rules
4) Only then begin tasks.

---

## 5) Cursor / Copilot workflows (DevOps-minded)

### 5.1 Small, safe iteration loop
1) Pick one unit of work (single rule atom / single state transition / single doc correction)
2) Implement
3) Add tests
4) Update docs
5) Commit with a narrow message (`feat(rule): implement ANOM-1`)

### 5.2 Required acceptance criteria for PRs
- [ ] deterministic logic
- [ ] unit tests + edge cases
- [ ] no glossary violations
- [ ] no lookahead in backtest
- [ ] docs updated (if behavior changed)

---

## 6) “Stop the agent” triggers (when to reject output)
Reject and re-prompt if the agent:
- uses non-glossary terms as if canonical
- jumps to entries without context gates
- proposes “always reversal” interpretations
- adds indicator dependencies as decision drivers
- changes Couling’s meanings (e.g., VPA vs VAP confusion)

**Recovery prompt**
> You violated the VPA contract. Remove non-glossary terms, restate using Couling’s validation/anomaly framework, enforce context gates, and provide deterministic conditions + tests only.

---
