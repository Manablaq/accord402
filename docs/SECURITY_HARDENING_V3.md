> **Payout-liveness supersession:** `docs/SECURITY_HARDENING_V4.md` supersedes this document's persistent-credit and vault-withdrawal model.

# Accord402 Security Hardening V3

Status: **MANDATORY SETTLEMENT-LIVENESS AMENDMENT**

This amendment supersedes settlement-recipient and vault-withdrawal language
in `SECURITY_HARDENING_V2.md` and every conflicting earlier document.

## Finding closed

The V10-R3 second security audit proved that tying vault credit only to the
economic buyer/provider does not guarantee universal withdrawal liveness:
a GenLayer party is not necessarily able to originate the required EVM vault
call.

## Authenticated frozen payout recipients

Economic identity and payout destination are separate.

- `open_covenant(terms, buyer_settlement_recipient)` authenticates and freezes
  the buyer payout recipient in the buyer-signed funding transaction.
- `accept_covenant(covenant_id, provider_settlement_recipient)` authenticates
  and freezes the provider payout recipient in the provider-signed acceptance
  transaction.
- zero payout recipients are invalid.
- provider payout binding cannot occur before successful provider
  authorization and cannot change after acceptance.
- economic buyer/provider identities remain authoritative for protocol
  authorization, reputation, and accounting.

No settlement method accepts a caller-selected destination.

## Core-to-vault settlement

`claim_settlement` remains permissionless. Its caller cannot select amount,
beneficiary, or payout recipient.

Core derives from covenant state the covenant id, exact outstanding principal,
economic beneficiary, and frozen authenticated payout recipient, then emits
exactly one finality-bound value-bearing EVM message:

`credit(covenant_id, economic_beneficiary, frozen_payout_recipient)`

## Covenant-keyed vault credit

Vault credit identity is `keccak256(abi.encode(source_core, covenant_id))`.
This prevents collisions across covenants involving the same party.

Each credit stores immutable economic beneficiary, payout recipient, and
amount. Duplicate credit for the same Core/covenant id is rejected.

## Permissionless execution, immutable destination

`withdraw(source_core, covenant_id)` is permissionless. Any account may pay
the gas to execute it.

The executor supplies only source Core and covenant id. Recipient and amount
are loaded from the frozen credit and cannot be changed by the executor.

A recipient-call failure reverts atomically, preserving the credit for retry.
The vault has no owner, administrator, upgrader, sweep, redirect, or
privileged debit path.

## Deployment consequence

This amendment is not a deployment authorization. The amended Core/vault must
pass local regression, Solidity compilation, second hidden-path audit, live
read-only Bradbury schema admission with raw response preservation, hardened
carrier rebuild/runtime equivalence, gas/cap preflight, and then receive a
fresh artifact-specific deployment authorization.
