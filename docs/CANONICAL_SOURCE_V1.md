# Accord402 V1 — Frozen Canonical Source Normalization

> **Security amendment:** `docs/SECURITY_HARDENING_V2.md` supersedes any conflicting weaker V1 rule in this document.

## 1. Scope

This document freezes the exact V1 grammar and validation rules for `AuthorityBinding.canonical_origin` and `EvidenceRecord.canonical_source`.

The rules are intentionally stricter than general-purpose URL syntax.

Accord402 V1 does not attempt to normalize every valid URI. A source that is not already in the exact canonical V1 form is rejected.

Canonicalization therefore means validate the exact canonical representation and return it unchanged.

No rejected spelling is decoded, repaired, redirected, rewritten, case-folded into acceptance, or treated as an alias.

## 2. Security goals

The canonical-source rules prevent multiple textual representations from silently naming the same high-consequence evidence source.

They also prevent a caller from broadening a frozen authority binding through URL userinfo, ports, subdomains, IP literals, percent encoding, dot segments, backslashes, queries, fragments, or parser-specific normalization.

URL canonicality never establishes factual truth, provenance, freshness, immutability, corroboration, or service satisfaction by itself.

## 3. Character model

Both `canonical_origin` and `canonical_source` must contain ASCII bytes only.

Unicode host names are not accepted in V1.

Punycode labels beginning with `xn--` are not accepted in V1.

Leading or trailing ASCII whitespace is invalid rather than trimmed.

Embedded whitespace and ASCII control characters are invalid.

The existing UTF-8 byte caps are still enforced before canonical-source validation.

## 4. Scheme

The only V1 scheme is the exact lowercase literal `https://`.

`http://` is invalid.

Uppercase or mixed-case scheme spellings are invalid rather than normalized.

No other URI scheme is admitted by this V1 web-source grammar.

## 5. Canonical DNS host grammar

A V1 host must be an already-lowercase ASCII DNS name.

The complete host must be at most 253 ASCII bytes.

The host must contain at least one dot.

The host must not begin or end with a dot and must not contain an empty label.

Each DNS label must contain between 1 and 63 characters.

Each label must match the exact grammar `[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?`.

The final top-level label must match `[a-z]{2,63}`.

No label may begin with `xn--`.

IPv4 and IPv6 literals are invalid.

Single-label names such as `localhost` are invalid.

The V1 denied local/special top-level labels are `local`, `localhost`, `internal`, `home`, `lan`, `test`, `invalid`, and `onion`.

No userinfo is permitted.

No explicit port is permitted, including explicit `:443`.

V1 therefore uses only the ordinary HTTPS default port.

Host aliases are not inferred. `example.com` and `www.example.com` are distinct authority origins.

## 6. canonical_origin

The exact canonical-origin form is:

```text
https://<canonical-host>
```

`canonical_origin` contains no trailing slash, path, query, fragment, userinfo, or port.

For example, `https://example.com` is canonical.

`https://example.com/` is not a canonical origin.

## 7. Canonical path grammar

Every `canonical_source` contains an explicit path beginning with `/`.

The root path `/` is permitted.

For a non-root path, every segment must be non-empty.

The only permitted path characters are ASCII letters, ASCII digits, `.`, `_`, `~`, and `-`.

Path segment comparison is case-sensitive and path case is preserved exactly.

The exact segment grammar is `[A-Za-z0-9._~-]+`.

The complete path is formed by joining those segments with the literal `/` separator.

The literal segments `.` and `..` are forbidden.

Consecutive slash characters are forbidden.

A non-root path must not end with `/`.

Percent signs are forbidden; V1 performs no percent decoding or percent normalization.

Backslashes are forbidden.

Query strings are forbidden.

Fragments are forbidden.

Semicolons, colons, at-signs, ampersands, equals signs, plus signs, commas, exclamation marks, parentheses, brackets, braces, quotes, and other characters outside the exact segment grammar are rejected.

## 8. canonical_source

The exact canonical-source form is:

```text
https://<canonical-host>/<canonical-path>
```

For the root resource the exact form is `https://<canonical-host>/`.

A source with no explicit `/` after the host is invalid as `canonical_source` even though the corresponding origin omits the slash.

The canonicalizer returns the input source byte-for-byte unchanged when it passes every V1 rule.

## 9. Exact origin binding

For every evidence record, Accord402 derives the source origin from `canonical_source` as the exact `https://<canonical-host>` prefix.

That derived origin must equal the resolved frozen `AuthorityBinding.canonical_origin` byte-for-byte.

No parent-domain, sibling-domain, wildcard-domain, suffix, registrable-domain, or subdomain inference is performed.

An authority bound to `https://example.com` does not authorize `https://www.example.com` or `https://api.example.com`.

An authority bound to `https://api.example.com` does not authorize `https://example.com`.

The exact origin is only one part of authority verification. Evidence must also resolve the exact frozen `(authority_id, authority_revision)` binding and satisfy the frozen identity, role, freshness, replay, and corroboration rules.

## 10. V1 source authorization class

The V1 source class represented by `AuthorityBinding.canonical_origin` is the exact HTTPS origin.

Within that exact origin, a path is admissible only when it independently satisfies the canonical path grammar and all evidence-policy rules.

`canonical_origin` is not a path-prefix wildcard and does not authorize another origin.

The authority identity fields remain necessary because possession of a URL on an allowed origin is not itself proof of approved publisher identity.

## 11. Immutable and live evidence

Canonical URL syntax does not convert mutable content into immutable evidence.

For immutable or versioned evidence, `immutable_version_or_record_id` must still identify the exact immutable/versioned record required by the frozen evidence policy.

A mutable branch, mutable page, or mutable API route cannot be represented as immutable merely because its URL is canonical.

For live evidence, the frozen `published_at`, `observed_at`, `expires_at`, `max_evidence_age`, authority, and corroboration requirements still apply.

## 12. Redirect policy

A redirect is not a canonical-source alias.

The stored `canonical_source` is never rewritten because a server redirects.

A redirect must never broaden authority from one origin to another.

Cross-origin redirects are never admissible as evidence for the originally bound authority.

Same-origin redirects also do not create a new canonical source automatically.

If the supported runtime follows redirects, V1 may treat the resulting content as admissible only when the implementation can prove that the effective resource URL is exactly the stored canonical source.

If the supported runtime cannot prove that equality, a redirecting resource is not admissible V1 evidence and the implementation must not pretend otherwise.

The supported-runtime gate must verify actual redirect behavior before contract implementation relies on any redirect-sensitive web source.

## 13. DNS and runtime URL safety

DNS resolution does not change the frozen canonical source or authority origin.

IP literals are rejected by the canonical grammar.

GenVM runtime URL restrictions remain an additional mandatory layer and are not replaced by Accord402 string validation.

No contract rule may treat DNS resolution, redirects, or runtime fetch success as authority proof.

## 14. Validation order

The applicable UTF-8 byte cap is checked first.

ASCII-only validation is checked before URL grammar parsing.

The exact scheme is checked before host parsing.

Host grammar is checked before path grammar.

Origin equality against the resolved authority binding is checked before evidence is admitted.

Canonical-source validation occurs before hashing the authority binding or evidence record into a consequential protocol hash.

Invalid canonical input is rejected without reserving an evidence ID, consuming a replay key, appending evidence history, changing the active evidence set, advancing review generation, or changing escrow accounting.

## 15. Canonical examples

The following are canonical origins:

```text
https://example.com
https://api.example.com
https://raw.githubusercontent.com
```

The following are canonical sources:

```text
https://example.com/
https://example.com/pricing
https://example.com/docs/report-v1
https://raw.githubusercontent.com/owner/repo/0123456789abcdef/file.mdx
```

Path spelling and case are preserved exactly.

## 16. Explicitly rejected examples

Each of the following is invalid in V1:

```text
http://example.com/pricing
HTTPS://example.com/pricing
https://Example.com/pricing
https://example.com:443/pricing
https://user@example.com/pricing
https://127.0.0.1/pricing
https://[::1]/pricing
https://localhost/pricing
https://example.local/pricing
https://xn--example-ova.com/pricing
https://example.com
https://example.com//pricing
https://example.com/pricing/
https://example.com/./pricing
https://example.com/a/../pricing
https://example.com/%70ricing
https://example.com/pricing%2Fcurrent
https://example.com\pricing
https://example.com/pricing?plan=pro
https://example.com/pricing#current
https://example.com/pricing;current
```

## 17. Repair behavior

When `CANONICAL_SOURCE` repair is authorized, the replacement source must independently pass this complete V1 grammar.

Repair never normalizes an invalid old source in place.

The replacement evidence record still requires a fresh covenant-wide `evidence_id` and all existing repair, replay, authority, freshness, and generation checks.

Changing canonical source cannot change `source_kind`, subject, kind, or `is_primary` because those fields remain non-repairable in V1.

## 18. Hash interaction

`canonical_origin` is encoded exactly by `STR(a.canonical_origin)` only after this validation succeeds.

`canonical_source` is encoded exactly by `STR(e.canonical_source)` only after this validation succeeds.

No additional URL normalization occurs inside the hash functions.

Therefore a rejected URL spelling can never be silently transformed into a different hash preimage.

## 19. Remaining pre-implementation freezes

This gate freezes V1 canonical origin and source grammar, exact origin matching, parser-confusion rejection, redirect authority behavior, and hash interaction.

It does not yet freeze:

- exact adjudication-result wire shape and parser rules;
- exact supported GenLayer dependency, linter, and test-tool pins.
