# Accord402 Bradbury Runtime Integration V1

Status: reproducible live-runtime harness present; **not yet executed for the
current hardened release**.

## Network binding

The harness is bound to current GenLayer Bradbury:

- network: `testnet_bradbury`
- chain ID: `4221`
- GenLayer RPC: `https://rpc-bradbury.genlayer.com`
- explorer: `https://explorer-bradbury.genlayer.com`
- exact Adjudicator source SHA-256:
  `9237e89878c74cb3ab3d71986d16aaf4c2f0cda3104b17a81ce79088d8f195a3`

The tracked `gltest.config.yaml` intentionally contains no signing account.
It explicitly retains the pinned suite's preconfigured `localnet` entry and
keeps `localnet` as the default, so ordinary repository pytest execution
does not acquire a Bradbury key and cannot silently become a Bradbury write.

## What the live test proves

`tests/integration/test_accord402_adjudicator_bradbury_runtime.py` provides a
supported-runtime deployment test for the exact hardened Adjudicator source.

When, and only when, the guarded live runner is explicitly authorized, it:

1. verifies the repository is an immutable clean Git commit;
2. verifies the exact Adjudicator source SHA-256;
3. verifies the selected RPC reports Bradbury chain ID `4221`;
4. creates an ephemeral `gltest.config.yaml` outside the repository;
5. injects the signing key through process environment substitution only;
6. deploys `Accord402Adjudicator.py` against the explicitly supplied Registry
   address using the pinned repository runtime;
7. persists the returned GenLayer consensus transaction ID immediately after
   the SDK returns it and before finality polling;
8. waits specifically for `TransactionStatus.FINALIZED`;
9. requires `tx_execution_result == 1` and
   `tx_execution_result_name == "FINISHED_WITH_RETURN"`;
10. requires the finalized receipt transaction ID to match the submitted ID;
11. extracts and persists the deployed contract address; and
12. preserves the finalized receipt and release/source binding in a dedicated
    evidence directory.

The pinned `genlayer-py 0.18.0` wait implementation requires exact
`FINALIZED`; `ACCEPTED` is not treated as satisfying a finalized wait.
Bradbury / Consensus v0.6 success is checked independently from status using
the receipt's explicit execution-result fields. The runtime test deliberately
does not rely on the pinned legacy `gltest.tx_execution_succeeded` helper
because that helper requires `leader_receipt`, which is not the authoritative
v0.6 execution-success field.

Bradbury / Consensus v0.6 deployment receipts can also expose
`tx_data_decoded: null`. For deployment-address provenance, the harness therefore
accepts a decoded `contract_address` / `contractAddress` when present and
otherwise requires the finalized transaction `recipient` as the deployed
Intelligent Contract address. The fallback is covered by a no-write regression
test and does not authorize another deployment.

## What it does not prove

A successful Adjudicator deployment test is not, by itself:

- a fresh deployment of the entire SettlementVault/Registry/Adjudicator/Core
  graph;
- live settlement proof;
- repair/retry/recovery proof;
- recipient-balance consequence proof;
- frontend E2E proof; or
- final reviewer certification.

Those remain separate release gates.

## Guarded execution contract

The live runner is:

`scripts/run_bradbury_runtime_integration.sh`

It refuses to run unless all of the following are true:

- the Git worktree is clean;
- the Adjudicator source matches the expected SHA;
- the runtime-test/config files are tracked in the current commit;
- `ACCORD402_BRADBURY_WRITE_AUTHORIZED=YES`;
- `ACCORD402_AUTHORIZED_RELEASE_COMMIT` exactly equals `HEAD`;
- `ACCORD402_AUTHORIZED_ADJUDICATOR_SHA256` exactly equals the expected source
  SHA;
- `ACCORD402_BRADBURY_PRIVATE_KEY` is present in process environment;
- `ACCORD402_BRADBURY_REGISTRY_ADDRESS` is a nonzero 20-byte hex address;
- `ACCORD402_BRADBURY_WRITE_AUTHORIZATION_ID` is supplied and has not already
  been consumed locally;
- the live RPC chain ID is exactly `4221`; and
- the requested evidence directory is absolute, outside the repository, and
  does not already exist.

Immediately before pytest can reach the write path, the runner atomically
creates a local authorization-consumed sentinel keyed by the supplied
authorization ID. Reusing the same authorization ID is refused.

The private key is never printed and is not written into the repository or
the generated ephemeral config.

## Current authorization state

This document and its harness do **not** authorize a Bradbury write.

The earlier Studio-dev profiling authorization remains consumed. A new,
explicit Bradbury authorization must bind the exact committed release SHA and
the exact permitted live action before this runner is used.
