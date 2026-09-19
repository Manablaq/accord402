# Accord402 V2 implementation status

**Status: SECURITY REMEDIATION CANDIDATE — current deployed graph is historical until the hardened source is recompiled, size-certified, redeployed, finalized, and live-certified.**

Security Hardening V6 binds the exact Core and Registry adjudication snapshots into the finalized callback, eliminating the single-RPC semantic-substitution boundary.

Branch: `refactor/hybrid-architecture-v1`

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

This result is deployment-admission evidence only. It does not make the
historical Bradbury graph current, and fresh Bradbury deployment, finality,
live settlement, and reviewer certification remain separate gates.

## Verification completed

- Solidity build: pass;
- Solidity lifecycle/security tests: 11 passed;
- existing Python regression suite: 75 passed;
- `py_compile` for the adjudicator and historical contract: pass;
- GenLayer linter/schema validation: pass;
- Registry/Core deployment-size measurement under the pinned optimizer/via-IR
  profile: pass;
- frontend typecheck and production build: pass;
- live production homepage, covenant API route, and browser smoke check: pass.

Measured local runtime bytecode for the current graph: SettlementVault `1,231`
bytes, Registry `23,074` bytes, and Core `24,243` bytes. Core remains below
the EIP-170 limit by 334 bytes under the pinned optimizer/via-IR profile.

## Remaining certification gates

The following are intentionally not marked complete until fresh Bradbury
evidence exists for the exact deployed graph:

1. A settlement authorization transaction finalized with
   `FINISHED_WITH_RETURN`.
2. The expected recipient GEN balance delta and corresponding protocol
   accounting delta.
3. A repeated settlement attempt that proves duplicate-claim resistance.
4. Recovery/expiry paths exercised with finalized balance outcomes.

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

The harness has **not** been executed for the current hardened release. It
does not certify a fresh Bradbury graph, settlement, repair/recovery, balance
consequence, frontend E2E, or reviewer completion. Those remain live release
gates.
