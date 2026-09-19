# Accord402 Canonical Bradbury Deployment V2

Status: **DEPLOYED AND INDEPENDENTLY AUDITED**

This document binds the hardened Accord402 V2 release to the canonical live
Bradbury deployment. It records deployment identity and source parity only; it
does not mark the later settlement-consequence or reviewer-certification gates
complete.

## Release binding

- release commit: `2c025294c66ade0c54b6d494bd5136490b9d1b3c`;
- release tree: `5de6c7a50c3ec7568cf4b6bce54383b51fd7b5df`;
- Bradbury chain ID: `4221`;
- GenLayer RPC: `https://rpc-bradbury.genlayer.com`;
- EVM chain RPC: `https://rpc.testnet-chain.genlayer.com`;
- explorer: `https://explorer-bradbury.genlayer.com`.

## Canonical component graph

| Component | Address | Deployment transaction |
| --- | --- | --- |
| SettlementVault | `0xFCc7FbE2243c32ff35cE74055695Bf8C23E17dD5` | `0xa478daf9a3a280214eb70592ffcd98cb7c4590fc044236fbaf4bf9df5537ffb7` |
| Registry | `0x5BD6f9EEBF7BE527321ED46649447c59fAc5315C` | `0xe8ebf7abdf511e2aaebfda13cb0fab9a6d2e881e785eeb969e0a30ec63007608` |
| Adjudicator | `0x5c958e498C3109922AFAc661EB466628Fe521CB6` | GenLayer `0x202b98d47307c95098e00f410f351db86f904358651de03ba8b7d55b8d620f38` |
| Core | `0x3eA9E19531a59BA31C2E4f396Ab2b0256304e835` | `0x86d5c73db9388b0df8de4753cf5c06751c3f6ec3b7fdfcdd60c1f4cb225e116e` |

Adjudicator outer EVM submission: `0x6ceef29669a2d888c22455555735352315bcdcf0274164f9b2307378e7421a50`.

The Core dependency getters independently resolve to:

- `registry()` → `0x5BD6f9EEBF7BE527321ED46649447c59fAc5315C`;
- `adjudicator()` → `0x5c958e498C3109922AFAc661EB466628Fe521CB6`;
- `settlementVault()` → `0xFCc7FbE2243c32ff35cE74055695Bf8C23E17dD5`.

## Source binding

```text
SettlementVault  e966518dac38ba95df3ff06f7a319bcd97b823a3e36d019003b45ee4a4fe6cd6
Registry         bac515e32c8e4a56073b412079995c8bf64ace94274314a491b2dbe411ea35ae
Adjudicator      9237e89878c74cb3ab3d71986d16aaf4c2f0cda3104b17a81ce79088d8f195a3
Core             ee8d58f6693c16c22eb610140570e0c92a0c923482f154e886f9ae25a7d3c289
```

The canonical deployment uses the repaired Adjudicator runtime-compatible
source, not the earlier Studio-dev profiling source.

## Independent deployment audit

The post-deployment read-only audit passed all deployment-identity gates:

- SettlementVault receipt and runtime parity: pass;
- Registry receipt and runtime parity: pass;
- Core receipt status: pass;
- Core creation input equals the frozen init artifact plus the exact
  Registry/Adjudicator/SettlementVault constructor encoding: pass;
- Core predicted-address match: pass;
- Core runtime code present: pass;
- Core dependency getters: pass;
- Adjudicator outer EVM receipt: pass;
- Adjudicator status: `FINALIZED`;
- Adjudicator consensus result: `AGREE`;
- Adjudicator execution result: `FINISHED_WITH_RETURN`;
- deployment evidence manifest integrity: pass;
- reuse of failed partial-deployment addresses: none.

Machine-readable evidence is committed at
[`../artifacts/ACCORD402_BRADBURY_CANONICAL_DEPLOYMENT_V2.json`](../artifacts/ACCORD402_BRADBURY_CANONICAL_DEPLOYMENT_V2.json).

## Authorization and write discipline

The final Core deployment used exactly one authorized EVM contract-creation
write at worker nonce `1236`. Its one-shot authorization was consumed before
the send. No finalize, retry, replacement, rebroadcast, post-deployment wiring,
or other blockchain write was performed by that Core-only authorization.

An earlier nonce-`1230` Core-only authorization stopped at pre-arm nonce drift,
remained unconsumed, and was superseded. Nonces `1230` through `1235` were
subsequently attributed read-only to successful non-Core `ConsensusMain`
`addTransaction` calls before the nonce-`1236` authorization was created.

## What remains

This deployment closes the canonical graph deployment/finality gate. It does
not close the remaining release gates:

1. execute the tracked supported-runtime Bradbury reproducibility harness for
   the current hardened release;
2. certify finalized live settlement consequence, including recipient balance
   and protocol accounting deltas;
3. prove duplicate-claim resistance;
4. exercise required recovery/expiry paths with finalized balance outcomes;
5. complete frontend E2E and public reviewer-surface verification;
6. run final regression and reviewer-readiness audit.

No later-stage result should be inferred from this deployment artifact alone.
