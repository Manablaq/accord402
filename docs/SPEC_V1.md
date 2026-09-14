# Accord402 V1 Protocol Specification

Status: FROZEN BEFORE IMPLEMENTATION

## 1. Product definition

Accord402 is a GenLayer-native service warranty protocol for autonomous agents.

A buyer funds a service covenant with native GEN. A provider accepts the covenant, performs the requested service, and submits a delivery with policy-bound evidence. If the delivery is not challenged before the challenge deadline, the provider becomes entitled to settlement. If the buyer challenges the delivery, GenLayer validators independently adjudicate whether the delivery satisfies the frozen service covenant.

The protocol exists specifically for claims that deterministic smart-contract logic cannot decide alone.

## 2. V1 scope

V1 includes:

- one canonical Accord402 Intelligent Contract;
- native GEN escrow;
- immutable covenant terms after funding;
- provider acceptance;
- delivery submission;
- evidence binding;
- buyer challenge;
- GenLayer-native evidence-based adjudication;
- evidence repair;
- transient review retry;
- deterministic expiry/recovery;
- finality-safe payout/refund;
- immutable warranty receipt data;
- deterministic reputation counters;
- public view methods suitable for frontend and agent SDK clients.

V1 excludes:

- ERC-20 settlement;
- production x402 payment integration;
- arbitrary split settlement;
- partial refunds;
- percentage-based adjudication;
- protocol governance;
- upgradeable contract logic;
- off-chain private arbitration;
- multi-provider covenants;
- buyer-selected payout destinations after funding.

## 3. Actors

### Buyer
The address that funds a covenant.

### Provider
The address committed in the covenant and exclusively authorized to accept and submit delivery.

### Permissionless caller
Any address may invoke an objective expiry/finalization helper only after its exact deterministic preconditions are satisfied.

### GenLayer validators
The decentralized validator committee that independently evaluates disputed delivery against the frozen covenant and admissible evidence.

## 4. Covenant immutability boundary

The following become immutable when funding succeeds:

- covenant ID;
- buyer;
- provider;
- escrow principal;
- service specification;
- service specification hash;
- acceptance deadline;
- delivery deadline;
- challenge duration/deadline rule;
- absolute dispute deadline;
- evidence-repair window;
- review-retry window;
- maximum review generations;
- evidence policy;
- approved evidence authorities;
- maximum evidence age;
- adjudication criteria;
- settlement rule version.

After funding, no method may mutate these fields.

### Authority-binding identity

Within one covenant, every approved authority binding is identified for evidence resolution by the exact pair `(authority_id, authority_revision)`.

That pair must be unique across the complete frozen authority-binding set for the covenant.

Two bindings with the same `(authority_id, authority_revision)` are forbidden even if their role, identity kind, identity value, canonical origin, list position, or other metadata differs.

Funding with a duplicate authority pair must revert before a covenant ID is consumed and before covenant storage, replay state, or escrow accounting changes.

Every submitted or repaired evidence record must resolve its `(authority_id, authority_revision)` to exactly one frozen authority binding for the same covenant.

The same `authority_id` may appear at different revisions only as distinct versioned bindings. A revision change does not by itself create independent corroboration.

Corroboration independence remains based on distinct approved authority identity under the frozen evidence policy; duplicate rows or revision variants of the same underlying authority must never be counted as independent corroborators.

The absolute dispute deadline is an explicit covenant value frozen when funding succeeds.

It must be strictly later than the latest possible challenge deadline: the delivery deadline plus the frozen challenge duration.

A delivery therefore cannot shorten the buyer's frozen challenge window merely because the provider delivered at the delivery deadline.

When evidence repair is required, the local repair deadline is the earlier of the repair-start time plus the frozen evidence-repair window and the absolute dispute deadline.

When review retry is required, the local retry deadline is the earlier of the retry-start time plus the frozen review-retry window and the absolute dispute deadline.

No repair, retry, validator recomputation, or later transaction may change or extend the absolute dispute deadline.

Evidence repair may replace only repair-authorized evidence records. It may not alter covenant terms, delivery content, delivery hash, principal, buyer, provider, or adjudication criteria.

## 5. Funding and escrow

V1 uses native GEN only.

Opening a covenant is payable. The contract must require the received `gl.message.value` to equal the exact covenant principal.

Zero-value canonical covenants are forbidden.

Underpayment and overpayment are rejected.

The contract must maintain explicit accounting for unresolved covenant principal and any unsettled entitlement.

## 6. Canonical covenant states

V1 separates contract state, adjudication decision, and closure reason. These concepts must not be conflated.

The canonical contract states are:

- `FUNDED`
- `SERVICE_ACCEPTED`
- `DELIVERED`
- `CHALLENGED`
- `EVIDENCE_REPAIR_REQUIRED`
- `REVIEW_RETRY_REQUIRED`
- `SETTLEMENT_AUTHORIZED_PROVIDER`
- `SETTLEMENT_AUTHORIZED_BUYER`
- `CLOSED_PROVIDER`
- `CLOSED_BUYER`

`CLOSED_PROVIDER` and `CLOSED_BUYER` are terminal.

Adjudication decisions are separate from covenant state and are defined in Section 12.

Canonical closure reasons are:

- `UNACCEPTED_EXPIRED`
- `NON_DELIVERY_EXPIRED`
- `UNCHALLENGED`
- `SERVICE_VERIFIED`
- `PROVIDER_BREACH`
- `BUYER_CLAIM_INVALID`
- `REPAIR_EXPIRED`
- `REVIEW_EXPIRED`

`REVIEW_EXPIRED` is a neutral liveness closure reason. It is not a finding of provider breach and is not a finding that the buyer claim was invalid.

The implementation must not introduce an economic transition, contract state, adjudication decision, or closure reason outside the frozen V1 state machine.
## 7. Acceptance

Only the frozen provider may accept.

Acceptance is valid only on or before the acceptance deadline.

Acceptance cannot be repeated.

If the provider does not accept before expiry, the covenant becomes eligible for deterministic buyer refund.

## 8. Delivery

Only the frozen provider may submit delivery.

Delivery is allowed only from `SERVICE_ACCEPTED`.

Delivery must occur on or before the delivery deadline.

The provider submits an exact delivery payload plus policy-compliant evidence metadata.

The delivery payload/hash becomes immutable after submission.

The challenge deadline is derived deterministically from the delivery transaction time and the covenant's frozen challenge duration.

## 9. Challenge

Only the frozen buyer may challenge.

A challenge is allowed only while the delivery challenge window is open.

The challenge identifies one or more frozen criterion IDs claimed to have failed and may include a bounded explanatory claim.

A challenge cannot alter the service specification, evidence policy, delivery, price, parties, or deadlines.

V1 permits only one unresolved challenge per covenant.

## 10. Unchallenged settlement

When the challenge deadline has passed without a valid challenge, deterministic contract logic may establish provider entitlement.

No LLM or web adjudication is needed for the absence of a challenge.

The economic transfer itself must still follow the verified finality-safe settlement design.

## 11. GenLayer-native adjudication boundary

Only a challenged delivery enters nondeterministic adjudication.

The leader and validators evaluate the same frozen decision inputs:

- covenant ID;
- service specification hash;
- exact adjudication criteria;
- delivery hash;
- evidence-set hash;
- evidence authority policy;
- evidence freshness constraints;
- buyer challenge;
- review generation.

The leader returns a compact structured result.

Validators must independently verify the substance of that result using the same frozen criteria and independently retrieved or independently assessed policy-approved evidence.

Leader-output-only shape validation is forbidden.

## 12. Allowed adjudication decisions

Only these decision classes are valid:

- `SERVICE_VERIFIED`
- `PROVIDER_BREACH`
- `BUYER_CLAIM_INVALID`
- `EVIDENCE_REPAIR_REQUIRED`
- `REVIEW_RETRY_REQUIRED`

No confidence score, percentage, fuzzy threshold, or tolerance may authorize payment or refund.

## 13. Exact consequential result fields

The accepted adjudication result must bind at minimum:

- covenant ID;
- delivery hash;
- evidence-set hash;
- review generation;
- decision;
- exact failed criterion IDs;
- exact failure classification when applicable.
- exact ordered repair authorization entries when the decision is `EVIDENCE_REPAIR_REQUIRED`.

If validators cannot independently verify these consequential fields, the transaction must not produce a settlement-authorizing state.

## 14. Evidence repair

`EVIDENCE_REPAIR_REQUIRED` is used for evidence defects that can be corrected without changing the delivered work.

Repair may replace only policy-permitted evidence identifiers, immutable/versioned references, timestamps, digests, and related evidence metadata.

For `EVIDENCE_REPAIR_REQUIRED`, the accepted adjudication result must contain an exact ordered non-empty repair authorization set.

Each repair authorization binds one evidence ID from the current active evidence set and an exact repair-field mask.

No other adjudication decision may create repair authorization.

A repair authorization may target only a currently active evidence record and only fields allowed by the frozen evidence policy.

The repair-field mask encoding must be frozen in `docs/STORAGE_AND_ABI_V1.md` before contract implementation.

Repair must not alter:

- covenant;
- service specification;
- delivery payload;
- delivery hash;
- principal;
- buyer;
- provider;
- challenged criteria.

A successful repair creates a new exact evidence-set hash and increments the review generation.

V1 evidence repair is atomic at the active-evidence-set level.

A repair transaction must provide exactly one replacement for every authorized evidence ID and no replacement for any unauthorized evidence ID.

Every replacement must use a fresh replay-safe evidence ID, satisfy the same frozen authority policy, preserve every non-authorized field exactly, and remain bound to the same covenant and delivery.

Successful repair appends the replacement evidence records to history, replaces the authorized active evidence IDs in their existing ordered positions, computes the new exact active evidence-set hash, consumes the complete repair authorization set, increments `review_generation` exactly once, and returns the covenant to `CHALLENGED` for fresh adjudication.

Missing, extra, duplicate, stale, or unauthorized replacements must revert without changing evidence history, active evidence selection, review generation, deadlines, or covenant state.

Repaired evidence IDs must be fresh and replay-safe.

### Covenant-wide evidence-ID uniqueness

Every accepted evidence record must have a non-empty `evidence_id`.

Within one covenant, an `evidence_id` is globally unique across all approved authorities, authority revisions, evidence roles, sources, and evidence generations.

Once an evidence ID has appeared in the immutable evidence history of covenant `C`, the same literal evidence ID can never be accepted again for covenant `C`.

Changing authority, authority revision, evidence role, source, repair generation, or other evidence metadata does not make a reused covenant evidence ID fresh.

This covenant-wide uniqueness rule is stricter than the separate authority-aware replay policy.

For every newly accepted evidence record, the contract must reserve the covenant-wide identity key `I|<covenant-key>|<evidence-id>`.

The `I|...` identity reservation is monotonic and is never cleared by repair, expiry, settlement, or terminal closure.

The frozen evidence replay scope additionally requires exactly one authority-aware replay key.

For replay scope `COVENANT`, that key is `C|<covenant-key>|<authority-id>|<evidence-id>`.

For replay scope `GLOBAL`, that key is `G|<authority-id>|<evidence-id>`.

Authority IDs and evidence IDs must reject the `|` character before any identity or replay key is constructed.

A new evidence record is valid only when both its covenant-wide `I|...` identity reservation and its applicable authority-aware replay key are unused.

Successful evidence-record insertion atomically appends the evidence record and marks both required keys used.

A reverted, rejected, malformed, unauthorized, duplicate, or otherwise unsuccessful evidence insertion consumes neither key.

The covenant-wide uniqueness rule ensures that every active evidence ID resolves to exactly one historical evidence record within that covenant.

Repair replacements are subject to the same rule and therefore must use a covenant-wide fresh evidence ID.

## 15. Review retry

`REVIEW_RETRY_REQUIRED` is used only when trustworthy adjudication cannot be completed because of transient source, model, validator, or infrastructure conditions that do not establish substantive provider breach.

A retry must preserve the same frozen covenant, delivery, challenged criterion IDs, and consequential bindings.

The evidence set remains unchanged unless a separate evidence repair was authorized under the frozen repair policy.

Each retry consumes a bounded review generation. Retry cannot reset or extend any covenant deadline.

### Review generation lifecycle

`max_review_generations` is an immutable positive covenant value frozen at funding. V1 must reject a funded covenant whose value is zero. The exact public-input upper cap is frozen separately with the ABI/input-cap gate.

Generation `0` means that no challenged adjudication generation has been allocated.

`review_generation` is initialized to `0` when funding succeeds and remains `0` through acceptance, delivery, and an unchallenged settlement path.

A valid buyer challenge atomically changes `review_generation` from `0` to `1` when the covenant enters `CHALLENGED`. Therefore the first challenged adjudication always evaluates generation `1`.

A covenant already challenged must never return to generation `0`.

Every challenged adjudication input and every accepted consequential result must bind the exact current `review_generation`.

Running adjudication does not itself increment `review_generation`.

An accepted `SERVICE_VERIFIED`, `PROVIDER_BREACH`, or `BUYER_CLAIM_INVALID` result terminates semantic review without incrementing the generation.

An accepted `EVIDENCE_REPAIR_REQUIRED` result at generation `N` records its exact repair authorization against generation `N`; merely entering `EVIDENCE_REPAIR_REQUIRED` does not increment the generation.

If `N < max_review_generations`, one successful complete authorized repair consumes that repair authorization and atomically changes `review_generation` from `N` to `N + 1` before returning the covenant to `CHALLENGED` for fresh adjudication.

An accepted `REVIEW_RETRY_REQUIRED` result at generation `N` does not itself increment the generation.

If `N < max_review_generations`, one valid retry atomically changes `review_generation` from `N` to `N + 1` before the fresh adjudication for that retry.

No repair, retry, adjudication, or other transition may ever produce `review_generation > max_review_generations`.

Rejected, reverted, malformed, stale-generation, duplicate, or otherwise unsuccessful repair/retry writes do not consume a generation.

If an accepted `EVIDENCE_REPAIR_REQUIRED` or `REVIEW_RETRY_REQUIRED` result occurs when `review_generation == max_review_generations`, the review-generation budget is exhausted because that intermediate result requires another generation to make further review progress.

Generation-budget exhaustion is a neutral liveness condition. It is not `PROVIDER_BREACH`, is not `BUYER_CLAIM_INVALID`, and creates no corresponding reputation judgment.

From `EVIDENCE_REPAIR_REQUIRED` or `REVIEW_RETRY_REQUIRED` with `review_generation == max_review_generations`, any caller may invoke `expire_review` without waiting for the absolute dispute deadline.

That generation-exhaustion `expire_review` path records closure reason `REVIEW_EXPIRED`, authorizes return of the exact unresolved principal to the immutable buyer, and invalidates any active repair authorization.

No repair or retry transaction is valid once the covenant is in an intermediate review state at `review_generation == max_review_generations`.

By contrast, `CHALLENGED` with `review_generation == max_review_generations` is not by itself generation exhaustion. The already allocated current generation must still be allowed to produce its trustworthy consequential adjudication result.

While a covenant remains `CHALLENGED`, generation equality alone must never let a caller bypass that current adjudication generation.

The absolute dispute deadline remains an independent ultimate liveness bound. After that deadline, the existing `expire_review` rule applies even if the generation budget has not been exhausted.

Neither generation allocation nor generation exhaustion changes or extends the absolute dispute deadline.


Every challenged covenant is bounded by an absolute dispute deadline fixed by the frozen covenant timing policy.

After that absolute dispute deadline passes without a trustworthy settlement-authorizing adjudication, any caller may invoke `expire_review`.

`expire_review` records closure reason `REVIEW_EXPIRED` and moves the covenant to `SETTLEMENT_AUTHORIZED_BUYER`.

`REVIEW_EXPIRED` is neutral: it creates no `PROVIDER_BREACH` finding, no `BUYER_CLAIM_INVALID` finding, and no corresponding reputation judgment.

A technical or infrastructure failure therefore cannot fabricate a semantic judgment and cannot lock escrow indefinitely.

## 16. Liveness

Every escrow-bearing nonterminal state has a deterministic bounded path forward.

At minimum:

- unaccepted covenant -> buyer settlement authorization after acceptance expiry;
- accepted but undelivered -> buyer settlement authorization after delivery expiry;
- delivered but unchallenged -> provider settlement authorization after challenge expiry;
- evidence repair required -> valid repair before its bounds or buyer settlement authorization after repair expiry;
- review retry required -> bounded retry before the absolute dispute deadline or neutral buyer settlement authorization through `REVIEW_EXPIRED`;
- challenged without a trustworthy consequential judgment -> neutral buyer settlement authorization after the absolute dispute deadline;
- settlement-authorized state -> permissionless settlement execution to the already-fixed immutable recipient for the exact unresolved principal.

Repair and retry must never extend the absolute dispute deadline.

No buyer, provider, validator, administrator, frontend, failed evidence source, model failure, or infrastructure failure may lock covenant principal indefinitely.

## 17. Settlement recipients

Canonical V1 settlement recipients are immutable:

- provider settlement authorization -> original covenant provider;
- buyer settlement authorization -> original covenant buyer.

The public settlement execution method is `claim_settlement(covenant_id)`.

The method accepts only the covenant ID. It accepts no recipient argument and no amount argument.

Settlement execution is permissionless because the caller cannot redirect value or alter the amount.

For `SETTLEMENT_AUTHORIZED_PROVIDER`, the contract derives the immutable provider and the exact unresolved covenant principal.

For `SETTLEMENT_AUTHORIZED_BUYER`, the contract derives the immutable buyer and the exact unresolved covenant principal.

No owner, administrator, caller, relayer, frontend, SDK, evidence record, or validator output may substitute another settlement recipient or amount.

V1 has no split settlement and no arbitrary settlement recipient.

The settlement write schedules exactly one external native GEN transfer through the finality-only external-message path.

A canonically closed covenant cannot schedule settlement a second time.

## 18. Finality and execution truth

Accord402 must not equate `Accepted` with final settlement.

An accepted transaction is provisional and may still be affected by the GenLayer finality process.

External settlement is finality-only. Accord402 must never create an on-acceptance external economic consequence.

A provisional `CLOSED_PROVIDER` or `CLOSED_BUYER` value is not proof that GEN reached the entitled participant.

Canonical settlement success requires both:

1. transaction status `Finalized`;
2. execution result `FINISHED_WITH_RETURN`.

A finalized transaction with an unsuccessful execution result is not a successful settlement.

Clients must separately track:

- transaction submission;
- consensus state;
- accepted or provisional state;
- settlement authorization;
- provisional closed state when visible;
- finality;
- execution result;
- external settlement evidence.

After a settlement transaction ID exists, the application must persist and continue tracking that exact transaction ID.

An uncertain observation, timeout, RPC failure, frontend restart, or process restart must not trigger blind settlement resubmission.

Bradbury certification must additionally prove the real recipient GEN balance effect, the corresponding Accord402 or Ghost balance effect, and duplicate-claim resistance for the exact persisted settlement transaction.

## 19. Warranty receipt

Every terminal covenant exposes durable contract receipt data including:

- covenant ID;
- immutable buyer;
- immutable provider;
- exact funded principal;
- terminal contract state (`CLOSED_PROVIDER` or `CLOSED_BUYER`);
- service specification hash;
- delivery hash when present;
- evidence-set hash when present;
- adjudication decision when one exists;
- exact closure reason;
- failed criterion IDs when present;
- settlement direction;
- review generation.

Contract state, adjudication decision, and closure reason are distinct receipt fields and must never be collapsed into a single terminal-decision field.

Deterministic expiry or unchallenged paths may have no adjudication decision. Their economic meaning is expressed by the exact closure reason and settlement direction.

`REVIEW_EXPIRED` records no `PROVIDER_BREACH` decision and no `BUYER_CLAIM_INVALID` decision.

The contract receipt does not self-certify transaction finality or prove that the external GEN transfer reached the recipient.

A receipt observed from provisional state is provisional.

The canonical warranty receipt is the receipt read from finalized successful contract state after the settlement transaction reaches `Finalized` with execution result `FINISHED_WITH_RETURN`.

Reviewer and client settlement evidence must bind that receipt to the exact persisted settlement transaction ID and independently verify the real external GEN balance consequence on Bradbury.

The receipt is protocol state, not an off-chain rating, frontend assertion, or substitute for chain execution evidence.

## 20. Reputation

Reputation is derived only from finalized terminal covenant outcomes.

V1 stores factual counters rather than subjective scores.

Provider counters may include:

- services accepted;
- deliveries submitted;
- services verified;
- provider breaches;
- non-deliveries;
- disputes won;
- disputes lost.

Buyer counters may include:

- funded covenants;
- challenges filed;
- valid challenges;
- invalid challenges.

Any percentage shown by the frontend is derived presentation and cannot drive settlement.

## 21. Frontend and SDK trust boundary

Frontend and SDK are untrusted clients.

Authorization, deadlines, evidence policy, state transitions, accounting, and settlement are enforced on-chain by the Intelligent Contract.

The UI must distinguish provisional/non-final state from finalized state.

## 22. Deployment discipline

No canonical Bradbury deployment occurs until:

- GenVM lint passes;
- typecheck passes;
- storage/schema checks pass;
- deterministic Direct Mode tests pass;
- adversarial Direct Mode tests pass;
- leader/validator tests pass;
- accounting invariant tests pass;
- frontend typecheck/build passes.

Every Bradbury write transaction ID is persisted and tracked. Pending actions are not blindly resubmitted.

## 23. V1 completion definition

Accord402 V1 is not complete until:

- the frozen specification and implementation agree;
- all deterministic/adversarial tests pass reproducibly;
- canonical source is hashed and frozen;
- Bradbury deployment reaches finality and successful execution;
- unchallenged provider settlement is demonstrated live;
- challenged valid delivery -> provider win is demonstrated live;
- challenged invalid delivery -> buyer win is demonstrated live;
- repairable evidence -> repair -> final judgment is demonstrated live;
- accepted provider with no delivery -> buyer refund is demonstrated live;
- finality-safe settlement behavior is proven;
- deployed-source parity is proven;
- reviewer evidence and submission documentation are complete.

## 24. Implementation stop rule

If implementation requires a GenLayer behavior or API not covered by the verified baseline, stop and verify the current official GenLayer documentation before coding against it.
