#!/usr/bin/env bash
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="$REPO/.venv/bin/python"

EXPECTED_SOURCE_SHA="35d8beeb2dedb9b2d6839c3237ad839d85a0a788abb80adbc0557ed15b07a271"
EXPECTED_NETWORK="testnet_bradbury"
EXPECTED_CHAIN_ID="4221"
EXPECTED_CHAIN_ID_HEX="0x107d"
EXPECTED_RPC="https://rpc-bradbury.genlayer.com"
EXPECTED_EVM_RPC="https://rpc.testnet-chain.genlayer.com"
EXPECTED_SENDER="0x1f87Ae197af539253978d435aD45cCf28Fb95024"
EXPECTED_REGISTRY="0x5BD6f9EEBF7BE527321ED46649447c59fAc5315C"
EXPECTED_REGISTRY_RUNTIME_SHA256="25b850052c2d02c202262fcff7216363fcffdf6cb7fc6d533268a1842a008d7c"
EXPECTED_MANIFEST_URL="https://raw.githubusercontent.com/genlayerlabs/genlayer-networks/main/bradbury/testnet_deployments.json"
EXPECTED_MANIFEST_VERSION="v0.5:9c68608"
EXPECTED_CONSENSUS_MAIN="0x0112Bf6e83497965A5fdD6Dad1E447a6E004271D"

fail() {
  echo "STOP: $*" >&2
  exit 1
}

sha256_file() {
  shasum -a 256 "$1" | awk '{print $1}'
}

need_env() {
  local name="$1"
  test -n "${!name:-}" || fail "MISSING REQUIRED ENV: $name"
}

cd "$REPO"

echo "================================================================"
echo "ACCORD402 GUARDED BRADBURY ADJUDICATOR RUNTIME INTEGRATION"
echo "LIVE BLOCKCHAIN WRITE — FRESH EXPLICIT AUTHORIZATION REQUIRED"
echo "================================================================"

test -x "$PY" || fail "PROJECT VENV PYTHON MISSING"
test -z "$(git status --porcelain=v1 --untracked-files=all)" \
  || fail "WORKTREE MUST BE CLEAN AND COMMITTED BEFORE LIVE EXECUTION"

RELEASE_COMMIT="$(git rev-parse HEAD)"
SOURCE_SHA="$(sha256_file contracts/Accord402Adjudicator.py)"

test "$SOURCE_SHA" = "$EXPECTED_SOURCE_SHA" || fail "ADJUDICATOR SOURCE SHA DRIFT"

for f in \
  gltest.config.yaml \
  docs/TOOLCHAIN_RELEASE_RECONCILIATION_V1.md \
  docs/BRADBURY_RUNTIME_INTEGRATION_V1.md \
  tests/integration/test_accord402_adjudicator_bradbury_runtime.py \
  scripts/run_bradbury_runtime_integration.sh \
  .github/workflows/verify.yml
do
  git ls-files --error-unmatch "$f" >/dev/null 2>&1 \
    || fail "REQUIRED RELEASE FILE IS NOT TRACKED: $f"
done

grep -Fq 'version: v1.8.1' .github/workflows/verify.yml \
  || fail "CI FOUNDRY RELEASE PIN IS NOT v1.8.1"

need_env ACCORD402_BRADBURY_WRITE_AUTHORIZED
need_env ACCORD402_AUTHORIZED_RELEASE_COMMIT
need_env ACCORD402_AUTHORIZED_ADJUDICATOR_SHA256
need_env ACCORD402_BRADBURY_WRITE_AUTHORIZATION_ID
need_env ACCORD402_BRADBURY_PRIVATE_KEY
need_env ACCORD402_BRADBURY_EXPECTED_SENDER
need_env ACCORD402_BRADBURY_EXPECTED_START_NONCE
need_env ACCORD402_BRADBURY_REGISTRY_ADDRESS
need_env ACCORD402_BRADBURY_EVIDENCE_DIR

test "$ACCORD402_BRADBURY_WRITE_AUTHORIZED" = "YES" \
  || fail "BRADBURY WRITE AUTHORIZATION FLAG MUST BE EXACTLY YES"
test "$ACCORD402_AUTHORIZED_RELEASE_COMMIT" = "$RELEASE_COMMIT" \
  || fail "AUTHORIZED RELEASE COMMIT DOES NOT MATCH HEAD"
test "$ACCORD402_AUTHORIZED_ADJUDICATOR_SHA256" = "$EXPECTED_SOURCE_SHA" \
  || fail "AUTHORIZED SOURCE SHA DOES NOT MATCH EXACT CANDIDATE"

AUTH_SENDER="$ACCORD402_BRADBURY_EXPECTED_SENDER"
AUTH_START_NONCE="$ACCORD402_BRADBURY_EXPECTED_START_NONCE"

"$PY" - "$AUTH_SENDER" "$EXPECTED_SENDER" "$AUTH_START_NONCE" <<'PY_AUTH'
import re
import sys

sender, expected_sender, nonce = sys.argv[1:]

assert re.fullmatch(r"0x[0-9a-fA-F]{40}", sender), "invalid authorized sender"
assert sender.lower() == expected_sender.lower(), "authorized sender mismatch"
assert nonce.isdigit(), "authorized start nonce must be decimal digits"
assert str(int(nonce)) == nonce, "authorized start nonce must be canonical decimal"
assert int(nonce) >= 0, "authorized start nonce must be nonnegative"
PY_AUTH

test "$(printf '%s' "$ACCORD402_BRADBURY_REGISTRY_ADDRESS" | tr '[:upper:]' '[:lower:]')" = \
     "$(printf '%s' "$EXPECTED_REGISTRY" | tr '[:upper:]' '[:lower:]')" \
  || fail "AUTHORIZED REGISTRY ADDRESS DOES NOT MATCH RELEASE-BOUND REGISTRY"

case "$ACCORD402_BRADBURY_WRITE_AUTHORIZATION_ID" in
  *[!A-Za-z0-9._-]*|"")
    fail "AUTHORIZATION ID MUST USE ONLY A-Z a-z 0-9 . _ -"
    ;;
esac

"$PY" - "$ACCORD402_BRADBURY_REGISTRY_ADDRESS" <<'PY'
import re, sys
value = sys.argv[1]
assert re.fullmatch(r"0x[0-9a-fA-F]{40}", value), "invalid Registry address"
assert int(value, 16) != 0, "Registry address must be nonzero"
PY

EVIDENCE="$ACCORD402_BRADBURY_EVIDENCE_DIR"
case "$EVIDENCE" in
  /*) ;;
  *) fail "EVIDENCE DIRECTORY MUST BE AN ABSOLUTE PATH" ;;
esac

case "$EVIDENCE/" in
  "$REPO/"*) fail "EVIDENCE DIRECTORY MUST BE OUTSIDE THE REPOSITORY" ;;
esac

test ! -e "$EVIDENCE" || fail "EVIDENCE DIRECTORY ALREADY EXISTS"
mkdir -m 700 "$EVIDENCE"

# All following checks are read-only and occur before authorization
# consumption. Any drift stops before signing or broadcast.
GEN_CHAIN_RESPONSE="$(
  curl --fail --silent --show-error \
    -H 'content-type: application/json' \
    --data '{"jsonrpc":"2.0","id":1,"method":"eth_chainId","params":[]}' \
    "$EXPECTED_RPC"
)"
printf '%s' "$GEN_CHAIN_RESPONSE" > "$EVIDENCE/genlayer-eth_chainId.raw.json"

EVM_CHAIN_RESPONSE="$(
  curl --fail --silent --show-error \
    -H 'content-type: application/json' \
    --data '{"jsonrpc":"2.0","id":2,"method":"eth_chainId","params":[]}' \
    "$EXPECTED_EVM_RPC"
)"
printf '%s' "$EVM_CHAIN_RESPONSE" > "$EVIDENCE/evm-eth_chainId.raw.json"

GEN_CHAIN_HEX="$(
  printf '%s' "$GEN_CHAIN_RESPONSE" |
  "$PY" -c 'import json,sys; o=json.load(sys.stdin); assert o.get("error") is None,o; print(o["result"])'
)"

EVM_CHAIN_HEX="$(
  printf '%s' "$EVM_CHAIN_RESPONSE" |
  "$PY" -c 'import json,sys; o=json.load(sys.stdin); assert o.get("error") is None,o; print(o["result"])'
)"

echo "LIVE_GENLAYER_CHAIN_ID_HEX=$GEN_CHAIN_HEX"
echo "LIVE_EVM_CHAIN_ID_HEX=$EVM_CHAIN_HEX"

test "$(printf '%s' "$GEN_CHAIN_HEX" | tr '[:upper:]' '[:lower:]')" = "$EXPECTED_CHAIN_ID_HEX" \
  || fail "LIVE GENLAYER RPC CHAIN ID MISMATCH"

test "$(printf '%s' "$EVM_CHAIN_HEX" | tr '[:upper:]' '[:lower:]')" = "$EXPECTED_CHAIN_ID_HEX" \
  || fail "LIVE EVM RPC CHAIN ID MISMATCH"

SYNC_RESPONSE="$(
  curl --fail --silent --show-error \
    -H 'content-type: application/json' \
    --data '{"jsonrpc":"2.0","id":3,"method":"gen_syncing","params":[]}' \
    "$EXPECTED_RPC"
)"
printf '%s' "$SYNC_RESPONSE" > "$EVIDENCE/gen_syncing.raw.json"

BLOCKS_BEHIND="$(
  printf '%s' "$SYNC_RESPONSE" |
  "$PY" -c 'import json,sys; o=json.load(sys.stdin); assert o.get("error") is None,o; print(o["result"]["blocksBehind"])'
)"

echo "LIVE_BRADBURY_BLOCKS_BEHIND=$BLOCKS_BEHIND"
test "$BLOCKS_BEHIND" = "0" || fail "BRADBURY RPC IS NOT SYNCED"

MANIFEST_RESPONSE="$(
  curl --fail --silent --show-error "$EXPECTED_MANIFEST_URL"
)"
printf '%s' "$MANIFEST_RESPONSE" > "$EVIDENCE/bradbury-deployment-manifest.raw.json"

MANIFEST_VERSION="$(
  printf '%s' "$MANIFEST_RESPONSE" |
  "$PY" -c 'import json,sys; d=json.load(sys.stdin)["genlayerTestnet"]["deployment_bradbury"]; print(d["Version"])'
)"

MANIFEST_CONSENSUS_MAIN="$(
  printf '%s' "$MANIFEST_RESPONSE" |
  "$PY" -c 'import json,sys; d=json.load(sys.stdin)["genlayerTestnet"]["deployment_bradbury"]; print(d["ConsensusMain"])'
)"

echo "LIVE_BRADBURY_MANIFEST_VERSION=$MANIFEST_VERSION"
echo "LIVE_BRADBURY_CONSENSUS_MAIN=$MANIFEST_CONSENSUS_MAIN"

test "$MANIFEST_VERSION" = "$EXPECTED_MANIFEST_VERSION" \
  || fail "BRADBURY DEPLOYMENT MANIFEST VERSION DRIFT"

test "$(printf '%s' "$MANIFEST_CONSENSUS_MAIN" | tr '[:upper:]' '[:lower:]')" = \
     "$(printf '%s' "$EXPECTED_CONSENSUS_MAIN" | tr '[:upper:]' '[:lower:]')" \
  || fail "BRADBURY CONSENSUS MAIN ADDRESS DRIFT"

REGISTRY_CODE_RESPONSE="$(
  curl --fail --silent --show-error \
    -H 'content-type: application/json' \
    --data "{\"jsonrpc\":\"2.0\",\"id\":4,\"method\":\"eth_getCode\",\"params\":[\"$EXPECTED_REGISTRY\",\"latest\"]}" \
    "$EXPECTED_EVM_RPC"
)"
printf '%s' "$REGISTRY_CODE_RESPONSE" > "$EVIDENCE/registry-code.raw.json"

REGISTRY_RUNTIME_SHA="$(
  printf '%s' "$REGISTRY_CODE_RESPONSE" |
  "$PY" -c '
import hashlib,json,sys
o=json.load(sys.stdin)
assert o.get("error") is None,o
v=o["result"]
assert isinstance(v,str) and v.startswith("0x") and len(v)>2
print(hashlib.sha256(bytes.fromhex(v[2:])).hexdigest())
'
)"

echo "LIVE_REGISTRY_RUNTIME_SHA256=$REGISTRY_RUNTIME_SHA"

test "$REGISTRY_RUNTIME_SHA" = "$EXPECTED_REGISTRY_RUNTIME_SHA256" \
  || fail "LIVE REGISTRY RUNTIME DOES NOT MATCH RELEASE-BOUND REGISTRY"

DERIVED_SENDER="$(
  "$PY" - <<'PY_SENDER'
import os
from eth_account import Account

private_key = os.environ["ACCORD402_BRADBURY_PRIVATE_KEY"]
print(Account.from_key(private_key).address)
PY_SENDER
)"

echo "PRIVATE_KEY_DERIVED_SENDER=$DERIVED_SENDER"

test "$(printf '%s' "$DERIVED_SENDER" | tr '[:upper:]' '[:lower:]')" = \
     "$(printf '%s' "$AUTH_SENDER" | tr '[:upper:]' '[:lower:]')" \
  || fail "PRIVATE KEY DOES NOT RESOLVE TO AUTHORIZED SENDER"

LATEST_NONCE_RESPONSE="$(
  curl --fail --silent --show-error \
    -H 'content-type: application/json' \
    --data "{\"jsonrpc\":\"2.0\",\"id\":5,\"method\":\"eth_getTransactionCount\",\"params\":[\"$AUTH_SENDER\",\"latest\"]}" \
    "$EXPECTED_EVM_RPC"
)"
printf '%s' "$LATEST_NONCE_RESPONSE" > "$EVIDENCE/sender-latest-nonce.raw.json"

PENDING_NONCE_RESPONSE="$(
  curl --fail --silent --show-error \
    -H 'content-type: application/json' \
    --data "{\"jsonrpc\":\"2.0\",\"id\":6,\"method\":\"eth_getTransactionCount\",\"params\":[\"$AUTH_SENDER\",\"pending\"]}" \
    "$EXPECTED_EVM_RPC"
)"
printf '%s' "$PENDING_NONCE_RESPONSE" > "$EVIDENCE/sender-pending-nonce.raw.json"

BALANCE_RESPONSE="$(
  curl --fail --silent --show-error \
    -H 'content-type: application/json' \
    --data "{\"jsonrpc\":\"2.0\",\"id\":7,\"method\":\"eth_getBalance\",\"params\":[\"$AUTH_SENDER\",\"latest\"]}" \
    "$EXPECTED_EVM_RPC"
)"
printf '%s' "$BALANCE_RESPONSE" > "$EVIDENCE/sender-balance.raw.json"

LATEST_NONCE="$(
  printf '%s' "$LATEST_NONCE_RESPONSE" |
  "$PY" -c 'import json,sys; o=json.load(sys.stdin); assert o.get("error") is None,o; print(int(o["result"],16))'
)"

PENDING_NONCE="$(
  printf '%s' "$PENDING_NONCE_RESPONSE" |
  "$PY" -c 'import json,sys; o=json.load(sys.stdin); assert o.get("error") is None,o; print(int(o["result"],16))'
)"

BALANCE_WEI="$(
  printf '%s' "$BALANCE_RESPONSE" |
  "$PY" -c 'import json,sys; o=json.load(sys.stdin); assert o.get("error") is None,o; print(int(o["result"],16))'
)"

echo "AUTHORIZED_SENDER=$AUTH_SENDER"
echo "AUTHORIZED_START_NONCE=$AUTH_START_NONCE"
echo "LIVE_SENDER_LATEST_NONCE=$LATEST_NONCE"
echo "LIVE_SENDER_PENDING_NONCE=$PENDING_NONCE"
echo "LIVE_SENDER_BALANCE_WEI=$BALANCE_WEI"

test "$LATEST_NONCE" = "$AUTH_START_NONCE" \
  || fail "LIVE LATEST NONCE DOES NOT MATCH AUTHORIZED START NONCE"

test "$PENDING_NONCE" = "$AUTH_START_NONCE" \
  || fail "LIVE PENDING NONCE DOES NOT MATCH AUTHORIZED START NONCE"

test "$BALANCE_WEI" -gt 0 \
  || fail "AUTHORIZED SENDER HAS ZERO BALANCE"

AUTH_DIR="$HOME/.accord402-write-authorizations"
mkdir -m 700 -p "$AUTH_DIR"
AUTH_SENTINEL="$AUTH_DIR/${ACCORD402_BRADBURY_WRITE_AUTHORIZATION_ID}.consumed"

test ! -e "$AUTH_SENTINEL" \
  || fail "THIS WRITE AUTHORIZATION ID HAS ALREADY BEEN CONSUMED"

RUNTIME_DIR="$EVIDENCE/runtime"
mkdir -m 700 "$RUNTIME_DIR"

cat > "$RUNTIME_DIR/gltest.config.yaml" <<EOF_CONFIG
networks:
  default: testnet_bradbury
  testnet_bradbury:
    id: 4221
    url: $EXPECTED_RPC
    accounts:
      - "\${ACCORD402_BRADBURY_PRIVATE_KEY}"
    chain_type: testnet_bradbury
    default_wait_interval: 3000
    default_wait_retries: 240

paths:
  contracts: $REPO/contracts
  artifacts: $EVIDENCE/gltest-artifacts
EOF_CONFIG

cat > "$EVIDENCE/release-binding.json" <<EOF_BINDING
{
  "schema": "accord402-bradbury-runtime-release-binding-v2",
  "network": "$EXPECTED_NETWORK",
  "chain_id": $EXPECTED_CHAIN_ID,
  "genlayer_rpc": "$EXPECTED_RPC",
  "evm_rpc": "$EXPECTED_EVM_RPC",
  "bradbury_manifest_version": "$MANIFEST_VERSION",
  "consensus_main": "$MANIFEST_CONSENSUS_MAIN",
  "release_commit": "$RELEASE_COMMIT",
  "source_path": "contracts/Accord402Adjudicator.py",
  "source_sha256": "$SOURCE_SHA",
  "registry_address": "$ACCORD402_BRADBURY_REGISTRY_ADDRESS",
  "registry_runtime_sha256": "$REGISTRY_RUNTIME_SHA",
  "authorized_sender": "$AUTH_SENDER",
  "authorized_start_nonce": $AUTH_START_NONCE,
  "authorization_id": "$ACCORD402_BRADBURY_WRITE_AUTHORIZATION_ID"
}
EOF_BINDING

# Consume the one-shot authorization immediately before pytest can enter the
# transaction submission path. noclobber makes the claim atomic.
(
  set -o noclobber
  umask 077
  printf '%s\n' \
    "release_commit=$RELEASE_COMMIT" \
    "source_sha256=$SOURCE_SHA" \
    "network=$EXPECTED_NETWORK" \
    "manifest_version=$MANIFEST_VERSION" \
    "consensus_main=$MANIFEST_CONSENSUS_MAIN" \
    "registry_address=$ACCORD402_BRADBURY_REGISTRY_ADDRESS" \
    "registry_runtime_sha256=$REGISTRY_RUNTIME_SHA" \
    "sender_address=$AUTH_SENDER" \
    "start_nonce=$AUTH_START_NONCE" \
    "authorization_id=$ACCORD402_BRADBURY_WRITE_AUTHORIZATION_ID" \
    > "$AUTH_SENTINEL"
) || fail "COULD NOT ATOMICALLY CONSUME AUTHORIZATION ID"

echo "BRADBURY_WRITE_AUTHORIZATION_CONSUMED=YES"
echo "RETRY_OR_REBROADCAST_AUTHORIZED=NO"

export ACCORD402_BRADBURY_NETWORK="$EXPECTED_NETWORK"
export ACCORD402_BRADBURY_CHAIN_ID="$EXPECTED_CHAIN_ID"
export ACCORD402_BRADBURY_RPC="$EXPECTED_RPC"
export ACCORD402_BRADBURY_EVM_RPC="$EXPECTED_EVM_RPC"
export ACCORD402_BRADBURY_EXPECTED_SENDER="$AUTH_SENDER"
export ACCORD402_BRADBURY_EXPECTED_START_NONCE="$AUTH_START_NONCE"
export ACCORD402_BRADBURY_MANIFEST_VERSION="$MANIFEST_VERSION"

cd "$RUNTIME_DIR"

"$PY" -m pytest \
  -q \
  "$REPO/tests/integration/test_accord402_adjudicator_bradbury_runtime.py"

echo
echo "================================================================"
echo "ACCORD402_BRADBURY_ADJUDICATOR_RUNTIME_INTEGRATION=PASS"
echo "RELEASE_COMMIT=$RELEASE_COMMIT"
echo "ADJUDICATOR_SHA256=$SOURCE_SHA"
echo "EVIDENCE_DIR=$EVIDENCE"
echo "AUTHORIZATION_ID=$ACCORD402_BRADBURY_WRITE_AUTHORIZATION_ID"
echo "AUTHORIZED_SENDER=$AUTH_SENDER"
echo "AUTHORIZED_START_NONCE=$AUTH_START_NONCE"
echo "BRADBURY_MANIFEST_VERSION=$MANIFEST_VERSION"
echo "BRADBURY_WRITE_AUTHORIZATION_CONSUMED=YES"
echo "RETRY_OR_REBROADCAST_AUTHORIZED=NO"
echo "================================================================"
