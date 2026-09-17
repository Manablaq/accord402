# Accord402 V1 — Settlement and Accounting Invariants

> **Payout-liveness amendment:** `docs/SECURITY_HARDENING_V4.md` supersedes conflicting persistent-credit and payout-withdrawal semantics.

> **Settlement-liveness amendment:** `docs/SECURITY_HARDENING_V3.md` supersedes conflicting payout-recipient and vault-withdrawal semantics.

> **Security amendment:** `docs/SECURITY_HARDENING_V2.md` supersedes any conflicting weaker V1 rule in this document.

## Purpose

GEN escrow is the highest-risk deterministic subsystem in Accord402. This document freezes economic invariants before implementation syntax is chosen.

The V1 value-transfer transport is frozen below. No contract implementation may weaken these invariants or substitute another economic transfer path without a new reviewed specification.

## Accounting unit

All native GEN amounts are represented in wei using `u256`.

V1 does not use floating-point currency arithmetic.

For every funded covenant:

```text
funded_amount > 0
funded_amount == exact amount accepted by open_covenant
```

No percentage tolerance or approximate amount is permitted.

## Core liability invariant

Define:

```text
outstanding_liability =
    sum(funded amounts for covenants whose economic entitlement has not been
        proven executed/closed)
```

The implementation must maintain a reviewer-visible accounting model that prevents spending one covenant's escrow to satisfy another covenant.

At minimum, deterministic bookkeeping must make it possible to prove:

```text
total_funded
=
total_closed_to_provider
+ total_closed_to_buyer
+ total_outstanding
```

subject only to explicitly documented protocol-level value-transfer semantics.

If the contract has a separate tracked balance/accounted-balance field, its invariant must be exact and tested after every value-bearing transition.

## One-covenant conservation

For covenant `c`:

```text
provider_settlement(c)
+ buyer_settlement(c)
+ outstanding(c)
=
funded_amount(c)
```

Each term is non-negative.

At most one of provider settlement or buyer settlement may ever become non-zero.

A covenant can never pay/refund more than its funded amount.

## No arbitrary recipient

No settlement method accepts an arbitrary recipient.

The only economically valid recipients are the covenant's immutable buyer or immutable provider according to the finalized outcome.

No owner, admin, relayer, frontend, SDK, validator result, evidence record, or repair operation may redirect settlement.

## No administrative extraction

V1 has no owner-only escrow withdrawal.

If protocol fees are introduced later, they require a separate frozen specification, explicit fee amount/rule, accounting invariant, tests, and reviewer disclosure.

The V1 default is zero protocol fee.

## No double settlement

After a covenant has proven settlement closure:

- no second provider payment;
- no second buyer refund;
- no retry;
- no repair;
- no challenge;
- no expiry;
- no administrative reset.

Replay of a settlement-triggering transaction must fail safely or become idempotent without sending value twice.

## Finality

Irreversible settlement consequences wait for GenLayer finality.

`ACCEPTED` is not treated as irreversible settlement truth.

The frontend and SDK must not announce `PAID` or `REFUNDED` merely because the adjudication transaction is accepted.

Canonical reviewer evidence must distinguish:

```text
consensus status
finality status
GenVM execution result
settlement authorization
settlement execution evidence
```

## Verified GenLayer transfer facts that constrain V1

Current GenLayer documentation states:

- native GEN is received by payable Intelligent Contract methods via `gl.message.value`;
- GEN values are `u256`;
- internal IC-to-IC messages with value deduct value into the message before child activation;
- if such an internal child transaction fails, value is not automatically returned to the sender;
- external messages to EOAs/EVM contracts execute only on finalization;
- an Intelligent Contract's GEN balance is held by its ghost contract on the chain layer.

These facts mean Accord402 must not casually use a value-bearing IC child message for escrow settlement.

## Frozen settlement transport

V1 settlement execution uses `claim_settlement(covenant_id)`.

The trigger is permissionless and accepts only the covenant ID. The caller supplies neither recipient nor amount.

From `SETTLEMENT_AUTHORIZED_PROVIDER`, the recipient is the immutable original provider and the amount is the exact unresolved covenant principal.

From `SETTLEMENT_AUTHORIZED_BUYER`, the recipient is the immutable original buyer and the amount is the exact unresolved covenant principal.

No caller, owner, administrator, relayer, frontend, SDK, evidence record, validator output, repair operation, or retry operation may redirect or resize settlement.

The settlement method deterministically closes the authorized covenant and updates its exact accounting while scheduling exactly one external native GEN transfer to the derived recipient.

The GEN transfer uses the GenLayer chain-layer external-message path. External settlement is finality-only; Accord402 must not use an on-acceptance external economic effect.

V1 must not substitute a value-bearing Intelligent-Contract child transaction for this settlement path.

A provisional `CLOSED_PROVIDER` or `CLOSED_BUYER` state is not proof that the recipient received GEN.

Canonical settlement requires the persisted settlement transaction to reach `Finalized` with execution result `FINISHED_WITH_RETURN`.

Bradbury certification must additionally verify the real recipient GEN balance effect, the corresponding Accord402 or Ghost balance effect, and duplicate-claim resistance.

Once a settlement transaction ID exists, uncertain observation, timeout, RPC failure, frontend restart, or process restart must resume tracking that same transaction ID rather than blindly submitting another settlement write.

## Deadline recovery

Every escrow-bearing nonterminal state has a bounded path forward.

Deterministic deadline recovery may be permissionless only when:

- the deadline is objectively passed using GenLayer transaction time;
- the next economic recipient is predetermined by frozen policy;
- the caller cannot supply or alter the recipient;
- the action cannot rewrite evidence or delivery;
- repeated invocation cannot duplicate value transfer.

## Reentrancy / asynchronous-message mindset

GenLayer internal and external messages are asynchronous consequences, not synchronous Solidity-style return-value calls.

The V1 design must therefore avoid assumptions that a settlement message returns success synchronously to the parent Intelligent Contract.

Any state transition that depends on downstream execution must have explicit evidence/confirmation semantics or avoid the dependency entirely.

## Balance safety tests

The deterministic suite must cover, at minimum:

- exact funding;
- zero funding rejection;
- wrong amount rejection where a quoted exact amount is required;
- two simultaneous covenants;
- refund of one covenant without affecting another;
- provider settlement of one covenant without affecting another;
- duplicate settlement attempt;
- duplicate refund attempt;
- settlement after repair;
- settlement after retry;
- deadline refund;
- terminal-state replay;
- maximum `u256` boundary behavior relevant to supported amounts;
- accounting equality after every tested transition.

## Completion rule

Accord402 cannot be called reviewer-ready until a supported-runtime/Bradbury test demonstrates the chosen settlement transport with real GEN and proves the final recipient balance outcome without replaying a transaction merely because finality takes time.
