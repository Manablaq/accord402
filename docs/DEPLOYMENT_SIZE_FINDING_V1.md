# Deployment Size Finding V1

Status: **CONFIRMED HISTORICAL BLOCKER**

The monolithic Accord402 Intelligent Contract was not accepted for Bradbury
inclusion because its deployment payload exceeded the observed per-transaction
gas ceiling. The committed diagnostic evidence records a gas ceiling of
`16,777,216` and a deployment estimate of approximately `40.39M` gas for the
then-canonical source.

The response is architectural, not cosmetic. Minifying or weakening the
monolith would not provide a reviewer-safe design. V2 moves deterministic
escrow, lifecycle, policy admission, evidence storage, and accounting into EVM
contracts and retains one deliberately narrow Intelligent Contract for
nondeterministic adjudication.

The exact source and payload sizes used for each V2 deployment candidate must
be freshly measured, hashed, and recorded before signing. Historical failure
artifacts remain in `artifacts/bradbury-deployment/` and are not overwritten.

This document records a blocker and its resolution strategy. It is not a claim
that any V2 artifact fits Bradbury until the size and gas gates pass.

## Local V2 measurement (2026-09-17)

Using the pinned `foundry.toml` profile (`solc 0.8.27`, optimizer runs `1`,
via-IR), the current deployed runtime bytecode measures:

- `Accord402SettlementVault`: `1,231` bytes;
- `Accord402Registry`: `22,043` bytes;
- `Accord402Core`: `24,193` bytes.

These are local EVM measurements only. They do not replace a fresh Bradbury
deployment estimate, finalized transaction, or source-parity check.
