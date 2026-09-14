# Accord402 V1 — Frozen Hash Preimages

## 1. Scope

This document freezes the exact deterministic byte preimages for the four consequential V1 SHA-256 hashes stored by Accord402.

The four hashes are `service_spec_hash`, `evidence_policy_hash`, `delivery_hash`, and `active_evidence_set_hash`.

This document freezes byte encoding, domain separation, field ordering, list ordering, and V1 protocol-version numbers.

It does not replace semantic validation, input caps, source canonicalization, evidence validation, or adjudication rules.

## 2. Hash algorithm and stored output

Every hash defined here is SHA-256 over the exact byte sequence specified below.

Every stored digest is lowercase 64-character hexadecimal with no `0x` prefix.

V1 does not derive protocol hashes from JSON serialization, Python compound-object string representations, map iteration order, delimiter-only concatenation, or native-endian integers.

## 3. Common binary codec

The following notation is normative:

```text
U32(x)   = x encoded as exactly 4 unsigned big-endian bytes
U64(x)   = x encoded as exactly 8 unsigned big-endian bytes
U256(x)  = x encoded as exactly 32 unsigned big-endian bytes
ADDR(a)  = the exact normalized 20 raw bytes of Address.as_bytes
BOOL(0)  = one byte 0x00
BOOL(1)  = one byte 0x01
UTF8(s)  = strict UTF-8 encoding of s
STR(s)   = U32(len(UTF8(s))) || UTF8(s)
HEX32(h) = exactly 32 raw bytes decoded from a validated lowercase 64-character hex digest
COUNT(n) = U32(n)
||       = byte concatenation
```

Every integer is explicitly range-checked before encoding.

Every input string must satisfy the applicable V1 UTF-8 byte cap before encoding.

String length prefixes count UTF-8 bytes rather than Unicode code points.

No Unicode normalization, trimming, case folding, or whitespace rewriting occurs merely because a string is hashed.

Fields governed by separate canonicalization rules are canonicalized and validated first; the hash commits to the exact resulting canonical stored value.

In particular, `canonical_source` and `canonical_origin` are hashed only after the separate V1 canonical-source rules have passed.

## 4. Domain separation

The exact ASCII domain byte strings are:

```text
SERVICE_DOMAIN  = b"ACCORD402:SERVICE_SPEC:V1\x00"
POLICY_DOMAIN   = b"ACCORD402:EVIDENCE_POLICY:V1\x00"
DELIVERY_DOMAIN = b"ACCORD402:DELIVERY:V1\x00"
EVIDENCE_DOMAIN = b"ACCORD402:ACTIVE_EVIDENCE_SET:V1\x00"
```

The trailing `\x00` byte is part of every domain.

A digest produced for one domain must never be accepted as a digest for another domain.

## 5. Frozen V1 protocol-version constants

```text
EVIDENCE_POLICY_VERSION       = 1
REPAIR_POLICY_VERSION         = 1
ADJUDICATION_CRITERIA_VERSION = 1
SETTLEMENT_RULE_VERSION       = 1
```

These are contract-defined V1 constants rather than caller-selected policy implementations.

## 6. Criterion encoding

For one frozen criterion:

```text
CRITERION(c) =
    STR(c.criterion_id)
 || STR(c.criterion_text)
```

Criteria are encoded in the exact validated order stored in `criteria_by_covenant`.

No sorting occurs during hashing.

## 7. Authority-binding encoding

For one frozen authority binding:

```text
AUTHORITY(a) =
    STR(a.authority_id)
 || U32(a.authority_revision)
 || STR(a.role)
 || STR(a.identity_kind)
 || STR(a.identity_value)
 || STR(a.canonical_origin)
```

Authority bindings are encoded in the exact validated order stored in `authority_bindings_by_covenant`.

No sorting or deduplication occurs inside the hash function.

Before funding, every `(authority_id, authority_revision)` pair must be unique within the covenant authority-binding set.

Every evidence record resolves that pair to exactly one frozen authority binding.

A duplicate pair is invalid input even if role, identity kind, identity value, canonical origin, or list position differs.

A revision variant of one underlying authority does not by itself count as independent corroboration.

## 8. Evidence-record encoding

For one active stored evidence record:

```text
EVIDENCE_RECORD(e) =
    U64(e.covenant_id)
 || U32(e.generation)
 || STR(e.evidence_id)
 || STR(e.authority_id)
 || U32(e.authority_revision)
 || STR(e.subject)
 || STR(e.kind)
 || STR(e.source_kind)
 || STR(e.canonical_source)
 || STR(e.immutable_version_or_record_id)
 || U64(e.published_at)
 || U64(e.observed_at)
 || U64(e.expires_at)
 || HEX32(e.content_digest)
 || BOOL(e.is_primary)
 || STR(e.replaces_evidence_id)
```

Original evidence records encode the empty-string sentinel as `replaces_evidence_id`.

Replacement records encode the exact historical evidence ID they replace.

`generation` is the immutable creation generation of that evidence record, not the current covenant review generation.

## 9. service_spec_hash

`service_spec_hash` commits to the exact service text and the exact ordered adjudication criteria defining satisfaction of that service.

```text
SERVICE_PREIMAGE =
    SERVICE_DOMAIN
 || STR(service_spec)
 || U32(ADJUDICATION_CRITERIA_VERSION)
 || COUNT(number_of_criteria)
 || CRITERION(criteria[0])
 || CRITERION(criteria[1])
 || ...

service_spec_hash = SHA256(SERVICE_PREIMAGE)
```

The service hash does not silently include buyer, provider, principal, deadlines, evidence records, challenge state, or settlement state.

Those values remain separately frozen covenant state and are separately bound where consequential.

## 10. evidence_policy_hash

`evidence_policy_hash` commits to the exact V1 evidence-policy versions, limits, replay scope, repair mask, and approved authority bindings.

```text
POLICY_PREIMAGE =
    POLICY_DOMAIN
 || U32(evidence_policy_version)
 || U64(max_evidence_age)
 || U32(required_corroboration_count)
 || U32(repair_policy_version)
 || U32(repair_allowed_field_mask)
 || STR(replay_scope)
 || U32(adjudication_criteria_version)
 || COUNT(number_of_authority_bindings)
 || AUTHORITY(authority_bindings[0])
 || AUTHORITY(authority_bindings[1])
 || ...

evidence_policy_hash = SHA256(POLICY_PREIMAGE)
```

For V1, `evidence_policy_version`, `repair_policy_version`, and `adjudication_criteria_version` equal the frozen constants in this document.

The V1 evidence-policy version identifies the contract-defined V1 source, freshness, immutable/versioned evidence, live-source, provenance, and corroboration semantics that are not caller-selectable policy programs.

Submitted evidence records are not inserted directly into this policy hash; they are committed by the active evidence-set hash.

## 11. delivery_hash

`delivery_hash` is covenant-specific and binds the immutable provider delivery to the frozen service hash and original delivery time.

```text
DELIVERY_PREIMAGE =
    DELIVERY_DOMAIN
 || U64(covenant_id)
 || ADDR(provider)
 || HEX32(service_spec_hash)
 || U64(delivered_at)
 || STR(delivery_payload)

delivery_hash = SHA256(DELIVERY_PREIMAGE)
```

`provider` is the immutable original covenant provider.

`delivered_at` is the normalized GenLayer transaction timestamp recorded by the successful initial delivery.

Evidence repair must never change `delivery_payload`, `delivered_at`, `service_spec_hash`, or `delivery_hash`.

## 12. active_evidence_set_hash

`active_evidence_set_hash` commits to the complete currently active evidence records in exact active-ID order.

For every ID in `active_evidence_ids_by_covenant`, the contract resolves exactly one historical evidence record for the same covenant and encodes the complete record with `EVIDENCE_RECORD`.

```text
ACTIVE_EVIDENCE_PREIMAGE =
    EVIDENCE_DOMAIN
 || U64(covenant_id)
 || HEX32(delivery_hash)
 || HEX32(evidence_policy_hash)
 || COUNT(number_of_active_evidence_records)
 || EVIDENCE_RECORD(active_record[0])
 || EVIDENCE_RECORD(active_record[1])
 || ...

active_evidence_set_hash = SHA256(ACTIVE_EVIDENCE_PREIMAGE)
```

The active record order is exactly the order of `active_evidence_ids_by_covenant`.

No sorting by evidence ID, authority, source, digest, timestamp, or generation occurs.

Every active record must satisfy `record.covenant_id == covenant_id` before hashing.

Any authorized repaired-field change and every fresh replacement evidence ID therefore changes the active evidence-set hash.

Unaffected active records retain their original creation generation and exact encoded values.

## 13. Review-generation separation

`CovenantRecord.review_generation` is intentionally not encoded directly in `ACTIVE_EVIDENCE_PREIMAGE`.

This is mandatory because a valid review retry increments `review_generation` while preserving the same active evidence IDs and the exact same active evidence-set hash.

The exact current review generation is instead bound separately into every challenged adjudication input and every accepted consequential result.

A successful evidence repair changes the active evidence-set hash because the active evidence records themselves change.

## 14. Hash timing and atomicity

`service_spec_hash` and `evidence_policy_hash` are computed only after all funding validation succeeds and before successful covenant state is committed.

`delivery_hash` and the initial `active_evidence_set_hash` are computed only after all delivery and evidence validation succeeds and are committed atomically with successful delivery.

After successful repair, the replacement active evidence-set hash is computed from the complete post-repair active-record sequence and committed atomically with the repair transition.

A rejected or reverted operation must not persist a partial hash, partial evidence selection, replay reservation, generation advancement, or accounting mutation.

## 15. Reference vectors

These vectors freeze byte-level interpretation only. The sample identities and URLs do not grant protocol authority.

### Service vector

```text
service_spec = "report-v1"
adjudication_criteria_version = 1
criteria[0] = ("accuracy", "Current pricing is correct")
criteria[1] = ("freshness", "Evidence is recent")
service_spec_hash = 24ed8bf8f78af3c9cd79a45c40cc568b8d40c43297773ebc1693b678acfa74eb
```

### Evidence-policy vector

```text
evidence_policy_version = 1
max_evidence_age = 1800
required_corroboration_count = 1
repair_policy_version = 1
repair_allowed_field_mask = 255
replay_scope = "COVENANT"
adjudication_criteria_version = 1
authority[0] = ("primary", 1, "PRIMARY", "DOMAIN", "example.com", "https://example.com")
authority[1] = ("corroborator", 1, "CORROBORATOR", "DOMAIN", "example.org", "https://example.org")
evidence_policy_hash = ce9a1834a6e7e10dae1eb402d05b2388505010c252716afaba1148cbf4e068bb
```

### Delivery vector

```text
covenant_id = 7
provider raw address bytes = 20 bytes of 0x11
service_spec_hash = 24ed8bf8f78af3c9cd79a45c40cc568b8d40c43297773ebc1693b678acfa74eb
delivered_at = 1700000000
delivery_payload = "done"
delivery_hash = de39b250f0060babd6fcfd6d6a845ed062171a843f1f361eb9a300102146123a
```

### Active-evidence vector

```text
covenant_id = 7
delivery_hash = de39b250f0060babd6fcfd6d6a845ed062171a843f1f361eb9a300102146123a
evidence_policy_hash = ce9a1834a6e7e10dae1eb402d05b2388505010c252716afaba1148cbf4e068bb
active record count = 1
record.covenant_id = 7
record.generation = 0
record.evidence_id = "ev-1"
record.authority_id = "primary"
record.authority_revision = 1
record.subject = "pricing"
record.kind = "PAGE"
record.source_kind = "LIVE"
record.canonical_source = "https://example.com/pricing"
record.immutable_version_or_record_id = "v1"
record.published_at = 1699999900
record.observed_at = 1699999950
record.expires_at = 1700001000
record.content_digest = 64 lowercase zero hex characters, decoded by HEX32 to 32 zero bytes
record.is_primary = true
record.replaces_evidence_id = ""
active_evidence_set_hash = 6dc04221bb31250fd0f38f48500d35591f2d0f022b3feaf9a1c446af215cef55
```

Any implementation producing a different digest for one of these exact vectors is nonconforming.

## 16. Forbidden hash shortcuts

V1 forbids protocol hashing of JSON text.

V1 forbids delimiter-only concatenation of variable-length strings.

V1 forbids platform-native integer endianness.

V1 forbids checksummed address text where `ADDR` is specified; the normalized raw 20 bytes are used.

V1 forbids sorting a protocol collection whose stored ordering is already consequential.

V1 forbids silently case-folding, padding, truncating, or otherwise repairing a malformed digest.

V1 forbids reusing a stale active evidence-set hash after successful evidence repair.

## 17. Remaining pre-implementation freezes

This gate freezes the four V1 hash preimages, binary codec, domains, field ordering, collection ordering, protocol-version numbers, and byte-level reference vectors.

It does not yet freeze:

- exact canonical source and URL normalization algorithm;
- exact adjudication-result wire shape and parser rules;
- exact supported GenLayer dependency, linter, and test-tool pins.
