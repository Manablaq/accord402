# Accord402

**The warranty layer for agent-to-agent commerce.**

Accord402 is a GenLayer-native service warranty protocol for autonomous agents.
The current implementation separates deterministic escrow, policy, evidence
provenance, and settlement from the one operation that requires GenLayer
consensus: semantic adjudication of disputed service delivery.

## Current architecture

- `contracts/Accord402SettlementVault.sol` — existing finality-bound GEN router.
- `contracts/Accord402Registry.sol` — policy, authority, evidence history, replay, freshness, and source-origin enforcement.
- `contracts/Accord402Core.sol` — escrow, lifecycle, accounting, repair/retry, and finality-gated settlement.
- `contracts/Accord402Adjudicator.py` — narrow GenLayer Intelligent Contract that reads a frozen snapshot, independently fetches approved evidence, and sends one finalized callback.

The historical `contracts/accord402.py` is preserved for reference/differential
work and is not the V2 deployment artifact. The `frontend/` directory is the
read-only Bradbury console for the deployed V2 graph; it does not replace
contract authority.

## Local verification

From the repository root:

```text
forge build --root .
forge test --root .
python -m py_compile contracts/Accord402Adjudicator.py
genvm-lint check contracts/Accord402Adjudicator.py --json
```

The Solidity profile is pinned in `foundry.toml` with optimizer runs `1` and
via-IR enabled because Bradbury/EVM deployment size is a hard gate. Current
local tests cover funding, acceptance and delivery, challenge binding,
provider/buyer settlement, expiry, retry, repair, replay isolation, and source
origin binding.

## Deployment status

The fresh SettlementVault is deployed on Bradbury at
`0xeECBE158401B932fec22e61dd0A336638D7A574a`.

The current bundle graph is:

- Registry: `0x5A622C41BAe12c4BFB1B6465af5ac1a3087497D7`
- Adjudicator: `0xEa6BB1a8Ed637cDF319455A718A18a449ACbe8c4`
- Core: `0xA1a2125B3C7D03b868628B4C79832B33B7af4923`

The updated Core and Registry expose compact, deterministic review bundles for
Bradbury’s deployed legacy runner. The Adjudicator has each validator fetch and
reproduce those bundles through the public chain RPC before it emits the
finalized callback. The corrected graph has passed local Solidity tests and a
live Bradbury open/accept/deliver/challenge run. The adjudication transaction
reached `AGREE / FINISHED_WITH_RETURN`; Bradbury finalization and callback
processing remain pending.

## Frontend

From `frontend/`, copy `.env.example` to `.env.local` when environment
overrides are needed, then run `npm run dev`. The Accord402 landing console
uses the hiking-template direction as an original contour-map visual system,
supports light/dark mode and scroll reveals, and continuously observes the
exact transaction ID entered by the user. It reports canonical success only
when Bradbury returns finalized status plus execution result
`FINISHED_WITH_RETURN`.
The console also reads live covenant records from the deployed Core, including
state, escrow, deadlines, participants, review round, and the latest decision.
