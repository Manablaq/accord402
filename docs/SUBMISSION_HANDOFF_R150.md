# Accord402 R150 Project Explorer handoff

Status: **CURRENT REVIEWER RESUBMISSION REFERENCE**

This is the reviewer-facing R150 reference. It does not authorize another contract deployment, Vercel deployment, or blockchain write.

## Canonical release

- repository: `https://github.com/Manablaq/accord402`
- R150 implementation commit: `7dde8f45ae88db996895c02883c951d6350cf48c`
- R150 implementation tree: `aa7f6129ce74e75c7e0405d482278568c127f100`
- exact implementation CI run: `35683293916`
- CI result: `success`
- stable production URL: `https://accord402.vercel.app`
- Bradbury chain ID: `4221`

## Canonical R150 graph

- SettlementVault: `0xFCc7FbE2243c32ff35cE74055695Bf8C23E17dD5`
- Registry: `0x5BD6f9EEBF7BE527321ED46649447c59fAc5315C`
- Adjudicator: `0x9b204786e4641EbFF5D771a08624e2B0849Fcc56`
- R150 Core: `0x142b20B20a24F659e1053A504c23fF48832c090f`

R150 Core deployment transaction:

`0x750577a17692ba91471d9821befd2c858ac06eaf7a94a80a71e866bd59757bf6`

R150 Core source SHA-256 / production source fingerprint:

`98c6cb19e1783b5f2515d24fe74e7428d01c2cfcc6991acd54c367f3cce06b7d`

## Reviewer fix

R150 closes the challenged-review and evidence-repair workflow while preserving the existing dependency graph.

- delivery evidence `observedAt` is normalized by Core to execution-time `block.timestamp`;
- replacement evidence `observedAt` is normalized the same way;
- the frontend can invoke adjudication from `CHALLENGED`;
- the authorized provider can submit repair from `EVIDENCE_REPAIR_REQUIRED`;
- repair authorization is bound to the active review generation;
- canonical transaction success requires `Finalized` and `FINISHED_WITH_RETURN`;
- after canonical success the application re-reads Core state.

## Verification completed

- R150 reviewer workflow guards: `7/7` passed on the implementation release;
- targeted R150 Core Solidity tests: `12/12` passed;
- complete Solidity CI suite: `18/18` passed;
- Python CI regression: `102 passed, 1 skipped`;
- GenVM lint/schema validation: passed;
- frontend typecheck + production build: passed;
- exact GitHub Actions run: success;
- R150 deployment receipt: verified successful;
- live Registry/Adjudicator/Vault immutable bindings: verified;
- stable production R150 binding: verified;
- public Next.js assets: verified;
- zero-argument Core functional reads: `9/9` passed.

## Reviewer reproduction

```bash
python -m pytest -q tests/test_r150_reviewer_workflow_guards.py
forge test --match-path tests/solidity/Accord402Core.t.sol
```

Complete repository gate:

```bash
forge build --root .
forge test --root .
python -m pytest -q
cd frontend
npm ci
npm run check
```

## Frontend reviewer note

The R150 Core is fresh and does not inherit historical R149 Covenant 1. The reviewer-closeout frontend starts neutral rather than auto-loading Covenant 1. Open a new covenant or enter a known R150 covenant number explicitly.

A complete wallet-signed R150 browser lifecycle is not claimed unless separately executed and recorded. Current evidence proves the deployed contracts, reviewer workflow implementation, production binding, read surfaces, transaction-finality observer, build, and regression gates.

## Historical evidence

R149 records remain available only as historical evidence:

- `SUBMISSION_HANDOFF_R149.md`
- `BRADBURY_CANONICAL_DEPLOYMENT_V3.md`
- `BRADBURY_CURRENT_CORE_ECONOMIC_PROOF_V1.md`

Do not use R149 addresses or Covenant 1 as the current R150 reviewer target.
