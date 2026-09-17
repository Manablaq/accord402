> **Settlement-liveness supersession:** `docs/SECURITY_HARDENING_V3.md` supersedes this document's settlement-recipient and vault-withdrawal model.

# Accord402 Security Hardening V2

Status: **MANDATORY SECURITY AMENDMENT**

This amendment supersedes every conflicting weaker V1 rule for all future
deployment and submission work.

## Evidence profile

Consequential evidence is restricted to exact immutable GitHub repository
records:

- `source_kind = IMMUTABLE`
- `identity_kind = GITHUB_REPOSITORY`
- identity = lowercase `<owner>/<repository>`
- origin = `https://raw.githubusercontent.com`
- source contains the exact identity, a 40-lowercase-hex commit, and canonical path
- `immutable_version_or_record_id` equals that exact commit

Generic DOMAIN, LIVE, generic VERSIONED, branches, tags, abbreviated commits,
and arbitrary redirect-capable publishers are not V2 consequential sources.

Corroboration is mandatory and independent by GitHub owner, not URL, repo,
authority alias, or authority revision.

V2 supports only covenant-scoped replay. The old GLOBAL label-derived key is
unsupported because labels can be renamed and content-global reservation is
publicly squattable.

## Canonical immutable manifest

Fetched evidence is canonical UTF-8 JSON with exactly:

`schema`, `authority_identity`, `canonical_source`, `record_id`, `subject`,
`kind`, `published_at`, `expires_at`, `payload`.

`schema = ACCORD402_EVIDENCE_MANIFEST_V1`.

The complete manifest is SHA-256 bound. Authority/source/record/subject/kind/
publication/expiry exact-match the stored record. Only the bounded `payload`
enters semantic adjudication.

## Bounded retrieval and time

Validators request `Range: bytes=0-8191` with `Accept-Encoding: identity`.

Terminal-capable retrieval requires HTTP 206, valid complete-file
`Content-Range`, total size <=8192 bytes, strict UTF-8, canonical manifest, and
payload <=2048 UTF-8 bytes.

Initial `observed_at` equals the delivery transaction timestamp. Repair
`observed_at` equals the repair transaction timestamp.

Validator review also requires the HTTPS server Date header. Freshness and
expiry use the later of transaction time and server response time. A materially
stale Date is a transport failure.

## Repair

The only repairable fields are canonical source, immutable record/commit,
published_at, observed_at, expires_at, and content digest. Authority identity
and revision are frozen.

The covenant repair mask is exactly `0xFC`.

An authorization mask permits changes inside the mask; outside-mask changes are
forbidden. A replacement must make at least one authorized change, use a fresh
evidence ID, and preserve nonrepairable fields.

## Liveness

`REVIEW_RETRY_REQUIRED` may be neutrally expired when its local retry deadline
passes, when generation is exhausted, or when the absolute dispute deadline
passes. Closure remains `REVIEW_EXPIRED` to the immutable buyer.

Zero providers and buyer==provider self-covenants are forbidden.

## Settlement transport

Direct native-GEN calls to arbitrary beneficiary addresses are superseded.

Core stores one immutable nonzero `settlement_vault` set at construction.
`claim_settlement` derives beneficiary and principal only from covenant state,
then emits one finality-only EVM call to
`settlement_vault.credit(beneficiary)` with the exact principal.

`contracts/Accord402SettlementVault.sol` has no owner, admin, upgrader, sweep,
or privileged debit. Credits are namespaced by depositing source and
beneficiary. Beneficiaries withdraw their own credit to a chosen payable
destination. Failed destination calls revert atomically and preserve credit.

This prevents a beneficiary contract that rejects native GEN from blocking the
Accord402 settlement transaction itself.

## Deployment consequence

Every pre-hardening carrier/Core artifact whose bytes differ from this amended
logic is historical/superseded. The already-submitted Shared D3 transaction is
never replayed.

No new blockchain deployment or finalization is authorized by this amendment.

Before any fresh deployment:
- GenVM lint/typecheck;
- Direct/adversarial/hash regressions;
- Solidity vault compilation;
- ABI/storage review;
- carrier decomposition rebuild;
- runtime-equivalence certification;
- read-only Bradbury Range/Date probe;
- read-only gas/admission check;
- second hidden-mutation/value-transfer audit.

A PASS label cannot waive a failed gate.

## Direct Mode artifact isolation

The pinned `genlayer-test` pytest plugin clears its configured artifacts
directory at session start. Accord402 stores reviewer and deployment evidence
under the tracked repository `artifacts/` tree, so Direct Mode MUST never use
that tracked directory.

Repository-level `pytest.ini` routes gltest to `.gltest-artifacts/`, and
`.gitignore` excludes that disposable directory. Release/security runs must
prove tracked `artifacts/` matches HEAD immediately before and after pytest.
