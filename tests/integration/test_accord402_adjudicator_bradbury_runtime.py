"""Guarded Bradbury runtime integration for Accord402Adjudicator.

This module is safe to collect during ordinary repository pytest runs. The
single live test is skipped unless the dedicated Bradbury runner has set the
explicit authorization environment gate.

A successful run is deployment-runtime evidence only; it is not full graph,
settlement, recovery, balance-consequence, or frontend certification.
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest
from web3 import Web3

from gltest import get_contract_factory, get_default_account, get_gl_client
from gltest.types import TransactionStatus


ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "contracts" / "Accord402Adjudicator.py"

EXPECTED_SOURCE_SHA256 = (
    "35d8beeb2dedb9b2d6839c3237ad839d85a0a788abb80adbc0557ed15b07a271"
)
EXPECTED_NETWORK = "testnet_bradbury"
EXPECTED_CHAIN_ID = 4221
EXPECTED_RPC = "https://rpc-bradbury.genlayer.com"
EXPECTED_EVM_RPC = "https://rpc.testnet-chain.genlayer.com"
EXPECTED_MANIFEST_VERSION = "v0.5:9c68608"
EXPECTED_SENDER = "0x1f87Ae197af539253978d435aD45cCf28Fb95024"

pytestmark = pytest.mark.skipif(
    os.environ.get("ACCORD402_BRADBURY_WRITE_AUTHORIZED") != "YES",
    reason=(
        "live Bradbury write is disabled; use the guarded runner only after "
        "fresh explicit authorization"
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
                return result if result.startswith("0x") else "0x" + result
        except Exception:
            pass
    return str(value)


def _atomic_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    data = json.dumps(
        payload,
        indent=2,
        sort_keys=True,
        default=_json_default,
    ) + "\n"
    tmp.write_text(data, encoding="utf-8")
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
            return result if result.startswith("0x") else "0x" + result
    return str(value)


def _extract_deployment_address(receipt: dict[str, Any]) -> str:
    # Accept legacy decoded deployment data, but also support Bradbury
    # receipts where tx_data_decoded is null and recipient is the deployed IC.
    candidate: Any = None

    decoded = receipt.get("tx_data_decoded")
    if isinstance(decoded, dict):
        candidate = decoded.get("contract_address")
        if candidate is None:
            candidate = decoded.get("contractAddress")

    if candidate is None:
        data = receipt.get("data")
        if isinstance(data, dict):
            candidate = data.get("contract_address")
            if candidate is None:
                candidate = data.get("contractAddress")

    if candidate is None:
        candidate = receipt.get("recipient")

    assert isinstance(candidate, str), receipt
    assert candidate.startswith("0x"), receipt
    assert len(candidate) == 42, receipt
    return candidate


def _required_env(name: str) -> str:
    value = os.environ.get(name, "")
    assert value, f"missing required environment variable: {name}"
    return value


def test_adjudicator_deploys_finalized_with_persisted_provenance() -> None:
    assert os.environ.get("ACCORD402_BRADBURY_WRITE_AUTHORIZED") == "YES"
    assert _required_env("ACCORD402_BRADBURY_NETWORK") == EXPECTED_NETWORK
    assert int(_required_env("ACCORD402_BRADBURY_CHAIN_ID")) == EXPECTED_CHAIN_ID
    assert _required_env("ACCORD402_BRADBURY_RPC") == EXPECTED_RPC
    assert _required_env("ACCORD402_BRADBURY_EVM_RPC") == EXPECTED_EVM_RPC
    assert (
        _required_env("ACCORD402_BRADBURY_MANIFEST_VERSION")
        == EXPECTED_MANIFEST_VERSION
    )

    expected_sender = _required_env("ACCORD402_BRADBURY_EXPECTED_SENDER")
    assert expected_sender.lower() == EXPECTED_SENDER.lower()

    expected_start_nonce = int(
        _required_env("ACCORD402_BRADBURY_EXPECTED_START_NONCE")
    )
    assert expected_start_nonce >= 0

    authorized_sha = _required_env("ACCORD402_AUTHORIZED_ADJUDICATOR_SHA256")
    assert authorized_sha == EXPECTED_SOURCE_SHA256

    source_bytes = CONTRACT.read_bytes()
    source_sha = hashlib.sha256(source_bytes).hexdigest()
    assert source_sha == EXPECTED_SOURCE_SHA256

    release_commit = _required_env("ACCORD402_AUTHORIZED_RELEASE_COMMIT")
    registry_address = _required_env("ACCORD402_BRADBURY_REGISTRY_ADDRESS")
    evidence_dir = Path(_required_env("ACCORD402_BRADBURY_EVIDENCE_DIR")).resolve()

    factory = get_contract_factory(contract_file_path="Accord402Adjudicator.py")
    factory_sha = hashlib.sha256(factory.contract_code.encode("utf-8")).hexdigest()
    assert factory_sha == EXPECTED_SOURCE_SHA256

    client = get_gl_client()
    account = get_default_account()

    assert int(client.chain.id) == EXPECTED_CHAIN_ID
    assert account.address.lower() == expected_sender.lower()

    evm_client = Web3(
        Web3.HTTPProvider(
            EXPECTED_EVM_RPC,
            request_kwargs={"timeout": 30},
        )
    )
    assert evm_client.is_connected()
    assert int(evm_client.eth.chain_id) == EXPECTED_CHAIN_ID

    pre_submit_latest_nonce = int(
        evm_client.eth.get_transaction_count(expected_sender, "latest")
    )
    pre_submit_pending_nonce = int(
        evm_client.eth.get_transaction_count(expected_sender, "pending")
    )

    assert pre_submit_latest_nonce == expected_start_nonce
    assert pre_submit_pending_nonce == expected_start_nonce

    _atomic_json(
        evidence_dir / "deployment-pre-submit-binding.json",
        {
            "schema": "accord402-bradbury-adjudicator-pre-submit-binding-v1",
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "network": EXPECTED_NETWORK,
            "chain_id": EXPECTED_CHAIN_ID,
            "genlayer_rpc": EXPECTED_RPC,
            "evm_rpc": EXPECTED_EVM_RPC,
            "manifest_version": EXPECTED_MANIFEST_VERSION,
            "release_commit": release_commit,
            "source_sha256": source_sha,
            "registry_address": registry_address,
            "authorized_sender": expected_sender,
            "loaded_sender": account.address,
            "authorized_start_nonce": expected_start_nonce,
            "latest_nonce": pre_submit_latest_nonce,
            "pending_nonce": pre_submit_pending_nonce,
        },
    )

    # Low-level send is intentional: deploy_contract_tx() waits before
    # returning and therefore cannot persist the submitted GenLayer tx id
    # before finality polling begins.
    tx_id = client.deploy_contract(
        code=factory.contract_code,
        account=account,
        args=[registry_address],
        leader_only=False,
    )

    post_submit_latest_nonce = int(
        evm_client.eth.get_transaction_count(expected_sender, "latest")
    )
    post_submit_pending_nonce = int(
        evm_client.eth.get_transaction_count(expected_sender, "pending")
    )

    assert post_submit_latest_nonce == expected_start_nonce + 1
    assert post_submit_pending_nonce == expected_start_nonce + 1

    tx_id_text = _hex_text(tx_id)

    # Provenance is persisted immediately after the SDK returns the GenLayer
    # transaction id and before finality polling.
    _atomic_json(
        evidence_dir / "deployment-submission.json",
        {
            "schema": "accord402-bradbury-adjudicator-runtime-submission-v1",
            "submitted_at": datetime.now(timezone.utc).isoformat(),
            "network": EXPECTED_NETWORK,
            "chain_id": EXPECTED_CHAIN_ID,
            "rpc": EXPECTED_RPC,
            "evm_rpc": EXPECTED_EVM_RPC,
            "manifest_version": EXPECTED_MANIFEST_VERSION,
            "release_commit": release_commit,
            "source_path": "contracts/Accord402Adjudicator.py",
            "source_sha256": source_sha,
            "registry_address": registry_address,
            "sender_address": account.address,
            "authorized_sender_address": expected_sender,
            "authorized_start_nonce": expected_start_nonce,
            "pre_submit_latest_nonce": pre_submit_latest_nonce,
            "pre_submit_pending_nonce": pre_submit_pending_nonce,
            "post_submit_latest_nonce": post_submit_latest_nonce,
            "post_submit_pending_nonce": post_submit_pending_nonce,
            "transaction_id": tx_id_text,
        },
    )

    receipt = client.wait_for_transaction_receipt(
        transaction_hash=tx_id,
        status=TransactionStatus.FINALIZED,
        interval=3000,
        retries=240,
        full_transaction=True,
    )

    _atomic_json(evidence_dir / "deployment-finalized-receipt.json", receipt)

    assert str(receipt.get("status")) == "7", receipt
    assert receipt.get("status_name") == "FINALIZED", receipt

    # Bradbury success requires both terminal finality and a successful
    # GenVM execution result. Do not use gltest's legacy
    # tx_execution_succeeded() helper here: the pinned helper depends on
    # leader_receipt, while the consequential execution outcome is exposed
    # directly as tx_execution_result / tx_execution_result_name.
    execution_result = receipt.get("tx_execution_result")
    execution_result_name = receipt.get("tx_execution_result_name")
    assert int(execution_result) == 1, receipt
    assert execution_result_name == "FINISHED_WITH_RETURN", receipt

    receipt_tx_id = _hex_text(receipt.get("tx_id"))
    assert receipt_tx_id.lower() == tx_id_text.lower(), receipt

    contract_address = _extract_deployment_address(receipt)

    _atomic_json(
        evidence_dir / "deployment-result.json",
        {
            "schema": "accord402-bradbury-adjudicator-runtime-result-v1",
            "result": "PASS",
            "network": EXPECTED_NETWORK,
            "chain_id": EXPECTED_CHAIN_ID,
            "rpc": EXPECTED_RPC,
            "evm_rpc": EXPECTED_EVM_RPC,
            "manifest_version": EXPECTED_MANIFEST_VERSION,
            "release_commit": release_commit,
            "source_path": "contracts/Accord402Adjudicator.py",
            "source_sha256": source_sha,
            "registry_address": registry_address,
            "sender_address": account.address,
            "authorized_sender_address": expected_sender,
            "authorized_start_nonce": expected_start_nonce,
            "pre_submit_latest_nonce": pre_submit_latest_nonce,
            "pre_submit_pending_nonce": pre_submit_pending_nonce,
            "post_submit_latest_nonce": post_submit_latest_nonce,
            "post_submit_pending_nonce": post_submit_pending_nonce,
            "transaction_id": tx_id_text,
            "finalized_status": 7,
            "execution_result": int(execution_result),
            "execution_result_name": execution_result_name,
            "execution_success": True,
            "contract_address": contract_address,
        },
    )
