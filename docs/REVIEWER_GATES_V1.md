# Accord402 V1 — Reviewer Readiness Gates

> **Payout-liveness amendment:** `docs/SECURITY_HARDENING_V4.md` supersedes conflicting persistent-credit and payout-withdrawal semantics.

> **Settlement-liveness amendment:** `docs/SECURITY_HARDENING_V3.md` supersedes conflicting payout-recipient and vault-withdrawal semantics.

> **Security amendment:** `docs/SECURITY_HARDENING_V2.md` supersedes any conflicting weaker V1 rule in this document.

A canonical Accord402 release is not submission-ready unless every applicable gate below passes.

## Architecture gates

| Gate | Required proof |
|---|---|
| GenLayer necessity | disputed fulfillment requires nondeterministic evidence interpretation and validator consensus; deterministic paths do not waste AI consensus |
| State-machine completeness | every write maps to a frozen state transition |
| Escrow liveness | every escrow-bearing nonterminal state has a bounded recovery path |
| No hidden economic path | every value-bearing/public/special/message path is enumerated and reviewed |
| No arbitrary recipient | settlement destination is fixed by covenant + finalized outcome |
| No privileged drain | no admin/owner escape can seize user escrow |

## Evidence gates

| Gate | Required proof |
|---|---|
| Provenance | approved evidence authorities are frozen before adjudication |
| Immutable/versioned evidence | immutable sources use immutable version identifiers and canonical parsing |
| Live-source honesty | mutable live pages are not mislabeled as immutable |
| Freshness | publication/observation/expiry/max-age rules are enforced |
| Corroboration | independence means distinct approved authority identity, not merely multiple URLs |
| Stable evidence identity | evidence IDs are replay-protected in explicit scope |
| Cross-covenant isolation | covenant/policy/evidence-set bindings prevent reuse confusion |
| Repair discipline | repair changes evidence only, never delivery/covenant/value recipient |
| Prompt-injection resistance | web content is untrusted data and cannot redefine policy |
| Failure classification | repairable party evidence faults are distinct from transient infrastructure retry |

## Consensus gates

| Gate | Required proof |
|---|---|
| Independent leader verification | validator consults independent permitted evidence |
| No shape-only validator | JSON/schema/enum/confidence checks alone cannot approve |
| Exact consequence binding | covenant, service hash, delivery hash, policy hash, evidence-set hash, decision, and required criteria fields are checked |
| No fuzzy authorization | no confidence score/tolerance/semantic similarity alone decides who receives GEN |
| Malformed-result handling | invalid leader/LLM results cannot create economic entitlement |
| Deterministic side effects | storage/value mutations occur outside nondeterministic blocks using only accepted structured result |

## Finality and transaction gates

| Gate | Required proof |
|---|---|
| Accepted != Finalized | UI, SDK, docs, and contract consequence model preserve distinction |
| Execution != consensus | canonical success requires appropriate status plus successful execution result |
| Finality-gated settlement | irreversible external consequence is not emitted on provisional acceptance |
| Transaction persistence | tx IDs are persisted/tracked; uncertain state does not trigger blind replay |
| Child/external message semantics | chosen settlement transport is tested against documented GenLayer behavior |

## Accounting gates

| Gate | Required proof |
|---|---|
| Exact GEN arithmetic | `u256` wei; no float/tolerance |
| Per-covenant conservation | buyer + provider + outstanding equals funded amount |
| Global conservation | closed-to-buyer + closed-to-provider + outstanding equals total funded |
| Cross-covenant isolation | settling one covenant cannot spend another covenant's liability |
| Double-settlement resistance | replay/duplicate action cannot pay twice |
| Real-network payout proof | canonical Bradbury case demonstrates actual recipient balance consequence |

## Storage and API gates

| Gate | Required proof |
|---|---|
| Storage-compatible types | class-level persistent fields use supported GenLayer types |
| Fully instantiated generics | persistent `TreeMap`/`DynArray` types are fully specified |
| Sized integers | persistent economic/timestamp/count values use deliberate sized types |
| Custom storage classes | use the required storage decorator/serialization pattern |
| Input bounds | strings, arrays, evidence count, and criteria count have explicit limits |
| ABI review | every public/view/write/payable/special method is intentional |

## Deterministic test gates

At minimum Direct Mode/adversarial tests must cover:

- valid funding;
- zero/wrong funding;
- provider-only acceptance/delivery/repair;
- buyer-only challenge;
- unaccepted expiry;
- non-delivery expiry;
- unchallenged provider settlement authorization;
- valid challenged provider win;
- valid challenged buyer win;
- invalid buyer claim;
- leader/validator disagreement;
- shape-only malicious leader output;
- stale evidence;
- future timestamps;
- wrong authority;
- mutable/ambiguous immutable source;
- evidence replay;
- cross-covenant replay;
- repair success;
- forbidden repair mutation;
- repair expiry;
- retry success;
- retry expiry;
- malformed LLM output;
- HTTP 4xx vs 5xx classification;
- prompt-injection evidence fixture;
- duplicate settlement/refund;
- terminal replay;
- two simultaneous covenants accounting isolation;
- exact liability/accounting invariants.

## Bradbury gates

Canonical live verification must prove, with fresh covenant/evidence identities:

1. contract deployment finalizes and execution succeeds;
2. deployed source bytes match the frozen source;
3. payable GEN funding is real;
4. provider acceptance/delivery is real;
5. at least one successful unchallenged path;
6. at least one real challenged validator adjudication;
7. at least one provider-side and one buyer-side consequential result across canonical/disposable cases;
8. finality is observed before irreversible consequence;
9. settlement transport delivers the expected real GEN balance effect;
10. transaction IDs are tracked without duplicate writes;
11. final contract state and accounting match expected liabilities;
12. production frontend reads the canonical Bradbury deployment.

Destructive/adversarial live cases should use disposable covenant identities or targets and must never corrupt the canonical successful demonstration merely to manufacture evidence.

## Documentation gates

Required reviewer-facing artifacts before submission:

- `README.md`
- `docs/SPEC_V1.md`
- `docs/STATE_MACHINE_V1.md`
- `docs/EVIDENCE_MODEL_V1.md`
- `docs/SETTLEMENT_INVARIANTS_V1.md`
- `docs/THREAT_MODEL_V1.md`
- `docs/VERIFIED_GENLAYER_BASELINE.md`
- deterministic test report/preflight artifact;
- Bradbury plan;
- current final evidence record;
- compact submission handoff.

Historical failed deployments must be clearly labeled historical/superseded and must never be presented as canonical.

## Pre-code implementation gates

The two previously unresolved protocol-design blockers are now closed.

### Retry exhaustion

V1 freezes an absolute dispute deadline. Retry and repair cannot extend it.

If trustworthy consequential adjudication is still unavailable after that deadline, `expire_review` permissionlessly records neutral closure reason `REVIEW_EXPIRED` and authorizes return of the exact unresolved principal to the immutable buyer.

`REVIEW_EXPIRED` creates no `PROVIDER_BREACH` finding, no `BUYER_CLAIM_INVALID` finding, and no corresponding reputation judgment.

### Settlement transport

V1 freezes settlement through `claim_settlement(covenant_id)`.

The caller supplies neither recipient nor amount.

The contract derives the immutable entitled participant and exact unresolved principal from covenant state.

Settlement execution is permissionless because the trigger cannot redirect or resize the economic consequence.

External native GEN settlement is finality-only. Provisional acceptance or provisional closed state is not canonical proof of payment.

Canonical settlement requires transaction status `Finalized` plus execution result `FINISHED_WITH_RETURN`.

Blind settlement replay is forbidden. Once a settlement transaction ID exists, clients must continue tracking that exact transaction instead of submitting another payment because observation is uncertain.

Bradbury recipient-balance proof, Ghost or Accord402 balance proof, and duplicate-claim resistance remain mandatory certification gates.

There is no remaining protocol-design blocker to defining the exact persistent storage schema and public ABI.

Contract implementation remains prohibited until those storage/API definitions are frozen and checked against the current supported GenLayer toolchain and APIs.

## Stop rule

If any hard gate fails, Accord402 is not reviewer-ready.

A PASS label, README claim, frontend badge, or prior assistant assertion is never a substitute for independently reproducible evidence.
