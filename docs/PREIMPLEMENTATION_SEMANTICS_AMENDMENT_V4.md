# Accord402 V1 — Implementation Semantics Amendment V4

Status: FROZEN DURING STEP 2 BEFORE IMPLEMENTATION COMPLETION

## 1. Scope and precedence

This document is an append-only clarification discovered during the Step 2 implementation-semantic audit after the first full contract candidate passed static ABI/storage and frozen-toolchain validation.

It does not modify the bytes or SHA-256 identities of any previously frozen Accord402 document.

Where an earlier frozen document requires exact immutable/versioned evidence identity but does not define the machine-checkable relation between `canonical_source` and `immutable_version_or_record_id`, this amendment controls the V1 implementation.

This amendment creates no new:

- public method;
- public parameter;
- return type;
- persistent storage field;
- covenant state;
- adjudication decision;
- failure-classification value;
- closure reason;
- repair-mask bit;
- hash-preimage field;
- adjudication-wire field;
- settlement path;
- privilege;
- toolchain dependency.

The subjects clarified here are limited to:

- exact source-to-version/record binding for `IMMUTABLE` and `VERSIONED`;
- deterministic admission and repair validation for that binding;
- exact digest-mismatch repair semantics for terminal-capable immutable/versioned evidence;
- continued `LIVE` evidence semantics.

## 2. Security objective

V1 must not permit a mutable route to become settlement-authorizing `IMMUTABLE` or `VERSIONED` evidence merely because:

- `source_kind` was caller-labeled `IMMUTABLE` or `VERSIONED`;
- `immutable_version_or_record_id` was non-empty; or
- a content digest happened to match the bytes fetched during one review.

The immutable/versioned record identity must be objectively bound to the canonical source before the evidence record can be admitted or used as terminal authority evidence.

A later digest repair must not bless changed bytes under the same alleged immutable/versioned record identity.

## 3. Exact V1 version/record identifier grammar

For `source_kind == IMMUTABLE` or `source_kind == VERSIONED`, `immutable_version_or_record_id` must satisfy all of the following:

1. it is non-empty;
2. it satisfies the existing 512-byte UTF-8 cap;
3. it is ASCII;
4. it is a single canonical path-segment token under the already-frozen V1 path-segment grammar:
   - every byte is one of `A-Z`, `a-z`, `0-9`, `.`, `_`, `~`, `-`;
   - it is not `.` or `..`;
   - it contains no slash, backslash, percent encoding, query delimiter, fragment delimiter, whitespace, control character, colon, semicolon, at-sign, ampersand, equals sign, plus sign, comma, brackets, braces, quotes, or other character outside that grammar.

No normalization, case folding, percent decoding, Unicode normalization, or aliasing is performed.

The stored identifier is the exact caller-supplied byte string after this validation succeeds.

For `source_kind == LIVE`, this amendment adds no new relationship between `canonical_source` and `immutable_version_or_record_id`. A non-empty value on `LIVE` remains non-consequential metadata and never converts the source into immutable/versioned evidence.

## 4. Exact canonical-source binding

For `IMMUTABLE` and `VERSIONED` evidence, after the existing canonical-source parser succeeds, Accord402 splits the canonical source path into its already-valid path segments.

The exact `immutable_version_or_record_id` must appear byte-for-byte as at least one complete path segment.

Substring matching is forbidden.

Examples:

```text
identifier = abc123
source     = https://example.com/records/abc123/report
result     = valid binding
```

```text
identifier = abc123
source     = https://example.com/records/prefix-abc123/report
result     = invalid binding
```

```text
identifier = abc123
source     = https://example.com/records/abc1234/report
result     = invalid binding
```

```text
identifier = e2d9fa8ca4228a44a7b30f4213fc09ea7fc7051f
source     = https://raw.githubusercontent.com/owner/repo/e2d9fa8ca4228a44a7b30f4213fc09ea7fc7051f/evidence.json
result     = valid binding
```

The identifier may occur more than once as an exact segment; repeated occurrence of the same literal identifier does not create additional authority, corroboration, or evidence weight.

A root source such as `https://example.com/` cannot satisfy `IMMUTABLE` or `VERSIONED` binding because it contains no version/record path segment.

## 5. Deterministic admission rule

Before an initial evidence record with source kind `IMMUTABLE` or `VERSIONED` is admitted, the implementation must enforce Sections 3 and 4 in addition to every earlier frozen:

- input-cap rule;
- authority-resolution rule;
- canonical-origin/source rule;
- source-kind rule;
- timestamp/freshness rule;
- content-digest syntax rule;
- replay rule;
- evidence-ID uniqueness rule;
- role/primary rule.

A source/version binding failure at initial `submit_delivery` is a deterministic admission failure.

The invalid record is not appended.

No covenant-wide evidence-ID reservation or authority-aware replay key is consumed.

No delivery hash, active evidence-set hash, challenge deadline, generation, or escrow accounting value changes.

## 6. Terminal-capable evidence rule

An active record may count toward the primary/corroboration authority structure for a settlement-authorizing terminal decision only when:

1. `source_kind` is `IMMUTABLE` or `VERSIONED`;
2. its exact stored version/record identifier satisfies Sections 3 and 4 against its exact stored canonical source; and
3. every earlier frozen authority, digest, freshness, replay, corroboration, and validator-independent-verification rule passes.

`LIVE` evidence remains excluded from terminal authority counting.

A non-empty but unbound version/record string never makes an evidence record terminal-capable.

## 7. Exact immutable/versioned digest-mismatch semantics

For a successful 2xx retrieval, the exact raw-body SHA-256 rule from Amendment V3 remains unchanged.

When:

```text
actual_digest != stored content_digest
```

the repair behavior now depends on source kind.

### 7.1 LIVE

For `LIVE` evidence, Amendment V3 remains unchanged.

If `CONTENT_DIGEST` repair is permitted, the exact digest-mismatch repair contribution is:

```text
CONTENT_DIGEST
```

If that bit is not permitted, the defect is unrepairable under the existing V3 rule.

### 7.2 IMMUTABLE or VERSIONED

For `IMMUTABLE` or `VERSIONED` evidence, V1 must not authorize a digest-only repair under the same frozen version/record identity.

A digest mismatch means the bytes currently returned by the bound source do not match the bytes committed by the active evidence record.

Because the implementation cannot objectively distinguish:

- an originally mistyped digest;
- a resource that changed under the same alleged immutable/versioned identifier;
- an authority serving different bytes for the same record identifier;
- or another integrity failure,

V1 chooses the settlement-safe rule.

A repairable immutable/versioned digest mismatch requires a complete re-anchor to a different canonical record reference.

The exact repair contribution is therefore the union:

```text
CANONICAL_SOURCE
| IMMUTABLE_VERSION_OR_RECORD_ID
| CONTENT_DIGEST
```

Numerically:

```text
0x0000008C
```

All three bits must be permitted by the covenant's immutable `repair_allowed_field_mask`.

If any one of the three bits is not permitted, the defect is unrepairable under Amendment V3 Section 7.

This rule prevents changed bytes from being blessed by changing only the digest while retaining the same alleged immutable/versioned record identity.

## 8. Immutable/versioned re-anchor repair

For a successful repair authorized by Section 7.2:

- `canonical_source` must change;
- `immutable_version_or_record_id` must change;
- `content_digest` must change;
- every changed field must satisfy the exact accepted repair mask;
- the new canonical source must independently satisfy the complete V1 canonical-source grammar;
- the new version/record identifier must independently satisfy Section 3;
- the new source must contain the new identifier as an exact complete path segment under Section 4;
- the exact frozen authority binding and canonical origin rules still apply;
- every non-repairable field remains unchanged;
- the replacement uses a fresh covenant-wide evidence ID;
- replay rules still apply;
- timestamps and freshness still pass all applicable frozen rules;
- the complete post-repair active evidence set still satisfies the terminal-capable structural rule.

Amendment V3's no-op rule remains in force: because these three bits are present, all three corresponding values must actually change.

The fresh replacement `evidence_id` remains mandatory and remains outside the repair mask.

## 9. Other repair combinations

This amendment does not alter the earlier exact repair contributions for:

- `OBSERVED_AT`;
- `EXPIRES_AT`;
- repairable HTTP 4xx `CANONICAL_SOURCE`;
- any independently established union of multiple defects.

If an immutable/versioned record has both a digest mismatch and another independently established repairable defect, its exact repair mask is the bitwise OR of:

```text
0x8C
```

and every other necessary permitted repair contribution.

If that complete exact mask cannot be represented within the covenant's frozen repair policy, the record is unrepairable.

A repairable HTTP 4xx condition by itself continues to contribute only `CANONICAL_SOURCE` under Amendment V3.

For such a repair, the unchanged immutable/versioned identifier must still appear as an exact path segment in the replacement canonical source.

## 10. Hash compatibility

This amendment changes validation semantics only.

It does not change any frozen hash codec, domain, field order, or preimage.

`immutable_version_or_record_id` was already an exact hashed field of every evidence record.

`canonical_source` and `content_digest` were already exact hashed fields.

Therefore the existing:

- service-spec hash;
- evidence-policy hash;
- delivery hash;
- active-evidence-set hash;
- reference vectors

remain byte-for-byte unchanged.

The existing active-evidence reference vector uses `source_kind = LIVE`; this amendment does not alter that vector.

## 11. Adjudication-wire compatibility

This amendment creates no new wire field or decision.

A repairable immutable/versioned digest mismatch still produces:

```text
decision = EVIDENCE_REPAIR_REQUIRED
failure_classification = REPAIRABLE_EVIDENCE_DEFECT
```

The corresponding repair entry carries the exact complete field mask determined by this amendment and all other independently established repair contributions.

If the required complete mask is not permitted, the existing unrepairable-evidence rule applies and no accepted adjudication wire is produced for that attempt.

## 12. Reviewer-gate consequence

After this amendment is enforced, V1 may count an `IMMUTABLE` or `VERSIONED` evidence record toward terminal settlement authority only when the contract can prove all of the following from frozen state and independently retrieved bytes:

- approved authority binding;
- exact canonical origin;
- exact canonical source;
- exact source-to-version/record path-segment binding;
- exact raw-body content digest;
- freshness;
- replay safety;
- evidence-ID uniqueness;
- source-kind eligibility;
- required independent corroboration.

A caller label and a non-empty version string alone are insufficient.

## 13. No other semantic changes

All earlier frozen rules remain in force, including:

- exact thirteen-write and twelve-view ABI;
- zero-argument constructor;
- exact persistent root-storage and record shapes;
- exact input caps and aggregate budgets;
- exact four protocol hash preimages and reference vectors;
- exact canonical-source grammar and opaque-redirect rules;
- exact authority roles and DOMAIN identity semantics;
- exact replay-key namespaces;
- exact state machine and generation rules;
- exact twelve-field adjudication wire;
- exact failure classifications;
- exact repair-mask universe;
- exact challenge/decision semantics;
- exact settlement recipient and amount derivation;
- finality-only external GEN transfer;
- exact reputation-counter semantics;
- frozen GenLayer runner and toolchain;
- no privileged economic path.

This amendment creates no Git commit, deployment authorization, or blockchain transaction authorization.

## 14. Implementation stop rule

Candidate V2 is not Step-2 complete because it does not enforce this amendment.

The installed Candidate V2 may remain in the repository temporarily as the audited pre-fix baseline, but it must not be committed, deployed, or treated as canonical.

Implementation may continue only by:

1. byte-freezing and certifying this amendment;
2. rebuilding the active implementation foundation packet to include it;
3. patching the contract without changing the frozen public ABI/storage/hash/wire/economic surfaces;
4. rerunning frozen lint, validation, typecheck, schema parity, hash vectors, and semantic-audit gates.

If another consequential ambiguity is discovered, implementation must stop again rather than silently choosing a value-affecting behavior in code.
