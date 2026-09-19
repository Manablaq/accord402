# Accord402

> **Security remediation candidate:** the current branch source has been hardened beyond the Bradbury addresses listed below. Those addresses remain historical evidence until this exact source passes local/CI size gates and a fresh canonical graph is deployed and certified.

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
| Bradbury V2 contract graph | Deployed |
| Local Solidity lifecycle/security suite | Passing (11 tests) |
| Python regression suite | Passing (75 tests) |
| GenLayer schema/linter checks | Passing |
| Bradbury lifecycle smoke run | Open → fund → accept → deliver → challenge completed |
| Bradbury adjudication | `AGREE / FINISHED_WITH_RETURN` observed |
| Production console | Live at [accord402.vercel.app](https://accord402.vercel.app) |
| Full settlement certification | Remaining: finalized recipient balance and duplicate-claim proof |

The last item is intentionally called out: an accepted or closed state is not
treated as proof of payment. Accord402 only reports canonical settlement after
the settlement transaction is finalized with `FINISHED_WITH_RETURN` and the
expected balance effects are verified.

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

The current hardened `contracts/Accord402Adjudicator.py` source
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

This profile is deployment-admission evidence for the exact hardened
Adjudicator source. It is **not** a Bradbury deployment or settlement
certification. The one-shot did not persist the exact Studio-dev transaction
ID or deployed contract address, so Accord402 does not claim an Explorer link
for that profiling deployment. The profiling authorization is consumed; no
second profiling deployment, retry, or rebroadcast is authorized.


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

This harness has not yet been executed for the current hardened release and
does not make the historical Bradbury graph current.

## Bradbury deployment

The current immutable dependency graph is:

- Settlement Vault: [`0xeECBE158401B932fec22e61dd0A336638D7A574a`](https://explorer-bradbury.genlayer.com/address/0xeECBE158401B932fec22e61dd0A336638D7A574a)
- Registry: [`0x5A622C41BAe12c4BFB1B6465af5ac1a3087497D7`](https://explorer-bradbury.genlayer.com/address/0x5A622C41BAe12c4BFB1B6465af5ac1a3087497D7)
- Adjudicator: [`0xEa6BB1a8Ed637cDF319455A718A18a449ACbe8c4`](https://explorer-bradbury.genlayer.com/address/0xEa6BB1a8Ed637cDF319455A718A18a449ACbe8c4)
- Core: [`0xA1a2125B3C7D03b868628B4C79832B33B7af4923`](https://explorer-bradbury.genlayer.com/address/0xA1a2125B3C7D03b868628B4C79832B33B7af4923)

The deployed graph is bound to the canonical Accord402 source fingerprint:

```text
d6f52562d0686ff213eb33773f201441f50f15a15190533306afd0a91ccf50c4
```

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
