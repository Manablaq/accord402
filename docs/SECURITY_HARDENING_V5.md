# Accord402 Security Hardening V5

Status: **MANDATORY V2 ARCHITECTURE AMENDMENT**

V5 supersedes the earlier description of Accord402 as one canonical deployable
Intelligent Contract. The economic semantics remain V1; the deployment
architecture is now hybrid because the monolithic Intelligent Contract failed
the observed Bradbury deployment-size gate.

## Trust boundaries

- Registry validates and stores deterministic facts. It never selects a payout
  side or recipient.
- Core owns all escrow, lifecycle transitions, accounting, and settlement
  authorization.
- Adjudicator produces only the exact reviewed result for a frozen snapshot.
- SettlementVault routes only the amount and registered recipient supplied by
  Core and rejects duplicate delivery identities.

## Finality rule

Adjudicator output is provisional until the GenLayer transaction is finalized
with a successful execution result. Only a finalized callback authenticated by
Core may change challenged economic state. `Accepted` alone is never payment,
finality, or successful execution.

## Stop rule

No deployment or reviewer submission may proceed with missing tests, missing
source parity, an unverified constructor binding, an ambiguous transaction, a
failed accounting invariant, or an unproven finality callback. A historical
PASS label, README statement, or estimated result is not a substitute for
reproducible evidence.
