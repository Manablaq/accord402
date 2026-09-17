# Accord402 V1 — Threat Model

> **Payout-liveness amendment:** `docs/SECURITY_HARDENING_V4.md` supersedes conflicting persistent-credit and payout-withdrawal semantics.

> **Settlement-liveness amendment:** `docs/SECURITY_HARDENING_V3.md` supersedes conflicting payout-recipient and vault-withdrawal semantics.

> **Security amendment:** `docs/SECURITY_HARDENING_V2.md` supersedes any conflicting weaker V1 rule in this document.

## Security objective

Accord402 must ensure that a service covenant can transfer its escrow only according to the immutable agreement and a deterministic deadline or finalized GenLayer adjudication outcome.

The protocol assumes neither buyer nor provider is honest.

The frontend, SDK, provider delivery, retrieved web content, and leader result are not trusted authorities.

## Protected assets

- escrowed GEN;
- immutable covenant terms;
- service and delivery digests;
- evidence authority policy;
- evidence identity/replay state;
- adjudication result;
- settlement recipient;
- finalized warranty receipt;
- reputation counters.

## Trust boundaries

### GenLayer consensus

Trusted only according to the protocol's finalized consensus model.

`ACCEPTED` remains provisional.

Successful application execution must be checked separately from consensus status.

### Leader

Untrusted proposer.

The leader can be wrong, manipulated, or malicious. Validators must independently verify substantive result fields.

### Validators

The protocol relies on GenLayer consensus, but contract-level validator logic must give validators sufficient evidence and explicit criteria to detect a bad leader result.

### Buyer

May submit false challenges, attempt replay, trigger methods in wrong states, or manipulate evidence claims.

### Provider

May submit incomplete work, stale evidence, forged authority references, mutable URLs, or attempt to repair by changing the original delivery.

### Web evidence

Untrusted, nondeterministic, potentially stale, personalized, unavailable, malicious, or prompt-injected.

### Frontend / SDK

Convenience clients only. They are never authoritative for state, deadlines, recipients, or adjudication outcome.

## Threats and required controls

| Threat | Required control |
|---|---|
| Provider never accepts | bounded acceptance deadline and buyer recovery |
| Provider accepts but never delivers | bounded delivery deadline and buyer recovery |
| Buyer withholds acceptance of valid work | deterministic unchallenged settlement after challenge window |
| Buyer files false challenge | GenLayer adjudication can return `BUYER_CLAIM_INVALID` |
| Provider submits bad work | adjudication can return `PROVIDER_BREACH` |
| Stale evidence | max-age and expiry checks |
| Mutable evidence masquerades as immutable | canonical immutable/versioned source rules where applicable |
| Fake publisher | approved authority identities frozen in evidence policy |
| Correlated sources called independent | explicit corroboration independence rule |
| Evidence replay | scoped single-use evidence identity |
| Challenge changes covenant | covenant hash/fields immutable after funding |
| Repair changes delivery | repair whitelist excludes delivery/service fields |
| Leader invents verdict | validators independently consult permitted evidence |
| Validator performs shape-only check | forbidden by reviewer gate; substantive re-verification required |
| Prompt injection from webpage | retrieved content treated as untrusted data, policy separated |
| Fuzzy decision redirects money | exact decision-bearing fields; no tolerance for economic authorization |
| Wrong settlement recipient | buyer/provider addresses frozen; no arbitrary recipient parameter |
| Double refund/payment | terminal/idempotency guard + accounting invariant |
| One covenant spends another's escrow | global and per-covenant liability accounting |
| Admin drains escrow | no administrative extraction path |
| Accepted treated as final | UI/SDK separate accepted, finalized, and execution success |
| Value-bearing IC child settlement loses or strands funds | V1 settlement forbids value-bearing IC child transactions; `claim_settlement(covenant_id)` schedules one finality-only external native GEN transfer to the immutable state-derived recipient |
| Provisional closed state is mistaken for payment | `CLOSED_PROVIDER` / `CLOSED_BUYER` observed provisionally is not payment proof; canonical settlement requires `Finalized` + `FINISHED_WITH_RETURN` and separate external balance evidence |
| Uncertain settlement observation causes duplicate transfer | persist the exact settlement transaction ID and resume tracking it; blind resubmission is forbidden and duplicate/terminal guards must prevent a second send |
| Retry forever | bounded retry deadline/policy |
| Repair forever | bounded repair deadline |
| Deadline caller captures funds | permissionless recovery uses predetermined recipient only |
| Hidden method bypass | ABI/static review of every public/write/payable/special method |
| Malformed LLM output | objective parsing + defined retry behavior |
| HTTP 4xx/5xx ambiguity | classify repairable party evidence failure vs transient infrastructure failure |
| Timestamp spoofing | compare evidence timestamps against deterministic GenLayer transaction time |
| Cross-covenant evidence confusion | covenant ID and policy/evidence-set hashes included in consequential result |
| Replay of old adjudication | covenant/delivery/evidence-set bindings exact |
| Reputation manipulation | counters updated only from terminal finalized outcomes |
| Frontend demo data mistaken for chain truth | canonical pages use live/finalized reads and clearly label provisional data |

## Hidden mutation/value-transfer review

Before every release, enumerate:

- constructor;
- every `@gl.public.write`;
- every `@gl.public.write.payable`;
- `__receive__`;
- undefined-method handler if present;
- every internal message emission;
- every external/EVM message emission;
- every method that changes liability, recipient, state, evidence, or reputation.

Reviewer audit must prove there is no unlisted path that can:

- mutate covenant terms;
- create value entitlement;
- redirect value;
- settle twice;
- bypass finality;
- alter adjudication decision;
- reuse evidence;
- erase liability without settlement proof.

## Denial-of-service considerations

Inputs must be bounded.

V1 must define reasonable maximum lengths/counts for:

- service specification;
- criteria;
- delivery payload/reference;
- challenge claim;
- evidence records;
- URLs/identifiers;
- failed-criteria result set.

A user must not be able to create unbounded storage or force pathological validator prompt/web work with one covenant.

## Privacy boundary

Accord402 V1 should assume covenant, delivery metadata, hashes, evidence references, adjudication decisions, and reputation data are public.

Secrets, API keys, private customer data, wallet private keys, and recovery phrases must never be stored in contract state or committed to the repository.

## Upgrade policy

V1 must not silently introduce an upgrade/admin mechanism late in implementation.

If contract upgradability is used at all, authority, storage compatibility, and reviewer consequences require a separate explicit design gate before deployment.

The safest default for the first canonical release is no privileged economic bypass.

## Security completion rule

A threat is not considered mitigated merely because the frontend hides a button.

The control must be enforced by contract logic, consensus validation, or a clearly documented external protocol property and covered by a reproducible test where feasible.
