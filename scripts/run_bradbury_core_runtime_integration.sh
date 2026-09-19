#!/usr/bin/env bash
set -euo pipefail

REPO="$(
  cd "$(dirname "${BASH_SOURCE[0]}")/.."
  pwd
)"

PY="$REPO/.venv/bin/python"

EXPECTED_SOURCE_SHA="60ac857d566e49ae912a384c7ce0a11da3bc3201d7349de3fe24bee0cd095692"
EXPECTED_NETWORK="testnet_bradbury"
EXPECTED_CHAIN_ID="4221"
EXPECTED_CHAIN_ID_HEX="0x107d"
EXPECTED_RPC="https://rpc-bradbury.genlayer.com"

fail() {
  echo "STOP: $*" >&2
  exit 1
}

sha256_file() {
  shasum -a 256 "$1" |
    awk '{print $1}'
}

need_env() {
  local name="$1"

  test -n "${!name:-}" ||
    fail "MISSING REQUIRED ENV: $name"
}

cd "$REPO"

echo "================================================================"
echo "ACCORD402 GUARDED BRADBURY CORE RUNTIME INTEGRATION"
echo "LIVE BLOCKCHAIN WRITE — FRESH EXPLICIT CORE AUTHORIZATION REQUIRED"
echo "================================================================"

test -x "$PY" ||
  fail "PROJECT VENV PYTHON MISSING"

test -z "$(
  git status --porcelain=v1 --untracked-files=all
)" ||
  fail "WORKTREE MUST BE CLEAN AND COMMITTED BEFORE LIVE EXECUTION"

RELEASE_COMMIT="$(
  git rev-parse HEAD
)"

SOURCE_SHA="$(
  sha256_file contracts/accord402.py
)"

test "$SOURCE_SHA" = "$EXPECTED_SOURCE_SHA" ||
  fail "CORE SOURCE SHA DRIFT"

for f in \
  gltest.config.yaml \
  contracts/accord402.py \
  tests/integration/test_accord402_core_bradbury_runtime.py \
  scripts/run_bradbury_core_runtime_integration.sh \
  .github/workflows/verify.yml
do
  git ls-files --error-unmatch "$f" \
    >/dev/null 2>&1 ||
    fail "REQUIRED RELEASE FILE IS NOT TRACKED: $f"
done

need_env ACCORD402_BRADBURY_CORE_WRITE_AUTHORIZED
need_env ACCORD402_AUTHORIZED_RELEASE_COMMIT
need_env ACCORD402_AUTHORIZED_CORE_SHA256
need_env ACCORD402_BRADBURY_CORE_WRITE_AUTHORIZATION_ID
need_env ACCORD402_BRADBURY_PRIVATE_KEY
need_env ACCORD402_BRADBURY_SETTLEMENT_VAULT_ADDRESS
need_env ACCORD402_BRADBURY_CORE_EVIDENCE_DIR

test "$ACCORD402_BRADBURY_CORE_WRITE_AUTHORIZED" = "YES" ||
  fail "CORE WRITE AUTHORIZATION FLAG MUST BE EXACTLY YES"

test "$ACCORD402_AUTHORIZED_RELEASE_COMMIT" = "$RELEASE_COMMIT" ||
  fail "AUTHORIZED RELEASE COMMIT DOES NOT MATCH HEAD"

test "$ACCORD402_AUTHORIZED_CORE_SHA256" = "$EXPECTED_SOURCE_SHA" ||
  fail "AUTHORIZED CORE SHA DOES NOT MATCH EXACT CANDIDATE"

case "$ACCORD402_BRADBURY_CORE_WRITE_AUTHORIZATION_ID" in
  *[!A-Za-z0-9._-]*|"")
    fail "AUTHORIZATION ID MUST USE ONLY A-Z a-z 0-9 . _ -"
    ;;
esac

"$PY" - "$ACCORD402_BRADBURY_SETTLEMENT_VAULT_ADDRESS" <<'PY'
import re
import sys

value = sys.argv[1]

assert re.fullmatch(
    r"0x[0-9a-fA-F]{40}",
    value,
), "invalid SettlementVault address"

assert (
    int(value, 16) != 0
), "SettlementVault address must be nonzero"
PY

EVIDENCE="$ACCORD402_BRADBURY_CORE_EVIDENCE_DIR"

case "$EVIDENCE" in
  /*) ;;
  *)
    fail "EVIDENCE DIRECTORY MUST BE AN ABSOLUTE PATH"
    ;;
esac

case "$EVIDENCE/" in
  "$REPO/"*)
    fail "EVIDENCE DIRECTORY MUST BE OUTSIDE THE REPOSITORY"
    ;;
esac

test ! -e "$EVIDENCE" ||
  fail "EVIDENCE DIRECTORY ALREADY EXISTS"

mkdir -m 700 "$EVIDENCE"

# Live read-only chain binding before authorization consumption.
CHAIN_RESPONSE="$(
  curl \
    --fail \
    --silent \
    --show-error \
    -H 'content-type: application/json' \
    --data \
    '{"jsonrpc":"2.0","id":1,"method":"eth_chainId","params":[]}' \
    "$EXPECTED_RPC"
)"

printf '%s' "$CHAIN_RESPONSE" \
  > "$EVIDENCE/eth_chainId.raw.json"

CHAIN_HEX="$(
  printf '%s' "$CHAIN_RESPONSE" |
  "$PY" -c \
    'import json,sys; print(json.load(sys.stdin)["result"])'
)"

echo "LIVE_CHAIN_ID_HEX=$CHAIN_HEX"

test "$(
  printf '%s' "$CHAIN_HEX" |
  tr '[:upper:]' '[:lower:]'
)" = "$EXPECTED_CHAIN_ID_HEX" ||
  fail "LIVE RPC CHAIN ID MISMATCH"

AUTH_DIR="$HOME/.accord402-write-authorizations"

mkdir -m 700 -p "$AUTH_DIR"

AUTH_SENTINEL="$AUTH_DIR/${ACCORD402_BRADBURY_CORE_WRITE_AUTHORIZATION_ID}.consumed"

test ! -e "$AUTH_SENTINEL" ||
  fail "THIS CORE WRITE AUTHORIZATION ID HAS ALREADY BEEN CONSUMED"

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
  "schema": "accord402-bradbury-core-runtime-release-binding-v1",
  "network": "$EXPECTED_NETWORK",
  "chain_id": $EXPECTED_CHAIN_ID,
  "rpc": "$EXPECTED_RPC",
  "release_commit": "$RELEASE_COMMIT",
  "source_path": "contracts/accord402.py",
  "source_sha256": "$SOURCE_SHA",
  "settlement_vault_address": "$ACCORD402_BRADBURY_SETTLEMENT_VAULT_ADDRESS",
  "authorization_id": "$ACCORD402_BRADBURY_CORE_WRITE_AUTHORIZATION_ID"
}
EOF_BINDING

# Consume the one-shot Core authorization atomically and immediately before
# pytest can reach the deployment submission path.
(
  set -o noclobber
  umask 077

  printf '%s\n' \
    "release_commit=$RELEASE_COMMIT" \
    "source_sha256=$SOURCE_SHA" \
    "network=$EXPECTED_NETWORK" \
    "authorization_id=$ACCORD402_BRADBURY_CORE_WRITE_AUTHORIZATION_ID" \
    > "$AUTH_SENTINEL"
) ||
  fail "COULD NOT ATOMICALLY CONSUME CORE AUTHORIZATION ID"

echo "BRADBURY_CORE_WRITE_AUTHORIZATION_CONSUMED=YES"
echo "RETRY_OR_REBROADCAST_AUTHORIZED=NO"

export ACCORD402_BRADBURY_NETWORK="$EXPECTED_NETWORK"
export ACCORD402_BRADBURY_CHAIN_ID="$EXPECTED_CHAIN_ID"
export ACCORD402_BRADBURY_RPC="$EXPECTED_RPC"

cd "$RUNTIME_DIR"

"$PY" -m pytest \
  -q \
  "$REPO/tests/integration/test_accord402_core_bradbury_runtime.py"

echo
echo "================================================================"
echo "ACCORD402_BRADBURY_CORE_RUNTIME_INTEGRATION=PASS"
echo "RELEASE_COMMIT=$RELEASE_COMMIT"
echo "CORE_SHA256=$SOURCE_SHA"
echo "SETTLEMENT_VAULT=$ACCORD402_BRADBURY_SETTLEMENT_VAULT_ADDRESS"
echo "EVIDENCE_DIR=$EVIDENCE"
echo "AUTHORIZATION_ID=$ACCORD402_BRADBURY_CORE_WRITE_AUTHORIZATION_ID"
echo "BRADBURY_CORE_WRITE_AUTHORIZATION_CONSUMED=YES"
echo "RETRY_OR_REBROADCAST_AUTHORIZED=NO"
echo "================================================================"
