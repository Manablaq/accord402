# Accord402 V1 — Pre-Implementation Semantics Amendment

Status: FROZEN BEFORE CONTRACT IMPLEMENTATION

## 1. Purpose and precedence

This document closes narrowly identified semantic gaps discovered after the
original Accord402 V1 foundation was frozen and before contracts/accord402.py
was created.

It is append-only. It does not modify the bytes or SHA-256 identities of any
previously frozen Accord402 V1 document.

Where this amendment defines an exact value or rule for a subject that the
earlier frozen documents left ambiguous, this amendment controls the V1
implementation.

It does not alter:

- the public ABI;
- persistent root-storage shape;
- calldata record shape;
- hash-preimage codecs or domains;
- adjudication-wire JSON shape;
- state names;
- adjudication decisions;
- closure reasons;
- repair-mask bits;
- timing rules;
- accounting invariants;
- settlement recipient derivation;
- the frozen GenLayer toolchain.

## 2. Exact V1 protocol-string constants

The only V1 authority-role values are:

```text
PRIMARY
CORROBORATOR
```

The only V1 authority identity-kind value is:

```text
DOMAIN
```

The only V1 evidence source-kind values are:

```text
IMMUTABLE
VERSIONED
LIVE
```

The only V1 settlement-direction values are:

```text
""
PROVIDER
BUYER
```

The empty settlement-direction string is the unset sentinel before an
economic entitlement exists.

The existing replay-scope constants remain exactly:

```text
COVENANT
GLOBAL
```

No alternate capitalization, alias, abbreviation, whitespace variation, or
additional value is valid in V1.

## 3. DOMAIN authority identity

V1 intentionally supports one machine-checkable authority identity mechanism:
`DOMAIN`.

For a binding whose `identity_kind` is `DOMAIN`:

1. `identity_value` is the exact canonical lowercase ASCII host.
2. `canonical_origin` must equal the literal string
   `https://` followed by exactly `identity_value`.
3. `canonical_origin` has no trailing slash.
4. No wildcard, suffix, parent-domain, sibling-domain, registrable-domain, or
   subdomain inference is permitted.
5. The earlier frozen canonical-host grammar remains independently mandatory.

Examples:

```text
identity_kind = DOMAIN
identity_value = example.com
canonical_origin = https://example.com
```

is valid when every frozen canonical-origin rule passes.

The following does not establish the same authority:

```text
https://www.example.com
https://api.example.com
```

unless separately frozen as its own DOMAIN identity.

`authority_id` is an evidence-resolution identifier.

`authority_revision` is a version of one authority binding.

Neither `authority_id`, a new `authority_revision`, list position, role, nor a
different source URL creates a new independent authority identity.

## 4. Exact corroboration identity key

For V1, the machine-checkable independent-authority key is the exact pair:

```text
(identity_kind, identity_value)
```

Because V1 permits only `DOMAIN`, the practical V1 key is:

```text
("DOMAIN", canonical-domain-host)
```

Two bindings with the same independent-authority key represent the same
underlying authority for corroboration purposes even when they have:

- different `authority_id` values;
- different `authority_revision` values;
- different roles;
- different canonical paths;
- different evidence IDs;
- different evidence generations.

Such duplicates count at most once.

A revision of one authority therefore never creates another corroborator.

## 5. Authority-role and evidence-role consistency

Every funded covenant must contain at least one `PRIMARY` authority binding.

An evidence record resolves its exact `(authority_id, authority_revision)`
binding before role validation.

For every accepted evidence record:

```text
binding.role == "PRIMARY"       <=> evidence.is_primary == true
binding.role == "CORROBORATOR"  <=> evidence.is_primary == false
```

Any mismatch is invalid evidence.

No other role exists in V1.

## 6. Corroboration capacity at funding

`required_corroboration_count` retains the existing frozen numeric range.

Before funding succeeds, the contract computes the distinct independent
authority keys among `CORROBORATOR` bindings.

A corroborator key that is identical to any `PRIMARY` authority key is not an
independent corroborator.

The covenant is invalid when:

```text
required_corroboration_count
>
number of distinct qualifying CORROBORATOR authority keys
```

This validation occurs before a covenant ID, escrow accounting, covenant
storage, evidence replay key, or other consequential state is consumed.

## 7. Corroboration during adjudication

For a settlement-authorizing semantic decision, validators may count at most
one corroborating authority for each distinct independent-authority key.

Multiple evidence records, URLs, revisions, or evidence generations belonging
to the same independent-authority key still count once.

A terminal semantic decision may authorize settlement only when the evidence
relied upon contains:

1. at least one valid active `PRIMARY` evidence record; and
2. at least `required_corroboration_count` distinct qualifying active
   `CORROBORATOR` authority identities.

Failure to establish required corroboration cannot be silently interpreted as
`SERVICE_VERIFIED`, `PROVIDER_BREACH`, or `BUYER_CLAIM_INVALID`.

Where the problem is an evidence defect that the frozen repair policy permits,
the only corresponding intermediate class is
`EVIDENCE_REPAIR_REQUIRED`.

Where trustworthy review cannot be completed because of a transient runtime,
transport, validator, model, or source condition, the only corresponding
intermediate class is `REVIEW_RETRY_REQUIRED`.

## 8. Exact source-kind semantics

`IMMUTABLE` means the evidence is represented as an immutable resource whose
identity is additionally bound by a non-empty
`immutable_version_or_record_id`.

`VERSIONED` means the evidence is bound to an exact immutable version or
record identifier through a non-empty `immutable_version_or_record_id`.

`LIVE` means the source is mutable live evidence.

A non-empty version or record field never converts a `LIVE` source into an
immutable source.

All three source kinds remain subject to:

- exact authority resolution;
- exact canonical-source validation;
- exact content digest validation;
- freshness rules;
- replay protection;
- evidence-ID uniqueness;
- challenge bindings;
- repair rules;
- validator independent verification.

## 9. Consequential use of LIVE evidence

Under the frozen GenVM runtime, `LIVE` evidence may be retrieved and assessed
but it is not sufficient to satisfy the primary or corroboration requirement
for a settlement-authorizing terminal semantic decision.

Only active evidence whose source kind is `IMMUTABLE` or `VERSIONED` may count
toward the authority evidence required for:

```text
SERVICE_VERIFIED
PROVIDER_BREACH
BUYER_CLAIM_INVALID
```

`LIVE` evidence may support diagnosis, repair classification, retry
classification, or non-consequential context, but it cannot by itself or by
quantity create an economic entitlement.

This rule prevents mutable live-page content from becoming exact settlement
truth merely because validators agree on it.

## 10. Frozen-runtime redirect amendment

The frozen Accord402 runtime is GenVM `v0.6.0-rc5`.

That runtime follows HTTP redirects but the contract-visible web response does
not expose the final effective URL or redirect history.

Therefore the V1 implementation must not claim that it verified an effective
resource URL when the runtime does not expose one.

The earlier requirement that redirect admissibility depend on proving that the
effective resource URL equals the stored canonical source is not implementable
under the frozen runtime.

For V1 implementation:

1. the requested URL must still equal the stored `canonical_source`
   byte-for-byte;
2. the requested URL's origin must still equal the resolved frozen
   `AuthorityBinding.canonical_origin` byte-for-byte;
3. canonical grammar validation occurs before web access;
4. runtime fetch success is never treated as authority proof by itself;
5. no leader or validator may assert that the effective URL was verified;
6. no `LIVE` response may satisfy the authority evidence required for a
   settlement-authorizing terminal semantic decision;
7. settlement-authorizing evidence must instead satisfy the
   `IMMUTABLE`/`VERSIONED`, exact-digest, exact-version, authority, freshness,
   and corroboration requirements in this amendment and the earlier frozen
   foundation.

This amendment does not treat redirects as canonical-source aliases.

The stored canonical source is never rewritten because a redirect occurred.

The protocol trusts the exact requested frozen authority/source binding and
the independently verified immutable/versioned evidence content; it does not
invent unavailable runtime knowledge about the final transport URL.

A later Accord402 version may restore strict effective-URL equality only after
the supported runtime exposes a verifiable final URL or redirect-control
primitive and that new behavior is separately frozen and tested.

## 11. Settlement-direction lifecycle

`settlement_direction` is initialized to the empty string.

When deterministic protocol logic first authorizes provider settlement, it
becomes exactly:

```text
PROVIDER
```

When deterministic protocol logic first authorizes buyer settlement, it
becomes exactly:

```text
BUYER
```

The value never returns to the empty string and never changes from one side to
the other.

It remains unchanged through the matching closed state.

It is derived only from the frozen deterministic state transition.

It is never accepted from:

- calldata;
- leader output;
- validator output;
- evidence;
- repair input;
- retry input;
- settlement caller input.

## 12. Existing reference-vector compatibility

The earlier frozen evidence-policy reference vector uses:

```text
role = PRIMARY
role = CORROBORATOR
identity_kind = DOMAIN
```

The earlier active-evidence reference vector uses:

```text
source_kind = LIVE
```

Those byte-level hash reference vectors remain unchanged.

This amendment changes semantic admissibility rules only where the earlier
documents had not frozen an exact implementation rule.

The existing hash preimages, field ordering, and reference digests are not
modified.

## 13. Implementation boundary

After this amendment is frozen and independently certified, the Accord402 V1
contract implementation must enforce it together with every earlier frozen
document.

No contract implementation may silently broaden:

- authority roles;
- authority identity kinds;
- source kinds;
- settlement directions;
- corroboration identity semantics;
- consequential LIVE-evidence use;
- redirect claims.

Any future broadening requires a separately reviewed protocol amendment.

This document creates no Git commit, deployment authorization, or blockchain
transaction authorization.
