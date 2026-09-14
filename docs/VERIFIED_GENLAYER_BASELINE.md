# Accord402 V1 — Verified GenLayer Baseline

Status: FROZEN FOR V1 IMPLEMENTATION

This document records implementation-sensitive GenLayer facts that Accord402 V1 is allowed to rely on. If the live GenLayer documentation changes materially, this baseline must be re-verified before contract changes are made.

## Verified platform facts

1. Native value is GEN. Values are denominated in wei and contract value amounts should use `u256`.
2. A public method receives GEN only when declared with `@gl.public.write.payable`; the amount sent is exposed as `gl.message.value`.
3. Persistent contract fields must be declared in the contract class body with supported storage types.
4. Persistent `list[T]` and `dict[K, V]` are not supported as ordinary Python containers; use `DynArray[T]` and `TreeMap[K, V]`.
5. Persistent integer fields use fixed-size types such as `u256` rather than Python `int` unless arbitrary precision is explicitly required.
6. Non-deterministic operations use the Equivalence Principle. The leader proposes a result and validators independently verify its substance.
7. Validator logic must not merely validate the leader result's shape or allowed enum. It must verify the decision against independently retrieved or independently evaluated evidence.
8. Non-deterministic side effects must not directly mutate state. State transitions use only the accepted result after the Equivalence Principle returns.
9. `Accepted` is provisional and does not mean successful execution. A finalized transaction can also contain an execution error. Applications must distinguish consensus status, finality, and execution result.
10. Irreversible settlement must wait for `Finalized`.
11. Intelligent Contract messages may be scheduled for finalization. External messages to EOAs/EVM contracts execute only on finalization.
12. Transaction time is available from GenLayer transaction context. Deadlines must use transaction context time rather than host wall-clock time.
13. Intelligent Contract writes and deployments have a full consensus lifecycle and must be tracked by their exact transaction identifiers rather than blindly resubmitted.
14. Bradbury is a persistent public GenLayer testnet suitable for production-like validation of real Intelligent Contract behavior.

## Official references verified for this baseline

- https://docs.genlayer.com/developers/intelligent-contracts/features/value-transfers
- https://docs.genlayer.com/developers/intelligent-contracts/storage
- https://docs.genlayer.com/developers/intelligent-contracts/equivalence-principle
- https://docs.genlayer.com/developers/intelligent-contracts/features/messages
- https://docs.genlayer.com/developers/intelligent-contracts/features/transaction-context
- https://docs.genlayer.com/understand-genlayer-protocol/core-concepts/optimistic-democracy/finality
- https://docs.genlayer.com/developers/intelligent-contracts/testing
- https://docs.genlayer.com/developers/networks

## Accord402 V1 consequences

- Escrow is native GEN only.
- The contract never uses a fuzzy score or tolerance to authorize payment or refund.
- Dispute adjudication returns a compact structured result with exact consequential fields.
- Validators independently verify the same covenant and evidence basis.
- Evidence failure is not automatically interpreted as provider breach.
- Every temporary escrow state has a deterministic recovery deadline.
- Payment/refund authorization is finality-safe.
- Frontend state must distinguish submitted, consensus-running, accepted, finality-pending, finalized, and execution-success states.
- No x402 payment rail is claimed as part of V1. “402” is product positioning around agent-service warranties; V1 settlement is native GEN on GenLayer.

## Settlement implementation caution

GenLayer distinguishes internal IC-to-IC messages from external messages to EOAs/EVM contracts.

Internal messages carrying value create child transactions, and current official documentation states that if such a child transaction fails, the value is not automatically returned to the sender.

External messages to EOAs/EVM contracts execute only on finalization.

Accord402 V1 freezes settlement execution through `claim_settlement(covenant_id)` using a finality-only external native GEN message to the immutable buyer or provider selected by covenant state.

For an EOA recipient, the current documented GenLayer interface pattern is an `@gl.evm.contract_interface` recipient followed by `emit_transfer(value=u256(amount))`.

This documented API pattern is an implementation baseline, not Bradbury settlement proof. Contract lint/typecheck/tests must still verify the implementation, and canonical Bradbury certification must separately prove `Finalized` plus `FINISHED_WITH_RETURN`, the real recipient balance effect, the corresponding Accord402 or Ghost balance effect, and duplicate-claim resistance.

## Implementation stop rule

If an implementation requires behavior not covered by this verified baseline, stop and verify the exact current GenLayer API or protocol rule before coding it.
