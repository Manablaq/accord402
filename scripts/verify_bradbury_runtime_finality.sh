#!/usr/bin/env bash
set -euo pipefail
umask 077

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="$REPO/.venv/bin/python"

EXPECTED_SOURCE_SHA="575e063661cc12a5de18dfa67ab3fbeb38bee1028694a08021efbc300115c198"
EXPECTED_CHAIN_ID="4221"

fail() {
  echo "STOP: $*" >&2
  exit 1
}

test -x "$PY" \
  || fail "PROJECT VENV PYTHON MISSING"

test -z "${ACCORD402_BRADBURY_PRIVATE_KEY:-}" \
  || fail "PRIVATE KEY MUST NOT BE LOADED"

test "${ACCORD402_BRADBURY_WRITE_AUTHORIZED:-NO}" != "YES" \
  || fail "WRITE AUTHORIZATION MUST BE DISABLED"

test -n "${ACCORD402_BRADBURY_EVIDENCE_DIR:-}" \
  || fail "MISSING ACCORD402_BRADBURY_EVIDENCE_DIR"

EVIDENCE="$ACCORD402_BRADBURY_EVIDENCE_DIR"
SUBMISSION="$EVIDENCE/deployment-submission.json"

test -f "$SUBMISSION" \
  || fail "DEPLOYMENT SUBMISSION EVIDENCE MISSING"

cd "$REPO"

"$PY" - \
  "$SUBMISSION" \
  "$EVIDENCE" \
  "$EXPECTED_SOURCE_SHA" \
  "$EXPECTED_CHAIN_ID" <<'PY'
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from genlayer_py import create_client
from genlayer_py.chains import testnet_bradbury
from genlayer_py.types import TransactionStatus


submission_path = Path(sys.argv[1])
evidence = Path(sys.argv[2])
expected_source_sha = sys.argv[3]
expected_chain_id = int(sys.argv[4])

submission = json.loads(
    submission_path.read_text(
        encoding="utf-8"
    )
)

assert submission["schema"] == (
    "accord402-bradbury-adjudicator-runtime-submission-v2"
)

assert submission["source_sha256"] == expected_source_sha
assert int(submission["chain_id"]) == expected_chain_id
assert submission["finality_wait_performed"] is False

tx_id = submission["transaction_id"]

provisional_address = submission[
    "provisional_contract_address"
]

assert isinstance(tx_id, str)
assert tx_id.startswith("0x")
assert len(tx_id) == 66

assert isinstance(provisional_address, str)
assert provisional_address.startswith("0x")
assert len(provisional_address) == 42
assert int(provisional_address, 16) != 0

release_commit = submission["release_commit"]

committed_source = subprocess.check_output(
    [
        "git",
        "show",
        (
            f"{release_commit}:"
            "contracts/Accord402Adjudicator.py"
        ),
    ]
)

assert (
    hashlib.sha256(
        committed_source
    ).hexdigest()
    == expected_source_sha
)


def hex_text(value: Any) -> str:
    if isinstance(value, str):
        return value

    if isinstance(value, (bytes, bytearray)):
        return "0x" + bytes(value).hex()

    method = getattr(value, "hex", None)

    if callable(method):
        result = method()

        if isinstance(result, str):
            return (
                result
                if result.startswith("0x")
                else "0x" + result
            )

    return str(value)


def atomic_json(
    path: Path,
    payload: Any,
) -> None:
    tmp = path.with_suffix(
        path.suffix + ".tmp"
    )

    tmp.write_text(
        json.dumps(
            payload,
            indent=2,
            sort_keys=True,
            default=hex_text,
        )
        + "\n",
        encoding="utf-8",
    )

    tmp.replace(path)


def extract_address(
    receipt: dict[str, Any],
) -> str:
    candidate: Any = None

    decoded = receipt.get(
        "tx_data_decoded"
    )

    if isinstance(decoded, dict):
        candidate = decoded.get(
            "contract_address"
        )

        if candidate is None:
            candidate = decoded.get(
                "contractAddress"
            )

    if candidate is None:
        data = receipt.get("data")

        if isinstance(data, dict):
            candidate = data.get(
                "contract_address"
            )

            if candidate is None:
                candidate = data.get(
                    "contractAddress"
                )

    if candidate is None:
        candidate = receipt.get(
            "recipient"
        )

    assert isinstance(candidate, str), receipt
    assert candidate.startswith("0x"), receipt
    assert len(candidate) == 42, receipt

    return candidate


client = create_client(
    chain=testnet_bradbury
)

assert int(client.chain.id) == expected_chain_id

receipt = client.wait_for_transaction_receipt(
    transaction_hash=tx_id,
    status=TransactionStatus.FINALIZED,
    interval=3000,
    retries=240,
    full_transaction=True,
)

atomic_json(
    evidence
    / "deployment-finalized-receipt.json",
    receipt,
)

assert str(receipt.get("status")) == "7", receipt
assert receipt.get("status_name") == "FINALIZED", receipt

execution_result = int(
    receipt.get(
        "tx_execution_result"
    )
)

execution_result_name = receipt.get(
    "tx_execution_result_name"
)

assert execution_result == 1, receipt

assert (
    execution_result_name
    == "FINISHED_WITH_RETURN"
), receipt

receipt_tx_id = hex_text(
    receipt.get("tx_id")
)

assert (
    receipt_tx_id.lower()
    == tx_id.lower()
), {
    "submitted_tx_id": tx_id,
    "finalized_tx_id": receipt_tx_id,
}

final_address = extract_address(
    receipt
)

assert (
    final_address.lower()
    == provisional_address.lower()
), {
    "provisional_address": provisional_address,
    "final_address": final_address,
}

result = {
    "schema": (
        "accord402-bradbury-adjudicator-runtime-finality-v1"
    ),
    "result": "PASS",
    "release_commit": release_commit,
    "source_sha256": submission[
        "source_sha256"
    ],
    "registry_address": submission[
        "registry_address"
    ],
    "sender_address": submission[
        "sender_address"
    ],
    "authorized_start_nonce": submission[
        "authorized_start_nonce"
    ],
    "outer_evm_tx_hash": submission[
        "outer_evm_tx_hash"
    ],
    "transaction_id": tx_id,
    "provisional_contract_address": provisional_address,
    "final_contract_address": final_address,
    "finalized_status": 7,
    "execution_result": execution_result,
    "execution_result_name": execution_result_name,
    "execution_success": True,
    "blockchain_write_performed": False,
}

atomic_json(
    evidence
    / "deployment-finality-result.json",
    result,
)

print("ADJUDICATOR_FINALITY_VERIFICATION=PASS")
print(f"GENLAYER_TX_ID={tx_id}")
print(f"CONTRACT_ADDRESS={final_address}")
print("FINALIZED_STATUS=7")
print("EXECUTION_RESULT=1")
print(
    "EXECUTION_RESULT_NAME="
    "FINISHED_WITH_RETURN"
)
print("BLOCKCHAIN_WRITE_PERFORMED=NO")
PY

echo "ACCORD402_BRADBURY_ADJUDICATOR_FINALITY=PASS"
