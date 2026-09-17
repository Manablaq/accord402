# Accord402 V1 — State Machine

> **Payout-liveness amendment:** `docs/SECURITY_HARDENING_V4.md` supersedes conflicting persistent-credit and payout-withdrawal semantics.

> **Settlement-liveness amendment:** `docs/SECURITY_HARDENING_V3.md` supersedes conflicting payout-recipient and vault-withdrawal semantics.

> **Security amendment:** `docs/SECURITY_HARDENING_V2.md` supersedes any conflicting weaker V1 rule in this document.

## Purpose

This document freezes the deterministic covenant lifecycle that `contracts/accord402.py` must implement. The Intelligent Contract may not invent additional value-bearing paths outside this state machine without first revising the specification and reviewer gates.

The adjudication step is GenLayer-native and nondeterministic; state transitions and economic accounting remain deterministic and consume only an accepted validator result.

## Canonical states

The V1 covenant state set is:

1. `FUNDED`
2. `SERVICE_ACCEPTED`
3. `DELIVERED`
4. `CHALLENGED`
5. `EVIDENCE_REPAIR_REQUIRED`
6. `REVIEW_RETRY_REQUIRED`
7. `SETTLEMENT_AUTHORIZED_PROVIDER`
8. `SETTLEMENT_AUTHORIZED_BUYER`
9. `CLOSED_PROVIDER`
10. `CLOSED_BUYER`

`CLOSED_PROVIDER` and `CLOSED_BUYER` are terminal. No method may reopen, mutate, repair, retry, challenge, expire, or settle a closed covenant.

The two settlement-authorized states represent an exact deterministic economic entitlement. They do not mean that GEN has already reached the recipient.

V1 settlement uses `claim_settlement(covenant_id)`. The method accepts only the covenant ID. Recipient and amount are derived exclusively from immutable covenant state.

Settlement authorization, provisional execution, finality, and proven recipient balance effect must never be conflated in UI or reviewer evidence.

## Canonical adjudication decisions

A disputed delivery may produce only:

- `SERVICE_VERIFIED`
- `PROVIDER_BREACH`
- `BUYER_CLAIM_INVALID`
- `EVIDENCE_REPAIR_REQUIRED`
- `REVIEW_RETRY_REQUIRED`

No confidence score, percentage, fuzzy threshold, or tolerance may independently authorize payment or refund.

`SERVICE_VERIFIED` and `BUYER_CLAIM_INVALID` authorize the provider side.

`PROVIDER_BREACH` authorizes the buyer side.

`EVIDENCE_REPAIR_REQUIRED` and `REVIEW_RETRY_REQUIRED` are non-economic intermediate results.

## Transition matrix

| Current state | Trigger | Preconditions | Next state | Economic direction |
|---|---|---|---|---|
| none | `open_covenant` | exact positive GEN amount; valid immutable covenant; unique covenant ID | `FUNDED` | none |
| `FUNDED` | `accept_covenant` | exact provider; before acceptance deadline | `SERVICE_ACCEPTED` | none |
| `FUNDED` | acceptance expiry | deadline passed; not accepted | `SETTLEMENT_AUTHORIZED_BUYER` | buyer refund |
| `SERVICE_ACCEPTED` | `submit_delivery` | exact provider; before delivery deadline; valid frozen delivery/evidence envelope | `DELIVERED` | none |
| `SERVICE_ACCEPTED` | delivery expiry | deadline passed; no delivery | `SETTLEMENT_AUTHORIZED_BUYER` | buyer refund |
| `DELIVERED` | `challenge_delivery` | exact buyer; within challenge window; unused challenge; `review_generation == 0`; `max_review_generations >= 1` | `CHALLENGED` | none; allocate generation `1` |
| `DELIVERED` | unchallenged expiry | challenge deadline passed | `SETTLEMENT_AUTHORIZED_PROVIDER` | provider payment |
| `CHALLENGED` | adjudication `SERVICE_VERIFIED` | exact result bindings | `SETTLEMENT_AUTHORIZED_PROVIDER` | provider payment |
| `CHALLENGED` | adjudication `BUYER_CLAIM_INVALID` | exact result bindings | `SETTLEMENT_AUTHORIZED_PROVIDER` | provider payment |
| `CHALLENGED` | adjudication `PROVIDER_BREACH` | exact result bindings | `SETTLEMENT_AUTHORIZED_BUYER` | buyer refund |
| `CHALLENGED` | adjudication `EVIDENCE_REPAIR_REQUIRED` | repairable evidence fault only | `EVIDENCE_REPAIR_REQUIRED` | none |
| `CHALLENGED` | adjudication `REVIEW_RETRY_REQUIRED` | transient/non-attributable review failure | `REVIEW_RETRY_REQUIRED` | none |
| `EVIDENCE_REPAIR_REQUIRED` | valid repair | before repair deadline; delivery/covenant frozen; `review_generation < max_review_generations`; complete authorized repair | `CHALLENGED` | none; increment generation exactly once |
| `EVIDENCE_REPAIR_REQUIRED` | repair expiry | repair deadline passed; `review_generation < max_review_generations` | `SETTLEMENT_AUTHORIZED_BUYER` | buyer refund; closure reason `REPAIR_EXPIRED` |
| `EVIDENCE_REPAIR_REQUIRED` | `expire_review` | `review_generation == max_review_generations`; generation budget exhausted | `SETTLEMENT_AUTHORIZED_BUYER` | buyer refund; neutral `REVIEW_EXPIRED` |
| `REVIEW_RETRY_REQUIRED` | retry review | before retry deadline; consequential bindings unchanged; `review_generation < max_review_generations` | `CHALLENGED` then review | none; increment generation exactly once |
| `CHALLENGED` | `expire_review` | absolute dispute deadline passed without trustworthy consequential judgment | `SETTLEMENT_AUTHORIZED_BUYER` | buyer refund; neutral `REVIEW_EXPIRED` |
| `REVIEW_RETRY_REQUIRED` | `expire_review` | `review_generation == max_review_generations` OR absolute dispute deadline passed without trustworthy consequential judgment | `SETTLEMENT_AUTHORIZED_BUYER` | buyer refund; neutral `REVIEW_EXPIRED` |
| `SETTLEMENT_AUTHORIZED_PROVIDER` | `claim_settlement(covenant_id)` | immutable provider; exact unresolved principal; no caller-controlled recipient or amount | `CLOSED_PROVIDER` | finality-only external GEN transfer to provider |
| `SETTLEMENT_AUTHORIZED_BUYER` | `claim_settlement(covenant_id)` | immutable buyer; exact unresolved principal; no caller-controlled recipient or amount | `CLOSED_BUYER` | finality-only external GEN transfer to buyer |

## Frozen retry-expiry policy

Every challenged covenant has an absolute dispute deadline fixed by the
covenant's frozen timing policy.

Retry, evidence repair, validator recomputation, web failure, model failure,
and infrastructure failure must not extend that absolute deadline.

Before the deadline, `REVIEW_RETRY_REQUIRED` may be retried only under the
frozen generation and input rules.

After the absolute dispute deadline passes without a trustworthy
settlement-authorizing adjudication, any caller may invoke `expire_review`.

`expire_review` deterministically:

- records closure reason `REVIEW_EXPIRED`;
- moves the covenant to `SETTLEMENT_AUTHORIZED_BUYER`;
- preserves the immutable buyer, provider, amount, covenant, and delivery;
- creates no `PROVIDER_BREACH` finding;
- creates no `BUYER_CLAIM_INVALID` finding;
- creates no provider-breach reputation penalty.

`REVIEW_EXPIRED` is a neutral liveness outcome, not an adjudication decision.

This prevents unavailable validators, web sources, models, or infrastructure
from locking escrow indefinitely or fabricating a semantic judgment.

## Review generation semantics

`review_generation` is `0` before any valid buyer challenge.

A valid buyer challenge allocates generation `1` atomically with the transition from `DELIVERED` to `CHALLENGED`.

The first challenged adjudication therefore always evaluates generation `1`.

Every challenged adjudication and every accepted consequential result binds the exact current generation.

Adjudication itself does not increment the generation.

An accepted terminal semantic result does not increment the generation.

An accepted `EVIDENCE_REPAIR_REQUIRED` or `REVIEW_RETRY_REQUIRED` result does not itself increment the generation.

When the current generation is below `max_review_generations`, a successful complete authorized repair or a valid retry allocates exactly the next generation before fresh adjudication.

Failed, reverted, malformed, duplicate, or stale repair/retry attempts do not consume a generation.

No transition may produce `review_generation > max_review_generations`.

When `EVIDENCE_REPAIR_REQUIRED` is reached at `review_generation == max_review_generations`, repair is no longer valid. `expire_review` is immediately permissionless and produces neutral `REVIEW_EXPIRED` buyer settlement authorization.

When `REVIEW_RETRY_REQUIRED` is reached at `review_generation == max_review_generations`, retry is no longer valid. `expire_review` is immediately permissionless and produces neutral `REVIEW_EXPIRED` buyer settlement authorization.

Generation exhaustion is not provider breach and is not an invalid buyer claim.

For `EVIDENCE_REPAIR_REQUIRED`, ordinary repair-deadline expiry with closure reason `REPAIR_EXPIRED` applies only while `review_generation < max_review_generations`.

This prevents the same maximum-generation state from racing between `REPAIR_EXPIRED` and generation-exhaustion `REVIEW_EXPIRED` closure reasons.

`CHALLENGED` at `review_generation == max_review_generations` is not itself exhausted. The already allocated generation must still receive its adjudication opportunity.

Generation equality alone therefore cannot trigger `expire_review` while the covenant remains `CHALLENGED`.

The absolute dispute deadline remains independent. After it passes without trustworthy consequential adjudication, the existing absolute-deadline `expire_review` path remains valid.

Neither generation allocation nor generation exhaustion changes or extends the absolute dispute deadline.

## State-transition invariants

For every covenant:

- `buyer` never changes.
- `provider` never changes.
- `amount` never changes.
- `service_spec_hash` never changes.
- `delivery_hash` cannot change after first valid delivery.
- a challenge cannot replace the delivery.
- evidence repair cannot replace the delivery or service specification.
- the active evidence-set hash may change only in `EVIDENCE_REPAIR_REQUIRED` under the frozen repair rules.
- only one buyer-side or provider-side economic entitlement may ever exist.
- total settlement entitlement can never exceed the funded amount.
- terminal closure can happen at most once.
- no transition may accept an arbitrary payout recipient.
- no administrative role may bypass a covenant state or redirect value.
- no nondeterministic block may directly perform storage mutation or economic transfer.

## Finality boundary

A leader/validator result may be produced during an Intelligent Contract transaction, but irreversible economic consequence must not be treated as final merely because consensus has reached `ACCEPTED`.

The application must distinguish:

1. transaction submitted;
2. consensus running;
3. accepted/provisional;
4. finalized;
5. execution result;
6. settlement authorization;
7. settlement execution.

Reviewer evidence must prove both finality and successful execution for every canonical consequential transaction.

## Settlement finality semantics

`claim_settlement(covenant_id)` is permissionless because recipient and amount are already fixed by covenant state.

External GEN settlement is finality-only. Accord402 must not use an on-acceptance external economic consequence.

A provisional `CLOSED_PROVIDER` or `CLOSED_BUYER` value is not proof of payment. Canonical settlement requires transaction status `Finalized` and execution result `FINISHED_WITH_RETURN`.

A finalized transaction with an unsuccessful execution result is not successful settlement.

The frontend and SDK must keep settlement authorization, provisional state, finality, execution success, and external payment evidence separate.

Bradbury certification must verify the persisted settlement transaction, recipient GEN balance effect, corresponding Accord402 or Ghost balance effect, and duplicate-claim resistance.

After a transaction ID exists, uncertain observation or timeout must resume tracking that same ID; blind resubmission is forbidden.

## Permission model

- Buyer-only actions: create/fund covenant, challenge delivery where applicable.
- Provider-only actions: accept covenant, submit delivery, submit permitted evidence repair.
- Permissionless deterministic recovery actions may be used after an objectively passed deadline if they cannot redirect value or change consequential bindings.
- Adjudication may be triggered only for a covenant that is in the exact reviewable state.
- No owner/admin emergency method may seize escrow, rewrite a covenant, alter a verdict, or select a settlement recipient.

## Stop rule

Implementation is blocked if any method cannot be mapped to exactly one transition in this document or if any value-bearing state lacks a bounded deterministic recovery path.
