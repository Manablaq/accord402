# Accord402 R149 Project Explorer handoff — Historical

Status: **HISTORICAL R149 SUBMISSION SNAPSHOT — SUPERSEDED BY R150**

This file records the reviewer-facing Accord402 R149 references. It does not
authorize a contract redeployment, replacement transaction, or change to the
public production URL.

## Frozen submission reference

- repository: `https://github.com/Manablaq/accord402`
- immutable submission commit:
  `ca83530866c6dbd3a73e908715349fce1c8b45e9`
- immutable submission tree:
  `bf64130bcf18aeb3f070cc5b8ef7939e8e1e0325`
- exact-commit CI run: `35541490960`
- CI result: `success`
- stable production URL: `https://accord402.vercel.app`
- production deployment observed during the R149 production certification:
  `https://accord402-py5jvd2ly-mr-albert-s-projects.vercel.app`

The immutable commit URL remains a permanent snapshot even when later
documentation-only maintenance commits are added to the repository.

## Canonical R149 graph

- SettlementVault:
  `0xFCc7FbE2243c32ff35cE74055695Bf8C23E17dD5`
- Registry:
  `0x5BD6f9EEBF7BE527321ED46649447c59fAc5315C`
- Adjudicator:
  `0x9b204786e4641EbFF5D771a08624e2B0849Fcc56`
- Core:
  `0xE315df22c15753D07a2FDb72b15B3AeAF4D27E2A`

Exact source SHA-256 values:

- SettlementVault:
  `e966518dac38ba95df3ff06f7a319bcd97b823a3e36d019003b45ee4a4fe6cd6`
- Registry:
  `bac515e32c8e4a56073b412079995c8bf64ace94274314a491b2dbe411ea35ae`
- Adjudicator:
  `575e063661cc12a5de18dfa67ab3fbeb38bee1028694a08021efbc300115c198`
- Core:
  `ee8d58f6693c16c22eb610140570e0c92a0c923482f154e886f9ae25a7d3c289`

## Canonical GenLayer finality proof

R149 Adjudicator transaction:

`0xb7db252117751910ea7454c1145a866ddbafce72e4f84abe123fd7206cdb4c5e`

Certified result:

- consensus: `FINALIZED`
- execution: `FINISHED_WITH_RETURN`
- deployed Adjudicator:
  `0x9b204786e4641EbFF5D771a08624e2B0849Fcc56`

Accepted state alone is not treated as canonical finality.

## Current economic reviewer case

Covenant `1` proves the current R149 non-delivery buyer-recovery path:

`open/fund -> provider accepts -> no delivery -> expireNonDelivery -> claimSettlement -> CLOSED_BUYER`

Certified consequence:

- principal: `10000000000000000` wei (`0.01 GEN`)
- exact payout delta: `10000000000000000` wei
- final Core balance: `0`
- Vault delivery bit: `true`
- duplicate settlement claim: rejected

The Covenant `1` proof does not claim that this same covenant traversed
provider delivery, challenge, repair/retry, or semantic adjudication.

## Production verification

The production R149 certification verified:

- `https://accord402.vercel.app` returns successfully;
- the page is bound to the current R149 Core and source fingerprint;
- Covenant `1` resolves to `CLOSED_BUYER`;
- the exact R149 Adjudicator transaction resolves to `Finalized`;
- execution result is `1`;
- canonical success is `true`.

Production result SHA-256:

`73fb57cc6cffff3871dd172e4834e203754b69d46af4fc9b7e8b5fe152e9d366`

## Supported-runtime harness scope

The guarded Bradbury supported-runtime deployment harness is tracked and
reproducible but was not executed for R149. It remains supplemental evidence
if a reviewer explicitly requests that specific harness.

No additional Bradbury deployment is authorized by this handoff.

## Maintenance rule

Post-submission cleanup may improve repository documentation and evidence
indexing, but it must not change:

- the submitted immutable commit reference;
- the canonical R149 contract addresses;
- the stable production URL `https://accord402.vercel.app`; or
- the historical evidence attached to the certified R149 transactions.
