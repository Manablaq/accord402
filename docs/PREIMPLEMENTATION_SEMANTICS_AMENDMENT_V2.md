# Accord402 V1 — Preimplementation Semantics Amendment V2

Status: FROZEN BEFORE CONTRACT IMPLEMENTATION

## 1. Scope and precedence

This document is an append-only clarification of Accord402 V1 semantics discovered during the Step 2 pre-code implementation audit.

It does not modify the bytes or SHA-256 identities of any previously frozen Accord402 document.

Where an earlier frozen document leaves one of the subjects below ambiguous, this amendment controls the V1 implementation.

This amendment creates no new public method, parameter, return type, storage field, contract state, adjudication decision, closure reason, repair-mask bit, hash-preimage field, adjudication-wire field, settlement path, privilege, or toolchain dependency.

The subjects clarified here are limited to:

- canonical challenged-criterion ordering;
- exact selection between `SERVICE_VERIFIED` and `BUYER_CLAIM_INVALID`;
- exact repair-authorization mask derivation;
- structural evidence completeness at delivery and the meaning of a "missing evidence record";
- exact persistent reputation-counter update points.

## 2. Canonical challenged-criterion ordering

A challenge must contain at least one challenged criterion ID and at most the frozen V1 maximum.

Every challenged criterion ID must identify exactly one frozen criterion for the covenant.

Duplicate challenged criterion IDs are invalid.

The challenge list must preserve the relative order of the frozen `criteria_by_covenant` array.

Equivalently, the stored `challenged_criterion_ids_by_covenant` is the exact ordered subsequence obtained by filtering the frozen criterion array to the criterion IDs selected by the buyer.

A challenge that supplies the same set in a different order is invalid and reverts before changing covenant state, challenge counters, review generation, or any other persistent state.

This rule makes the challenged list canonical and permits exact comparison with the complete frozen criterion list.

## 3. Exact terminal semantic decision selection

`PROVIDER_BREACH`, `SERVICE_VERIFIED`, and `BUYER_CLAIM_INVALID` are distinct semantic findings. They are not interchangeable aliases for provider-side or buyer-side economic direction.

The validator independently evaluates every criterion in the canonical challenged-criterion list against the frozen covenant, delivery, evidence policy, and qualifying active evidence.

Decision selection is exactly:

### 3.1 `PROVIDER_BREACH`

`PROVIDER_BREACH` is required when one or more challenged criteria are independently established to have substantively failed.

Its `failed_criterion_ids` is the exact ordered subsequence of challenged criteria that failed.

Its `failure_classification` is exactly `SUBSTANTIVE_PROVIDER_BREACH`.

Its repair authorization list is empty.

### 3.2 `SERVICE_VERIFIED`

`SERVICE_VERIFIED` is permitted only when all of the following are true:

1. the canonical challenged-criterion list is byte-for-byte equal to the complete frozen criterion-ID list in the same order;
2. no challenged criterion substantively fails;
3. all consequential evidence requirements are satisfied, including the exact primary, corroboration, freshness, authority, source-kind, digest, and version rules;
4. no repairable evidence defect remains;
5. no transient review failure prevents trustworthy adjudication.

`SERVICE_VERIFIED` therefore means the challenge put the complete frozen service-criterion set at issue and the validators independently verified that complete set.

Its `failed_criterion_ids` is empty.

Its `failure_classification` is the empty string.

Its repair authorization list is empty.

### 3.3 `BUYER_CLAIM_INVALID`

`BUYER_CLAIM_INVALID` is required when all of the following are true:

1. the canonical challenged-criterion list is a strict ordered subsequence of the complete frozen criterion-ID list;
2. no challenged criterion substantively fails;
3. all consequential evidence requirements are satisfied for the challenged criteria;
4. no repairable evidence defect remains;
5. no transient review failure prevents trustworthy adjudication.

`BUYER_CLAIM_INVALID` is an affirmative semantic finding that the buyer's specific challenged subset is unsupported by the independently verified evidence.

The mere absence of provider breach is not by itself proof that a buyer claim is invalid.

Its `failed_criterion_ids` is empty.

Its `failure_classification` is the empty string.

Its repair authorization list is empty.

### 3.4 Intermediate-result precedence

If a repairable evidence defect prevents trustworthy terminal evaluation, the result is `EVIDENCE_REPAIR_REQUIRED`, not a terminal semantic decision.

If a transient runtime, transport, source, model, or validator condition prevents trustworthy terminal evaluation, the result is `REVIEW_RETRY_REQUIRED`, not a terminal semantic decision.

A terminal decision is forbidden whenever the frozen consequential primary/corroboration requirements are not satisfied.

The exact terminal-decision distinction is consequential. Leader and validators must independently derive the same exact decision; agreement only on provider-side economic direction is insufficient.

## 4. Structural evidence completeness at delivery

V1 evidence repair can replace existing active evidence records but cannot append an entirely new active slot that had no predecessor.

Therefore a valid `submit_delivery` must establish the minimum structural evidence set required for any later consequential adjudication.

Before delivery succeeds, deterministic code must require:

1. at least one admitted evidence record whose resolved frozen authority binding has role `PRIMARY` and whose `is_primary` value is `true`;
2. at least `required_corroboration_count` admitted evidence records whose resolved frozen authority bindings have role `CORROBORATOR`, whose `is_primary` values are `false`, and whose independent-authority keys are distinct under Amendment V1;
3. no corroborator counted toward the requirement may share the independent-authority key of any admitted primary evidence;
4. every admitted evidence record must pass the deterministic envelope, authority-resolution, canonical-source, replay, identifier, timestamp-ordering, source-kind, and input-bound checks that are decidable without nondeterministic content retrieval.

This delivery-time rule is structural. It does not claim that the referenced content is substantively valid, fresh at a later adjudication time, reachable, truthful, or sufficient to prove the service criteria.

Those consequential facts remain subject to independent adjudication.

If the delivery input lacks the required primary or corroborator structure, `submit_delivery` is invalid and reverts. The covenant remains `SERVICE_ACCEPTED`; no delivery hash, evidence history, active-evidence selection, replay reservation, delivery counter, or challenge deadline is consumed.

## 5. Meaning of a missing evidence record

Earlier evidence-model language listed a "missing required evidence record" as an example of a repairable evidence failure.

For V1, this phrase means that a required active evidence slot exists but its referenced or repairable metadata/content cannot satisfy the frozen evidence requirement and can be corrected by replacing that existing active record under an exact authorized repair mask.

It does not authorize insertion of a brand-new active evidence slot.

A literal absence of the structurally required primary/corroborator slots cannot reach `DELIVERED` because Section 4 rejects such a delivery deterministically.

Repair cannot:

- create a new active-evidence array position;
- increase or decrease the active evidence-record count;
- repair `subject`;
- repair `kind`;
- repair `source_kind`;
- repair `is_primary`;
- change the covenant or delivery;
- change authority trust beyond the already-frozen approved authority bindings.

A replacement may change `authority_id` or `authority_revision` only when the accepted repair mask authorizes those fields and the replacement still resolves to an already-frozen approved authority binding consistent with all role, primary/corroborator, independence, source, and consequential-evidence rules.

## 6. Exact repair-authorization mask derivation

Repair authorization is consequential consensus output. The mask is not discretionary.

For each active evidence record that independently has one or more repairable defects, the leader and validators derive the exact minimal nonzero repair mask.

A repair bit is set if and only if changing that corresponding repairable field is necessary to cure at least one independently established repairable defect for that active evidence record.

No bit may be set merely to permit optional editing, future flexibility, convenience, or a broader replacement.

No repairable defective field may be omitted from the mask when that field must change for the record to become admissible.

The exact mask is the bitwise OR of all and only the necessary frozen repair bits for that record.

Every derived mask must remain a subset of both:

- the covenant's immutable `repair_allowed_field_mask`; and
- the V1 repair universe `0x000000FF`.

A zero mask is never valid repair authorization.

If a defect requires changing a non-repairable field, changing a field outside the covenant's repair policy, adding an active slot, or otherwise exceeding V1 repair semantics, validators must not fabricate a broader repair authorization.

Such a condition cannot produce `EVIDENCE_REPAIR_REQUIRED` unless the complete defect is actually repairable within the frozen V1 replacement ABI and policy.

The ordered repair-authorization list contains exactly one entry for each active evidence record that requires an authorized repair, in the relative order of those evidence IDs in the current active-evidence list.

No unaffected evidence record appears in that list.

## 7. Persistent reputation counters

The V1 persistent reputation records contain exactly these counters:

Provider:

- `accepted_covenants`;
- `deliveries`;
- `non_deliveries`;
- `disputes_won`;
- `disputes_lost`.

Buyer:

- `funded_covenants`;
- `challenges_filed`;
- `valid_challenges`;
- `invalid_challenges`.

All persistent V1 reputation counters are updated only by a successful `claim_settlement` execution that deterministically moves an authorized covenant to `CLOSED_PROVIDER` or `CLOSED_BUYER`.

No counter is incremented at funding, acceptance, delivery, challenge, settlement authorization, repair, retry, or intermediate adjudication.

This preserves the frozen rule that canonical reputation is derived from finalized terminal covenant outcomes: provisional execution may expose provisional storage, but only finalized successful chain state is canonical.

For one covenant, the successful first and only settlement execution increments counters exactly as follows.

### 7.1 Buyer funded counter

`buyer_stats[buyer].funded_covenants += 1` for every successfully closed covenant.

### 7.2 Provider acceptance counter

If `accepted_at != 0`:

`provider_stats[provider].accepted_covenants += 1`.

Otherwise it does not increment.

### 7.3 Provider delivery counter

If `delivered_at != 0`:

`provider_stats[provider].deliveries += 1`.

Otherwise it does not increment.

### 7.4 Provider non-delivery counter

If and only if `closure_reason == "NON_DELIVERY_EXPIRED"`:

`provider_stats[provider].non_deliveries += 1`.

No other closure increments `non_deliveries`.

### 7.5 Buyer challenge-filed counter

If `challenged_at != 0`:

`buyer_stats[buyer].challenges_filed += 1`.

Otherwise it does not increment.

### 7.6 Provider dispute win and buyer invalid-challenge counters

If and only if `adjudication_decision` is `SERVICE_VERIFIED` or `BUYER_CLAIM_INVALID`:

`provider_stats[provider].disputes_won += 1`

and

`buyer_stats[buyer].invalid_challenges += 1`.

### 7.7 Provider dispute loss and buyer valid-challenge counters

If and only if `adjudication_decision == "PROVIDER_BREACH"`:

`provider_stats[provider].disputes_lost += 1`

and

`buyer_stats[buyer].valid_challenges += 1`.

### 7.8 Neutral and non-semantic closures

`UNACCEPTED_EXPIRED`, `NON_DELIVERY_EXPIRED`, `UNCHALLENGED`, `REPAIR_EXPIRED`, and `REVIEW_EXPIRED` do not increment `disputes_won`, `disputes_lost`, `valid_challenges`, or `invalid_challenges` unless a terminal semantic adjudication decision was already recorded as specified above.

In canonical V1 state flow, `REPAIR_EXPIRED` and `REVIEW_EXPIRED` carry no terminal semantic provider-breach or invalid-buyer-claim finding and therefore increment none of those four dispute-merit counters.

## 8. Counter overflow rule

Each reputation counter is a persistent `u64`.

Every reputation-counter increment uses deterministic saturating increment:

```text
if value < 18446744073709551615:
    value = value + 1
else:
    value = 18446744073709551615
```

Counter saturation must never block settlement, alter settlement recipient, alter settlement amount, or cause an otherwise valid `claim_settlement` to revert.

Saturation is presentation/accounting protection only and never creates an economic consequence.

## 9. Settlement and anti-replay interaction

The reputation updates in Section 7 occur in the same deterministic `claim_settlement` state transition that:

- verifies the covenant is in exactly one settlement-authorized state;
- derives the immutable recipient and exact outstanding principal;
- requires `settlement_message_scheduled == false`;
- moves the covenant to the matching closed state;
- moves the exact outstanding amount to the matching settlement accumulator;
- updates global accounting;
- sets `settlement_message_scheduled = true`;
- schedules exactly one finality-only external GEN transfer.

A duplicate or terminal-state settlement call cannot increment reputation counters a second time because it cannot pass the settlement preconditions.

No reputation counter can authorize, resize, redirect, or otherwise influence settlement.

## 10. No other semantic changes

All earlier frozen rules remain in force, including:

- exact thirteen-write and twelve-view ABI;
- zero-argument constructor;
- exact persistent root-storage shape and record shapes;
- exact covenant decimal map key;
- exact replay-key namespaces;
- exact hash preimages and reference vectors;
- exact canonical-source rules as amended by Amendment V1;
- exact authority-role, identity-kind, source-kind, and settlement-direction constants;
- exact corroboration identity key;
- exact adjudication wire with exactly twelve top-level fields;
- exact failure classifications;
- exact state machine and generation rules;
- exact settlement recipient and amount derivation;
- finality-only external GEN transfer;
- no privileged economic path;
- no caller-selected settlement recipient or amount;
- frozen GenLayer runner and toolchain.

This amendment creates no new public method, parameter, return type, storage field, hash field, wire field, or value-transfer path.

## 11. Implementation stop rule

Contract implementation may proceed only after this amendment is byte-frozen and independently certified together with every earlier frozen foundation file.

If implementation reveals another consequential ambiguity rather than a syntax/API question, stop and freeze the semantics before choosing behavior in code.
