# Accord402 Toolchain Release Reconciliation V1

Status: release-candidate reconciliation, 2026-09-19.

This document does not rewrite or supersede `TOOLCHAIN_V1.md`. It separates
three roles that must not be conflated in reviewer evidence.

## 1. Frozen repository/local baseline

The repository development and deterministic regression baseline remains:

- Python `3.12.14`
- pytest `9.1.1`
- `genlayer-py 0.18.0`
  - commit `a3dc35e04898e3889cbfa855bcaf7d2664675b8f`
- `genlayer-test 0.29.2`
  - commit `9c09578b143905471fb0657dd53bdaf18da8e35f`
- `genvm-linter 0.11.1rc2`
  - commit `28450e665666300fc648dbe495110dfd0cb6a7b4`

That baseline is the toolchain used by the repository Direct Mode/security
harnesses and remains the meaning of the frozen Toolchain V1 document.

## 2. Studio-dev deployment-admission profiling toolchain

The separately preserved Studio-dev deployment fee-profile evidence used an
isolated release-candidate environment:

- Python `3.12.14`
- pytest `9.1.1`
- `genlayer-py 0.19.0rc2`
- `genlayer-test 0.30.0rc2`
- network `studio_devnet`
- chain ID `61997`

That one-shot profile is deployment-admission evidence for the exact
`Accord402Adjudicator.py` source SHA-256
`4e3d3fabce4563f660eb10b4328b805c1cbeea92f83ecd047add00f1b01a1775`.
It does not replace the repository baseline and it is not Bradbury
certification.

The prior Studio-dev authorization was consumed. Nothing in this
reconciliation authorizes another Studio-dev deployment, retry, or
rebroadcast.

## 3. Foundry local/CI release pin

The complete local Solidity regression and runtime-size gates for the current
candidate were executed with Foundry `1.8.1`.

The proposed CI workflow had been configured for `v1.8.3` without an
equivalent current-candidate CI execution. R9-R14 confirmed that an earlier
`24.20.0` Foundry reading was a parser false positive caused by the Node pin.

For the immutable reviewer-ready snapshot, CI is therefore aligned to the
already proven local release toolchain:

- local Foundry: `1.8.1`
- CI Foundry: `v1.8.1`

This is a reproducibility alignment, not a claim that another Foundry release
is defective.

## 4. Bradbury runtime-test role

The committed Bradbury runtime harness continues to use the repository
baseline (`genlayer-py 0.18.0` / `genlayer-test 0.29.2`) because R9-R15
verified the exact pinned APIs used by that harness:

- `testnet_bradbury` network support;
- environment-variable interpolation for account configuration;
- `get_contract_factory`;
- low-level `GenLayerClient.deploy_contract`;
- exact `TransactionStatus.FINALIZED` polling;
- `tx_execution_succeeded`;
- `extract_contract_address`.

The live Bradbury runner is intentionally dormant by default and requires a
fresh explicit write authorization plus an out-of-repository private-key
environment variable. See `BRADBURY_RUNTIME_INTEGRATION_V1.md`.

## Release boundary

This reconciliation is repository-local. It does not create a Git commit,
push a branch, submit a transaction, deploy a contract, or certify the
current hardened graph on Bradbury.
