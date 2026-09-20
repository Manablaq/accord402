# Accord402

> **Canonical Bradbury release:** R149 source release `ebfe5ce3be305de360bcf86dde05c55936f8b637` / tree `0694e768890cb17e4eb32f014ab0b4ae6ee24e7b` is the current four-component graph. The current Core has a live Covenant `1` non-delivery recovery proof with exact `0.01 GEN` buyer settlement, zero remaining Core balance, Vault delivery recorded, and duplicate-claim rejection. Production frontend rebinding to R149 remains a separate publication gate.

**Proof-bound service agreements for agent-to-agent commerce.**

Accord402 is a GenLayer-native warranty protocol for autonomous services. A
buyer funds a covenant, a provider delivers against explicit criteria, and
approved evidence is reviewed before settlement. Deterministic escrow,
policy, provenance, deadlines, and accounting stay on the EVM contracts; the
one semantic operation—reviewing disputed delivery—runs through a narrow
GenLayer Intelligent Contract.

## Status

| Surface | Status |
| --- | --- |
| Bradbury R149 canonical graph | Deployed, dependency-bound, and live re-certified |
| Local Solidity lifecycle/security suite | Passing (11 tests) |
| Python regression suite | Passing (75 tests) |
| GenLayer schema/linter checks | Passing |
| Current R149 Core recovery case | Open/fund → accept → non-delivery expiry → buyer claim completed |
| Canonical Bradbury Adjudicator deployment | `FINALIZED / AGREE / FINISHED_WITH_RETURN` |
| Production console | Stable URL live at [accord402.vercel.app](https://accord402.vercel.app); R149 environment rebinding/redeploy pending |
| Current Core economic recovery certification | Complete: exact recipient delta, conservation, Vault routing, and duplicate-claim proof |

Accord402 does not infer payment from a state label alone. The current R149
recovery case binds successful transaction receipts to an exact
`10000000000000000`-wei payout delta, zero final Core balance, accounting
conservation, Vault routing, and a rejected duplicate claim. GenLayer
Adjudicator deployment finality remains independently bound to finalized
consensus and `FINISHED_WITH_RETURN`.

## Architecture

The V2 graph is split so deterministic money movement and policy enforcement
remain auditable and deployable under Bradbury limits.

| Component | Responsibility |
| --- | --- |
| `contracts/Accord402SettlementVault.sol` | Finality-bound GEN routing and registered payout recipients |
| `contracts/Accord402Registry.sol` | Frozen service policy, authorities, evidence history, replay, freshness, and source-origin checks |
| `contracts/Accord402Core.sol` | Escrow, covenant state machine, deadlines, accounting, retry/repair, and finality-gated settlement |
| `contracts/Accord402Adjudicator.py` | Narrow GenLayer consensus review over a frozen snapshot and independently fetched evidence |
| `frontend/` | Read/write Bradbury console with configuration validation, wallet actions, live covenant reads, and transaction-finality observation |

`contracts/accord402.py` is retained as historical/reference material. It is
not the V2 deployment artifact.

## Studio-dev finalized deployment fee profile

An earlier hardened `contracts/Accord402Adjudicator.py` source
(`4e3d3fabce4563f660eb10b4328b805c1cbeea92f83ecd047add00f1b01a1775`)
was profiled exactly once on GenLayer `studio_devnet` (chain `61997`) with
`genlayer-py 0.19.0rc2` and `genlayer-test 0.30.0rc2`. The frozen test used
live fee estimation, explicit deployment fees, and `wait_until="finalized"`.

The measured deployment recommendation is:

- `leaderTimeunitsAllocation`: `125`
- `validatorTimeunitsAllocation`: `250`
- `executionBudgetPerRound`: `98466250000000`
- `totalMessageFees`: `0`
- `rotationsPerRound`: `3`

Canonical evidence is frozen in
[`artifacts/ACCORD402_STUDIO_DEVNET_DEPLOY_FEE_PROFILE_V1.json`](artifacts/ACCORD402_STUDIO_DEVNET_DEPLOY_FEE_PROFILE_V1.json)
with SHA-256 `a9a120391392f5e66c6d9008d7a50c474d76e9bea7f1cfdfcee0d60a4fd16f02`.

This profile is historical deployment-admission evidence for that earlier
Adjudicator source. It is **not** the canonical Bradbury deployment or
settlement certification. That `9237e89878c74cb3ab3d71986d16aaf4c2f0cda3104b17a81ce79088d8f195a3`
source belongs to the superseded V2 deployment record. The current R149
Adjudicator source is `575e063661cc12a5de18dfa67ab3fbeb38bee1028694a08021efbc300115c198` and is bound to the V3 graph below.
The Studio-dev one-shot did not persist the exact transaction ID or deployed
contract address, so Accord402 does not claim an Explorer link for that
profiling deployment. The profiling authorization is consumed; no second
profiling deployment, retry, or rebroadcast is authorized.


## Reproducible Bradbury runtime integration

The repository now contains a guarded supported-runtime deployment harness for
the exact hardened Adjudicator source:

- tracked safe-default configuration: [`gltest.config.yaml`](gltest.config.yaml);
- live test: [`tests/integration/test_accord402_adjudicator_bradbury_runtime.py`](tests/integration/test_accord402_adjudicator_bradbury_runtime.py);
- one-shot guarded runner: [`scripts/run_bradbury_runtime_integration.sh`](scripts/run_bradbury_runtime_integration.sh);
- evidence and authorization boundary: [`docs/BRADBURY_RUNTIME_INTEGRATION_V1.md`](docs/BRADBURY_RUNTIME_INTEGRATION_V1.md);
- baseline/RC2/Foundry role reconciliation: [`docs/TOOLCHAIN_RELEASE_RECONCILIATION_V1.md`](docs/TOOLCHAIN_RELEASE_RECONCILIATION_V1.md).

The tracked configuration contains **no Bradbury signing account** and keeps
`localnet` as the default. The live test is skipped unless the guarded runner
sets a fresh explicit authorization gate. A live run persists the submitted
GenLayer transaction ID before finality polling, waits for exact `Finalized`,
requires successful GenVM execution, and persists the resulting contract
address and finalized receipt.

This tracked harness has not yet been executed for the current hardened
release and remains a separate supported-runtime certification gate. The
canonical graph below was deployed and independently audited through the
guarded release-deployment path; that does not substitute for executing this
specific reproducibility harness.

## Current canonical Bradbury deployment — R149

The current Bradbury graph is:

| Component | Canonical address | Provenance |
| --- | --- | --- |
| Settlement Vault | `0xFCc7FbE2243c32ff35cE74055695Bf8C23E17dD5` | reused verified V2 deployment |
| Registry | `0x5BD6f9EEBF7BE527321ED46649447c59fAc5315C` | reused verified V2 deployment |
| Adjudicator | `0x9b204786e4641EbFF5D771a08624e2B0849Fcc56` | R149 GenLayer deployment |
| Core | `0xE315df22c15753D07a2FDb72b15B3AeAF4D27E2A` | R149 EVM deployment |

Current source SHA-256 values:

- SettlementVault: `e966518dac38ba95df3ff06f7a319bcd97b823a3e36d019003b45ee4a4fe6cd6`
- Registry: `bac515e32c8e4a56073b412079995c8bf64ace94274314a491b2dbe411ea35ae`
- Adjudicator: `575e063661cc12a5de18dfa67ab3fbeb38bee1028694a08021efbc300115c198`
- Core: `ee8d58f6693c16c22eb610140570e0c92a0c923482f154e886f9ae25a7d3c289`

Current Covenant `1` reviewer-case transactions:

- open/fund: `0x7b45999ab31e82e941d25712be32770c7fd4f3d66b1e3ab938d591c93f5ca9cd`
- provider acceptance: `0xaa010bd94bdd93ae2c9dc185174aba92a931a3609c1d6ef07bbb6783da8a98f3`
- non-delivery expiry: `0x1219914b612f60c439953be4818702d7e081167535e0bdc62c0ac86c87de3740`
- settlement claim: `0x18197505652f86fc21ad1a926e8e5220a5a518b9673c97468c5fbbd3a151c77b`

Final state is `CLOSED_BUYER`; accounting is
`10000000000000000|0|10000000000000000|0`; Core native balance is `0`; the registered
payout received exactly `10000000000000000` wei; the Vault delivery bit is true; and
a duplicate claim is rejected.

See
[`docs/BRADBURY_CANONICAL_DEPLOYMENT_V3.md`](docs/BRADBURY_CANONICAL_DEPLOYMENT_V3.md)
and
[`docs/BRADBURY_CURRENT_CORE_ECONOMIC_PROOF_V1.md`](docs/BRADBURY_CURRENT_CORE_ECONOMIC_PROOF_V1.md).

## Historical Bradbury V2 deployment — superseded by R149

The hardened V2 release is deployed on Bradbury chain `4221` as one immutable
four-component dependency graph:

| Component | Canonical address | Deployment evidence |
| --- | --- | --- |
| Settlement Vault | [`0xFCc7FbE2243c32ff35cE74055695Bf8C23E17dD5`](https://explorer-bradbury.genlayer.com/address/0xFCc7FbE2243c32ff35cE74055695Bf8C23E17dD5) | EVM tx [`0xa478daf9a3a280214eb70592ffcd98cb7c4590fc044236fbaf4bf9df5537ffb7`](https://explorer-bradbury.genlayer.com/tx/0xa478daf9a3a280214eb70592ffcd98cb7c4590fc044236fbaf4bf9df5537ffb7) |
| Registry | [`0x5BD6f9EEBF7BE527321ED46649447c59fAc5315C`](https://explorer-bradbury.genlayer.com/address/0x5BD6f9EEBF7BE527321ED46649447c59fAc5315C) | EVM tx [`0xe8ebf7abdf511e2aaebfda13cb0fab9a6d2e881e785eeb969e0a30ec63007608`](https://explorer-bradbury.genlayer.com/tx/0xe8ebf7abdf511e2aaebfda13cb0fab9a6d2e881e785eeb969e0a30ec63007608) |
| Adjudicator | [`0x5c958e498C3109922AFAc661EB466628Fe521CB6`](https://explorer-bradbury.genlayer.com/address/0x5c958e498C3109922AFAc661EB466628Fe521CB6) | GenLayer tx [`0x202b98d47307c95098e00f410f351db86f904358651de03ba8b7d55b8d620f38`](https://explorer-bradbury.genlayer.com/transactions/0x202b98d47307c95098e00f410f351db86f904358651de03ba8b7d55b8d620f38) |
| Core | [`0x3eA9E19531a59BA31C2E4f396Ab2b0256304e835`](https://explorer-bradbury.genlayer.com/address/0x3eA9E19531a59BA31C2E4f396Ab2b0256304e835) | EVM tx [`0x86d5c73db9388b0df8de4753cf5c06751c3f6ec3b7fdfcdd60c1f4cb225e116e`](https://explorer-bradbury.genlayer.com/tx/0x86d5c73db9388b0df8de4753cf5c06751c3f6ec3b7fdfcdd60c1f4cb225e116e) |

The Adjudicator outer EVM submission is `0x6ceef29669a2d888c22455555735352315bcdcf0274164f9b2307378e7421a50`. Its GenLayer
transaction is `FINALIZED`, consensus result `AGREE`, and execution result
`FINISHED_WITH_RETURN`.

The live graph is bound to release commit `2c025294c66ade0c54b6d494bd5136490b9d1b3c` and tree
`5de6c7a50c3ec7568cf4b6bce54383b51fd7b5df`. Exact component source SHA-256 values are:

```text
SettlementVault  e966518dac38ba95df3ff06f7a319bcd97b823a3e36d019003b45ee4a4fe6cd6
Registry         bac515e32c8e4a56073b412079995c8bf64ace94274314a491b2dbe411ea35ae
Adjudicator      9237e89878c74cb3ab3d71986d16aaf4c2f0cda3104b17a81ce79088d8f195a3
Core             ee8d58f6693c16c22eb610140570e0c92a0c923482f154e886f9ae25a7d3c289
```

Independent read-only deployment evidence re-verified Vault/Registry runtime
parity, exact frozen Core creation input, predicted Core address, non-empty
Core runtime code, Core dependency getters, Adjudicator finality/execution,
and zero reuse of the failed partial-deployment addresses.

See [`docs/BRADBURY_CANONICAL_DEPLOYMENT_V2.md`](docs/BRADBURY_CANONICAL_DEPLOYMENT_V2.md)
and [`artifacts/ACCORD402_BRADBURY_CANONICAL_DEPLOYMENT_V2.json`](artifacts/ACCORD402_BRADBURY_CANONICAL_DEPLOYMENT_V2.json).

This deployment evidence does **not** claim the remaining settlement
recipient-balance, duplicate-claim, recovery/expiry, frontend-E2E, or final
reviewer-certification gates are complete.

## Repository layout

```text
contracts/       Solidity contracts and the GenLayer adjudicator
frontend/        Next.js Bradbury console
tests/           Python hash/vector and compatibility tests
docs/            Protocol, security, architecture, and operations documentation
artifacts/       Deployment evidence, source freezes, and certification records
foundry.toml     Pinned Solidity toolchain and optimizer profile
```

## Local verification

From the repository root:

```bash
forge build --root .
forge test --root .
python -m py_compile contracts/Accord402Adjudicator.py
genvm-lint check contracts/Accord402Adjudicator.py --json
```

For the production console:

```bash
cd frontend
npm ci
npm run check
npm run dev
```

The frontend requires every variable in [`frontend/.env.example`](frontend/.env.example).
It has no deployment-value fallbacks: missing or inconsistent values disable
wallet actions and display a configuration error instead of sending a
transaction. All frontend variables are public chain/configuration values;
wallet keys, issuer private keys, and Vercel credentials must never be placed
in the frontend environment.

## Lifecycle and finality

The normal covenant path is:

```text
open/fund → provider accepts → provider delivers evidence
→ buyer may challenge → GenLayer review → retry/repair or settlement
```

The console observes the exact transaction identity supplied by the user. It
does not replace an uncertain write with a new write, and it does not call an
accepted transaction settled. Canonical success requires both:

1. Bradbury transaction status `Finalized`.
2. Execution result `FINISHED_WITH_RETURN`.

See [`docs/STATE_MACHINE_V1.md`](docs/STATE_MACHINE_V1.md) for transitions and
[`docs/SETTLEMENT_INVARIANTS_V1.md`](docs/SETTLEMENT_INVARIANTS_V1.md) for the
economic and finality requirements.

## Documentation

Start with [`docs/README.md`](docs/README.md), then use the operational guide
for local checks, deployment, live reads, and evidence capture:

- [`docs/BRADBURY_CANONICAL_DEPLOYMENT_V3.md`](docs/BRADBURY_CANONICAL_DEPLOYMENT_V3.md) — current R149 Bradbury graph and source binding
- [`docs/BRADBURY_CURRENT_CORE_ECONOMIC_PROOF_V1.md`](docs/BRADBURY_CURRENT_CORE_ECONOMIC_PROOF_V1.md) — current Core non-delivery economic proof
- [`docs/OPERATIONS.md`](docs/OPERATIONS.md) — contributor and deployment runbook
- [`docs/ARCHITECTURE_V2.md`](docs/ARCHITECTURE_V2.md) — system boundaries and trust model
- [`docs/IMPLEMENTATION_V2_STATUS.md`](docs/IMPLEMENTATION_V2_STATUS.md) — implementation and verification status
- [`docs/REVIEWER_GATES_V1.md`](docs/REVIEWER_GATES_V1.md) — reviewer-facing acceptance gates
- [`docs/THREAT_MODEL_V1.md`](docs/THREAT_MODEL_V1.md) — threat model and security assumptions
- [`docs/STATE_MACHINE_V1.md`](docs/STATE_MACHINE_V1.md) — covenant state transitions
- [`docs/SETTLEMENT_INVARIANTS_V1.md`](docs/SETTLEMENT_INVARIANTS_V1.md) — settlement correctness and finality

Deployment evidence is preserved under `artifacts/bradbury-deployment/`. Do
not edit evidence files by hand; regenerate them from the documented command
or test that produced them.
