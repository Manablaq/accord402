# Accord402 V1 — Preimplementation Semantics Amendment V3

Status: FROZEN BEFORE CONTRACT IMPLEMENTATION

## 1. Scope and precedence

This document is an append-only clarification of Accord402 V1 adjudication-failure handling discovered during the Step 2 implementation audit.

It does not modify the bytes or SHA-256 identities of any previously frozen Accord402 document.

Where an earlier frozen document leaves one of the subjects below ambiguous, this amendment controls the V1 implementation.

This amendment creates no new public method, parameter, return type, persistent storage field, covenant state, adjudication decision, failure-classification value, closure reason, repair-mask bit, hash-preimage field, adjudication-wire field, settlement path, privilege, or toolchain dependency.

The subjects clarified here are limited to:

- terminal-capable evidence structure at delivery and after repair;
- exact HTTP response classification for adjudication;
- exact raw-body content-digest semantics;
- exact text-decoding behavior for semantic review;
- precedence when transient, repairable, and unrepairable evidence conditions coexist;
- exact treatment of an evidence defect that cannot be represented by the frozen repair ABI/policy;
- consequential use of `LIVE` evidence.

## 2. Terminal-capable structural evidence

Amendment V1 freezes that `LIVE` evidence cannot satisfy the primary or corroboration requirement for a settlement-authorizing terminal semantic decision.

Amendment V2 freezes that a valid delivery must establish the minimum active evidence structure required for a later consequential adjudication.

Read together, V1 implementation must require the delivery-time structural primary and corroborator capacity to be terminal-capable.

Therefore, before `submit_delivery` succeeds, the active evidence set must contain:

1. at least one admitted `PRIMARY` record whose `source_kind` is exactly `IMMUTABLE` or `VERSIONED`; and
2. at least `required_corroboration_count` distinct qualifying `CORROBORATOR` independent-authority keys represented by admitted records whose `source_kind` is exactly `IMMUTABLE` or `VERSIONED`;
3. no counted corroborator key may equal any counted primary independent-authority key.

A `LIVE` record may still be admitted as additional diagnostic/non-consequential evidence when it independently passes all ordinary deterministic admission rules, but it never counts toward this structural terminal-capacity requirement.

The same terminal-capacity rule is rechecked over the complete post-repair active evidence set before a repair may commit.

Repair cannot change `source_kind` or `is_primary`, so a repair may not silently turn a structurally non-terminal evidence slot into terminal authority evidence.

## 3. HTTP response status classes

V1 web evidence retrieval uses the frozen runtime's contract-visible HTTP response status and body. The implementation must not infer a final effective URL or redirect history that the frozen runtime does not expose.

For adjudication, a returned HTTP status is classified exactly as follows.

### 3.1 Successful retrieval

Any integer status from `200` through `299` inclusive is a successful HTTP retrieval for content-digest and semantic-processing purposes.

### 3.2 Transient review failure

The following conditions are `TRANSIENT_REVIEW_FAILURE` conditions:

- web transport throws before a usable response is returned;
- the response status cannot be represented as an integer;
- status is `408`;
- status is `425`;
- status is `429`;
- status is any integer from `500` through `599` inclusive;
- a status in the `100` through `199` range is surfaced as the final contract-visible result;
- a status in the `300` through `399` range is surfaced as the final contract-visible result;
- any other non-2xx status outside the exact repairable-4xx rule below for which V1 cannot establish a correctable frozen evidence-reference defect.

A transient condition does not create party fault and does not authorize settlement.

### 3.3 Repairable HTTP 4xx reference failure

An integer status from `400` through `499` inclusive, except `408`, `425`, and `429`, is treated as an objective evidence-reference defect only when the covenant permits `CANONICAL_SOURCE` repair.

For that active evidence record, the exact repair requirement contributed by the HTTP status is:

```text
CANONICAL_SOURCE
```

No authority, timestamp, digest, source-kind, subject, kind, or primary-role repair bit is inferred from the HTTP status alone.

The replacement source must still:

- satisfy the complete canonical-source grammar;
- remain within or move only through an independently authorized frozen authority binding as permitted by the complete accepted repair mask;
- preserve every non-repairable field;
- use a fresh covenant-wide evidence ID;
- pass replay rules;
- pass the same delivery/evidence policy on re-entry.

If `CANONICAL_SOURCE` repair is not permitted by the covenant, that 4xx condition is an unrepairable evidence defect under Section 7 rather than a transient failure.

This rule does not claim that every replacement URL will succeed. It only identifies the exact field that must change before the failed reference can be retried as repaired evidence.

## 4. Raw-body content-digest semantics

For a successful 2xx retrieval, `content_digest` means exactly:

```text
lowercase_hex(SHA256(exact_raw_HTTP_response_body_bytes))
```

The digest is computed over the response body bytes exactly as exposed to the Intelligent Contract by the frozen runtime.

Digest computation occurs before any UTF-8 decoding, whitespace handling, JSON parsing, HTML parsing, model prompting, text extraction, or other content interpretation.

No newline normalization, Unicode normalization, transcoding, trimming, decompression invented by Accord402, canonical JSON conversion, or parser reserialization is performed by the contract before this SHA-256 computation.

Transport processing already performed by the frozen runtime before it exposes `response.body` is outside Accord402's contract-visible semantics.

A digest mismatch is an objective evidence defect.

If `CONTENT_DIGEST` repair is permitted, the exact repair requirement contributed by that mismatch is:

```text
CONTENT_DIGEST
```

If `CONTENT_DIGEST` repair is not permitted, the mismatch is an unrepairable evidence defect under Section 7.

The contract never changes the stored digest automatically.

## 5. Text decoding for V1 semantic review

Accord402 V1 freezes no binary-document, image, archive, or arbitrary-character-set semantic codec for web evidence.

After raw-body digest verification succeeds, evidence content supplied to the V1 text semantic adjudication path must decode as strict UTF-8.

Lossy decoding with replacement characters is forbidden for consequential semantic review.

If a digest-valid 2xx body does not decode as strict UTF-8, V1 treats the current review as `TRANSIENT_REVIEW_FAILURE`.

This classification creates no party fault, no repair authorization, and no terminal settlement decision.

A later protocol version may freeze additional binary/image/document codecs separately.

## 6. Objective freshness repair contributions

Active evidence is re-evaluated against the deterministic adjudication transaction timestamp.

When an otherwise admitted record becomes stale because:

```text
adjudication_time - observed_at > max_evidence_age
```

the exact objective repair requirement contributed by that defect is:

```text
OBSERVED_AT
```

when that bit is permitted by the covenant.

When:

```text
expires_at <= adjudication_time
```

the exact objective repair requirement contributed by that defect is:

```text
EXPIRES_AT
```

when that bit is permitted by the covenant.

When both independently established defects exist, the record's exact objective mask contains both bits.

If a required bit is not permitted by the covenant, the corresponding condition is an unrepairable evidence defect under Section 7.

`published_at > observed_at` and an observation timestamp that is already in the future at evidence insertion are deterministic admission failures. V1 does not commit such a record and later invent a repair authorization for an invalid stored envelope.

## 7. Unrepairable evidence defect

An unrepairable evidence defect exists when a trustworthy adjudication establishes an evidence defect but curing that complete defect would require at least one of:

- a non-repairable field;
- a repair bit outside the covenant's immutable `repair_allowed_field_mask`;
- a repair bit outside the V1 `0x000000FF` universe;
- addition or deletion of an active evidence slot;
- changing `source_kind`, `subject`, `kind`, `is_primary`, covenant, delivery, settlement recipient, or settlement amount;
- a field change whose exact necessary minimal repair mask cannot be independently established.

An unrepairable evidence defect is not:

- `PROVIDER_BREACH`;
- `BUYER_CLAIM_INVALID`;
- `SERVICE_VERIFIED`;
- `EVIDENCE_REPAIR_REQUIRED`;
- `REVIEW_RETRY_REQUIRED` unless a separate transient condition independently exists.

V1 intentionally adds no new wire decision or failure-classification value for this condition.

When an unrepairable evidence defect is the blocking condition and no transient condition exists, challenged adjudication must not emit an accepted consequential wire result.

The adjudication attempt therefore leaves persistent state unchanged.

The covenant remains bounded by its immutable absolute dispute deadline.

If no trustworthy consequential judgment becomes possible before that deadline, `expire_review` produces the already-frozen neutral buyer-side `REVIEW_EXPIRED` liveness outcome.

This neutral expiry does not establish provider breach or an invalid buyer claim and creates no dispute-merit reputation judgment.

## 8. Complete-repair-set precedence

An `EVIDENCE_REPAIR_REQUIRED` wire must contain the complete exact ordered repair authorization set for the current active evidence set.

Therefore the implementation evaluates the current active evidence set as a whole before producing an intermediate wire.

Precedence is exactly:

1. if any active record cannot be reliably assessed because of a transient review condition, the only accepted intermediate result for that attempt is `REVIEW_RETRY_REQUIRED`;
2. otherwise, if any unrepairable evidence defect exists, no accepted adjudication wire is produced for that attempt;
3. otherwise, if one or more repairable evidence defects exist, the result is `EVIDENCE_REPAIR_REQUIRED` with the exact complete ordered repair set;
4. otherwise, terminal semantic adjudication may proceed if all previously frozen terminal-authority and corroboration requirements are satisfied.

A repairable defect found on one record never permits the contract to omit an unknown defect on another record merely because retrieval of that other record failed transiently.

This rule preserves Amendment V2's exact-completeness and minimal-mask requirements.

## 9. Exact repair-mask union

For one active evidence record, the accepted repair mask is the bitwise OR of every independently established necessary repair contribution for that record.

Only fields that are actually necessary to change may appear.

Every bit present in an accepted authorization must correspond to a field that changes in the successful replacement.

A successful repair may not consume review generation with a no-op value for an authorized field.

Every field whose bit is absent must remain exactly equal to the replaced active record.

The fresh replacement `evidence_id` remains mandatory and is not represented by a mask bit.

If independently established defects cannot be represented by one complete permitted exact mask, the record is unrepairable under Section 7.

## 10. Consequential use of LIVE evidence

The earlier Amendment V1 rule is made operationally explicit.

`LIVE` evidence may be fetched to establish objective envelope, freshness, digest, repair, or retry conditions.

Its content may be used only for diagnosis or other non-consequential context.

`LIVE` content must not be supplied as evidence that determines `failed_criterion_ids` for a settlement-authorizing semantic decision.

The semantic criterion evaluation that can produce:

```text
SERVICE_VERIFIED
PROVIDER_BREACH
BUYER_CLAIM_INVALID
```

uses only qualifying active `IMMUTABLE` or `VERSIONED` evidence content after all objective checks pass.

This restriction applies even when the active set also contains enough separate immutable/versioned primary and corroborator authority evidence.

## 11. Provider delivery remains semantic input

The frozen provider `delivery_payload` is untrusted data but is part of the substance being adjudicated.

A semantic review that may produce a terminal decision must evaluate the challenged criteria against:

- the frozen service specification and challenged criteria;
- the frozen provider `delivery_payload`;
- the qualifying active terminal evidence;
- the frozen evidence/authority policy.

Binding only `delivery_hash` in the consequential wire is not a substitute for supplying the actual frozen delivery content to the independent semantic review.

The delivery remains immutable after successful `submit_delivery`.

## 12. No other semantic changes

All earlier frozen rules remain in force, including:

- exact thirteen-write and twelve-view public ABI;
- zero-argument constructor;
- exact persistent root-storage and record shapes;
- exact four protocol hash preimages and reference vectors;
- exact canonical-source grammar and opaque-redirect amendment;
- exact replay-key namespaces;
- exact states, closure reasons, settlement directions, and generation rules;
- exact twelve-field adjudication wire;
- exact four failure-classification values;
- exact terminal decision distinction from Amendment V2;
- exact repair-field universe and non-repairable fields;
- exact settlement recipient and amount derivation;
- finality-only external GEN transfer;
- exact reputation-counter semantics;
- frozen GenLayer runner and toolchain;
- no privileged economic path.

This amendment creates no Git commit, deployment authorization, or blockchain transaction authorization.

## 13. Implementation stop rule

Contract implementation may proceed only after this amendment is byte-frozen and independently certified together with the earlier frozen foundation.

If another consequential ambiguity is discovered, implementation must stop again rather than silently choosing a value-affecting behavior in code.
