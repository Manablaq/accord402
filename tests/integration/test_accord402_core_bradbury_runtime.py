"""Guarded Bradbury runtime integration for the Accord402 Core.

Ordinary repository test runs collect this module safely. The live deployment
test is skipped unless the dedicated Core runner supplies a fresh, explicit,
Core-specific Bradbury write authorization.

A successful result proves only deployment provenance, finality, successful
GenVM execution, and the exact SettlementVault constructor binding.
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest

from gltest import get_contract_factory, get_default_account, get_gl_client
from gltest.types import TransactionStatus


ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "contracts" / "accord402.py"

EXPECTED_SOURCE_SHA256 = (
    "60ac857d566e49ae912a384c7ce0a11da3bc3201d7349de3fe24bee0cd095692"
)
EXPECTED_NETWORK = "testnet_bradbury"
EXPECTED_CHAIN_ID = 4221
EXPECTED_RPC = "https://rpc-bradbury.genlayer.com"

pytestmark = pytest.mark.skipif(
    os.environ.get("ACCORD402_BRADBURY_CORE_WRITE_AUTHORIZED") != "YES",
    reason=(
        "live Bradbury Core deployment is disabled; use the dedicated guarded "
        "Core runner only after fresh explicit authorization"
    ),
)


def _json_default(value: Any) -> str:
    if isinstance(value, (bytes, bytearray)):
        return "0x" + bytes(value).hex()

    hex_method = getattr(value, "hex", None)

    if callable(hex_method):
        try:
            result = hex_method()

            if isinstance(result, str):
                return (
                    result
                    if result.startswith("0x")
                    else "0x" + result
                )
        except Exception:
            pass

    return str(value)


def _atomic_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    tmp = path.with_suffix(path.suffix + ".tmp")

    data = (
        json.dumps(
            payload,
            indent=2,
            sort_keys=True,
            default=_json_default,
        )
        + "\n"
    )

    tmp.write_text(
        data,
        encoding="utf-8",
    )

    tmp.replace(path)


def _hex_text(value: Any) -> str:
    if isinstance(value, str):
        return value

    if isinstance(value, (bytes, bytearray)):
        return "0x" + bytes(value).hex()

    hex_method = getattr(value, "hex", None)

    if callable(hex_method):
        result = hex_method()

        if isinstance(result, str):
            return (
                result
                if result.startswith("0x")
                else "0x" + result
            )

    return str(value)


def _extract_deployment_address(
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

    # Bradbury / consensus v0.6 deployment receipts expose the deployed
    # Intelligent Contract address as recipient when decoded data is absent.
    if candidate is None:
        candidate = receipt.get(
            "recipient"
        )

    assert isinstance(
        candidate,
        str,
    ), receipt

    assert candidate.startswith(
        "0x"
    ), receipt

    assert len(candidate) == 42, receipt

    return candidate


def _required_env(name: str) -> str:
    value = os.environ.get(
        name,
        "",
    )

    assert value, (
        "missing required environment variable: "
        f"{name}"
    )

    return value


def test_core_deploys_finalized_with_persisted_provenance() -> None:
    assert (
        os.environ.get(
            "ACCORD402_BRADBURY_CORE_WRITE_AUTHORIZED"
        )
        == "YES"
    )

    assert (
        _required_env(
            "ACCORD402_BRADBURY_NETWORK"
        )
        == EXPECTED_NETWORK
    )

    assert (
        int(
            _required_env(
                "ACCORD402_BRADBURY_CHAIN_ID"
            )
        )
        == EXPECTED_CHAIN_ID
    )

    assert (
        _required_env(
            "ACCORD402_BRADBURY_RPC"
        )
        == EXPECTED_RPC
    )

    authorized_sha = _required_env(
        "ACCORD402_AUTHORIZED_CORE_SHA256"
    )

    assert (
        authorized_sha
        == EXPECTED_SOURCE_SHA256
    )

    source_bytes = CONTRACT.read_bytes()

    source_sha = hashlib.sha256(
        source_bytes
    ).hexdigest()

    assert (
        source_sha
        == EXPECTED_SOURCE_SHA256
    )

    release_commit = _required_env(
        "ACCORD402_AUTHORIZED_RELEASE_COMMIT"
    )

    settlement_vault = _required_env(
        "ACCORD402_BRADBURY_SETTLEMENT_VAULT_ADDRESS"
    )

    authorized_worker = _required_env(
        "ACCORD402_AUTHORIZED_CORE_WORKER_ADDRESS"
    )

    authorized_preflight_nonce = int(
        _required_env(
            "ACCORD402_AUTHORIZED_CORE_PREFLIGHT_NONCE"
        )
    )

    evidence_dir = Path(
        _required_env(
            "ACCORD402_BRADBURY_CORE_EVIDENCE_DIR"
        )
    ).resolve()

    factory = get_contract_factory(
        contract_file_path="accord402.py"
    )

    factory_sha = hashlib.sha256(
        factory.contract_code.encode(
            "utf-8"
        )
    ).hexdigest()

    assert (
        factory_sha
        == EXPECTED_SOURCE_SHA256
    )

    client = get_gl_client()
    account = get_default_account()

    assert (
        int(client.chain.id)
        == EXPECTED_CHAIN_ID
    )

    assert (
        account.address.lower()
        == authorized_worker.lower()
    )

    latest_nonce = int(
        client.get_transaction_count(
            account.address,
            "latest",
        )
    )

    pending_nonce = int(
        client.get_transaction_count(
            account.address,
            "pending",
        )
    )

    assert (
        latest_nonce
        == authorized_preflight_nonce
    )

    assert (
        pending_nonce
        == authorized_preflight_nonce
    )

    # A second nonce gate lives inside the test immediately before the
    # deployment path. Nonce drift therefore fails closed before the write.
    # Use the low-level SDK deployment call so the GenLayer transaction ID is
    # persisted immediately after submission and before finality polling.
    tx_id = client.deploy_contract(
        code=factory.contract_code,
        account=account,
        args=[settlement_vault],
        leader_only=False,
    )

    tx_id_text = _hex_text(tx_id)

    _atomic_json(
        evidence_dir
        / "deployment-submission.json",
        {
            "schema": (
                "accord402-bradbury-core-"
                "runtime-submission-v1"
            ),
            "submitted_at": (
                datetime.now(
                    timezone.utc
                ).isoformat()
            ),
            "network": EXPECTED_NETWORK,
            "chain_id": EXPECTED_CHAIN_ID,
            "rpc": EXPECTED_RPC,
            "release_commit": release_commit,
            "source_path": (
                "contracts/accord402.py"
            ),
            "source_sha256": source_sha,
            "settlement_vault_address": (
                settlement_vault
            ),
            "sender_address": (
                account.address
            ),
            "authorized_preflight_nonce": (
                authorized_preflight_nonce
            ),
            "observed_predeploy_nonce": (
                latest_nonce
            ),
            "transaction_id": tx_id_text,
        },
    )

    receipt = (
        client.wait_for_transaction_receipt(
            transaction_hash=tx_id,
            status=TransactionStatus.FINALIZED,
            interval=3000,
            retries=240,
            full_transaction=True,
        )
    )

    _atomic_json(
        evidence_dir
        / "deployment-finalized-receipt.json",
        receipt,
    )

    assert (
        str(receipt.get("status"))
        == "7"
    ), receipt

    assert (
        receipt.get("status_name")
        == "FINALIZED"
    ), receipt

    execution_result = receipt.get(
        "tx_execution_result"
    )

    execution_result_name = receipt.get(
        "tx_execution_result_name"
    )

    assert (
        int(execution_result)
        == 1
    ), receipt

    assert (
        execution_result_name
        == "FINISHED_WITH_RETURN"
    ), receipt

    receipt_tx_id = _hex_text(
        receipt.get("tx_id")
    )

    assert (
        receipt_tx_id.lower()
        == tx_id_text.lower()
    ), receipt

    contract_address = (
        _extract_deployment_address(
            receipt
        )
    )

    _atomic_json(
        evidence_dir
        / "deployment-result.json",
        {
            "schema": (
                "accord402-bradbury-core-"
                "runtime-result-v1"
            ),
            "result": "PASS",
            "network": EXPECTED_NETWORK,
            "chain_id": EXPECTED_CHAIN_ID,
            "rpc": EXPECTED_RPC,
            "release_commit": release_commit,
            "source_path": (
                "contracts/accord402.py"
            ),
            "source_sha256": source_sha,
            "settlement_vault_address": (
                settlement_vault
            ),
            "sender_address": (
                account.address
            ),
            "authorized_preflight_nonce": (
                authorized_preflight_nonce
            ),
            "observed_predeploy_nonce": (
                latest_nonce
            ),
            "transaction_id": tx_id_text,
            "finalized_status": 7,
            "execution_result": (
                int(execution_result)
            ),
            "execution_result_name": (
                execution_result_name
            ),
            "execution_success": True,
            "contract_address": (
                contract_address
            ),
        },
    )
