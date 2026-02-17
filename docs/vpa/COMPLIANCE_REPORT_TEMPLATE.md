# COMPLIANCE_REPORT.md
**VPA Canonical System — Compliance Report**
- Date:
- Code version:
- Config version:
- Dataset (if applicable):

## 1) Executive summary
- Overall status: PASS / FAIL
- Blocking issues (count):
- Drift issues (count):
- Missing implementations (count):
- Missing tests (count):

## 2) Vocabulary drift (docs + optionally code comments)
- Blacklist hits:
- Exceptions used:
- Notes:

## 3) Registry coverage (VPA_RULE_REGISTRY.yaml)
- Total atomic rules:
- Total setups:
- IDs missing from registry but present in code (“EXTRA”):
- IDs in registry missing in code (“MISSING”):

## 4) Traceability matrix status (VPA_TRACEABILITY.md)
- OK:
- PARTIAL:
- MISSING:
- DRIFT:
- EXTRA:

## 5) Pipeline compliance (VPA_SIGNAL_FLOW.md)
- Stage ordering violations:
- Layer separation violations (rule/setup/risk/execution):
- Context gate enforcement violations (CTX-1/2/3):

## 6) Determinism and config compliance
- Hardcoded thresholds found:
- Config/schema mismatches:
- Non-deterministic behavior found:

## 7) Backtest anti-lookahead checks
- Bar-close evaluation enforced:
- Next-bar execution enforced:
- Stop fill model deterministic:
- Lookahead risks found:

## 8) Tests + fixtures
- Fixture runner status:
- Missing fixtures for rules/setups:
- Integration replay status:

## 9) Required actions
List only blocking items. Each must include:
- ID
- file(s)
- acceptance criteria
- test(s) to add
