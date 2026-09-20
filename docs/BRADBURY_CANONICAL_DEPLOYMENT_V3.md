# Accord402 Canonical Bradbury Deployment V3

Status: **CURRENT CANONICAL R149 GRAPH**

This document supersedes the V2 deployment record as the current Accord402
Bradbury graph. V1/V2 artifacts remain preserved as historical evidence.

## Release binding

- source release commit: `ebfe5ce3be305de360bcf86dde05c55936f8b637`
- source release tree: `0694e768890cb17e4eb32f014ab0b4ae6ee24e7b`
- Bradbury chain ID: `4221`
- GenLayer RPC: `https://rpc-bradbury.genlayer.com`
- EVM RPC: `https://rpc.testnet-chain.genlayer.com`
- explorer: `https://explorer-bradbury.genlayer.com`

## Current canonical graph

| Component | Address | Deployment provenance |
| --- | --- | --- |
| SettlementVault | `0xFCc7FbE2243c32ff35cE74055695Bf8C23E17dD5` | reused verified V2 deployment; EVM tx `0xa478daf9a3a280214eb70592ffcd98cb7c4590fc044236fbaf4bf9df5537ffb7` |
| Registry | `0x5BD6f9EEBF7BE527321ED46649447c59fAc5315C` | reused verified V2 deployment; EVM tx `0xe8ebf7abdf511e2aaebfda13cb0fab9a6d2e881e785eeb969e0a30ec63007608` |
| Adjudicator | `0x9b204786e4641EbFF5D771a08624e2B0849Fcc56` | R149 GenLayer tx `0xb7db252117751910ea7454c1145a866ddbafce72e4f84abe123fd7206cdb4c5e`; outer EVM tx `0xc5304a59e389ee9bb26f5437f6c7612c3722a4e9ab5e6f16db8358001535838f` |
| Core | `0xE315df22c15753D07a2FDb72b15B3AeAF4D27E2A` | R149 EVM deployment tx `0xa8ece88c6e71b7d5bb7a5e14fa2dc711cff9fa158699b56c511d49daf563259d` |

The earlier Adjudicator `0x5c958e498C3109922AFAc661EB466628Fe521CB6` and Core `0x3eA9E19531a59BA31C2E4f396Ab2b0256304e835` are
superseded deployment components. They remain historical evidence only.

## Exact source binding

- SettlementVault SHA-256: `e966518dac38ba95df3ff06f7a319bcd97b823a3e36d019003b45ee4a4fe6cd6`
- Registry SHA-256: `bac515e32c8e4a56073b412079995c8bf64ace94274314a491b2dbe411ea35ae`
- Adjudicator SHA-256: `575e063661cc12a5de18dfa67ab3fbeb38bee1028694a08021efbc300115c198`
- Core SHA-256: `ee8d58f6693c16c22eb610140570e0c92a0c923482f154e886f9ae25a7d3c289`

The current Core dependency getters resolve to the Registry, Adjudicator, and
SettlementVault addresses listed above.

## Adjudicator finality

- GenLayer transaction: `0xb7db252117751910ea7454c1145a866ddbafce72e4f84abe123fd7206cdb4c5e`
- deployed address: `0x9b204786e4641EbFF5D771a08624e2B0849Fcc56`
- status: finalized
- execution result: `FINISHED_WITH_RETURN`
- graph certification SHA-256: `d3e070b2992175dc6356f028a0ee7b0a783ed4e74a79a16b7c552803fbb9d886`

An Accepted lifecycle is not treated as a substitute for finalized consensus.

## Current Core economic certification

Covenant `1` was executed with isolated reviewer-case signers:

- buyer: `0x67a6F6dD67E7DffEcD760a99b4D5A2fe019EbA4f`
- provider: `0x64f332ba2ED3F7372fF3FE3d777Ad01fbd3195a4`
- registered settlement payout: `0x1f87Ae197af539253978d435aD45cCf28Fb95024`
- principal: `10000000000000000` wei (`0.01 GEN`)
- open transaction: `0x7b45999ab31e82e941d25712be32770c7fd4f3d66b1e3ab938d591c93f5ca9cd`
- acceptance transaction: `0xaa010bd94bdd93ae2c9dc185174aba92a931a3609c1d6ef07bbb6783da8a98f3`
- non-delivery expiry transaction: `0x1219914b612f60c439953be4818702d7e081167535e0bdc62c0ac86c87de3740`
- settlement claim transaction: `0x18197505652f86fc21ad1a926e8e5220a5a518b9673c97468c5fbbd3a151c77b`
- final state: `CLOSED_BUYER`
- accounting: `10000000000000000|0|10000000000000000|0`
- final Core native balance: `0`
- exact payout delta: `10000000000000000` wei
- Vault delivery bit: `true`
- duplicate claim: rejected read-only with `SettlementAlreadyClaimed()`
  selector `0x3eed0c7d`

See `BRADBURY_CURRENT_CORE_ECONOMIC_PROOF_V1.md`.

## Evidence binding

- canonical graph certification SHA-256: `d3e070b2992175dc6356f028a0ee7b0a783ed4e74a79a16b7c552803fbb9d886`
- isolated open/accept result SHA-256: `56ff80afc9fd0cda606b9dac0d5715dace980fd10c572c8e1272a90a3b7ced4c`
- non-delivery settlement result SHA-256: `8ab851d5706e0c0f22bb570730cd0c4f8acfaf5ca704338df6b491c4605dc67d`
- release reconciliation SHA-256: `e298b12a6d4baeb674abab9b9d215910f238aba8a7b3a440d08c4fc70757ba86`

## Scope

This live Covenant `1` proves the current R149 Core path:

    open/fund
    -> provider accepts
    -> no delivery
    -> expireNonDelivery
    -> buyer settlement authorized
    -> claimSettlement
    -> CLOSED_BUYER
    -> duplicate claim rejected

It proves exact native-GEN consequence, accounting conservation, liveness
recovery, Vault routing, and duplicate-claim resistance.

It does not claim that Covenant `1` exercised delivery, challenge,
repair/retry, or semantic adjudication.

Publication with green CI and production frontend R149 rebinding/E2E are
complete. The guarded supported-runtime deployment harness remains available
as supplemental reproducibility evidence if a reviewer explicitly requests
that specific harness; it has not been executed for R149 and no additional
Bradbury write is authorized by this release record. Submission readiness is
determined by the final no-write repository/evidence/production audit.
