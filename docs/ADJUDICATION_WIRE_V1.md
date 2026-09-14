# Accord402 V1 — Frozen Adjudication Wire Shape

## 1. Scope

This document freezes the exact V1 consequential adjudication result crossing the GenLayer nondeterministic consensus boundary.

The wire contains only fields that validators must agree on exactly before deterministic protocol state can change.

Reasoning prose, model chain-of-thought, confidence scores, percentages, settlement recipients, settlement amounts, contract state, closure reason, and settlement direction are not wire fields.

## 2. Consensus model

Only a covenant in exact `CHALLENGED` state may execute challenged adjudication.

Deterministic code first copies every required frozen covenant, criterion, authority, evidence, challenge, and generation value into memory.

The leader independently evaluates the frozen inputs and policy-approved evidence.

The validator independently evaluates the same frozen inputs and policy-approved evidence.

The validator must not approve merely because leader output has valid JSON shape, valid keys, or a recognized decision enum.

The validator must independently establish the substance of every consequential field it accepts.

If independently derived consequential fields differ, the validator returns disagreement.

Storage mutation and external-message emission occur only after the nondeterministic consensus call returns to deterministic execution.

## 3. Wire transport

The V1 consensus result is a canonical JSON string.

The leader may obtain noncanonical raw JSON text from a model, but that raw text is never itself the accepted protocol wire.

Raw model JSON is strictly parsed and validated, then serialized into the canonical form below before the leader returns it.

The validator receives the leader result, requires the successful GenLayer return form, requires its payload to be a string, and strictly parses that canonical string.

The deterministic caller reparses and revalidates the accepted canonical string after consensus before applying any state transition.

Maximum raw or canonical adjudication wire size is 65536 UTF-8 bytes.

## 4. Canonical JSON serialization

The canonical serializer is equivalent to Python `json.dumps` with:

```text
sort_keys=True
separators=(",", ":")
ensure_ascii=True
allow_nan=False
```

The accepted consensus wire must byte-for-byte equal its canonical reserialization.

Whitespace outside JSON strings is therefore absent.

Object keys appear in lexicographic order.

Array order is preserved and is consequential.

Duplicate JSON object keys are rejected during parsing.

Floating-point numbers, exponent-form numbers, NaN, Infinity, and negative unsigned values are rejected.

JSON booleans are never accepted where an integer is required.

`null` is not used by the V1 wire schema.

## 5. Exact top-level shape

The top-level JSON value must be an object with exactly these twelve keys and no others:

```text
wire_version
covenant_id
service_spec_hash
delivery_hash
evidence_policy_hash
active_evidence_set_hash
review_generation
decision
challenged_criterion_ids
failed_criterion_ids
failure_classification
repair_authorizations
```

`wire_version` is the JSON integer `1`.

`covenant_id` is a positive unsigned 64-bit integer and must exactly equal the covenant being adjudicated.

`review_generation` is a positive unsigned 32-bit integer and must exactly equal the current stored challenged review generation.

Each hash field is exactly 64 lowercase hexadecimal characters with no `0x` prefix and must exactly equal current frozen covenant state.

The wire service, delivery, policy, and active-evidence hashes must all match before any decision field is considered.

## 6. Decision enum

The only V1 wire decisions are:

```text
SERVICE_VERIFIED
PROVIDER_BREACH
BUYER_CLAIM_INVALID
EVIDENCE_REPAIR_REQUIRED
REVIEW_RETRY_REQUIRED
```

No unknown decision is accepted.

No confidence score, probability, tolerance, semantic-similarity score, or percentage modifies these decisions.

## 7. Challenged criterion binding

`challenged_criterion_ids` must byte-for-byte equal the complete immutable stored challenged-criterion ID list in its existing order.

It must contain between 1 and 16 unique IDs.

The validator must independently evaluate the criteria identified by that frozen list.

The leader cannot omit, add, duplicate, reorder, or substitute challenged criteria.

## 8. Failed criterion binding

`failed_criterion_ids` contains only substantive service criteria independently determined to have failed.

It contains at most 16 unique IDs.

Every failed ID must be a member of `challenged_criterion_ids`.

Its order is exactly the order obtained by filtering the frozen `challenged_criterion_ids` list to the failed IDs.

Permutation of the same failed-ID set is not canonical.

Intermediate evidence-repair or transient-retry results do not label criteria as substantively failed.

## 9. Failure classification

The exact V1 `failure_classification` values are:

```text
""
SUBSTANTIVE_PROVIDER_BREACH
REPAIRABLE_EVIDENCE_DEFECT
TRANSIENT_REVIEW_FAILURE
```

The empty string is the explicit not-applicable value.

No other failure classification is valid.

Failure classification does not independently authorize settlement.

## 10. Repair authorization wire entries

`repair_authorizations` is a JSON array with at most 16 entries.

Each entry is an object with exactly two keys:

```text
evidence_id
field_mask
```

`evidence_id` must identify a currently active evidence record.

Each repair target is unique.

`field_mask` is an unsigned integer in the inclusive range `1..255`.

Every mask must be a subset of the covenant frozen `repair_allowed_field_mask`.

Reserved repair-mask bits are forbidden.

Repair entries appear in the same relative order as their target IDs in `active_evidence_ids_by_covenant`.

The wire does not carry a separate repair generation: every accepted repair entry is deterministically stored with the exact wire `review_generation`.

## 11. Decision-specific invariants

### SERVICE_VERIFIED

`failed_criterion_ids` must be empty.

`failure_classification` must be the empty string.

`repair_authorizations` must be empty.

### PROVIDER_BREACH

`failed_criterion_ids` must be non-empty.

`failure_classification` must equal `SUBSTANTIVE_PROVIDER_BREACH`.

`repair_authorizations` must be empty.

### BUYER_CLAIM_INVALID

`failed_criterion_ids` must be empty.

`failure_classification` must be the empty string.

`repair_authorizations` must be empty.

### EVIDENCE_REPAIR_REQUIRED

`failed_criterion_ids` must be empty because no substantive service breach is established by this intermediate result.

`failure_classification` must equal `REPAIRABLE_EVIDENCE_DEFECT`.

`repair_authorizations` must be non-empty and satisfy every frozen repair rule.

### REVIEW_RETRY_REQUIRED

`failed_criterion_ids` must be empty.

`failure_classification` must equal `TRANSIENT_REVIEW_FAILURE`.

`repair_authorizations` must be empty.

A transient review failure cannot itself create economic entitlement.

## 12. Deterministic consequence mapping

The wire never contains recipient, amount, settlement direction, contract state, closure reason, repair deadline, or retry deadline.

After consensus, deterministic code derives consequences only from validated current covenant state and the accepted exact decision.

`SERVICE_VERIFIED` deterministically records that decision and authorizes the immutable provider side under closure reason `SERVICE_VERIFIED`.

`BUYER_CLAIM_INVALID` deterministically records that decision and authorizes the immutable provider side under closure reason `BUYER_CLAIM_INVALID`.

`PROVIDER_BREACH` deterministically records that decision and authorizes the immutable buyer side under closure reason `PROVIDER_BREACH`.

`EVIDENCE_REPAIR_REQUIRED` enters the matching intermediate state and creates only the exact ordered repair authorization set from the accepted wire.

The repair deadline is derived deterministically from transaction time, the frozen repair window, and the absolute dispute deadline.

`REVIEW_RETRY_REQUIRED` enters the matching intermediate state without changing the active evidence set.

The retry deadline is derived deterministically from transaction time, the frozen retry window, and the absolute dispute deadline.

At maximum review generation, an accepted intermediate repair/retry result remains an intermediate adjudication result and existing neutral generation-exhaustion rules govern subsequent `expire_review`.

## 13. Forbidden wire fields

Because the top-level key set is exact, fields such as the following are rejected:

```text
recipient
amount
payout_amount
settlement_direction
state
closure_reason
repair_deadline
retry_deadline
confidence
confidence_bps
score
probability
rationale
reasoning
analysis
```

No leader, model, validator, frontend, or caller may directly choose an economic recipient or amount through the adjudication wire.

## 14. Malformed-output rule

A malformed, oversized, duplicate-key, noncanonical, unknown-enum, wrong-binding, wrong-type, or decision-inconsistent accepted-wire candidate is rejected.

Malformed leader output never directly authorizes provider payment, buyer refund, repair authority, or any settlement direction.

A model formatting failure cannot be silently transformed into a substantive party judgment.

Any transition to `REVIEW_RETRY_REQUIRED` must itself be independently supported as a transient review failure under the frozen policy and must arrive as a valid exact wire result.

## 15. Independent validator rule

Shape-only validation is forbidden.

Recognizing `decision`, checking hash syntax, or parsing JSON is necessary but not sufficient.

The validator independently retrieves or assesses policy-approved evidence as required, applies the frozen service criteria and evidence rules, and derives its own consequential result.

The validator compares the independently derived consequential result to the leader result across all twelve top-level fields and every repair entry.

Reasoning prose is excluded from the wire so nondeterministic wording cannot create false disagreement or economic authority.

If any consequential field differs, the validator must disagree.

## 16. Deterministic revalidation after consensus

After consensus returns, deterministic code parses the canonical wire again.

It rechecks exact covenant ID, four frozen hashes, review generation, challenged criterion IDs, decision-specific invariants, failed-ID ordering, repair targets, and repair masks against current state.

Only then may deterministic storage state change.

No nondeterministic block writes storage, changes accounting, or emits the external GEN settlement message.

## 17. Reference serialization vector

The reference SERVICE_VERIFIED object uses:

```text
wire_version = 1
covenant_id = 7
service_spec_hash = 64 characters of "1"
delivery_hash = 64 characters of "2"
evidence_policy_hash = 64 characters of "3"
active_evidence_set_hash = 64 characters of "4"
review_generation = 1
decision = "SERVICE_VERIFIED"
challenged_criterion_ids = ["accuracy","freshness"]
failed_criterion_ids = []
failure_classification = ""
repair_authorizations = []
```

Its canonical JSON UTF-8 length is 573 bytes.

Its canonical JSON SHA-256 is `5b2f175973c8bb8eda1b7208f19bbbfd9aa2d39db8d6c8c67b1fb2520a255b2a`.

This SHA is a serialization test vector only and is not a covenant protocol hash.

## 18. Remaining pre-implementation freeze

After this wire shape is frozen, the remaining pre-implementation gate is the exact supported GenLayer dependency, linter, test-tool, and runtime pin set.
