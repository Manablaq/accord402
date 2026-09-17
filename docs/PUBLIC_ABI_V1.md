# Accord402 V1 — Frozen Public ABI

> **Payout-liveness amendment:** `docs/SECURITY_HARDENING_V4.md` supersedes conflicting persistent-credit and payout-withdrawal semantics.

> **Settlement-liveness amendment:** `docs/SECURITY_HARDENING_V3.md` supersedes conflicting payout-recipient and vault-withdrawal semantics.

> **Security amendment:** `docs/SECURITY_HARDENING_V2.md` supersedes any conflicting weaker V1 rule in this document.

## 1. Scope

This document freezes the exact V1 public contract surface before `contracts/accord402.py` is implemented.

It freezes constructor shape, calldata record shape, public write and view names, parameter types, return types, payability, caller authority, and special-method exclusions.

It does not yet freeze exact string or collection size caps, hash preimages, URL canonicalization, adjudication wire encoding, or toolchain dependency hashes. Those remain separate pre-implementation gates.

The certified persistent-storage schema remains `docs/STORAGE_AND_ABI_V1.md` and is not modified by this ABI gate.

## 2. GenLayer ABI conventions

The V1 constructor is a normal undecorated `__init__` method.

Read-only public methods use `@gl.public.view`.

Nonpayable state-changing methods use `@gl.public.write`.

The only payable public method is `open_covenant`, which uses `@gl.public.write.payable`.

All other public writes are nonpayable and must not accept GEN.

Actor checks use `gl.message.sender_address`, not a caller-supplied actor address.

## 3. Constructor

```python
def __init__(self) -> None
```

The V1 constructor accepts no arguments.

It creates no owner, administrator, treasury, upgrade authority, fee recipient, settlement recipient, or governance role.

Persistent root values use the zero-initialized storage model frozen in `docs/STORAGE_AND_ABI_V1.md`.

## 4. Calldata-only input records

These records are ABI input structures. They are not additional Accord402 persistent root fields.

```python
@dataclass
class CriterionInput:
    criterion_id: str
    criterion_text: str

@dataclass
class AuthorityBindingInput:
    authority_id: str
    authority_revision: u32
    role: str
    identity_kind: str
    identity_value: str
    canonical_origin: str

@dataclass
class OpenCovenantInput:
    provider: Address
    principal: u256
    service_spec: str
    acceptance_deadline: u64
    delivery_deadline: u64
    challenge_duration: u64
    absolute_dispute_deadline: u64
    evidence_repair_window: u64
    review_retry_window: u64
    max_review_generations: u32
    max_evidence_age: u64
    required_corroboration_count: u32
    repair_allowed_field_mask: u32
    replay_scope: str
    criteria: list[CriterionInput]
    authority_bindings: list[AuthorityBindingInput]

@dataclass
class EvidenceInput:
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

@dataclass
class EvidenceReplacementInput:
    replaces_evidence_id: str
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

@dataclass
class AccountingTotalsView:
    total_funded: u256
    total_closed_to_provider: u256
    total_closed_to_buyer: u256
    total_outstanding: u256
```

The contract derives `buyer` from `gl.message.sender_address` during `open_covenant`.

The contract derives covenant ID, opened time, protocol-version fields, service-specification hash, evidence-policy hash, delivery hash, evidence-set hash, evidence generation, and replacement generation. None is accepted as a caller-controlled substitute for the canonical derived value.

V1 protocol-version storage fields are contract-defined V1 constants rather than arbitrary caller-selected policy implementations.


### Authority-binding input validation

`OpenCovenantInput.authority_bindings` must contain unique `(authority_id, authority_revision)` pairs.

A duplicate pair is invalid even if `role`, `identity_kind`, `identity_value`, or `canonical_origin` differs.

Evidence supplied to `submit_delivery` or `submit_evidence_repair` must resolve its `(authority_id, authority_revision)` to exactly one frozen authority binding for that covenant.

This rule adds no public method, parameter, return value, or persistent field.

## 5. Canonical public write ABI

```python
@gl.public.write.payable
def open_covenant(self, terms: OpenCovenantInput) -> u64

@gl.public.write
def accept_covenant(self, covenant_id: u64) -> None

@gl.public.write
def expire_unaccepted(self, covenant_id: u64) -> None

@gl.public.write
def submit_delivery(
    self,
    covenant_id: u64,
    delivery_payload: str,
    evidence: list[EvidenceInput],
) -> None

@gl.public.write
def expire_non_delivery(self, covenant_id: u64) -> None

@gl.public.write
def challenge_delivery(
    self,
    covenant_id: u64,
    challenge_claim: str,
    challenged_criterion_ids: list[str],
) -> None

@gl.public.write
def authorize_unchallenged_settlement(self, covenant_id: u64) -> None

@gl.public.write
def adjudicate_challenge(self, covenant_id: u64) -> None

@gl.public.write
def submit_evidence_repair(
    self,
    covenant_id: u64,
    replacements: list[EvidenceReplacementInput],
) -> None

@gl.public.write
def expire_repair(self, covenant_id: u64) -> None

@gl.public.write
def retry_review(self, covenant_id: u64) -> None

@gl.public.write
def expire_review(self, covenant_id: u64) -> None

@gl.public.write
def claim_settlement(self, covenant_id: u64) -> None
```

There are exactly thirteen V1 public write methods.

`open_covenant` is the only payable write.

No public write accepts an arbitrary payout recipient, payout amount, buyer identity, adjudication decision, closure reason, settlement direction, review generation, evidence-set hash, service hash, or delivery hash.

## 6. Write authorization and transition mapping

| Method | Caller rule | Exact protocol purpose |
|---|---|---|
| `open_covenant` | any caller; sender becomes immutable buyer | exact positive GEN funding into a new `FUNDED` covenant |
| `accept_covenant` | immutable provider only | `FUNDED` to `SERVICE_ACCEPTED` before acceptance deadline |
| `expire_unaccepted` | permissionless | expired `FUNDED` to buyer settlement authorization with `UNACCEPTED_EXPIRED` |
| `submit_delivery` | immutable provider only | `SERVICE_ACCEPTED` to `DELIVERED` with immutable delivery and initial evidence |
| `expire_non_delivery` | permissionless | expired `SERVICE_ACCEPTED` to buyer settlement authorization with `NON_DELIVERY_EXPIRED` |
| `challenge_delivery` | immutable buyer only | valid `DELIVERED` challenge to `CHALLENGED`, allocating review generation `1` |
| `authorize_unchallenged_settlement` | permissionless | expired unchallenged `DELIVERED` to provider settlement authorization with `UNCHALLENGED` |
| `adjudicate_challenge` | permissionless | run the frozen GenLayer adjudication only while state is exactly `CHALLENGED` |
| `submit_evidence_repair` | immutable provider only | consume the exact active repair authorization and return to `CHALLENGED` at the next generation |
| `expire_repair` | permissionless | ordinary expired repair state below max generation to buyer settlement authorization with `REPAIR_EXPIRED` |
| `retry_review` | permissionless | valid bounded retry from `REVIEW_RETRY_REQUIRED`, allocate exactly the next generation and perform fresh review |
| `expire_review` | permissionless | neutral `REVIEW_EXPIRED` only under the already-frozen generation-exhaustion or absolute-deadline rules |
| `claim_settlement` | permissionless | close an already-authorized covenant and schedule exactly one finality-only external GEN transfer |

Permissionless methods never accept a recipient or amount and cannot rewrite frozen covenant, delivery, evidence-policy, or settlement bindings.

`adjudicate_challenge` cannot run outside exact `CHALLENGED` state.

`retry_review` cannot run unless state is `REVIEW_RETRY_REQUIRED`, the retry deadline still permits retry, and `review_generation < max_review_generations`.

`expire_repair` cannot be used for maximum-generation repair exhaustion; that path uses `expire_review` and `REVIEW_EXPIRED`.

`claim_settlement` accepts exactly one argument: `covenant_id`. Recipient and amount are derived solely from immutable covenant state.

## 7. Canonical public view ABI

```python
@gl.public.view
def get_covenant_count(self) -> u64

@gl.public.view
def get_covenant(self, covenant_id: u64) -> CovenantRecord

@gl.public.view
def get_criteria(self, covenant_id: u64) -> DynArray[CriterionRecord]

@gl.public.view
def get_authority_bindings(self, covenant_id: u64) -> DynArray[AuthorityBinding]

@gl.public.view
def get_evidence_history(self, covenant_id: u64) -> DynArray[EvidenceRecord]

@gl.public.view
def get_active_evidence_ids(self, covenant_id: u64) -> DynArray[str]

@gl.public.view
def get_repair_authorizations(self, covenant_id: u64) -> DynArray[RepairAuthorizationRecord]

@gl.public.view
def get_challenged_criterion_ids(self, covenant_id: u64) -> DynArray[str]

@gl.public.view
def get_failed_criterion_ids(self, covenant_id: u64) -> DynArray[str]

@gl.public.view
def get_provider_stats(self, provider: Address) -> ProviderStats

@gl.public.view
def get_buyer_stats(self, buyer: Address) -> BuyerStats

@gl.public.view
def get_accounting_totals(self) -> AccountingTotalsView
```

There are exactly twelve V1 public view methods.

`get_covenant` is the canonical covenant-state read. For a terminal covenant its stored fields provide the durable warranty-receipt state defined by the V1 specification.

No view method claims transaction finality, successful external GEN delivery, recipient chain balance, or Ghost balance.

No view method exposes a caller-controlled interpretation that can modify settlement.

## 8. Special methods and fallback surface

V1 intentionally defines no `__receive__` method.

V1 intentionally defines no `__handle_undefined_method__` method.

Therefore no value-only or undefined-method fallback is an intentional Accord402 funding path.

`open_covenant` is the sole intentional payable protocol entry point.

Unexpected GEN must never create a covenant, increase `total_funded`, increase `total_outstanding`, or create settlement entitlement outside a successful `open_covenant` transaction.

## 9. ABI exclusions

V1 has no owner/admin write.

V1 has no upgrade write.

V1 has no emergency withdrawal or escrow drain.

V1 has no arbitrary transfer method.

V1 has no fee withdrawal method.

V1 has no method to alter buyer or provider after funding.

V1 has no method to alter service terms after funding.

V1 has no method to replace challenged criterion IDs after challenge.

V1 has no caller-supplied adjudication-result method.

V1 has no caller-supplied settlement recipient or settlement amount method.

V1 has no method that marks finality or payment success from caller input.

## 10. Remaining pre-implementation freezes

This ABI freeze does not authorize contract implementation yet.

Before `contracts/accord402.py` is created, V1 must still freeze and review:

- exact string and collection input caps;
- exact service-specification hash preimage;
- exact evidence-policy hash preimage;
- exact delivery hash preimage;
- exact active evidence-set hash preimage;
- exact canonical source and URL normalization algorithm;
- exact adjudication-result wire shape and parser rules;
- exact supported GenLayer dependency, linter, and test-tool pins.

The generated contract schema must later be compared against this document exactly. Any schema mismatch is a stop condition, not permission to silently change this ABI.

## 11. Implementation stop rule

No contract implementation may add a public method, payable path, fallback, caller-controlled economic parameter, or return shape outside this frozen V1 ABI without an explicit reviewed specification amendment.

