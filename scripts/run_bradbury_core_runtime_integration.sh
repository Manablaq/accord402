#!/usr/bin/env bash
set -euo pipefail
umask 077

REPO="$(
  cd "$(
    dirname "${BASH_SOURCE[0]}"
  )/.."
  pwd
)"

PY="$REPO/.venv/bin/python"

EXPECTED_CORE_SHA="60ac857d566e49ae912a384c7ce0a11da3bc3201d7349de3fe24bee0cd095692"
EXPECTED_CORE_BYTES="51757"
EXPECTED_CHUNK_SIZE="14336"
EXPECTED_CHUNK_COUNT="4"
EXPECTED_EOA_WRITE_COUNT="6"

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
echo "ACCORD402 GUARDED BRADBURY CHUNKED CORE DEPLOYMENT"
echo "EXACT AUTHORIZED EOA WRITE COUNT: 6"
echo "1 FACTORY + 4 CHUNKS + 1 TRIGGER"
echo "CHILD DEPLOYMENT IS PROTOCOL-TRIGGERED ON FINALIZED"
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

CORE_SHA="$(
  sha256_file \
    contracts/accord402.py
)"

CORE_BYTES="$(
  wc -c \
    < contracts/accord402.py |
  tr -d ' '
)"

FACTORY_SHA="$(
  sha256_file \
    contracts/accord402_core_chunk_deployer.py
)"

test "$CORE_SHA" = "$EXPECTED_CORE_SHA" ||
  fail "CORE SOURCE SHA DRIFT"

test "$CORE_BYTES" = "$EXPECTED_CORE_BYTES" ||
  fail "CORE SOURCE BYTE LENGTH DRIFT"

for f in \
  gltest.config.yaml \
  contracts/accord402.py \
  contracts/accord402_core_chunk_deployer.py \
  tests/integration/test_accord402_core_bradbury_runtime.py \
  tests/test_accord402_core_chunk_deployer_guards.py \
  scripts/run_bradbury_core_runtime_integration.sh \
  .github/workflows/verify.yml
do
  git ls-files --error-unmatch "$f" \
    >/dev/null 2>&1 ||
    fail "REQUIRED RELEASE FILE IS NOT TRACKED: $f"
done

need_env ACCORD402_BRADBURY_CHUNKED_CORE_WRITE_AUTHORIZED
need_env ACCORD402_AUTHORIZED_RELEASE_COMMIT
need_env ACCORD402_AUTHORIZED_CORE_SHA256
need_env ACCORD402_AUTHORIZED_FACTORY_SHA256
need_env ACCORD402_AUTHORIZED_CORE_WORKER_ADDRESS
need_env ACCORD402_AUTHORIZED_BATCH_START_NONCE
need_env ACCORD402_AUTHORIZED_EOA_WRITE_COUNT
need_env ACCORD402_BRADBURY_CHUNKED_CORE_WRITE_AUTHORIZATION_ID
need_env ACCORD402_BRADBURY_PRIVATE_KEY
need_env ACCORD402_BRADBURY_SETTLEMENT_VAULT_ADDRESS
need_env ACCORD402_BRADBURY_CORE_EVIDENCE_DIR

test "$ACCORD402_BRADBURY_CHUNKED_CORE_WRITE_AUTHORIZED" = "YES" ||
  fail "CHUNKED CORE WRITE AUTHORIZATION FLAG MUST BE EXACTLY YES"

test "$ACCORD402_AUTHORIZED_RELEASE_COMMIT" = "$RELEASE_COMMIT" ||
  fail "AUTHORIZED RELEASE COMMIT DOES NOT MATCH HEAD"

test "$ACCORD402_AUTHORIZED_CORE_SHA256" = "$CORE_SHA" ||
  fail "AUTHORIZED CORE SHA DOES NOT MATCH EXACT CANDIDATE"

test "$ACCORD402_AUTHORIZED_FACTORY_SHA256" = "$FACTORY_SHA" ||
  fail "AUTHORIZED FACTORY SHA DOES NOT MATCH EXACT CANDIDATE"

test "$ACCORD402_AUTHORIZED_EOA_WRITE_COUNT" = "$EXPECTED_EOA_WRITE_COUNT" ||
  fail "AUTHORIZED EOA WRITE COUNT MUST BE EXACTLY 6"

case "$ACCORD402_BRADBURY_CHUNKED_CORE_WRITE_AUTHORIZATION_ID" in
  *[!A-Za-z0-9._-]*|"")
    fail "AUTHORIZATION ID MUST USE ONLY A-Z a-z 0-9 . _ -"
    ;;
esac

"$PY" - \
  "$ACCORD402_BRADBURY_SETTLEMENT_VAULT_ADDRESS" \
  "$ACCORD402_AUTHORIZED_CORE_WORKER_ADDRESS" \
  "$ACCORD402_AUTHORIZED_BATCH_START_NONCE" <<'PY_VALIDATE'
import re
import sys

vault, worker, nonce = sys.argv[1:]

for label, value in (
    ("SettlementVault", vault),
    ("worker", worker),
):
    assert re.fullmatch(
        r"0x[0-9a-fA-F]{40}",
        value,
    )

    assert int(
        value,
        16,
    ) != 0

assert re.fullmatch(
    r"[0-9]+",
    nonce,
)
PY_VALIDATE

START_NONCE="$ACCORD402_AUTHORIZED_BATCH_START_NONCE"

END_NONCE="$(
  "$PY" - \
    "$START_NONCE" \
    "$EXPECTED_EOA_WRITE_COUNT" <<'PY_NONCE'
import sys

start = int(
    sys.argv[1]
)

count = int(
    sys.argv[2]
)

print(
    start + count - 1
)
PY_NONCE
)"

EVIDENCE="$ACCORD402_BRADBURY_CORE_EVIDENCE_DIR"

case "$EVIDENCE" in
  /*) ;;
  *)
    fail "EVIDENCE DIRECTORY MUST BE ABSOLUTE"
    ;;
esac

case "$EVIDENCE/" in
  "$REPO/"*)
    fail "EVIDENCE DIRECTORY MUST BE OUTSIDE REPOSITORY"
    ;;
esac

test ! -e "$EVIDENCE" ||
  fail "EVIDENCE DIRECTORY ALREADY EXISTS"

mkdir -m 700 "$EVIDENCE"

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

test "$(
  printf '%s' "$CHAIN_HEX" |
  tr '[:upper:]' '[:lower:]'
)" = "$EXPECTED_CHAIN_ID_HEX" ||
  fail "LIVE RPC CHAIN ID MISMATCH"

LATEST_RESPONSE="$(
  curl \
    --fail \
    --silent \
    --show-error \
    -H 'content-type: application/json' \
    --data \
    "{\"jsonrpc\":\"2.0\",\"id\":2,\"method\":\"eth_getTransactionCount\",\"params\":[\"$ACCORD402_AUTHORIZED_CORE_WORKER_ADDRESS\",\"latest\"]}" \
    "$EXPECTED_RPC"
)"

PENDING_RESPONSE="$(
  curl \
    --fail \
    --silent \
    --show-error \
    -H 'content-type: application/json' \
    --data \
    "{\"jsonrpc\":\"2.0\",\"id\":3,\"method\":\"eth_getTransactionCount\",\"params\":[\"$ACCORD402_AUTHORIZED_CORE_WORKER_ADDRESS\",\"pending\"]}" \
    "$EXPECTED_RPC"
)"

printf '%s' "$LATEST_RESPONSE" \
  > "$EVIDENCE/worker_nonce_latest.raw.json"

printf '%s' "$PENDING_RESPONSE" \
  > "$EVIDENCE/worker_nonce_pending.raw.json"

LATEST="$(
  printf '%s' "$LATEST_RESPONSE" |
  "$PY" -c \
    'import json,sys; print(int(json.load(sys.stdin)["result"],16))'
)"

PENDING="$(
  printf '%s' "$PENDING_RESPONSE" |
  "$PY" -c \
    'import json,sys; print(int(json.load(sys.stdin)["result"],16))'
)"

echo "AUTHORIZED_BATCH_START_NONCE=$START_NONCE"
echo "AUTHORIZED_BATCH_END_NONCE=$END_NONCE"
echo "AUTHORIZED_EOA_WRITE_COUNT=$EXPECTED_EOA_WRITE_COUNT"
echo "IMMEDIATE_NONCE_LATEST=$LATEST"
echo "IMMEDIATE_NONCE_PENDING=$PENDING"

test "$LATEST" = "$START_NONCE" ||
  fail "LATEST NONCE DRIFTED FROM AUTHORIZED BATCH START"

test "$PENDING" = "$START_NONCE" ||
  fail "PENDING NONCE DRIFTED FROM AUTHORIZED BATCH START"

echo "IMMEDIATE_BATCH_NONCE_BINDING=PASS"

"$PY" - \
  contracts/accord402.py \
  "$EXPECTED_CORE_SHA" \
  "$EXPECTED_CORE_BYTES" \
  "$EXPECTED_CHUNK_SIZE" \
  "$EXPECTED_CHUNK_COUNT" \
  "$EVIDENCE/batch-plan.json" \
  "$RELEASE_COMMIT" \
  "$FACTORY_SHA" \
  "$START_NONCE" \
  "$END_NONCE" \
  "$ACCORD402_BRADBURY_SETTLEMENT_VAULT_ADDRESS" <<'PY_PLAN'
import hashlib
import json
import sys
from pathlib import Path

(
    core_path,
    expected_sha,
    expected_bytes,
    chunk_size,
    chunk_count,
    output,
    release,
    factory_sha,
    start_nonce,
    end_nonce,
    vault,
) = sys.argv[1:]

expected_bytes = int(
    expected_bytes
)

chunk_size = int(
    chunk_size
)

chunk_count = int(
    chunk_count
)

source = Path(
    core_path
).read_bytes()

assert len(source) == expected_bytes

assert hashlib.sha256(
    source
).hexdigest() == expected_sha

text = source.decode(
    "ascii",
    errors="strict",
)

chunks = [
    text[
        offset:
        offset + chunk_size
    ].encode(
        "ascii"
    )
    for offset in range(
        0,
        len(text),
        chunk_size,
    )
]

assert len(chunks) == chunk_count

rebuilt = b"".join(
    chunks
)

assert rebuilt == source

payload = {
    "schema": (
        "accord402-bradbury-chunked-core-"
        "authorized-batch-plan-v1"
    ),
    "release_commit": release,
    "core_source_sha256": expected_sha,
    "core_source_bytes": expected_bytes,
    "factory_source_sha256": factory_sha,
    "chunk_size": chunk_size,
    "chunk_count": chunk_count,
    "chunk_sha256": [
        hashlib.sha256(
            chunk
        ).hexdigest()
        for chunk in chunks
    ],
    "chunk_byte_lengths": [
        len(chunk)
        for chunk in chunks
    ],
    "eoa_write_count": 6,
    "batch_start_nonce": int(
        start_nonce
    ),
    "batch_end_nonce": int(
        end_nonce
    ),
    "write_shape": [
        "factory_deploy",
        "chunk_0",
        "chunk_1",
        "chunk_2",
        "chunk_3",
        "deploy_trigger",
    ],
    "settlement_vault_address": vault,
    "child_deployment_on": "finalized",
}

Path(
    output
).write_text(
    json.dumps(
        payload,
        indent=2,
        sort_keys=True,
    )
    + "\n",
    encoding="utf-8",
)
PY_PLAN

cat > "$EVIDENCE/release-binding.json" <<EOF_BINDING
{
  "schema": "accord402-bradbury-chunked-core-release-binding-v1",
  "network": "$EXPECTED_NETWORK",
  "chain_id": $EXPECTED_CHAIN_ID,
  "rpc": "$EXPECTED_RPC",
  "release_commit": "$RELEASE_COMMIT",
  "core_source_path": "contracts/accord402.py",
  "core_source_sha256": "$CORE_SHA",
  "core_source_bytes": $CORE_BYTES,
  "factory_source_path": "contracts/accord402_core_chunk_deployer.py",
  "factory_source_sha256": "$FACTORY_SHA",
  "chunk_size": $EXPECTED_CHUNK_SIZE,
  "chunk_count": $EXPECTED_CHUNK_COUNT,
  "authorized_eoa_write_count": $EXPECTED_EOA_WRITE_COUNT,
  "authorized_batch_start_nonce": $START_NONCE,
  "authorized_batch_end_nonce": $END_NONCE,
  "settlement_vault_address": "$ACCORD402_BRADBURY_SETTLEMENT_VAULT_ADDRESS",
  "worker_address": "$ACCORD402_AUTHORIZED_CORE_WORKER_ADDRESS",
  "authorization_id": "$ACCORD402_BRADBURY_CHUNKED_CORE_WRITE_AUTHORIZATION_ID"
}
EOF_BINDING

AUTH_DIR="$HOME/.accord402-write-authorizations"

mkdir -m 700 -p "$AUTH_DIR"

AUTH_SENTINEL="$AUTH_DIR/${ACCORD402_BRADBURY_CHUNKED_CORE_WRITE_AUTHORIZATION_ID}.consumed"

test ! -e "$AUTH_SENTINEL" ||
  fail "THIS CHUNKED CORE BATCH AUTHORIZATION IS ALREADY CONSUMED"

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

(
  set -o noclobber
  umask 077

  printf '%s\n' \
    "release_commit=$RELEASE_COMMIT" \
    "core_source_sha256=$CORE_SHA" \
    "factory_source_sha256=$FACTORY_SHA" \
    "network=$EXPECTED_NETWORK" \
    "worker_address=$ACCORD402_AUTHORIZED_CORE_WORKER_ADDRESS" \
    "authorized_batch_start_nonce=$START_NONCE" \
    "authorized_batch_end_nonce=$END_NONCE" \
    "authorized_eoa_write_count=$EXPECTED_EOA_WRITE_COUNT" \
    "authorization_id=$ACCORD402_BRADBURY_CHUNKED_CORE_WRITE_AUTHORIZATION_ID" \
    > "$AUTH_SENTINEL"
) ||
  fail "COULD NOT ATOMICALLY CONSUME BATCH AUTHORIZATION"

echo "CHUNKED_CORE_BATCH_AUTHORIZATION_CONSUMED=YES"
echo "THIS_BATCH_RUNNER_MUST_NEVER_BE_RERUN=YES"
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
echo "ACCORD402_BRADBURY_CHUNKED_CORE_RUNTIME_INTEGRATION=PASS"
echo "RELEASE_COMMIT=$RELEASE_COMMIT"
echo "CORE_SHA256=$CORE_SHA"
echo "FACTORY_SHA256=$FACTORY_SHA"
echo "CHUNK_SIZE=$EXPECTED_CHUNK_SIZE"
echo "CHUNK_COUNT=$EXPECTED_CHUNK_COUNT"
echo "AUTHORIZED_EOA_WRITE_COUNT=$EXPECTED_EOA_WRITE_COUNT"
echo "AUTHORIZED_BATCH_START_NONCE=$START_NONCE"
echo "AUTHORIZED_BATCH_END_NONCE=$END_NONCE"
echo "EVIDENCE_DIR=$EVIDENCE"
echo "AUTHORIZATION_ID=$ACCORD402_BRADBURY_CHUNKED_CORE_WRITE_AUTHORIZATION_ID"
echo "CHUNKED_CORE_BATCH_AUTHORIZATION_CONSUMED=YES"
echo "THIS_BATCH_RUNNER_MUST_NEVER_BE_RERUN=YES"
echo "RETRY_OR_REBROADCAST_AUTHORIZED=NO"
echo "================================================================"
