# Accord402 R150 Predeployment Freeze

Status: **PREDEPLOYMENT SOURCE FREEZE — NO BRADBURY WRITE**

This record freezes the reviewer-fix source and deployment payload before any
new Bradbury transaction is authorized.

## Baseline

- parent main commit: `3701bdec7a8c41dcfa7eeaa95487e00c0f9e65c6`
- parent tree: `fcf548fd2cf451ddf8e52a46b6f394cb37a600cd`
- Bradbury chain ID: `4221`
- EVM RPC: `https://rpc.testnet-chain.genlayer.com`
- production alias remains: `https://accord402.vercel.app`

## R150 Core candidate

- source SHA-256: `98c6cb19e1783b5f2515d24fe74e7428d01c2cfcc6991acd54c367f3cce06b7d`
- source bytes: `33612`
- creation bytecode bytes: `23921`
- creation bytecode SHA-256: `8a643a0720396965fd41a7c6248e70bba239c11578097f75bf796ef7626353a5`
- creation bytecode keccak: `0xb4a06c2861fd567a49627a45678533ca9236d529b39d6889548eda476f59adb1`
- runtime bytecode bytes: `23571`
- runtime bytecode SHA-256: `8554abb9b3d637e247f67d85e80f710974228dfa3df7d4cfbad4bdabbe62ba50`
- runtime bytecode keccak: `0x02709e4faca0f70ba73303500e43888577d9f6d3e946673e6757b7f04c81bf43`
- EIP-170 runtime-size gate: `PASS`
- deployment init bytes: `24017`
- deployment init keccak: `0x3066c5e92c06f33c467db39ea2d1ed43867532e21760870b278970b0fd8adadf`
- `submitEvidenceRepair(...)` selector: `0xd8c2a186`

The Core normalizes delivery and repair `observedAt` to its execution-time
`block.timestamp` before Registry validation. The ABI selector is unchanged.

## Constructor binding

- Registry: `0x5BD6f9EEBF7BE527321ED46649447c59fAc5315C`
- Adjudicator: `0x9b204786e4641EbFF5D771a08624e2B0849Fcc56`
- SettlementVault: `0xFCc7FbE2243c32ff35cE74055695Bf8C23E17dD5`

Only a new Core deployment is required. Registry, Adjudicator, and
SettlementVault are intentionally reused.

## Reviewer workflow

The application now exposes the challenged-review workflow:

`CHALLENGED -> adjudicate -> canonical finality -> Core refresh ->
EVIDENCE_REPAIR_REQUIRED -> provider submitEvidenceRepair -> canonical finality
-> Core refresh -> CHALLENGED -> adjudicate -> settlement authorization ->
claimSettlement`

The exact GenLayer adjudication transaction ID and Core EVM transaction hashes
flow through the existing canonical observer. Canonical success requires both
`Finalized` and `FINISHED_WITH_RETURN`.

## Verification

- targeted Accord402 Core tests: `12/12 PASS`
- complete Solidity suite: `18/18 PASS`
- R150 reviewer guards: `7/7 PASS`
- non-integration Python regression: `95/95 PASS`
- frontend TypeScript and production Next.js build: `PASS`
- delivery timestamp-mismatch regression: `PASS`
- repair timestamp-mismatch regression: `PASS`

## Deployment safety

- new Core deployment required: `YES`
- new Registry deployment required: `NO`
- new Adjudicator deployment required: `NO`
- new SettlementVault deployment required: `NO`
- frontend Core-address rebind required after deployment: `YES`
- frontend source-fingerprint rebind required after deployment: `YES`
- production URL change required: `NO`
- deployment authorized by this record: `NO`
- blockchain write performed by this record: `NO`

The R149 Core remains the live canonical Core until a separately authorized
R150 Core deployment is submitted, persisted, and verified.
