# Accord402 documentation

The current reviewer release is **R150**. Use the R150 handoff and deployment record first; older release documents are preserved only as historical evidence.

## Start here

1. [`SUBMISSION_HANDOFF_R150.md`](SUBMISSION_HANDOFF_R150.md) — current reviewer/resubmission handoff.
2. [`BRADBURY_CANONICAL_DEPLOYMENT_R150.md`](BRADBURY_CANONICAL_DEPLOYMENT_R150.md) — current Bradbury R150 deployment and source binding.
3. [`R150_PREDEPLOYMENT_FREEZE.md`](R150_PREDEPLOYMENT_FREEZE.md) — immutable R150 source/bytecode freeze recorded before deployment.
4. [`IMPLEMENTATION_V2_STATUS.md`](IMPLEMENTATION_V2_STATUS.md) — implementation and verification status.
5. [`OPERATIONS.md`](OPERATIONS.md) — local verification, frontend configuration, and Bradbury operations.

## Current R150 reviewer evidence

- R150 implementation commit: `7dde8f45ae88db996895c02883c951d6350cf48c`
- R150 implementation tree: `aa7f6129ce74e75c7e0405d482278568c127f100`
- Core: `0x142b20B20a24F659e1053A504c23fF48832c090f`
- Core deployment tx: `0x750577a17692ba91471d9821befd2c858ac06eaf7a94a80a71e866bd59757bf6`
- GitHub Actions verify run: `35683293916` — success
- production: [accord402.vercel.app](https://accord402.vercel.app)
- machine-readable certification: [`../artifacts/ACCORD402_R150_CERTIFICATION_V1.json`](../artifacts/ACCORD402_R150_CERTIFICATION_V1.json)

## Protocol design

- [`ARCHITECTURE_V2.md`](ARCHITECTURE_V2.md)
- [`SPEC_V1.md`](SPEC_V1.md)
- [`STATE_MACHINE_V1.md`](STATE_MACHINE_V1.md)
- [`STORAGE_AND_ABI_V1.md`](STORAGE_AND_ABI_V1.md)
- [`PUBLIC_ABI_V1.md`](PUBLIC_ABI_V1.md)
- [`INPUT_CAPS_V1.md`](INPUT_CAPS_V1.md)
- [`EVIDENCE_MODEL_V1.md`](EVIDENCE_MODEL_V1.md)
- [`ADJUDICATION_WIRE_V1.md`](ADJUDICATION_WIRE_V1.md)
- [`HASH_PREIMAGES_V1.md`](HASH_PREIMAGES_V1.md)

## Security and review

- [`THREAT_MODEL_V1.md`](THREAT_MODEL_V1.md)
- [`SETTLEMENT_INVARIANTS_V1.md`](SETTLEMENT_INVARIANTS_V1.md)
- [`REVIEWER_GATES_V1.md`](REVIEWER_GATES_V1.md)
- Security-hardening amendments remain append-only historical design records.

## Historical release evidence

- [`SUBMISSION_HANDOFF_R149.md`](SUBMISSION_HANDOFF_R149.md) — historical R149 submission snapshot.
- [`BRADBURY_CANONICAL_DEPLOYMENT_V3.md`](BRADBURY_CANONICAL_DEPLOYMENT_V3.md) — historical R149 graph.
- [`BRADBURY_CURRENT_CORE_ECONOMIC_PROOF_V1.md`](BRADBURY_CURRENT_CORE_ECONOMIC_PROOF_V1.md) — historical R149 Covenant 1 economic proof.

Historical evidence is intentionally preserved and must not be read as the current R150 deployment.
