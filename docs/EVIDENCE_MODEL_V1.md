# Accord402 V1 — Evidence Model

> **Security amendment:** `docs/SECURITY_HARDENING_V2.md` supersedes any conflicting weaker V1 rule in this document.

## Goal

Accord402 does not treat a URL, page hash, LLM output, or provider assertion as trustworthy merely because it exists.

Evidence must be bound to the covenant before it can drive a consequential adjudication, and validators must independently verify the substance of the leader result against the same permitted evidence policy.

## Evidence-policy boundary

Each funded covenant freezes an evidence policy containing, at minimum:

- policy version;
- approved evidence authority identities;
- approved canonical source prefixes or source classes;
- maximum evidence age;
- required corroboration count where applicable;
- required fields/content shape;
- whether rendered-page evidence is permitted;
- repair policy;
- replay scope;
- adjudication criteria version.

The evidence policy hash is consequential and immutable after funding.

### Authority-binding key uniqueness

Within one covenant, `(authority_id, authority_revision)` is the exact authority-resolution key for evidence records and must identify exactly one frozen authority binding.

The complete authority-binding list must not contain the same pair more than once.

Changing role, identity kind, identity value, canonical origin, or list position does not make a duplicate authority pair valid.

Every initial or repaired evidence record must resolve its authority pair to exactly one approved binding before that evidence can enter the active evidence set.

A different revision of the same authority does not automatically constitute an independent corroborating authority. Corroboration independence remains determined by the frozen approved authority identity.

A challenge cannot broaden the authority set.

A provider cannot add a new trusted publisher merely because existing evidence is unfavorable.

## Evidence record

Each evidence record must bind stable fields such as:

```text
evidence_id
covenant_id
issuer / authority
canonical_source
immutable_version_or_record_id
published_at
observed_at
expires_at
content_digest
subject
kind
```

The exact persisted representation must use GenLayer storage-compatible types and sized integers.

## Evidence identity and replay

An evidence ID is not merely cosmetic.

The contract must prevent reuse within the frozen replay scope. At minimum, the key must bind:

Evidence-ID uniqueness is stricter than issuer-scoped replay protection.

Every non-empty `evidence_id` is unique within its covenant across all approved authorities, all evidence roles, and all evidence generations.

Once an `evidence_id` has appeared in any evidence-history record for covenant `C`, that same literal `evidence_id` must never be accepted again for covenant `C`, even under a different authority, authority revision, role, repair generation, or source.

Therefore every covenant records a covenant-wide evidence-ID reservation independently of issuer identity.

The canonical covenant-wide reservation key is `I|<covenant-key>|<evidence-id>`.

Authority IDs and evidence IDs must reject the `|` character before any replay or reservation key is constructed.

The `I|...` reservation is monotonic and may move only from absent/false to true. It is never cleared by repair, expiry, settlement, or closure.

The authority-aware replay key remains separately required by the covenant's frozen `COVENANT` or `GLOBAL` replay scope.

For `COVENANT` replay scope, the canonical authority-aware key is `C|<covenant-key>|<authority-id>|<evidence-id>`.

For `GLOBAL` replay scope, the canonical authority-aware key is `G|<authority-id>|<evidence-id>`.

Acceptance of a new evidence record requires both its covenant-wide `I|...` reservation key and its applicable authority-aware replay key to be unused.

Both keys become used atomically with successful evidence-record insertion.

A failed or reverted evidence insertion must consume neither key.

This invariant guarantees that an active evidence ID resolves to at most one `EvidenceRecord` in one covenant, regardless of authority.

```text
covenant
issuer
kind
evidence_id
```

If a broader cross-covenant replay restriction is required for the evidence kind, that rule must be explicit rather than inferred.

Evidence from covenant A must never satisfy covenant B solely because the URL or digest matches.

## Canonical source handling

Mutable or parser-ambiguous source identifiers are reviewer-risky.

Where evidence relies on immutable repository content, V1 should require a canonical form with:

- approved publisher/repository identity;
- exact immutable commit/version identifier;
- parser-stable path;
- no dot-segment aliases;
- no percent-encoded path aliases;
- no backslash aliases;
- no query/fragment identity tricks;
- no mutable branch as immutable evidence.

For ordinary live web sources where immutable snapshots are impossible, the covenant must instead bind the authority/source class, observation/freshness rules, and corroboration requirement. The contract must not pretend a live page is immutable.

## Freshness

Consequential evidence must satisfy all frozen time rules.

At minimum:

```text
published_at <= observed_at
observed_at <= adjudication transaction time
adjudication_time - observed_at <= max_evidence_age
expires_at > adjudication transaction time
```

Exact rules may vary by evidence kind but must be deterministic.

Future timestamps, expired evidence, impossible ordering, missing timestamps, or wrong integer/string types are rejected or routed to a defined repair state.

## Corroboration

High-consequence facts should not be accepted from multiple URLs controlled by the same authority and called independent corroboration.

Where the covenant requires independent corroboration, the policy must define what independence means, for example:

- different approved publisher owners;
- different signed issuer identities;
- distinct authoritative systems.

The exact rule must be machine-checkable before it is relied on.

## Web access

Web/API calls are nondeterministic and must occur inside GenLayer nondeterministic execution.

The leader should:

1. fetch permitted evidence;
2. check objective envelope/provenance/freshness rules;
3. extract only the stable facts required by the service criteria;
4. return a compact structured adjudication result.

Validators must independently verify the leader's substance. A validator that only checks JSON shape, enum membership, non-empty prose, or a confidence range is forbidden.

## Prompt-injection boundary

Web content is untrusted data, not instructions.

The adjudication prompt must clearly separate:

- frozen covenant criteria;
- trusted policy instructions;
- untrusted provider delivery;
- untrusted retrieved evidence.

Retrieved pages must never be allowed to redefine the covenant, change trusted authorities, change payout addresses, alter deadlines, or instruct the model to ignore policy.

Where objective parsing can reject evidence before LLM use, it should.

## Exact consequential result

The accepted adjudication result must bind at least:

```text
covenant_id
service_spec_hash
delivery_hash
evidence_policy_hash
active_evidence_set_hash
decision
failed_criteria
```

Any field that changes who receives value is exact-match consequential data.

Incidental prose may vary, but it cannot drive settlement.

## Repairable evidence failures

Evidence failures are classified before economic consequence.

Examples intended for `EVIDENCE_REPAIR_REQUIRED`:

- wrong or missing digest;
- unsupported/mutable source form;
- stale or expired evidence;
- missing required evidence record;
- wrong approved authority binding;
- objective HTTP 4xx evidence record failure where the provider can submit a corrected permitted reference.

A repair may change only repair-authorized evidence fields.

Repair authority is itself a consequential consensus output.

Only an accepted `EVIDENCE_REPAIR_REQUIRED` adjudication may create repair authority.

That adjudication must bind an exact ordered non-empty repair authorization set.

Each repair authorization entry identifies exactly one evidence ID from the current active evidence set and one exact repair-field mask.

The repair-field mask may authorize only fields permitted by the covenant's frozen repair policy.

No repair authorization may target an inactive, historical, replaced, foreign-covenant, or nonexistent evidence record.

No frontend, buyer, provider, caller, administrator, or later retry may broaden the accepted repair authorization.

It must not change:

- buyer;
- provider;
- amount;
- service specification;
- service criteria;
- delivery result;
- delivery hash;
- original delivery timestamp;
- payout recipients.

A repaired evidence record requires a fresh evidence ID and must satisfy the same frozen authority policy.

V1 repair is atomic over the complete accepted repair authorization set.

A repair transaction must supply exactly one replacement for every authorized evidence ID and no replacement for any unauthorized evidence ID.

Each replacement must preserve every field not authorized by its exact repair-field mask.

Each replacement remains bound to the same covenant, delivery, authority policy, and replay policy.

Successful repair appends each replacement to immutable evidence history and replaces only the authorized active evidence IDs in their existing ordered positions.

The resulting ordered active evidence set determines one new exact active evidence-set hash.

The complete repair authorization set is consumed atomically on successful repair and cannot be reused.

Successful repair is valid only when the current `review_generation` is strictly below `max_review_generations`.

For a valid repair at generation `N`, the complete accepted repair authorization for generation `N` is consumed atomically, the repaired active evidence set is committed, and `review_generation` changes exactly once from `N` to `N + 1` before the covenant returns to `CHALLENGED` for fresh adjudication.

Missing, extra, duplicate, stale, inactive, replayed, or unauthorized replacements must revert without modifying evidence history, active evidence selection, active evidence-set hash, review generation, repair authorization, deadlines, or covenant state.

## Review-generation evidence semantics

Generation `0` means no challenged evidence review generation has been allocated.

A valid buyer challenge allocates generation `1`; therefore the first challenged adjudication always evaluates generation `1`.

Every challenged evidence review and every accepted consequential adjudication result must bind the exact current `review_generation`.

Adjudication itself does not increment `review_generation`.

An accepted terminal `SERVICE_VERIFIED`, `PROVIDER_BREACH`, or `BUYER_CLAIM_INVALID` result ends semantic review without allocating another generation.

An accepted `EVIDENCE_REPAIR_REQUIRED` result at generation `N` binds its complete ordered repair authorization to generation `N` and does not itself increment the generation.

When `N < max_review_generations`, successful complete repair allocates exactly generation `N + 1` after committing the repaired active evidence set.

When `N == max_review_generations`, no repair transaction is valid. The intermediate result represents neutral review-generation exhaustion and may be closed permissionlessly through `expire_review` with closure reason `REVIEW_EXPIRED`.

Generation-exhaustion `expire_review` invalidates any active repair authorization without deleting its immutable authorization history.

An accepted `REVIEW_RETRY_REQUIRED` result at generation `N` does not itself increment the generation and does not alter the active evidence set.

When `N < max_review_generations`, one valid retry allocates exactly generation `N + 1` before fresh adjudication while preserving the same active evidence IDs and exact active evidence-set hash.

When `N == max_review_generations`, no retry transaction is valid. The intermediate result represents neutral review-generation exhaustion and may be closed permissionlessly through `expire_review` with closure reason `REVIEW_EXPIRED`.

Rejected, reverted, malformed, duplicate, stale-generation, unauthorized, or otherwise unsuccessful repair/retry attempts do not consume a generation.

No evidence transition may produce `review_generation > max_review_generations`.

`CHALLENGED` at `review_generation == max_review_generations` is not itself exhausted. The already allocated generation must still be allowed to reach a trustworthy adjudication result.

Generation equality alone cannot authorize `expire_review` while the covenant remains `CHALLENGED`.

Generation exhaustion does not establish evidence falsity, provider breach, or an invalid buyer claim and creates no corresponding reputation judgment.

The absolute dispute deadline remains an independent liveness bound and is never changed or extended by generation allocation, repair, retry, or generation exhaustion.

## Retryable infrastructure failures

Failures that do not establish party fault belong in `REVIEW_RETRY_REQUIRED`, for example:

- temporary HTTP 5xx;
- validator/web transport failure;
- malformed model response where no reliable substantive judgment was reached;
- temporary inability to obtain required independent evidence.

Retry does not silently mutate the covenant or delivery.

## Evidence storage minimization

Raw dynamic web pages should not be stored on-chain merely for completeness.

Persist:

- identity;
- canonical reference;
- stable extracted fields needed for adjudication;
- digests;
- timestamps;
- final structured decision data.

Reviewer evidence may preserve off-chain raw response bytes separately where reproducibility requires it, but those artifacts must be explicitly distinguished from canonical contract state.

## Evidence trust reviewer questions

Before implementation passes:

1. Who is trusted?
2. Where is that trust bound?
3. Can a party change the trusted authority after funding?
4. Can mutable content masquerade as immutable evidence?
5. Can stale evidence settle a new covenant?
6. Can one issuer masquerade as independent corroboration?
7. Can an evidence ID be replayed?
8. Can repair change the work being judged?
9. Do validators independently consult permitted evidence?
10. Can untrusted page text redefine the adjudication policy?

Any unanswered question blocks deployment.
