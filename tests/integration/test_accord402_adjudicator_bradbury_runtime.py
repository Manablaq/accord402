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

from gltest import get_contract_factory, get_default_account, get_gl_client
from gltest.assertions import tx_execution_succeeded
from gltest.types import TransactionStatus
from gltest.utils import extract_contract_address


ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "contracts" / "Accord402Adjudicator.py"

EXPECTED_SOURCE_SHA256 = (
    "4e3d3fabce4563f660eb10b4328b805c1cbeea92f83ecd047add00f1b01a1775"
)
EXPECTED_NETWORK = "testnet_bradbury"
EXPECTED_CHAIN_ID = 4221
EXPECTED_RPC = "https://rpc-bradbury.genlayer.com"

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


def _required_env(name: str) -> str:
    value = os.environ.get(name, "")
    assert value, f"missing required environment variable: {name}"
    return value


def test_adjudicator_deploys_finalized_with_persisted_provenance() -> None:
    assert os.environ.get("ACCORD402_BRADBURY_WRITE_AUTHORIZED") == "YES"
    assert _required_env("ACCORD402_BRADBURY_NETWORK") == EXPECTED_NETWORK
    assert int(_required_env("ACCORD402_BRADBURY_CHAIN_ID")) == EXPECTED_CHAIN_ID
    assert _required_env("ACCORD402_BRADBURY_RPC") == EXPECTED_RPC

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

    # Low-level send is intentional: deploy_contract_tx() waits before
    # returning and therefore cannot persist the submitted GenLayer tx id
    # before finality polling begins.
    tx_id = client.deploy_contract(
        code=factory.contract_code,
        account=account,
        args=[registry_address],
        leader_only=False,
    )
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
            "release_commit": release_commit,
            "source_path": "contracts/Accord402Adjudicator.py",
            "source_sha256": source_sha,
            "registry_address": registry_address,
            "sender_address": account.address,
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
    assert tx_execution_succeeded(receipt), receipt

    receipt_tx_id = _hex_text(receipt.get("tx_id"))
    assert receipt_tx_id.lower() == tx_id_text.lower(), receipt

    contract_address = extract_contract_address(receipt)
    assert isinstance(contract_address, str)
    assert contract_address.startswith("0x")
    assert len(contract_address) == 42

    _atomic_json(
        evidence_dir / "deployment-result.json",
        {
            "schema": "accord402-bradbury-adjudicator-runtime-result-v1",
            "result": "PASS",
            "network": EXPECTED_NETWORK,
            "chain_id": EXPECTED_CHAIN_ID,
            "rpc": EXPECTED_RPC,
            "release_commit": release_commit,
            "source_path": "contracts/Accord402Adjudicator.py",
            "source_sha256": source_sha,
            "registry_address": registry_address,
            "sender_address": account.address,
            "transaction_id": tx_id_text,
            "finalized_status": 7,
            "execution_success": True,
            "contract_address": contract_address,
        },
    )
