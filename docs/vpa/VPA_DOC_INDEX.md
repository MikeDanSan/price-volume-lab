# VPA_DOC_INDEX.md
**Project:** VPA — Canonical System  
**Purpose:** Single entry point for humans and AI agents. Defines reading order and how docs are used.

## 1) Non-negotiables
- Canonical source: Anna Couling (2013) *A Complete Guide to Volume Price Analysis*.
- Only use terms from `VPA_GLOSSARY.md` when claiming VPA logic.
- Reasoning order must be: Candle → Volume → Context (trend location + structure) → Confirmation/response → Action.
- Do not introduce Wyckoff/VSA/SMC terms unless explicitly requested by the user.

## 2) Reading order (AI must follow)
1) `CANONICAL_CONTRACT.md` (repo root) — one-page guardrails
2) `docs/vpa-ck/vpa_ai_context.md` — AI behavior contract
3) `docs/vpa-ck/vpa_glossary.md` — vocabulary whitelist
4) `docs/vpa-ck/vpa_canonical_model.md` — concepts & relationships
5) `docs/vpa-ck/vpa_actionable_rules.md` — deterministic rules + setups
6) `docs/vpa-ck/vpa_system_spec.md` — engineering spec
7) `docs/vpa-ck/vpa_signal_flow.md` — pipeline / dependency order
8) `docs/vpa/VPA_CONFIG.md` + `docs/config/vpa.default.json` — parameter contract
9) `docs/vpa/VPA_TEST_FIXTURES.md` + `docs/config/fixtures/vpa/` — proof via tests
10) `docs/vpa/VPA_TRACEABILITY.md` — doc→code→test mapping

## 3) Implementation sources of truth
- Rule IDs + Setup IDs: `docs/vpa/VPA_RULE_REGISTRY.yaml`
- Config validation: `docs/config/vpa_config.schema.json`
- Drift prevention: `docs/vpa/VPA_VOCAB_*.txt` + `scripts/vpa_vocab_lint.*` (lint script TBD)

## 4) Change control
Any change to rules/spec requires:
- update registry (YAML) + traceability matrix
- update fixtures/tests
- update config docs if parameters changed
- small PR with acceptance criteria

## 5) Quick-start for new AI agents
Prompt:
- “Read `CANONICAL_CONTRACT.md` then `VPA_DOC_INDEX.md` and follow the reading order. Do not modify logic until you produce a traceability matrix and drift report.”
