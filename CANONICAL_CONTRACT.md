# CANONICAL_CONTRACT.md
**VPA Canonical System — AI/Dev Contract (Pinned)**

## Source of truth
- Anna Couling (2013) *A Complete Guide to Volume Price Analysis* is canonical.
- If anything conflicts with Couling framing/terminology → Couling wins.

## Vocabulary
- Use only terms defined in: `docs/vpa/VPA_GLOSSARY.md`
- Do NOT introduce Wyckoff/VSA/SMC terminology unless explicitly requested by the user.

## Reasoning order (mandatory)
1) Candle anatomy (spread + wicks)
2) Volume (validation vs anomaly; effort vs result)
3) Context gates (trend location + structure + timeframe)
4) Confirmation/response (next candle(s) when required)
5) Action (setup → entry → stop/size)

## Engineering separation (mandatory)
- Rule Engine emits atomic SignalEvents only (no orders).
- Setup Composer matches sequences only (no sizing).
- Risk Engine owns stops/sizing/rejects.
- Backtest must be bar-close evaluated and next-bar executed by default (no lookahead).

## Drift firewall
- All Rule IDs/Setup IDs must exist in: `docs/vpa/VPA_RULE_REGISTRY.yaml`
- Traceability must be maintained in: `docs/vpa/VPA_TRACEABILITY.md`
- Vocabulary drift is blocked by: `scripts/vpa_vocab_lint.*`

## If uncertain
- Mark: `UNKNOWN / NEEDS BOOK CHECK`
- Do NOT invent new “Couling rules” or rename canonical terms.
