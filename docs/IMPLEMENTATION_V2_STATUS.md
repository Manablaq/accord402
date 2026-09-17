# Accord402 V2 Implementation Status

Status: **BUNDLE GRAPH DEPLOYED — ADJUDICATION ACCEPTED, BRADBURY FINALIZATION PENDING**

Branch: `refactor/hybrid-architecture-v1`

Base checkpoint: `a534591b8a88d5ad8f00b70de2339ffe6bd00948`

## Implemented

- deterministic Registry and Core contracts;
- immutable constructor binding between Registry, Adjudicator, Core, and the
  fresh SettlementVault;
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
- GenLayer schema validation and legacy-runner compatibility probe;
- Bradbury Adjudicator deployment with `AGREE` consensus and
  `FINISHED_WITH_RETURN` execution;
- Bradbury Core deployment with live immutable dependency verification;
- live Core/Registry compact-bundle reads on a newly opened covenant;
- live funding, acceptance, timestamp-exact delivery, and buyer challenge on
  Bradbury;
- live corrected adjudication with all five validators agreeing on the exact
  wire result.

## Verification completed

- Solidity build: pass;
- Solidity lifecycle/security tests: 11 passed;
- existing Python regression suite: 75 passed;
- `py_compile` for the adjudicator and historical contract: pass;
- GenLayer linter/schema validation: pass;
- Registry/Core deployment-size measurement under the pinned optimizer/via-IR
  profile: pass.

Measured local runtime bytecode for the current graph: SettlementVault `1,231`
bytes, Registry `23,074` bytes, and Core `24,243` bytes. Core remains below the
EIP-170 limit by 334 bytes under the pinned optimizer/via-IR profile.

## Remaining hard gates

The fresh SettlementVault is live at
`0xeECBE158401B932fec22e61dd0A336638D7A574a`. The current Registry,
Adjudicator, and Core are live at `0x5A622C41BAe12c4BFB1B6465af5ac1a3087497D7`,
`0xEa6BB1a8Ed637cDF319455A718A18a449ACbe8c4`, and
`0xA1a2125B3C7D03b868628B4C79832B33B7af4923`. Deployment and live-test
evidence is recorded under `artifacts/bradbury-deployment/`.

The adjudication transaction is accepted and waiting for Bradbury’s protocol
finalization window. Core will remain `CHALLENGED` until the emitted callback
is finalized and processed; the accepted transaction and callback payload are
recorded in the deployment manifest. Frontend integration remains deferred by
design.
