# Accord402

> **Current reviewer release: R150.** The canonical Bradbury Core is `0x142b20B20a24F659e1053A504c23fF48832c090f`, deployed from R150 implementation commit `7dde8f45ae88db996895c02883c951d6350cf48c`. Production remains at [accord402.vercel.app](https://accord402.vercel.app) and is bound to the R150 Core and source fingerprint.

**Proof-bound service agreements for agent-to-agent commerce.**

Accord402 is a GenLayer-native warranty protocol for autonomous services. A buyer funds a covenant, a provider delivers against explicit criteria, and approved evidence is reviewed before settlement. Deterministic escrow, policy, provenance, deadlines, repair bounds, and accounting stay on the EVM contracts; the semantic review step runs through a narrow GenLayer Intelligent Contract.

## Current R150 status

| Surface | Status |
| --- | --- |
| Bradbury chain | `4221` |
| R150 Core | `0x142b20B20a24F659e1053A504c23fF48832c090f` |
| R150 Core deployment | Successful — tx `0x750577a17692ba91471d9821befd2c858ac06eaf7a94a80a71e866bd59757bf6` |
| Registry / Adjudicator / Vault | Reused and live-wiring verified |
| Complete Solidity suite | Passing: 18 tests |
| Python regression suite | Passing: 102 tests, 1 skipped on the R150 implementation release |
| R150 reviewer workflow guards | Passing: 7/7 on the R150 implementation release |
| GenLayer schema/linter checks | Passing |
| Frontend typecheck + production build | Passing |
| GitHub Actions | `verify` run `35683293916` succeeded for the R150 implementation commit |
| Production console | R150-bound at [accord402.vercel.app](https://accord402.vercel.app) |
| Canonical transaction success | Requires `Finalized` **and** `FINISHED_WITH_RETURN` |

## Canonical Bradbury R150 graph

| Component | Canonical address | R150 status |
| --- | --- | --- |
| SettlementVault | `0xFCc7FbE2243c32ff35cE74055695Bf8C23E17dD5` | Reused verified deployment |
| Registry | `0x5BD6f9EEBF7BE527321ED46649447c59fAc5315C` | Reused verified deployment |
| Adjudicator | `0x9b204786e4641EbFF5D771a08624e2B0849Fcc56` | Reused finalized GenLayer deployment |
| Core | `0x142b20B20a24F659e1053A504c23fF48832c090f` | R150 deployment |

Exact source SHA-256 values:

- SettlementVault: `e966518dac38ba95df3ff06f7a319bcd97b823a3e36d019003b45ee4a4fe6cd6`
- Registry: `bac515e32c8e4a56073b412079995c8bf64ace94274314a491b2dbe411ea35ae`
- Adjudicator: `575e063661cc12a5de18dfa67ab3fbeb38bee1028694a08021efbc300115c198`
- R150 Core: `98c6cb19e1783b5f2515d24fe74e7428d01c2cfcc6991acd54c367f3cce06b7d`

See [`docs/BRADBURY_CANONICAL_DEPLOYMENT_R150.md`](docs/BRADBURY_CANONICAL_DEPLOYMENT_R150.md) for the current deployment record.

## What R150 closes

R150 addresses the challenged-review and repair workflow at the contract and product layers.

1. **Execution-time evidence binding.** Delivery and evidence-repair `observedAt` values are normalized by Core to execution-time `block.timestamp` before Registry validation.
2. **Reviewer workflow reachability.** The production console exposes challenged adjudication, repair, re-adjudication, settlement authorization, and settlement claim instead of leaving them contract-only.
3. **Canonical finality handling.** An accepted transaction is not reported as canonical success. Consequential writes require `Finalized` plus `FINISHED_WITH_RETURN`.
4. **Resulting-state refresh.** After canonical success, the UI re-reads the covenant from Core instead of assuming the resulting state.
5. **Repair authorization bounds.** Provider identity, review generation, repair authorization, repair mask, freshness, provenance, and corroboration constraints remain contract-enforced.

The challenged path is:

```text
CHALLENGED
→ adjudicate
→ canonical finality
→ Core refresh
→ EVIDENCE_REPAIR_REQUIRED
→ provider submits authorized repair
→ canonical finality
→ Core refresh
→ CHALLENGED
→ adjudicate
→ settlement authorization
→ claimSettlement
```

## Architecture

| Component | Responsibility |
| --- | --- |
| `contracts/Accord402SettlementVault.sol` | Finality-bound GEN routing and registered payout recipients |
| `contracts/Accord402Registry.sol` | Frozen service policy, authorities, evidence history, replay, freshness, provenance, and repair validation |
| `contracts/Accord402Core.sol` | Escrow, covenant state machine, deadlines, accounting, retry/repair, and settlement |
| `contracts/Accord402Adjudicator.py` | GenLayer semantic review over a frozen Core/Registry snapshot and independently fetched evidence |
| `frontend/` | R150 Bradbury console with configuration validation, covenant creation/read, state-aware wallet actions, and exact-transaction finality observation |

`contracts/accord402.py` is historical/reference material and is not the current deployment artifact.

## Finality and settlement rule

Accord402 never infers settlement from an intermediate consensus label. Canonical transaction success requires both:

1. GenLayer consensus status `Finalized`.
2. Execution result `FINISHED_WITH_RETURN`.

The console continues observing the original transaction identity and never blindly replaces an uncertain write.

## Frontend behavior

The R150 console starts in a neutral state. It does **not** assume a pre-seeded covenant exists on the fresh R150 Core.

A reviewer can:

- open a new covenant;
- load an existing covenant number explicitly;
- use only actions allowed by the current on-chain state and connected wallet role;
- observe the exact submitted transaction until canonical completion;
- refresh the covenant from Core after canonical success.

Missing or inconsistent public configuration disables wallet actions instead of guessing deployment values.

## Reproduce the release checks

From the repository root:

```bash
forge build --root .
forge test --root .
python -m pytest -q
python -m py_compile contracts/Accord402Adjudicator.py contracts/accord402.py
genvm-lint check contracts/Accord402Adjudicator.py --json
```

Frontend:

```bash
cd frontend
npm ci
npm run check
```

Reviewer-specific R150 guards:

```bash
python -m pytest -q tests/test_r150_reviewer_workflow_guards.py
forge test --match-path tests/solidity/Accord402Core.t.sol
```

## Repository layout

```text
contracts/       EVM contracts and GenLayer adjudicator
frontend/        Next.js Bradbury console
tests/           Solidity, Python, security, direct-mode, and integration checks
docs/            Protocol, security, deployment, operations, and reviewer handoff
artifacts/       Frozen deployment/certification evidence
```

## Reviewer documentation

Start here:

- [`docs/SUBMISSION_HANDOFF_R150.md`](docs/SUBMISSION_HANDOFF_R150.md) — current R150 reviewer handoff.
- [`docs/BRADBURY_CANONICAL_DEPLOYMENT_R150.md`](docs/BRADBURY_CANONICAL_DEPLOYMENT_R150.md) — current R150 deployment and source binding.
- [`docs/R150_PREDEPLOYMENT_FREEZE.md`](docs/R150_PREDEPLOYMENT_FREEZE.md) — immutable predeployment source/bytecode freeze.
- [`docs/IMPLEMENTATION_V2_STATUS.md`](docs/IMPLEMENTATION_V2_STATUS.md) — current implementation and verification status.
- [`docs/REVIEWER_GATES_V1.md`](docs/REVIEWER_GATES_V1.md) — protocol reviewer gates.
- [`docs/OPERATIONS.md`](docs/OPERATIONS.md) — verification and operations runbook.
- [`artifacts/ACCORD402_R150_CERTIFICATION_V1.json`](artifacts/ACCORD402_R150_CERTIFICATION_V1.json) — machine-readable R150 certification anchors.

R149 and earlier records remain in the repository as **historical evidence only**. They are not the current deployment or submission reference.
