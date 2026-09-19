# Accord402 Security Hardening V6

Status: **MANDATORY REVIEW-SNAPSHOT BINDING AMENDMENT**

This amendment closes the V2 hybrid architecture RPC snapshot trust boundary.

The GenLayer Adjudicator may use ordinary EVM `eth_call` reads inside leader and
validator nondeterministic execution, but raw RPC content is never sufficient
authority for an economic consequence.

For every adjudication:

1. the Adjudicator hashes the exact length-prefixed Core review snapshot bytes
   returned by the RPC;
2. it separately hashes the exact length-prefixed Registry review snapshot
   bytes returned by the RPC;
3. those two hashes are included in the exact validator-agreed result;
4. the finality-only EVM callback carries those hashes to Core;
5. Core recomputes the Core snapshot hash from canonical Core storage and the
   Registry snapshot hash from canonical Registry storage;
6. any mismatch reverts as a stale or tampered adjudication result.

The Core snapshot binds state, committed policy/evidence hashes, review
generation, provider delivery payload, buyer challenge claim, dispute deadline,
and exact challenged-criterion ordering.

The Registry snapshot binds service specification, evidence-policy parameters,
criteria, authority bindings, complete evidence history, and the active
evidence-ID set.

The callback ABI type sequence is unchanged. The first two existing `string`
slots now carry `coreSnapshotHash` and `registrySnapshotHash`. Solidity
parameter names do not affect the function selector.

A single RPC response therefore cannot redefine semantic material reviewed by
validators and still authorize settlement. Canonical on-chain state must
reproduce the exact snapshots at final callback processing.

This amendment does not authorize deployment. Any source change supersedes the
previous Bradbury graph until the new source passes all local and CI gates,
code-size gates, Bradbury deployment/finality checks, and live settlement
certification.
