# Accord402 V2 implementation status

**Status: Bradbury graph deployed; production console live; final settlement certification remains.**

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
