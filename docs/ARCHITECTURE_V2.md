# Accord402 V2 — Hybrid Architecture Amendment

Status: **IMPLEMENTATION IN PROGRESS — NOT DEPLOYMENT AUTHORIZATION**

Accord402 V2 separates deterministic protocol enforcement from semantic
evidence adjudication. The former belongs in ordinary EVM contracts; the latter
is the only responsibility retained by a GenLayer Intelligent Contract.

## Canonical components

1. `Accord402SettlementVault.sol` — the fresh Bradbury-deployed finality-bound
   native GEN router. Deployment evidence is recorded under
   `artifacts/bradbury-deployment/ACCORD402_V2_FRESH_VAULT_20260917/`.
2. `Accord402Registry.sol` — immutable service-policy, authority-binding, and
   evidence-history storage and validation.
3. `Accord402Core.sol` — the single authoritative escrow and covenant state
   machine.
4. `Accord402Adjudicator.py` — one small Intelligent Contract that performs
   disputed semantic review and schedules a finalized callback to Core.

Core and Registry communicate synchronously through deterministic EVM calls.
The Adjudicator does not own escrow, policy state, evidence history, payout
addresses, or settlement decisions. It reads a frozen snapshot and returns a
strict consequential wire. Core applies that wire only after the finalized
GenLayer message is authenticated and every binding matches current state.

The historical monolithic `contracts/accord402.py` is preserved as a reference
implementation for differential semantic testing. It is not deleted, hidden,
or treated as the V2 deployment artifact.

## Non-negotiable invariants

- Native GEN enters only through `openCovenant` with exact `msg.value`.
- Buyer and provider payout recipients are registered and frozen before the
  corresponding economic state is committed.
- No caller supplies a settlement recipient, settlement amount, or adjudication
  result.
- No provisional consensus status can authorize payment.
- The finalized adjudication callback is authenticated by immutable Adjudicator
  address and strictly bound to Core, covenant, policy, delivery, evidence set,
  and review generation.
- Every authorized covenant has exactly one settlement claim path.
- Per-covenant and global accounting identities are checked by tests.
- Any failed required gate stops implementation or deployment.

## Deployment order

The existing SettlementVault is verified first. Registry is then deployed,
followed by the Adjudicator with Registry as its constructor dependency, and
finally Core with immutable Registry, Adjudicator, and SettlementVault
addresses. No post-deployment setter is part of the architecture.

Frontend integration is intentionally deferred until the contracts, local
regression suite, source-parity evidence, and live Bradbury gates pass.
