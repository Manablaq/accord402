# Accord402 V2 implementation status

**Status: R149 CURRENT CANONICAL GRAPH, NON-DELIVERY BUYER-RECOVERY ECONOMIC PROOF, PUBLICATION, AND PRODUCTION R149 FRONTEND REBINDING/E2E ARE COMPLETE. The guarded supported-runtime deployment harness remains available as supplemental reproducibility evidence if explicitly requested; it has not been executed for this release. Final reviewer audit and submission handoff remain.**

Security Hardening V6 binds the exact Core and Registry adjudication snapshots into the finalized callback, eliminating the single-RPC semantic-substitution boundary.

Branch: `refactor/hybrid-architecture-v1`

Exact current R149 deployed source binding:

- SettlementVault SHA-256: `e966518dac38ba95df3ff06f7a319bcd97b823a3e36d019003b45ee4a4fe6cd6`
- Registry SHA-256: `bac515e32c8e4a56073b412079995c8bf64ace94274314a491b2dbe411ea35ae`
- Adjudicator SHA-256: `575e063661cc12a5de18dfa67ab3fbeb38bee1028694a08021efbc300115c198`
- Core SHA-256: `ee8d58f6693c16c22eb610140570e0c92a0c923482f154e886f9ae25a7d3c289`

## R149 current canonical release

- source release commit: `ebfe5ce3be305de360bcf86dde05c55936f8b637`
- source release tree: `0694e768890cb17e4eb32f014ab0b4ae6ee24e7b`
- Bradbury chain ID: `4221`
- SettlementVault: `0xFCc7FbE2243c32ff35cE74055695Bf8C23E17dD5`
- Registry: `0x5BD6f9EEBF7BE527321ED46649447c59fAc5315C`
- Adjudicator: `0x9b204786e4641EbFF5D771a08624e2B0849Fcc56`
- Core: `0xE315df22c15753D07a2FDb72b15B3AeAF4D27E2A`

Current Covenant `1` proof:

- principal: `10000000000000000` wei
- isolated buyer: `0x67a6F6dD67E7DffEcD760a99b4D5A2fe019EbA4f`
- isolated provider: `0x64f332ba2ED3F7372fF3FE3d777Ad01fbd3195a4`
- registered payout: `0x1f87Ae197af539253978d435aD45cCf28Fb95024`
- open: `0x7b45999ab31e82e941d25712be32770c7fd4f3d66b1e3ab938d591c93f5ca9cd`
- accept: `0xaa010bd94bdd93ae2c9dc185174aba92a931a3609c1d6ef07bbb6783da8a98f3`
- expire non-delivery: `0x1219914b612f60c439953be4818702d7e081167535e0bdc62c0ac86c87de3740`
- claim settlement: `0x18197505652f86fc21ad1a926e8e5220a5a518b9673c97468c5fbbd3a151c77b`
- final state: `CLOSED_BUYER`
- accounting: `10000000000000000|0|10000000000000000|0`
- Core balance: `0`
- payout delta: `10000000000000000` wei
- Vault delivery bit: `true`
- duplicate claim: rejected

This case proves the current Core non-delivery liveness and buyer-recovery
economic path. It does not claim that Covenant `1` exercised delivery,
challenge, repair/retry, or semantic adjudication.

See `BRADBURY_CANONICAL_DEPLOYMENT_V3.md` and
`BRADBURY_CURRENT_CORE_ECONOMIC_PROOF_V1.md`.

## Implemented

- deterministic Registry, Core, and SettlementVault contracts;
- immutable constructor binding between Registry, Adjudicator, Core, and Vault;
- exact native GEN funding and global/per-covenant accounting;
- provider acceptance and evidence delivery;
- buyer challenge with ordered criterion binding;
- unchallenged settlement and bounded non-delivery/unaccepted expiry;
- finality-only Adjudicator callback with hash and generation binding;
- evidence replay protection scoped by covenant;
- approved-authority identity and canonical-origin enforcement;
- freshness, expiry, immutable/versioned source, digest, and corroboration checks;
- explicit repair masks that cannot mutate delivery, policy, or payout fields;
- retry and repair generation limits with an absolute dispute deadline;
- strict canonical adjudication wire and independent validator recomputation;
- GenLayer schema validation and legacy-runner compatibility probing;
- Bradbury Adjudicator deployment with `AGREE` and `FINISHED_WITH_RETURN` observed;
- Bradbury Core deployment with live immutable dependency verification;
- live Core/Registry reads from a newly opened covenant;
- live Bradbury open/fund/accept/deliver/challenge lifecycle smoke run;
- production Next.js console with configuration validation, live covenant reads,
  wallet actions, and exact-transaction finality observation;
- Vercel production deployment at [accord402.vercel.app](https://accord402.vercel.app).

## Studio-dev deployment fee profile

A one-shot finalized deployment profile has been measured for the exact current
hardened Adjudicator source SHA-256
`4e3d3fabce4563f660eb10b4328b805c1cbeea92f83ecd047add00f1b01a1775`.

- network: `studio_devnet`;
- chain ID: `61997`;
- toolchain: `genlayer-py 0.19.0rc2`, `genlayer-test 0.30.0rc2`,
  Python `3.12.14`;
- live fee estimation: yes;
- explicit deployment fees: yes;
- finality requirement: `wait_until="finalized"`;
- wait retries: `240`;
- measured deploy values: leader `125`, validator `250`,
  execution budget per round `98466250000000`, total message fees `0`,
  rotations per round `3`;
- source fee-profile SHA-256:
  `d461023eff9e6cc8ca35bf09482e7084c9559163bb429a589c82a27dcfe0693b`;
- canonical repository artifact:
  `artifacts/ACCORD402_STUDIO_DEVNET_DEPLOY_FEE_PROFILE_V1.json`;
- canonical artifact SHA-256: `a9a120391392f5e66c6d9008d7a50c474d76e9bea7f1cfdfcee0d60a4fd16f02`.

The test completed only after the RC2 finalization waiter returned a stored
`finalized` lifecycle, and the deploy observation was then derived from that
returned receipt. The exact Studio-dev transaction ID and deployed contract
address were not persisted. That provenance limitation is recorded explicitly;
no transaction hash, contract address, or Explorer link is inferred.

This result remains deployment-admission evidence only and does not itself
certify Bradbury. Since that profile was recorded, the hardened V2 graph at
release commit `2c025294c66ade0c54b6d494bd5136490b9d1b3c` / tree `5de6c7a50c3ec7568cf4b6bce54383b51fd7b5df` has been freshly
deployed on Bradbury and independently audited. Canonical deployment finality
is therefore complete; live settlement consequence and reviewer certification
remain separate gates.

## Historical Bradbury V2 deployment (2026-09-19; superseded by R149)

- SettlementVault: `0xFCc7FbE2243c32ff35cE74055695Bf8C23E17dD5` — EVM tx `0xa478daf9a3a280214eb70592ffcd98cb7c4590fc044236fbaf4bf9df5537ffb7`;
- Registry: `0x5BD6f9EEBF7BE527321ED46649447c59fAc5315C` — EVM tx `0xe8ebf7abdf511e2aaebfda13cb0fab9a6d2e881e785eeb969e0a30ec63007608`;
- Adjudicator: `0x5c958e498C3109922AFAc661EB466628Fe521CB6` — GenLayer tx `0x202b98d47307c95098e00f410f351db86f904358651de03ba8b7d55b8d620f38`;
- Core: `0x3eA9E19531a59BA31C2E4f396Ab2b0256304e835` — EVM tx `0x86d5c73db9388b0df8de4753cf5c06751c3f6ec3b7fdfcdd60c1f4cb225e116e`;
- Adjudicator result: `FINALIZED / AGREE / FINISHED_WITH_RETURN`;
- Core creation input: exact frozen init bytecode plus bound
  Registry/Adjudicator/SettlementVault constructor values;
- Core dependency getters: exact match to the canonical Registry,
  Adjudicator, and SettlementVault;
- old failed partial-deployment address reuse: none.

Reviewer-facing details and source bindings are frozen in
[`BRADBURY_CANONICAL_DEPLOYMENT_V2.md`](BRADBURY_CANONICAL_DEPLOYMENT_V2.md)
and
[`../artifacts/ACCORD402_BRADBURY_CANONICAL_DEPLOYMENT_V2.json`](../artifacts/ACCORD402_BRADBURY_CANONICAL_DEPLOYMENT_V2.json).

## Verification completed

- Solidity build: pass;
- Solidity lifecycle/security tests: 17 passed;
- existing Python regression suite: 95 passed, 1 skipped;
- `py_compile` for the adjudicator and historical contract: pass;
- GenLayer linter/schema validation: pass;
- Registry/Core deployment-size measurement under the pinned optimizer/via-IR
  profile: pass;
- frontend typecheck and production build: pass;
- live production R149 homepage binding, Covenant `1` API route, and exact-transaction finality observer: pass.

Measured local runtime bytecode for the current graph: SettlementVault `1,231`
bytes, Registry `23,429` bytes, and Core `22,304` bytes. Core remains below
the EIP-170 limit by 2,272 bytes under the pinned optimizer/via-IR profile.

## Remaining publication and reviewer-readiness gates

The R149 graph deployment, current Core non-delivery recovery economic proof,
publication with green CI, production R149 environment binding, stable
`accord402.vercel.app` alias, and production homepage/API/finality-observer
E2E are complete.

The remaining release work is:

1. complete the final regression/evidence/reviewer-readiness audit; and
2. prepare the compact reviewer submission handoff.

The guarded supported-runtime Bradbury deployment harness remains tracked as
supplemental reproducibility evidence if a reviewer explicitly requests that
specific harness. It has not been executed for R149, and this status document
does not authorize an additional Bradbury write.

The live review-retry path is implemented and observable. `REVIEW_RETRY_REQUIRED`
is a non-economic intermediate state, not a payout failure or a claim that a
settlement already occurred. See [`OPERATIONS.md`](OPERATIONS.md) for the exact
evidence sequence required to close these gates.


Core size remediation removes only the redundant aggregate `getReviewHashes()` view; the four individual hash getters and all settlement/adjudication semantics remain unchanged.

Core bytecode compaction also removes the legacy string wrappers `getServiceSpecHashHex()` and `getDeliveryHashHex()`. The canonical `bytes32` getters remain, and finalized adjudication is bound to the stronger full Core/Registry snapshot hashes defined by Security Hardening V6.

## Reproducible Bradbury runtime integration

A guarded Bradbury runtime deployment test is now part of the release
candidate:

- `gltest.config.yaml` is secret-free, explicitly retains preconfigured `localnet`, and defaults to local execution;
- `tests/integration/test_accord402_adjudicator_bradbury_runtime.py` is skipped
  unless a fresh live-write authorization gate is supplied;
- `scripts/run_bradbury_runtime_integration.sh` requires a clean immutable
  release commit, exact source hash, explicit Registry address, private key in
  process environment, and a one-shot authorization ID;
- the live test persists the GenLayer transaction ID before finality polling,
  waits for exact `FINALIZED`, requires execution success, and persists the
  deployed address plus finalized receipt.

The harness has **not** been executed for the current hardened release. It is
retained as supplemental supported-runtime reproducibility evidence if a
reviewer explicitly requests that specific harness. The canonical R149
Bradbury graph deployment, current non-delivery recovery and exact
balance-consequence proof, and production R149 rebinding/E2E are complete.
Final reviewer audit and submission handoff remain. No additional Bradbury
write is authorized by this documentation update.
