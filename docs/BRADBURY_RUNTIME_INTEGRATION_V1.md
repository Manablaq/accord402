# Accord402 Bradbury Runtime Integration V1

Status: reproducible split-phase live-runtime harness present; **not yet executed for the current hardened release**. The authorized write phase submits and persists the deployment without waiting for GenLayer finality; finality is verified later by a dedicated read-only verifier.

## Network binding

The harness is bound to current GenLayer Bradbury:

- network: `testnet_bradbury`
- chain ID: `4221`
- GenLayer RPC: `https://rpc-bradbury.genlayer.com`
- EVM RPC: `https://rpc.testnet-chain.genlayer.com`
- release-bound Bradbury deployment-manifest version:
  `v0.5:9c68608`
- ConsensusMain:
  `0x0112Bf6e83497965A5fdD6Dad1E447a6E004271D`
- Registry:
  `0x5BD6f9EEBF7BE527321ED46649447c59fAc5315C`
- expected signing address:
  `0x1f87Ae197af539253978d435aD45cCf28Fb95024`
- exact Adjudicator source SHA-256:
  `35d8beeb2dedb9b2d6839c3237ad839d85a0a788abb80adbc0557ed15b07a271`

The live runner checks the official Bradbury deployment manifest before
authorization consumption. If its version or ConsensusMain changes, execution
stops; this document does not treat the release-bound manifest version as a
timeless claim about Bradbury.

The tracked `gltest.config.yaml` intentionally contains no signing account.
It retains the pinned suite's preconfigured local test entry as the default,
so ordinary repository pytest execution does not acquire a Bradbury key and
cannot silently become a Bradbury write.

The start nonce is deliberately **not hard-coded into the repository**.
Every fresh live authorization must bind an exact decimal start nonce. Before
authorization consumption, the runner requires both live `latest` and
`pending` EOA nonce to equal that authorized value. The runtime test repeats
the same check immediately before submission and requires the nonce to advance
by exactly one after the SDK returns the deployment transaction ID.

## What the live test proves

`tests/integration/test_accord402_adjudicator_bradbury_runtime.py` provides a
supported-runtime deployment test for the exact hardened Adjudicator source.

When, and only when, the guarded live runner is explicitly authorized, it:

1. verifies the repository is an immutable clean Git commit;
2. verifies the exact Adjudicator source SHA-256;
3. verifies both configured RPCs report Bradbury chain ID `4221`;
4. waits within a bounded pre-authorization readiness window until
   `gen_syncing` reports the exact fully-synced condition
   `blocksBehind == 0` and `syncedBlock == latestBlock`;
5. verifies the official Bradbury deployment manifest still matches the
   release-bound version and ConsensusMain;
6. verifies the supplied Registry equals the release-bound Registry and its
   live runtime hash matches the certified runtime;
7. verifies the explicitly authorized signer equals the release-bound signer;
8. verifies the supplied private key resolves to that exact signer without
   printing or persisting the key;
9. verifies both `latest` and `pending` signer nonce equal the exact authorized
   start nonce before authorization consumption;
10. creates an ephemeral `gltest.config.yaml` outside the repository;
11. injects the signing key through process-environment substitution only;
12. atomically consumes the one-shot authorization before pytest can reach the
    deployment submission path;
13. independently verifies the loaded account is the exact authorized signer;
14. repeats the `latest` / `pending` nonce check immediately before submission;
15. persists the pre-submit signer/nonce/release binding;
16. deploys `Accord402Adjudicator.py` against the release-bound Registry using
    the pinned repository runtime;
17. requires the signer nonce to advance from `N` to exactly `N + 1` after
    submission;
18. immediately persists the returned GenLayer consensus transaction ID;
19. binds the exact outer EVM transaction and its creation event;
20. requires `NewTransaction` so a provisional Intelligent Contract address
    is available for the dependent Core submission;
21. persists that provisional contract address and returns from the authorized
    submission phase **without waiting for GenLayer finality**;
22. performs no retry, replacement, rebroadcast, appeal, or finalization write;
    and
23. later uses `scripts/verify_bradbury_runtime_finality.sh` as a read-only
    verifier for exact `FINALIZED`, `FINISHED_WITH_RETURN`, transaction-ID
    identity, and provisional-to-final contract-address identity.

The later read-only finality verifier uses the pinned `genlayer-py 0.18.0`
wait implementation and requires exact `FINALIZED`; `ACCEPTED` is not treated
as satisfying a finalized wait.
Execution success is checked independently from consensus status using the
receipt's explicit `tx_execution_result` and `tx_execution_result_name`
fields. The runtime test deliberately does not rely on the pinned legacy
`gltest.tx_execution_succeeded` helper because that helper depends on
`leader_receipt` rather than the explicit consequential execution-result
fields used here.

Bradbury deployment receipts can expose `tx_data_decoded: null`. For
deployment-address provenance, the harness therefore accepts a decoded
`contract_address` / `contractAddress` when present and otherwise requires the
finalized transaction `recipient` as the deployed Intelligent Contract
address. The fallback is covered by a no-write regression test and does not
authorize another deployment.

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

The write-authorized submission runner is:

`scripts/run_bradbury_runtime_integration.sh`

The later read-only finality verifier is:

`scripts/verify_bradbury_runtime_finality.sh`

It refuses to run unless all of the following are true:

- the Git worktree is clean;
- the Adjudicator source matches the expected SHA;
- the runtime-test/config files are tracked in the current commit;
- `ACCORD402_BRADBURY_WRITE_AUTHORIZED=YES`;
- `ACCORD402_AUTHORIZED_RELEASE_COMMIT` exactly equals `HEAD`;
- `ACCORD402_AUTHORIZED_ADJUDICATOR_SHA256` exactly equals the expected source
  SHA;
- `ACCORD402_BRADBURY_EXPECTED_SENDER` equals the release-bound signing
  address;
- `ACCORD402_BRADBURY_EXPECTED_START_NONCE` is a canonical decimal nonce;
- `ACCORD402_BRADBURY_PRIVATE_KEY` is present in process environment and
  resolves to the exact authorized sender;
- `ACCORD402_BRADBURY_REGISTRY_ADDRESS` equals the release-bound Registry;
- the live Registry runtime hash matches the certified Registry runtime;
- `ACCORD402_BRADBURY_WRITE_AUTHORIZATION_ID` is supplied and has not already
  been consumed locally;
- both live RPC chain IDs are exactly `4221`;
- within the bounded pre-authorization readiness window, the Bradbury node
  reports the exact fully-synced condition `blocksBehind == 0` with
  `syncedBlock == latestBlock`; each attempted sync response is persisted as
  evidence and the exact successful response is retained as
  `gen_syncing.raw.json`;
- the Bradbury deployment manifest version and ConsensusMain match the
  release-bound values;
- both live `latest` and `pending` signer nonce equal the exact authorized
  start nonce before authorization consumption and again immediately before
  deployment; and
- the requested evidence directory is absolute, outside the repository, and
  does not already exist.

Immediately before pytest can reach the write path, the runner atomically
creates a local authorization-consumed sentinel keyed by the supplied
authorization ID. The sentinel records the exact release, source, network,
manifest version, ConsensusMain, Registry/runtime hash, sender, start nonce,
and authorization ID. Reusing that authorization ID is refused.

The private key is never printed and is not written into the repository or
the generated ephemeral config.

The bounded sync loop does not relax GenLayer's definition of full sync. It
does not authorize submission while `blocksBehind` is nonzero. Its only
purpose is to tolerate a moving public Bradbury tip by waiting, before
authorization consumption, for one exact `blocksBehind == 0` observation.
If that exact state is not observed within the bounded window, execution
stops before authorization consumption.

## Current authorization state

This document and its harness do **not** authorize a Bradbury write.

A new explicit Bradbury authorization must bind the exact committed release
SHA, exact Adjudicator source SHA, exact signer, exact freshly verified start
nonce, Registry address, and the single permitted deployment action before
this runner is used. Any nonce, release, network-manifest, or dependency drift
is a stop condition; it does not authorize a retry, replacement, rebroadcast,
appeal, finalization action, or second deployment.
