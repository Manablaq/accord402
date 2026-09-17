# Accord402 V1 — Storage and Public ABI Freeze

> **Payout-liveness amendment:** `docs/SECURITY_HARDENING_V4.md` supersedes conflicting persistent-credit and payout-withdrawal semantics.

> **Settlement-liveness amendment:** `docs/SECURITY_HARDENING_V3.md` supersedes conflicting payout-recipient and vault-withdrawal semantics.

> **Security amendment:** `docs/SECURITY_HARDENING_V2.md` supersedes any conflicting weaker V1 rule in this document.

Status: STORAGE TYPES AND ROOT SCHEMA FROZEN; PUBLIC ABI, INPUT CAPS, HASH PREIMAGES, AND TOOLCHAIN PIN NOT YET FROZEN

This document freezes the persistent storage model before contract implementation.

No `contracts/accord402.py` implementation is authorized merely because this storage section exists. Public method signatures, exact input caps, canonical hash preimages, and the pinned supported toolchain must pass later gates first.

## 1. Verified GenLayer storage constraints

The V1 implementation must follow these current GenLayer storage rules:

- every persistent field is declared as a typed class attribute on the `gl.Contract` class;
- persistent ordinary Python `list` and `dict` are forbidden;
- persistent arrays use fully instantiated `DynArray[T]`;
- persistent mappings use fully instantiated `TreeMap[K, V]`;
- custom persistent records use `@allow_storage` plus `@dataclass`;
- persistent integers use sized integer types rather than Python `int`;
- native GEN amounts use `u256`;
- addresses use `Address`;
- timestamps and duration windows use `u64`;
- protocol versions, bounded counts, and review generations use `u32`;
- no V1 storage field uses floating point or `bigint`;
- storage data required by nondeterministic adjudication is copied to memory before the nondeterministic block.

The current transaction datetime source is `gl.message_raw["datetime"]`, an ISO 8601 string. Accord402 stores normalized UTC Unix-second values as `u64`; host wall-clock time is never authoritative.

## 2. Canonical storage encodings

### Covenant identity

`covenant_id` is a positive one-based `u64`. Value `0` is reserved as the unset sentinel.

Persistent covenant-indexed `TreeMap` collections use a canonical decimal string key derived from `covenant_id` with no sign and no leading zeroes.

The stored `CovenantRecord.covenant_id` must exactly match the numeric value represented by its map key.

### Digest fields

All SHA-256 digest fields are stored as canonical lowercase 64-character hexadecimal `str` values with no `0x` prefix.

An empty string is allowed only where the corresponding artifact does not yet exist or the field is explicitly optional.

Non-empty digest values must never be case-folded, truncated, padded, or accepted in an alternate representation.

### Protocol string values

Contract states, adjudication decisions, closure reasons, settlement directions, source kinds, authority roles, identity kinds, and replay scopes are stored as canonical bounded `str` values.

They are compared against exact V1 constants. V1 does not rely on an unverified persistent Python `Enum` representation.

The empty string is the unset sentinel only for fields whose lifecycle permits no value yet.

### Time values

Every persisted timestamp and duration is a non-negative `u64` number of seconds.

Absolute timestamps are UTC Unix seconds. Value `0` is the unset sentinel for lifecycle timestamps that have not yet occurred.

Deadline comparisons follow the frozen rule: an action permitted by a deadline remains valid when `now <= deadline`; expiry becomes valid only when `now > deadline`.

### Replay-key encoding

Authority IDs and evidence IDs must reject the `|` character.

The existing `evidence_replay_keys: TreeMap[str, bool]` stores two distinct namespaces: covenant-wide evidence-ID identity reservations and authority-aware replay reservations.

For every accepted evidence record, the canonical covenant-wide identity reservation key is `I|<covenant-key>|<evidence-id>`.

The `I|...` namespace is independent of authority identity and therefore makes one non-empty evidence ID unique within one covenant across authorities, authority revisions, evidence roles, sources, and evidence generations.

For covenant-scoped authority-aware replay protection the canonical key is `C|<covenant-key>|<authority-id>|<evidence-id>`.

For explicitly global authority-aware replay protection the canonical key is `G|<authority-id>|<evidence-id>`.

Acceptance of a new evidence record requires its `I|...` identity reservation and exactly one authority-aware `C|...` or `G|...` replay reservation, selected by the covenant's frozen replay scope, to both be unused.

Successful insertion appends the evidence record and sets both required keys to true atomically.

A reverted, rejected, malformed, unauthorized, duplicate, or otherwise unsuccessful evidence insertion must leave both keys unused.

Repair replacement records follow the same rule and therefore require a covenant-wide fresh evidence ID.

Because covenant-wide evidence IDs never repeat, each ID in `active_evidence_ids_by_covenant` resolves to at most one historical `EvidenceRecord` for that covenant.

The only V1 replay-scope constants are `COVENANT` and `GLOBAL`.

No replay key is derived from a URL alone.

### Repair-field mask

V1 freezes the repair-field mask as an unsigned `u32` bitset.

The only defined V1 repair bits are:

```text
0x00000001  AUTHORITY_ID
0x00000002  AUTHORITY_REVISION
0x00000004  CANONICAL_SOURCE
0x00000008  IMMUTABLE_VERSION_OR_RECORD_ID
0x00000010  PUBLISHED_AT
0x00000020  OBSERVED_AT
0x00000040  EXPIRES_AT
0x00000080  CONTENT_DIGEST
```

The complete V1 repair-mask universe is therefore `0x000000FF`.

Bits `0x00000100` through `0x80000000` are reserved and must be zero in V1.

`repair_allowed_field_mask` is frozen per covenant at funding and must be a subset of `0x000000FF`.

A zero covenant repair mask means the covenant authorizes no evidence-field repair; such a covenant cannot validly enter `EVIDENCE_REPAIR_REQUIRED`.

Every accepted repair authorization `field_mask` must be nonzero and must be a subset of both the covenant's frozen `repair_allowed_field_mask` and `0x000000FF`.

The replacement `evidence_id` is always required to be fresh and therefore is not represented by a repair-mask bit.

`generation` and `replaces_evidence_id` are deterministic lifecycle fields and are not repair-mask controlled.

`covenant_id`, `subject`, `kind`, `source_kind`, and `is_primary` are not repairable in V1 and must exactly match the record being replaced.

## 3. Persistent record types

Every record below is implemented as `@allow_storage` plus `@dataclass`.

### `CriterionRecord`

```python
@allow_storage
@dataclass
class CriterionRecord:
    covenant_id: u64
    criterion_id: str
    criterion_text: str
```

`criterion_id` is unique inside one covenant. The criterion text is immutable after funding.

### `AuthorityBinding`

```python
@allow_storage
@dataclass
class AuthorityBinding:
    covenant_id: u64
    authority_id: str
    authority_revision: u32
    role: str
    identity_kind: str
    identity_value: str
    canonical_origin: str
```

The binding freezes authority identity before adjudication. `role` identifies the exact policy role such as primary or corroborator. `identity_kind` and `identity_value` bind the approved publisher, issuer identity, signing key identity, or other explicitly reviewed authority mechanism.

An authority URL alone is not sufficient authority identity.

The exact evidence-to-authority lookup key is `(authority_id, authority_revision)` within the covenant.

That pair must be unique across `authority_bindings_by_covenant`; two `AuthorityBinding` records for the same covenant must never share the same pair, even when any other binding field differs.

Every stored `EvidenceRecord` must resolve its `authority_id` and `authority_revision` to exactly one frozen `AuthorityBinding` under the same covenant key.

A duplicate authority pair is invalid funding input and must be rejected before any covenant ID, persistent covenant state, replay key, or accounting value is consumed.

This invariant requires no additional V1 persistent field. The canonical authority-binding collection remains the frozen source of authority data.

### `EvidenceRecord`

```python
@allow_storage
@dataclass
class EvidenceRecord:
    covenant_id: u64
    generation: u32
    evidence_id: str
    authority_id: str
    authority_revision: u32
    subject: str
    kind: str
    source_kind: str
    canonical_source: str
    immutable_version_or_record_id: str
    published_at: u64
    observed_at: u64
    expires_at: u64
    content_digest: str
    is_primary: bool
    replaces_evidence_id: str
```

`source_kind` distinguishes immutable or versioned evidence from mutable live evidence. A mutable source must never be represented as immutable merely because a digest was recorded.

Repair appends a new evidence record with a fresh `evidence_id`; it does not overwrite the historical record it replaces. `replaces_evidence_id` is empty for an original record and identifies the replaced record for a repair.

### Evidence record generation semantics

`EvidenceRecord.generation` is the immutable evidence-record creation generation.

It is not a moving copy of `CovenantRecord.review_generation`, and it is not the generation that authorized replacement of the record.

Every original evidence record accepted with the provider's first valid delivery is stored with `generation == 0`.

Those original evidence records remain generation `0` even after a buyer challenge allocates review generation `1`.

For a successful authorized repair performed from review generation `N`, every newly appended replacement evidence record is stored with `generation == N + 1`.

The replacement evidence record's `replaces_evidence_id` must equal the exact active evidence ID authorized for replacement by the generation-`N` repair authorization.

An unaffected active evidence record is not rewritten merely because another record was repaired; it retains the generation at which that record itself was created.

Therefore one active evidence set may legitimately contain evidence records created in different generations.

The canonical active evidence set is defined by ordered active evidence IDs plus the exact active evidence-set hash, not by requiring every active record to carry the same `EvidenceRecord.generation`.

A review retry creates no evidence record, changes no `EvidenceRecord.generation`, and leaves the active evidence IDs and active evidence-set hash unchanged.

No evidence record may be appended with a generation greater than `max_review_generations`.

Because repair execution is valid only when `N < max_review_generations`, every valid repaired evidence record generation `N + 1` is at most `max_review_generations`.

`EvidenceRecord.generation`, `evidence_id`, and `replaces_evidence_id` are immutable after the record is appended to evidence history.

Historical evidence generation is audit metadata. It never independently authorizes settlement, repair, retry, or expiry.

### `RepairAuthorizationRecord`

```python
@allow_storage
@dataclass
class RepairAuthorizationRecord:
    covenant_id: u64
    generation: u32
    evidence_id: str
    field_mask: u32
```

`generation` is the exact review generation whose accepted `EVIDENCE_REPAIR_REQUIRED` result created the authorization.

`evidence_id` identifies the currently active evidence record that may be replaced.

`field_mask` is interpreted only under the frozen V1 repair-field-mask encoding above.

Repair authorization records are consensus-derived audit history. After creation their fields never change.

### `ProviderStats`

```python
@allow_storage
@dataclass
class ProviderStats:
    accepted_covenants: u64
    deliveries: u64
    non_deliveries: u64
    disputes_won: u64
    disputes_lost: u64
```

### `BuyerStats`

```python
@allow_storage
@dataclass
class BuyerStats:
    funded_covenants: u64
    challenges_filed: u64
    valid_challenges: u64
    invalid_challenges: u64
```

Reputation records are factual counters only. Neutral `REVIEW_EXPIRED` closure does not increment provider disputes won, provider disputes lost, buyer valid challenges, or buyer invalid challenges.

### `CovenantRecord`

```python
@allow_storage
@dataclass
class CovenantRecord:
    covenant_id: u64
    buyer: Address
    provider: Address

    funded_amount: u256
    outstanding_amount: u256
    provider_settlement: u256
    buyer_settlement: u256

    state: str

    service_spec: str
    service_spec_hash: str

    opened_at: u64
    acceptance_deadline: u64
    delivery_deadline: u64
    challenge_duration: u64
    absolute_dispute_deadline: u64
    evidence_repair_window: u64
    review_retry_window: u64
    max_review_generations: u32

    evidence_policy_version: u32
    evidence_policy_hash: str
    max_evidence_age: u64
    required_corroboration_count: u32
    repair_policy_version: u32
    repair_allowed_field_mask: u32
    replay_scope: str
    adjudication_criteria_version: u32
    settlement_rule_version: u32

    accepted_at: u64
    delivered_at: u64
    challenge_deadline: u64
    challenged_at: u64
    repair_deadline: u64
    retry_deadline: u64
    closed_at: u64

    delivery_payload: str
    delivery_hash: str
    active_evidence_set_hash: str
    repair_authorization_generation: u32
    repair_authorization_active: bool

    challenge_claim: str
    review_generation: u32
    adjudication_decision: str
    failure_classification: str
    closure_reason: str
    settlement_direction: str

    settlement_message_scheduled: bool
```

The record deliberately separates contract state, adjudication decision, failure classification, closure reason, and settlement direction.

`settlement_message_scheduled` records that the settlement write scheduled its single external GEN message. It is an anti-replay and audit field only. It is not proof that GEN reached the recipient.

`provider_settlement` and `buyer_settlement` remain zero while a covenant is merely settlement-authorized. Authorization does not reduce `outstanding_amount`.

During the successful `claim_settlement` write, exactly one side settlement field receives the exact prior `outstanding_amount`, `outstanding_amount` becomes zero, the corresponding global closed total is increased by the same amount, `total_outstanding` is reduced by the same amount, `settlement_message_scheduled` becomes true, and the covenant moves to its matching closed state while exactly one finality-only external GEN message is scheduled.

Those storage changes are provisional until the settlement transaction itself becomes canonical. A provisional closed record or true `settlement_message_scheduled` flag is not external payment evidence.

No field stores or claims the GenLayer transaction ID, finality status, `FINISHED_WITH_RETURN`, recipient chain balance, or Ghost balance. Those facts are transaction/client certification evidence and cannot be self-certified by contract storage.

### Review-generation storage lifecycle

`max_review_generations` is immutable after funding and must be positive. Its exact V1 public-input upper cap is frozen separately with the ABI/input-cap gate.

`review_generation` is initialized to `0` when funding succeeds. Generation `0` is reserved to mean that no challenged adjudication generation has yet been allocated.

`repair_authorization_generation` is initialized to `0` and `repair_authorization_active` is initialized to `false`.

Acceptance, delivery, and an unchallenged settlement path leave `review_generation == 0`.

A valid buyer challenge requires `review_generation == 0` and atomically changes it to `1` with the transition to `CHALLENGED`.

After a valid challenge, `review_generation` must never return to `0`.

Every challenged adjudication input and every accepted consequential result binds the exact stored `review_generation`.

Adjudication itself never increments `review_generation`.

An accepted terminal `SERVICE_VERIFIED`, `PROVIDER_BREACH`, or `BUYER_CLAIM_INVALID` result does not increment `review_generation`.

An accepted `EVIDENCE_REPAIR_REQUIRED` result at generation `N` does not increment `review_generation`. It appends the exact consensus-created repair authorization entries with `generation == N`, sets `repair_authorization_generation = N`, and sets `repair_authorization_active = true`.

The active repair authorization is therefore identified by both `repair_authorization_active == true` and authorization-entry generation equal to `repair_authorization_generation`.

When `N < max_review_generations`, a successful complete authorized repair atomically commits the repaired active evidence set, consumes the active authorization, sets `repair_authorization_active = false`, and changes `review_generation` exactly from `N` to `N + 1` before returning to `CHALLENGED`.

After successful repair, `repair_authorization_generation` remains the historical generation of the most recently created repair authorization until a later accepted `EVIDENCE_REPAIR_REQUIRED` result replaces that pointer. The false active flag prevents stale authorization reuse.

An accepted `REVIEW_RETRY_REQUIRED` result at generation `N` does not increment `review_generation` and does not alter the active evidence selection.

When `N < max_review_generations`, one valid retry changes `review_generation` exactly from `N` to `N + 1` before fresh adjudication. The active evidence IDs and active evidence-set hash remain unchanged.

Rejected, reverted, malformed, duplicate, stale-generation, unauthorized, or otherwise unsuccessful repair/retry attempts leave `review_generation` unchanged.

No storage transition may produce `review_generation > max_review_generations`.

If `EVIDENCE_REPAIR_REQUIRED` is accepted when `review_generation == max_review_generations`, its consensus repair authorization may be persisted for audit, but repair execution is forbidden because no next review generation can be allocated.

In that maximum-generation repair state, permissionless `expire_review` produces neutral `REVIEW_EXPIRED`, preserves `review_generation`, invalidates the active repair authorization by setting `repair_authorization_active = false`, and does not delete historical authorization entries.

If `REVIEW_RETRY_REQUIRED` is accepted when `review_generation == max_review_generations`, retry execution is forbidden and permissionless `expire_review` produces neutral `REVIEW_EXPIRED` without changing `review_generation`.

Ordinary repair-deadline closure reason `REPAIR_EXPIRED` is valid only when `review_generation < max_review_generations`; maximum-generation repair exhaustion uses `REVIEW_EXPIRED` instead.

`CHALLENGED` with `review_generation == max_review_generations` is not itself exhausted. Generation equality alone must not authorize `expire_review` while the current challenged generation still has its adjudication opportunity.

The absolute dispute deadline remains independent and may trigger its existing neutral `REVIEW_EXPIRED` path regardless of remaining generation capacity.

Generation allocation, repair, retry, and generation exhaustion must never change or extend the absolute dispute deadline.


## 4. Contract root storage

The canonical V1 root storage is:

```python
class Accord402(gl.Contract):
    covenant_count: u64

    covenants: TreeMap[str, CovenantRecord]
    criteria_by_covenant: TreeMap[str, DynArray[CriterionRecord]]
    authority_bindings_by_covenant: TreeMap[str, DynArray[AuthorityBinding]]
    evidence_records_by_covenant: TreeMap[str, DynArray[EvidenceRecord]]
    active_evidence_ids_by_covenant: TreeMap[str, DynArray[str]]
    repair_authorizations_by_covenant: TreeMap[str, DynArray[RepairAuthorizationRecord]]
    challenged_criterion_ids_by_covenant: TreeMap[str, DynArray[str]]
    failed_criterion_ids_by_covenant: TreeMap[str, DynArray[str]]

    evidence_replay_keys: TreeMap[str, bool]

    provider_stats: TreeMap[Address, ProviderStats]
    buyer_stats: TreeMap[Address, BuyerStats]

    total_funded: u256
    total_closed_to_provider: u256
    total_closed_to_buyer: u256
    total_outstanding: u256
```

No V1 root storage field represents an owner, administrator, treasury, fee recipient, arbitrary payout recipient, mutable settlement destination, upgrade authority, emergency escrow withdrawal authority, or governance role.

V1 has one canonical contract and zero protocol fee.

### Collection ownership

Every covenant-indexed collection key is the canonical covenant decimal key.

Every `CriterionRecord`, `AuthorityBinding`, and `EvidenceRecord` stored under that key must contain the matching numeric `covenant_id`.

`criteria_by_covenant` and `authority_bindings_by_covenant` become immutable after successful funding.

`evidence_records_by_covenant` is append-only after funding. Repair appends; it never deletes or rewrites historical evidence.

`active_evidence_ids_by_covenant` is the canonical ordered active evidence selection for the covenant.

Initial delivery stores the accepted evidence IDs in exact canonical order.

Evidence history and active evidence selection are separate: historical records remain append-only even after they cease to be active.

A successful repair replaces only authorized active evidence IDs in their existing array positions; it must not reorder unaffected active evidence.

`repair_authorizations_by_covenant` is append-only consensus-derived authorization history.

For the currently active repair set, entries whose `generation` equals `CovenantRecord.repair_authorization_generation` define the exact ordered authorization set created by the accepted `EVIDENCE_REPAIR_REQUIRED` result.

`repair_authorization_active` may become true only when that exact accepted result has been deterministically validated and persisted.

A new repair authorization set must not be created while `repair_authorization_active` is already true.

When `review_generation < max_review_generations`, successful repair sets `repair_authorization_active` to false atomically with replacement, active-set-hash recomputation, and the exact `N` to `N + 1` review-generation increment.

Any deterministic expiry or terminal transition out of `EVIDENCE_REPAIR_REQUIRED` also invalidates the active authorization by setting `repair_authorization_active` to false; historical authorization records remain preserved.

`challenged_criterion_ids_by_covenant` is empty before challenge and becomes immutable after the single valid challenge.

`failed_criterion_ids_by_covenant` is written only from an accepted exact consequential adjudication result and otherwise remains empty.

`evidence_replay_keys` is monotonic across every `I|...`, `C|...`, and `G|...` namespace: a key may move only from absent/false to true and may never be cleared.

Repair, replacement, expiry, settlement authorization, settlement execution, and terminal closure must never clear an identity or replay reservation.

### Covenant existence

`covenant_count` is the number of successfully funded canonical covenants.

Canonical IDs are allocated consecutively starting at `1`.

A covenant exists only when its canonical map key is present and its stored nonzero `covenant_id` matches that key.

Rejected or reverted funding attempts must not consume a covenant ID or increment `covenant_count`.

## 5. Storage-level economic invariants

For every funded covenant `c`:

```text
provider_settlement(c)
+ buyer_settlement(c)
+ outstanding_amount(c)
=
funded_amount(c)
```

At most one of `provider_settlement` and `buyer_settlement` may ever be nonzero.

Before successful settlement execution, `outstanding_amount == funded_amount`.

After canonical successful settlement execution, `outstanding_amount == 0` and exactly one side settlement equals `funded_amount`.

Globally:

```text
total_funded
=
total_closed_to_provider
+ total_closed_to_buyer
+ total_outstanding
```

Opening a covenant increases `total_funded` and `total_outstanding` by exactly `gl.message.value` after exact funding validation.

Acceptance, delivery, challenge, evidence repair, retry, adjudication, and settlement authorization do not change the four global GEN accounting totals.

Only canonical funding and the settlement execution write alter those global accounting values.

Settlement of covenant A must never read or consume the outstanding amount of covenant B.

## 6. Lifecycle storage invariants

- buyer and provider never change after funding;
- funded amount never changes after funding;
- service specification and its digest never change after funding;
- frozen timing policy never changes after funding;
- evidence policy, authorities, criteria, and settlement rule version never change after funding;
- delivery payload and delivery hash become immutable after the first valid delivery;
- a challenge cannot replace delivery or covenant terms;
- repair may append only policy-permitted evidence and cannot alter delivery;
- the canonical active evidence set is exactly the ordered IDs in `active_evidence_ids_by_covenant`;
- every active evidence ID must resolve to exactly one evidence-history record for the same covenant;
- an accepted `EVIDENCE_REPAIR_REQUIRED` result is the only path that may activate repair authorization;
- every active repair authorization targets an evidence ID currently present in the active evidence set;
- every active repair field mask is nonzero and a subset of the covenant's immutable `repair_allowed_field_mask`;
- replacement evidence ID freshness is mandatory and is not controlled by the repair mask;
- successful repair consumes the entire active repair authorization atomically;
- partial, extra, duplicate, inactive-target, stale-generation, reserved-bit, or unauthorized-field repair must revert;
- repair authorization history remains append-only after consumption or expiry;
- retry cannot alter covenant, delivery, challenge criteria, or current evidence set;
- repair and retry cannot extend the absolute dispute deadline;
- `review_generation` begins at `0`, and a valid buyer challenge allocates generation `1`;
- adjudication results themselves do not increment `review_generation`;
- successful repair and valid retry may allocate exactly one next generation only while below `max_review_generations`;
- failed repair/retry attempts do not consume a review generation;
- no transition may produce a review generation above `max_review_generations`;
- generation exhaustion in an intermediate repair/retry state resolves neutrally through `REVIEW_EXPIRED`;
- `CHALLENGED` at the maximum generation cannot expire merely because the generation equals the maximum;
- closed covenants cannot be reopened, repaired, retried, challenged, expired, or settled again;
- no write may choose a recipient or settlement amount outside frozen state.

## 7. Nondeterministic adjudication storage boundary

The challenged covenant record and every required criterion, authority binding, evidence record, challenge criterion, and other frozen consequential input must be copied from storage into memory before nondeterministic web or model work.

The nondeterministic block must not mutate persistent storage and must not emit economic messages.

Validators independently assess the same frozen memory snapshot and permitted evidence.

Only after the Equivalence Principle accepts the exact structured consequential result may deterministic code update adjudication fields, failed criterion IDs, review generation, deadlines, and settlement-authorizing state.

Leader-output schema validation alone is insufficient.

## 8. Storage allocation rule

Nested persistent generic collections are fully instantiated types.

When implementation needs an in-memory instance of a storage generic, it must use the GenLayer-supported allocation pattern such as `gl.storage.inmem_allocate(...)` where required by the current toolchain.

The implementation must not depend on ordinary Python container allocation behaving as persistent GenVM storage.

## 9. Explicitly absent V1 persistent state

V1 contains no persistent:

- owner or admin role;
- upgrade authority;
- emergency drain flag;
- protocol-fee balance;
- arbitrary recipient registry;
- user-selected post-funding payout address;
- percentage payout or confidence threshold;
- floating-point GEN accounting;
- frontend-controlled settlement state;
- validator-selected payout amount;
- validator-selected payout recipient;
- mutable evidence-authority override;
- finality-success flag claimed by contract storage;
- external recipient-balance proof claimed by contract storage.

## 10. Storage compatibility and source parity

The deployed V1 storage field names and types must match this frozen schema exactly unless this document is deliberately revised and re-reviewed before deployment.

V1 is not upgradeable in place. A future incompatible schema is a new reviewed deployment rather than an implicit mutation of the canonical V1 contract.

The final contract source SHA-256 and deployed-source parity must be proven before canonical Bradbury certification.

## 11. Items intentionally not frozen by this storage gate

This storage gate does not yet freeze:

- public constructor signature;
- public write/view method signatures;
- exact string and collection size caps;
- exact service-specification hash preimage;
- exact evidence-policy hash preimage;
- exact delivery hash preimage;
- exact evidence-set hash preimage;
- exact canonical URL normalization algorithm;
- exact adjudication result wire shape;
- exact pinned `py-genlayer`, linter, and test-tool versions.

Those items must be frozen and independently checked before `contracts/accord402.py` is created.

## 12. Implementation stop rule

If the current GenLayer linter/schema generator rejects any storage type or nesting pattern frozen here, do not weaken the protocol silently. Stop, preserve the failing output, verify the current supported API, and amend this document through an explicit reviewed gate before implementation continues.

