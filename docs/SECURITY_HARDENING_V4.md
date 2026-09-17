# Accord402 Security Hardening V4

Status: **MANDATORY PAYOUT-LIVENESS AMENDMENT**

This amendment supersedes the persistent-credit / permissionless-withdrawal
model in `SECURITY_HARDENING_V3.md` and every conflicting earlier document.

## Finding closed

V11-R6 locally proved authenticated frozen payout recipients, but a frozen EVM
contract recipient could still permanently reject native GEN. Permissionless
retry alone therefore did not satisfy the release gate `STUCK_VALUE_PATHS=0`.

The target GenLayer Chain uses the ZK Stack account model. Payout destinations
must use the documented code-free default-account path rather than arbitrary
recipient contracts.

## Constructor-resistant registration

Registration is deliberately two-step:

1. `begin_payout_registration()` records `block.number + 1` and requires
   `msg.sender.code.length == 0`.
2. `confirm_payout_registration()` executes in a later block and again requires
   `msg.sender.code.length == 0`.

The second block closes the constructor window: a contract can have zero code
length during construction, but after deployment its runtime code is present.
No `tx.origin` dependency and no SELFDESTRUCT force-send are used.

## Core binding

`open_covenant` and `accept_covenant` require their authenticated payout
destinations to be registered before funding/acceptance state is committed.
A contract or Intelligent Contract party may nominate a separate registered
payout wallet while retaining its economic protocol identity.

## Atomic routing

The settlement EVM contract no longer keeps beneficiary credits and exposes no
withdrawal path. Finalized Core settlement atomically routes the exact native
GEN value to the registered payout account. Delivery identity is
`(source_core, covenant_id)` and duplicates are rejected.

A successful route therefore leaves no settlement balance locked in the
router.

## Privilege model

The router has no owner, administrator, upgrader, sweep, recovery redirect,
delegatecall, SELFDESTRUCT, or caller-selected settlement destination.

## Platform binding

This design is bound to the currently documented GenLayer/ZK Stack
default-account semantics. A chain upgrade that permits a registered code-free
payout account to acquire mutable rejecting runtime code at the same address is
release-breaking and requires a new security audit before deployment/upgrade.

## Remaining release gates

This amendment is not a deployment authorization. The amended Core/router must
still pass local regression, pinned Solidity compilation, second hidden-path
audit, read-only Bradbury schema admission with raw bytes preserved before
decode, live read-only default-account behavior probes, hardened carrier
rebuild/runtime equivalence, gas/cap preflight, and fresh artifact-specific
deployment authorization.
