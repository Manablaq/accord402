# Accord402 documentation

This directory is organized around three questions: how the protocol works,
what it guarantees, and how to operate or verify it.

## Start here

1. [`../README.md`](../README.md) — product overview, deployment addresses, quickstart, and current status.
2. [`OPERATIONS.md`](OPERATIONS.md) — local verification, frontend configuration, deployment, and live Bradbury checks.
3. [`IMPLEMENTATION_V2_STATUS.md`](IMPLEMENTATION_V2_STATUS.md) — implementation inventory and current verification status.
4. [`SUBMISSION_HANDOFF_R149.md`](SUBMISSION_HANDOFF_R149.md) — compact frozen R149 Project Explorer handoff and reviewer references.

## Current Bradbury R149 evidence

- [`BRADBURY_CANONICAL_DEPLOYMENT_V3.md`](BRADBURY_CANONICAL_DEPLOYMENT_V3.md) — current canonical R149 graph, source binding, and deployment provenance.
- [`BRADBURY_CURRENT_CORE_ECONOMIC_PROOF_V1.md`](BRADBURY_CURRENT_CORE_ECONOMIC_PROOF_V1.md) — live Covenant `1` non-delivery recovery, exact GEN consequence, conservation, Vault routing, and duplicate-claim rejection.
- [`../artifacts/CANONICAL_R149_CERTIFICATION_V1.json`](../artifacts/CANONICAL_R149_CERTIFICATION_V1.json) — machine-readable R149 certification.

Older V1/V2 deployment and amendment records remain append-only historical
evidence.

## Protocol design

- [`ARCHITECTURE_V2.md`](ARCHITECTURE_V2.md) — component boundaries and trust assumptions.
- [`SPEC_V1.md`](SPEC_V1.md) — protocol behavior and public semantics.
- [`STATE_MACHINE_V1.md`](STATE_MACHINE_V1.md) — covenant states, transitions, and authorization.
- [`STORAGE_AND_ABI_V1.md`](STORAGE_AND_ABI_V1.md) — storage and public ABI constraints.
- [`PUBLIC_ABI_V1.md`](PUBLIC_ABI_V1.md) — caller-facing method surface.
- [`INPUT_CAPS_V1.md`](INPUT_CAPS_V1.md) — frozen input and liveness limits.
- [`EVIDENCE_MODEL_V1.md`](EVIDENCE_MODEL_V1.md) — authority, provenance, freshness, replay, and repair semantics.
- [`ADJUDICATION_WIRE_V1.md`](ADJUDICATION_WIRE_V1.md) — canonical consensus input/output wire.
- [`HASH_PREIMAGES_V1.md`](HASH_PREIMAGES_V1.md) — hash-domain and preimage definitions.

## Security and review

- [`THREAT_MODEL_V1.md`](THREAT_MODEL_V1.md) — assets, adversaries, and assumptions.
- [`SETTLEMENT_INVARIANTS_V1.md`](SETTLEMENT_INVARIANTS_V1.md) — escrow, payout, finality, and replay invariants.
- [`REVIEWER_GATES_V1.md`](REVIEWER_GATES_V1.md) — reviewer-facing acceptance checklist.
- [`SECURITY_HARDENING_V2.md`](SECURITY_HARDENING_V2.md) through [`SECURITY_HARDENING_V5.md`](SECURITY_HARDENING_V5.md) — hardening amendments and their rationale.

## Compatibility and evidence

- [`TOOLCHAIN_V1.md`](TOOLCHAIN_V1.md) — pinned build and test assumptions.
- [`VERIFIED_GENLAYER_BASELINE.md`](VERIFIED_GENLAYER_BASELINE.md) — verified GenLayer baseline.
- `../artifacts/bradbury-deployment/` — deployment manifests, source freezes, runtime probes, and live-test evidence.

The amendment documents are append-only historical records. When an amendment
supersedes an earlier statement, follow the newest applicable amendment and the
implementation status document.
