# Accord402 V2 implementation status

**Status: R150 IS THE CURRENT REVIEWER RELEASE. Deployment, production rebinding, publication, CI, and post-publication verification are complete for the R150 implementation release. R149 remains historical evidence only.**

## Canonical R150 release

- implementation commit: `7dde8f45ae88db996895c02883c951d6350cf48c`
- implementation tree: `aa7f6129ce74e75c7e0405d482278568c127f100`
- Bradbury chain ID: `4221`
- production URL: `https://accord402.vercel.app`
- GitHub Actions verify run: `35683293916` — `success`

Canonical graph:

- SettlementVault: `0xFCc7FbE2243c32ff35cE74055695Bf8C23E17dD5`
- Registry: `0x5BD6f9EEBF7BE527321ED46649447c59fAc5315C`
- Adjudicator: `0x9b204786e4641EbFF5D771a08624e2B0849Fcc56`
- R150 Core: `0x142b20B20a24F659e1053A504c23fF48832c090f`
- R150 Core deployment tx: `0x750577a17692ba91471d9821befd2c858ac06eaf7a94a80a71e866bd59757bf6`

Exact current source SHA-256 values:

- SettlementVault: `e966518dac38ba95df3ff06f7a319bcd97b823a3e36d019003b45ee4a4fe6cd6`
- Registry: `bac515e32c8e4a56073b412079995c8bf64ace94274314a491b2dbe411ea35ae`
- Adjudicator: `575e063661cc12a5de18dfa67ab3fbeb38bee1028694a08021efbc300115c198`
- Core: `98c6cb19e1783b5f2515d24fe74e7428d01c2cfcc6991acd54c367f3cce06b7d`

## R150 reviewer change

R150 closes the challenged-review/evidence-repair workflow and removes caller control over consequential observation time.

- Core normalizes delivery `observedAt` to execution-time `block.timestamp`.
- Core normalizes replacement evidence `observedAt` the same way.
- Registry validation receives the normalized timestamp.
- The frontend exposes adjudication from `CHALLENGED`.
- The frontend exposes authorized provider repair from `EVIDENCE_REPAIR_REQUIRED`.
- Canonical transaction success requires `Finalized` and `FINISHED_WITH_RETURN`.
- After canonical success, the UI re-reads the covenant from Core.
- Repair remains provider-bound, generation-bound, field-mask-bound, freshness-bound, and provenance-bound.

## Verification completed

The exact R150 implementation commit passed:

- complete Solidity suite: **18 passed**;
- Python regression suite: **102 passed, 1 skipped**;
- R150 reviewer workflow guards: **7 passed**;
- Python compile check: **passed**;
- GenVM lint/schema validation: **passed**;
- Registry runtime size: **23,429 bytes**;
- R150 Core runtime size: **23,571 bytes**;
- frontend typecheck + production Next.js build: **passed**;
- GitHub Actions `verify`: **success**.

Post-publication verification confirmed the stable production URL, R150 production binding, deployment receipt, live immutable wiring, static assets, and zero-argument Core reads.

## Frontend release state

The R150 frontend is state-aware and finality-aware. The reviewer-closeout UI starts without assuming that a fresh Core already contains Covenant 1. Reviewers explicitly open a new covenant or load an existing covenant number.

The transaction observer treats `Accepted` as provisional. Canonical success is reported only after `Finalized` and `FINISHED_WITH_RETURN`, then the covenant is re-read from Core.

A complete signed browser lifecycle on R150 is a separate live-write exercise. This document does not claim a wallet-signed R150 covenant lifecycle that has not been executed.

## Historical R149 evidence

R149 is retained only as historical release evidence. Its Covenant 1 economic proof remains useful for the older R149 Core but is not presented as an R150 covenant execution.

For the current reviewer reference, use `SUBMISSION_HANDOFF_R150.md`.
