# Accord402 Current Core Economic Proof V1

Status: **PASS — R149 NON-DELIVERY BUYER RECOVERY**

This document records the live economic consequence of Covenant `1` on the
current R149 Core `0xE315df22c15753D07a2FDb72b15B3AeAF4D27E2A`.

## Bound release

- source release commit: `ebfe5ce3be305de360bcf86dde05c55936f8b637`
- source release tree: `0694e768890cb17e4eb32f014ab0b4ae6ee24e7b`
- chain ID: `4221`
- Core source SHA-256: `ee8d58f6693c16c22eb610140570e0c92a0c923482f154e886f9ae25a7d3c289`
- R2C open/accept evidence SHA-256: `56ff80afc9fd0cda606b9dac0d5715dace980fd10c572c8e1272a90a3b7ced4c`
- R6D settlement evidence SHA-256: `8ab851d5706e0c0f22bb570730cd0c4f8acfaf5ca704338df6b491c4605dc67d`

## Participants

- isolated buyer: `0x67a6F6dD67E7DffEcD760a99b4D5A2fe019EbA4f`
- isolated provider: `0x64f332ba2ED3F7372fF3FE3d777Ad01fbd3195a4`
- registered settlement payout: `0x1f87Ae197af539253978d435aD45cCf28Fb95024`
- principal: `10000000000000000` wei (`0.01 GEN`)

The payout is intentionally separate from the isolated buyer signer.

## Signer bootstrap provenance

- provider funding transaction: `0x14e392a963cb595c46b1cde09b15f64768d9eb92efa5834c4eed4245ac08b8a3`
- isolated buyer funding transaction: `0xf286625e7bb90652d680519b7dcd2bd5786ba70d44702e9daaa6c9cf3cd7d08c`

Those transfers funded the isolated reviewer signers. They are not covenant
settlement transactions.

## Current Core execution

| Action | Transaction | Block | Receipt status |
| --- | --- | ---: | ---: |
| open/fund Covenant 1 | `0x7b45999ab31e82e941d25712be32770c7fd4f3d66b1e3ab938d591c93f5ca9cd` | 22374366 | 1 |
| provider accepts | `0xaa010bd94bdd93ae2c9dc185174aba92a931a3609c1d6ef07bbb6783da8a98f3` | 22374391 | 1 |
| expire non-delivery | `0x1219914b612f60c439953be4818702d7e081167535e0bdc62c0ac86c87de3740` | 22376150 | 1 |
| claim settlement | `0x18197505652f86fc21ad1a926e8e5220a5a518b9673c97468c5fbbd3a151c77b` | 22376179 | 1 |

After provider acceptance:

    state                     SERVICE_ACCEPTED
    totalFunded               10000000000000000
    totalClosedToProvider     0
    totalClosedToBuyer        0
    totalOutstanding          10000000000000000
    Core native balance       10000000000000000

After the delivery deadline passed, `expireNonDelivery(1)` authorized buyer
recovery without moving principal.

The subsequent `claimSettlement(1)` closed Covenant `1` to the buyer.

## Exact native GEN consequence

Registered payout balance immediately before the claim block:

    1708649136406490755 wei

Registered payout balance in the claim block:

    1718649136406490755 wei

Exact balance delta:

    10000000000000000 wei

The delta equals the entire covenant principal.

The claim receipt contained the exact Core `SettlementClaimed` and Vault
`SettlementRouted` events for:

- covenant ID: `1`
- beneficiary: `0x67a6F6dD67E7DffEcD760a99b4D5A2fe019EbA4f`
- recipient: `0x1f87Ae197af539253978d435aD45cCf28Fb95024`
- amount: `10000000000000000` wei
- Vault source: `0xE315df22c15753D07a2FDb72b15B3AeAF4D27E2A`

## Final conservation state

    state                     CLOSED_BUYER
    totalFunded               10000000000000000
    totalClosedToProvider     0
    totalClosedToBuyer        10000000000000000
    totalOutstanding          0
    Core native balance       0
    Vault delivered bit       true

Conservation therefore holds exactly:

    totalFunded
    =
    totalClosedToProvider
    + totalClosedToBuyer
    + totalOutstanding
    =
    10000000000000000

## Duplicate claim resistance

A second `claimSettlement(1)` was issued only as a read-only call.

- duplicate claim rejected: yes
- expected error: `SettlementAlreadyClaimed()`
- expected selector: `0x3eed0c7d`
- selector observed in revert response: yes
- second settlement blockchain write: none

## Scope limitation

This case proves current-R149 non-delivery liveness and buyer recovery. It
does not prove that Covenant `1` traversed provider delivery, challenge,
repair/retry, or semantic adjudication. Those claims require their own bound
evidence.
