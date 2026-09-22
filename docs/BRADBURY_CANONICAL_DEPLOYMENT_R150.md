# Accord402 Canonical Bradbury Deployment — R150

Status: **CURRENT CANONICAL R150 REVIEWER RELEASE**

R150 reuses the verified Registry, Adjudicator, and SettlementVault and replaces only the Core. The stable production URL is unchanged.

## Release binding

- R150 implementation commit: `7dde8f45ae88db996895c02883c951d6350cf48c`
- R150 implementation tree: `aa7f6129ce74e75c7e0405d482278568c127f100`
- Bradbury chain ID: `4221`
- EVM RPC: `https://rpc.testnet-chain.genlayer.com`
- production URL: `https://accord402.vercel.app`

## Canonical graph

| Component | Address | Provenance |
| --- | --- | --- |
| SettlementVault | `0xFCc7FbE2243c32ff35cE74055695Bf8C23E17dD5` | reused verified deployment |
| Registry | `0x5BD6f9EEBF7BE527321ED46649447c59fAc5315C` | reused verified deployment |
| Adjudicator | `0x9b204786e4641EbFF5D771a08624e2B0849Fcc56` | reused finalized GenLayer deployment |
| Core | `0x142b20B20a24F659e1053A504c23fF48832c090f` | R150 EVM deployment |

R150 Core deployment transaction:

`0x750577a17692ba91471d9821befd2c858ac06eaf7a94a80a71e866bd59757bf6`

## Exact source and bytecode binding

Source SHA-256:

- SettlementVault: `e966518dac38ba95df3ff06f7a319bcd97b823a3e36d019003b45ee4a4fe6cd6`
- Registry: `bac515e32c8e4a56073b412079995c8bf64ace94274314a491b2dbe411ea35ae`
- Adjudicator: `575e063661cc12a5de18dfa67ab3fbeb38bee1028694a08021efbc300115c198`
- R150 Core: `98c6cb19e1783b5f2515d24fe74e7428d01c2cfcc6991acd54c367f3cce06b7d`

R150 Core bytecode freeze:

- creation bytes: `23921`
- creation SHA-256: `8a643a0720396965fd41a7c6248e70bba239c11578097f75bf796ef7626353a5`
- runtime bytes: `23571`
- runtime SHA-256: `8554abb9b3d637e247f67d85e80f710974228dfa3df7d4cfbad4bdabbe62ba50`
- EIP-170 runtime-size gate: `PASS`

See `R150_PREDEPLOYMENT_FREEZE.md` for the pre-write freeze.

## Live immutable wiring

Post-deployment reads resolved:

- `registry()` → `0x5BD6f9EEBF7BE527321ED46649447c59fAc5315C`
- `adjudicator()` → `0x9b204786e4641EbFF5D771a08624e2B0849Fcc56`
- `settlementVault()` → `0xFCc7FbE2243c32ff35cE74055695Bf8C23E17dD5`

The live R150 Core runtime length is `23571` bytes.

## Production binding

Production remains:

`https://accord402.vercel.app`

The certified R150 production public configuration SHA-256 is:

`e52e39cfb594a588258952f8fbf78468af7a87ef81fd9f916ff00e2f789b3d23`

Post-cutover verification confirmed HTTP 200, R150 Core/fingerprint binding, absence of R149 references on the production surface, 12/12 discovered Next.js assets, and 9/9 zero-argument Core view calls.

## Reviewer workflow

```text
CHALLENGED
→ adjudicate
→ canonical finality
→ Core refresh
→ EVIDENCE_REPAIR_REQUIRED
→ authorized provider repair
→ canonical finality
→ Core refresh
→ CHALLENGED
→ adjudicate
→ settlement authorization
→ claimSettlement
```

Canonical GenLayer success requires `Finalized` and `FINISHED_WITH_RETURN`.

## Verification

GitHub Actions run `35683293916` succeeded for the R150 implementation commit. That run passed 18 Solidity tests, 102 Python tests with 1 skip, Python compile, GenVM lint/schema validation, runtime-size hard gates, and frontend typecheck/build.

## Fresh-Core note

The R150 Core is a new deployment. Historical R149 Covenant 1 does not exist on this Core and is not presented as an R150 execution. The reviewer-closeout frontend therefore starts without auto-loading a seeded covenant.

R149 deployment and economic proof documents remain historical evidence only.
