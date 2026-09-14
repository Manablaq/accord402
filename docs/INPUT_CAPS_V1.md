# Accord402 V1 — Frozen Input Caps

## 1. Purpose

These are protocol-level safety bounds, not claims about the largest payload the GenLayer transport can technically carry.

The contract rejects out-of-cap input before hashing, canonical-source parsing, persistent insertion, web access, LLM use, or nondeterministic adjudication whenever the relevant validation can be performed first.

All string limits are measured as the byte length of the string encoded as UTF-8, not Unicode code-point count.

For nested public inputs, both each field cap and the applicable aggregate dynamic-string-byte cap must pass.

No truncation is permitted. Over-cap input reverts rather than being shortened or silently normalized to fit.

## 2. Global collection caps

```text
MAX_CRITERIA                    = 16
MAX_AUTHORITY_BINDINGS          = 16
MAX_INITIAL_EVIDENCE            = 16
MAX_CHALLENGED_CRITERIA         = 16
MAX_REPAIR_REPLACEMENTS         = 16
MAX_REQUIRED_CORROBORATION       = 8
MAX_REVIEW_GENERATIONS           = 4
```

`criteria` must contain at least one and at most 16 entries.

`authority_bindings` must contain at least one and at most 16 entries.

Initial delivery evidence must contain at least one and at most 16 evidence records.

`challenged_criterion_ids` must contain at least one and at most 16 IDs, contain no duplicate ID, and every ID must identify a criterion frozen for that covenant.

`replacements` must contain at least one and at most 16 records and must still exactly equal the complete active repair-authorization target set.

`required_corroboration_count` must be between 0 and 8 inclusive and can never require more qualifying corroborators than the frozen evidence/authority policy can supply.

`max_review_generations` must be between 1 and 4 inclusive.

The repair mask remains independently restricted to the frozen V1 universe `0x00000000` through `0x000000FF`, subject to the existing nonzero authorization-entry rule.

## 3. Per-string UTF-8 byte caps

```text
service_spec                       8192
criterion_id                         64
criterion_text                     2048
authority_id                        128
role                                 32
identity_kind                        32
identity_value                      512
canonical_origin                    512
delivery_payload                  16384
evidence_id                         128
replaces_evidence_id                128
subject                             512
kind                                 64
source_kind                          32
canonical_source                   2048
immutable_version_or_record_id      512
content_digest                       64
challenge_claim                    4096
replay_scope                          8
```

Every non-empty identifier or text field must satisfy both its semantic validation rules and its byte cap.

`content_digest` is not merely capped at 64 bytes: V1 requires exactly 64 ASCII bytes containing lowercase hexadecimal SHA-256 with no `0x` prefix.

`replay_scope` remains the exact frozen enum `COVENANT` or `GLOBAL`; the 8-byte bound is only a defensive envelope.

Authority IDs and evidence IDs continue to reject `|` regardless of byte length.

## 4. Aggregate dynamic-string budgets per write

The aggregate budget is the sum of UTF-8 byte lengths of every string leaf supplied in that method call, including strings inside nested input records and lists.

```text
open_covenant                     65536 bytes
submit_delivery                   98304 bytes
challenge_delivery                 8192 bytes
submit_evidence_repair            65536 bytes
```

Methods with no caller-supplied dynamic string input have no separate dynamic-string aggregate budget.

An argument set that satisfies every individual field cap but exceeds its method aggregate budget still reverts.

These aggregate limits prevent nested arrays from bypassing the individual-field bounds.

## 5. Deadline and liveness caps

All deadline validation uses the normalized GenLayer transaction timestamp `now` for the successful `open_covenant` execution.

The following V1 constants are exact seconds:

```text
MIN_FUTURE_DEADLINE_SECONDS          = 60
MAX_ACCEPTANCE_HORIZON_SECONDS       = 604800
MAX_DELIVERY_HORIZON_SECONDS         = 1209600
MIN_CHALLENGE_DURATION_SECONDS       = 60
MAX_CHALLENGE_DURATION_SECONDS       = 604800
MIN_REPAIR_WINDOW_SECONDS            = 60
MAX_REPAIR_WINDOW_SECONDS            = 86400
MIN_RETRY_WINDOW_SECONDS             = 60
MAX_RETRY_WINDOW_SECONDS             = 86400
MIN_POST_CHALLENGE_REVIEW_HEADROOM   = 3600
MAX_ABSOLUTE_DISPUTE_HORIZON_SECONDS = 2592000
MAX_EVIDENCE_AGE_SECONDS             = 2592000
```

Funding is valid only if `acceptance_deadline >= now + 60` and `acceptance_deadline <= now + 604800`.

Funding is valid only if `delivery_deadline > acceptance_deadline` and `delivery_deadline <= now + 1209600`.

`challenge_duration` must be between 60 and 604800 seconds inclusive.

`evidence_repair_window` must be between 60 and 86400 seconds inclusive.

`review_retry_window` must be between 60 and 86400 seconds inclusive.

`max_evidence_age` must be greater than zero and at most 2592000 seconds.

The absolute dispute deadline must be strictly later than the delivery deadline.

The absolute dispute deadline must also be at least `delivery_deadline + challenge_duration + 3600`, using checked arithmetic.

The absolute dispute deadline must be at most `now + 2592000`.

These bounds ensure that even a delivery made at the latest permitted delivery time still has its complete challenge window plus at least one hour of dispute headroom before the absolute dispute deadline.

All additions used to validate deadline bounds must be checked for `u64` overflow before comparison.

After funding, none of these deadlines or windows may be extended.

## 6. Numeric input bounds

`principal` must be positive, must fit `u256`, and `gl.message.value` must equal it exactly.

V1 does not impose a smaller arbitrary GEN-denominated principal ceiling in this cap gate.

Before accepting funding, additions to `total_funded` and `total_outstanding` must be proven to remain inside `u256`; overflow must revert.

`authority_revision` must fit `u32`.

`required_corroboration_count`, `repair_allowed_field_mask`, and `max_review_generations` must be range-checked explicitly before their values are relied upon.

## 7. Evidence-history growth bound

The active evidence set contains at most 16 records.

Because `max_review_generations <= 4`, successful repair can allocate at most generations 2, 3, and 4 after the initial challenged generation 1.

Therefore a covenant can append at most 64 evidence-history records in V1 if all 16 active records are replaced at every possible successful repair generation.

An accepted repair-required result at the maximum generation may persist authorization history for audit but cannot append replacement evidence because repair execution is forbidden there.

Retry review creates no evidence records and therefore cannot increase evidence-history size.

## 8. Validation-order safety

Collection counts are checked before iterating caller-provided collections.

Individual string byte caps are checked before expensive canonicalization, digest verification, web access, or nondeterministic processing.

Aggregate dynamic-string budgets are checked before any web access or nondeterministic processing.

Duplicate criterion IDs, duplicate challenged criterion IDs, duplicate evidence IDs, duplicate replacement targets, and duplicate replacement evidence IDs are rejected before consequential processing.

Duplicate `(authority_id, authority_revision)` pairs in `authority_bindings` are rejected before consequential processing or covenant creation.

A failure of any cap check reverts without consuming covenant IDs, evidence replay keys, repair authority, review generations, escrow accounting, or settlement state.

## 9. No security meaning from size alone

Passing a size cap never establishes authority, freshness, correctness, corroboration, canonicality, or semantic validity.

All frozen evidence, replay, repair, adjudication, state-machine, accounting, and settlement checks remain independently mandatory.

## 10. Remaining pre-implementation freezes

This gate freezes V1 input size, count, timing-horizon, and review-generation bounds.

It does not yet freeze:

- exact service-specification hash preimage;
- exact evidence-policy hash preimage;
- exact delivery hash preimage;
- exact active evidence-set hash preimage;
- exact canonical source/URL normalization algorithm;
- exact adjudication-result wire shape and parser rules;
- exact supported GenLayer dependency, linter, and test-tool pins.

