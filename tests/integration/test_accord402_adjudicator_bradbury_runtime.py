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
from web3.logs import DISCARD

from genlayer_py.chains.testnet_bradbury import CONSENSUS_MAIN_CONTRACT

from gltest import get_contract_factory, get_default_account, get_gl_client
from gltest.types import TransactionStatus


ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "contracts" / "Accord402Adjudicator.py"

EXPECTED_SOURCE_SHA256 = (
    "575e063661cc12a5de18dfa67ab3fbeb38bee1028694a08021efbc300115c198"
)
EXPECTED_NETWORK = "testnet_bradbury"
EXPECTED_CHAIN_ID = 4221
EXPECTED_RPC = "https://rpc-bradbury.genlayer.com"
EXPECTED_EVM_RPC = "https://rpc.testnet-chain.genlayer.com"
EXPECTED_MANIFEST_VERSION = "v0.5:9c68608"
EXPECTED_SENDER = "0x1f87Ae197af539253978d435aD45cCf28Fb95024"
EXPECTED_CONSENSUS_MAIN = "0x0112Bf6e83497965A5fdD6Dad1E447a6E004271D"

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



def _find_outer_submission(
    evm_client: Web3,
    *,
    sender: str,
    nonce: int,
    from_block: int,
    to_block: int,
    expected_tx_id: str,
) -> dict[str, Any]:
    consensus = evm_client.eth.contract(
        address=Web3.to_checksum_address(EXPECTED_CONSENSUS_MAIN),
        abi=CONSENSUS_MAIN_CONTRACT["abi"],
    )

    matches: list[dict[str, Any]] = []

    for block_number in range(max(0, from_block), to_block + 1):
        block = evm_client.eth.get_block(
            block_number,
            full_transactions=True,
        )

        for tx in block["transactions"]:
            if str(tx.get("from", "")).lower() != sender.lower():
                continue
            if int(tx["nonce"]) != nonce:
                continue

            assert tx.get("to") is not None, tx
            assert (
                str(tx["to"]).lower()
                == EXPECTED_CONSENSUS_MAIN.lower()
            ), tx

            receipt = evm_client.eth.get_transaction_receipt(tx["hash"])
            assert int(receipt["status"]) == 1, receipt

            new_events = (
                consensus.events.NewTransaction()
                .process_receipt(receipt, errors=DISCARD)
            )
            created_events = (
                consensus.events.CreatedTransaction()
                .process_receipt(receipt, errors=DISCARD)
            )

            assert len(new_events) + len(created_events) == 1, {
                "new_transaction_events": len(new_events),
                "created_transaction_events": len(created_events),
                "receipt": dict(receipt),
            }

            if created_events:
                raise AssertionError(
                    "deployment submission is queued as CreatedTransaction; "
                    "a deployed address is not available yet, so the dependent "
                    "Core must not be submitted"
                )

            event = new_events[0]
            event_tx_id = _hex_text(event["args"]["txId"])

            assert event_tx_id.lower() == expected_tx_id.lower(), {
                "sdk_tx_id": expected_tx_id,
                "event_tx_id": event_tx_id,
            }

            recipient = str(event["args"]["recipient"])
            activator = str(event["args"]["activator"])

            assert recipient.startswith("0x")
            assert len(recipient) == 42
            assert int(recipient, 16) != 0

            outer_hash = _hex_text(tx["hash"])

            matches.append(
                {
                    "outer_evm_tx_hash": outer_hash,
                    "outer_evm_block_number": int(receipt["blockNumber"]),
                    "outer_evm_receipt_status": int(receipt["status"]),
                    "creation_event_type": "NewTransaction",
                    "transaction_id": event_tx_id,
                    "provisional_contract_address": recipient,
                    "event_activator": activator,
                }
            )

    assert len(matches) == 1, {
        "sender": sender,
        "nonce": nonce,
        "from_block": from_block,
        "to_block": to_block,
        "matches": matches,
    }

    return matches[0]



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

    # Capture the EVM height immediately before submission so the exact
    # outer EVM transaction can be bound after deploy_contract() returns.
    # deploy_contract() waits for the outer EVM receipt, not GenLayer finality.
    pre_submit_evm_block = int(evm_client.eth.block_number)

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
    post_submit_evm_block = int(evm_client.eth.block_number)

    # Persist the SDK-returned GenLayer transaction id immediately. If any
    # later provenance extraction fails, the submitted write is still recorded.
    submission_payload: dict[str, Any] = {
        "schema": "accord402-bradbury-adjudicator-runtime-submission-v2",
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
        "pre_submit_evm_block": pre_submit_evm_block,
        "post_submit_evm_block": post_submit_evm_block,
        "transaction_id": tx_id_text,
        "outer_evm_tx_hash": None,
        "outer_evm_block_number": None,
        "outer_evm_receipt_status": None,
        "creation_event_type": None,
        "provisional_contract_address": None,
        "event_activator": None,
        "finality_wait_performed": False,
    }

    _atomic_json(
        evidence_dir / "deployment-submission.json",
        submission_payload,
    )

    outer = _find_outer_submission(
        evm_client,
        sender=expected_sender,
        nonce=expected_start_nonce,
        from_block=max(0, pre_submit_evm_block - 2),
        to_block=post_submit_evm_block,
        expected_tx_id=tx_id_text,
    )

    submission_payload.update(outer)

    _atomic_json(
        evidence_dir / "deployment-submission.json",
        submission_payload,
    )

    defer_finality = os.environ.get(
        "ACCORD402_BRADBURY_DEFER_FINALITY",
        "NO",
    )
    assert defer_finality in {"YES", "NO"}

    if defer_finality == "YES":
        # Stage-2 batch workflow stops here deliberately. The transaction ID,
        # outer EVM transaction, and provisional IC address are all persisted.
        # Finality is verified later by the dedicated read-only finalizer.
        return

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
