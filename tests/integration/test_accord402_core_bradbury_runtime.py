"""Guarded Bradbury deployment of the exact Accord402 Core through a chunk deployer.

Ordinary repository test runs collect this module safely but skip the live
batch. Only the dedicated one-shot runner may enable it.

The authorized EOA write batch is exactly:

1. deploy the small chunk deployer;
2. append four exact ordered Core-source chunks;
3. call deploy_core once.

The deploy_core call emits exactly one GenLayer child deployment on
``finalized``. The child transaction itself is then followed read-only until
``FINALIZED / FINISHED_WITH_RETURN`` and its decoded deployment payload is
bound back to the exact frozen Core source and SettlementVault constructor.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest
from web3 import Web3

from gltest import (
    get_contract_factory,
    get_default_account,
    get_gl_client,
)
from gltest.types import TransactionStatus


ROOT = Path(__file__).resolve().parents[2]

CORE = ROOT / "contracts" / "accord402.py"
DEPLOYER = (
    ROOT
    / "contracts"
    / "accord402_core_chunk_deployer.py"
)

EXPECTED_CORE_SHA256 = (
    "60ac857d566e49ae912a384c7ce0a11da3bc3201d7349de3fe24bee0cd095692"
)

EXPECTED_CORE_BYTES = 51757

CHUNK_SIZE = 14336
CHUNK_COUNT = 4
FINAL_CHUNK_SIZE = 8749
EXPECTED_EOA_WRITE_COUNT = 6

EXPECTED_NETWORK = "testnet_bradbury"
EXPECTED_CHAIN_ID = 4221
EXPECTED_RPC = "https://rpc-bradbury.genlayer.com"


pytestmark = pytest.mark.skipif(
    os.environ.get(
        "ACCORD402_BRADBURY_CHUNKED_CORE_WRITE_AUTHORIZED"
    )
    != "YES",
    reason=(
        "live Bradbury chunked Core deployment is disabled; "
        "use the dedicated guarded runner only after a fresh "
        "explicit six-write batch authorization"
    ),
)


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


def _json_default(value: Any) -> str:
    if isinstance(
        value,
        (bytes, bytearray),
    ):
        return "0x" + bytes(value).hex()

    hex_method = getattr(
        value,
        "hex",
        None,
    )

    if callable(hex_method):
        try:
            result = hex_method()

            if isinstance(
                result,
                str,
            ):
                return (
                    result
                    if result.startswith("0x")
                    else "0x" + result
                )
        except Exception:
            pass

    return str(value)


def _atomic_json(
    path: Path,
    payload: Any,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    tmp = path.with_suffix(
        path.suffix + ".tmp"
    )

    raw = (
        json.dumps(
            payload,
            indent=2,
            sort_keys=True,
            default=_json_default,
        )
        + "\n"
    ).encode(
        "utf-8"
    )

    tmp.write_bytes(raw)
    tmp.replace(path)


def _hex_text(value: Any) -> str:
    if isinstance(
        value,
        str,
    ):
        return value

    if isinstance(
        value,
        (bytes, bytearray),
    ):
        return (
            "0x"
            + bytes(value).hex()
        )

    method = getattr(
        value,
        "hex",
        None,
    )

    if callable(method):
        result = method()

        if isinstance(
            result,
            str,
        ):
            return (
                result
                if result.startswith("0x")
                else "0x" + result
            )

    return str(value)


def _assert_final_success(
    receipt: dict[str, Any],
) -> None:
    assert str(
        receipt.get("status")
    ) == "7", receipt

    assert (
        receipt.get("status_name")
        == "FINALIZED"
    ), receipt

    assert int(
        receipt.get(
            "tx_execution_result"
        )
    ) == 1, receipt

    assert (
        receipt.get(
            "tx_execution_result_name"
        )
        == "FINISHED_WITH_RETURN"
    ), receipt


def _extract_deployment_address(
    receipt: dict[str, Any],
) -> str:
    decoded = receipt.get(
        "tx_data_decoded"
    )

    candidate: Any = None

    if isinstance(
        decoded,
        dict,
    ):
        candidate = decoded.get(
            "contract_address"
        )

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


def _split_core(
    source_bytes: bytes,
) -> list[str]:
    text = source_bytes.decode(
        "ascii",
        errors="strict",
    )

    chunks = [
        text[
            offset:
            offset + CHUNK_SIZE
        ]
        for offset in range(
            0,
            len(text),
            CHUNK_SIZE,
        )
    ]

    assert len(chunks) == CHUNK_COUNT

    assert [
        len(
            chunk.encode(
                "ascii"
            )
        )
        for chunk in chunks
    ] == [
        CHUNK_SIZE,
        CHUNK_SIZE,
        CHUNK_SIZE,
        FINAL_CHUNK_SIZE,
    ]

    rebuilt = "".join(
        chunks
    ).encode(
        "ascii"
    )

    assert rebuilt == source_bytes

    assert hashlib.sha256(
        rebuilt
    ).hexdigest() == EXPECTED_CORE_SHA256

    return chunks


def _nonce_gate(
    client: Any,
    account: Any,
    expected_nonce: int,
) -> tuple[int, int]:
    latest = int(
        client.get_transaction_count(
            account.address,
            "latest",
        )
    )

    pending = int(
        client.get_transaction_count(
            account.address,
            "pending",
        )
    )

    assert latest == expected_nonce
    assert pending == expected_nonce

    return latest, pending


def _wait_finalized(
    client: Any,
    tx_id: Any,
) -> dict[str, Any]:
    receipt = (
        client.wait_for_transaction_receipt(
            transaction_hash=tx_id,
            status=TransactionStatus.FINALIZED,
            interval=3000,
            retries=240,
            full_transaction=True,
        )
    )

    _assert_final_success(
        receipt
    )

    return receipt


def _persist_step_submission(
    evidence_dir: Path,
    *,
    step: int,
    kind: str,
    tx_id: Any,
    expected_nonce: int,
    latest_nonce: int,
    pending_nonce: int,
    extra: dict[str, Any] | None = None,
) -> None:
    payload: dict[str, Any] = {
        "schema": (
            "accord402-bradbury-chunked-core-"
            "step-submission-v1"
        ),
        "submitted_at": (
            datetime.now(
                timezone.utc
            ).isoformat()
        ),
        "step": step,
        "kind": kind,
        "expected_eoa_nonce": expected_nonce,
        "observed_latest_nonce": latest_nonce,
        "observed_pending_nonce": pending_nonce,
        "transaction_id": _hex_text(
            tx_id
        ),
    }

    if extra:
        payload.update(extra)

    _atomic_json(
        evidence_dir
        / (
            f"step-{step:02d}-"
            f"{kind}-submission.json"
        ),
        payload,
    )


def _persist_step_receipt(
    evidence_dir: Path,
    *,
    step: int,
    kind: str,
    receipt: dict[str, Any],
) -> None:
    _atomic_json(
        evidence_dir
        / (
            f"step-{step:02d}-"
            f"{kind}-finalized-receipt.json"
        ),
        receipt,
    )


def _wait_for_one_triggered_child(
    client: Any,
    trigger_tx_id: Any,
) -> str:
    last: list[Any] = []

    for _ in range(120):
        last = list(
            client.get_triggered_transaction_ids(
                trigger_tx_id
            )
        )

        if len(last) == 1:
            return _hex_text(
                last[0]
            )

        assert len(last) <= 1, last

        time.sleep(3)

    raise AssertionError(
        "exactly one triggered child transaction "
        f"did not materialize; last={last!r}"
    )


def test_chunked_core_deploys_exact_child_finalized() -> None:
    assert (
        os.environ.get(
            "ACCORD402_BRADBURY_CHUNKED_CORE_WRITE_AUTHORIZED"
        )
        == "YES"
    )

    assert (
        _required_env(
            "ACCORD402_BRADBURY_NETWORK"
        )
        == EXPECTED_NETWORK
    )

    assert int(
        _required_env(
            "ACCORD402_BRADBURY_CHAIN_ID"
        )
    ) == EXPECTED_CHAIN_ID

    assert (
        _required_env(
            "ACCORD402_BRADBURY_RPC"
        )
        == EXPECTED_RPC
    )

    authorized_core_sha = (
        _required_env(
            "ACCORD402_AUTHORIZED_CORE_SHA256"
        )
    )

    assert (
        authorized_core_sha
        == EXPECTED_CORE_SHA256
    )

    authorized_factory_sha = (
        _required_env(
            "ACCORD402_AUTHORIZED_FACTORY_SHA256"
        )
    )

    release_commit = (
        _required_env(
            "ACCORD402_AUTHORIZED_RELEASE_COMMIT"
        )
    )

    settlement_vault = (
        _required_env(
            "ACCORD402_BRADBURY_SETTLEMENT_VAULT_ADDRESS"
        )
    )

    authorized_worker = (
        _required_env(
            "ACCORD402_AUTHORIZED_CORE_WORKER_ADDRESS"
        )
    )

    start_nonce = int(
        _required_env(
            "ACCORD402_AUTHORIZED_BATCH_START_NONCE"
        )
    )

    authorized_write_count = int(
        _required_env(
            "ACCORD402_AUTHORIZED_EOA_WRITE_COUNT"
        )
    )

    assert (
        authorized_write_count
        == EXPECTED_EOA_WRITE_COUNT
    )

    evidence_dir = Path(
        _required_env(
            "ACCORD402_BRADBURY_CORE_EVIDENCE_DIR"
        )
    ).resolve()

    core_bytes = CORE.read_bytes()

    assert len(
        core_bytes
    ) == EXPECTED_CORE_BYTES

    core_sha = hashlib.sha256(
        core_bytes
    ).hexdigest()

    assert (
        core_sha
        == EXPECTED_CORE_SHA256
    )

    chunks = _split_core(
        core_bytes
    )

    chunk_manifest = [
        {
            "index": index,
            "byte_length": len(
                chunk.encode(
                    "ascii"
                )
            ),
            "sha256": hashlib.sha256(
                chunk.encode(
                    "ascii"
                )
            ).hexdigest(),
        }
        for index, chunk
        in enumerate(chunks)
    ]

    _atomic_json(
        evidence_dir
        / "exact-core-chunk-plan.json",
        {
            "schema": (
                "accord402-bradbury-chunked-core-"
                "plan-v1"
            ),
            "release_commit": release_commit,
            "core_source_path": (
                "contracts/accord402.py"
            ),
            "core_source_sha256": core_sha,
            "core_source_bytes": len(
                core_bytes
            ),
            "chunk_size": CHUNK_SIZE,
            "chunk_count": CHUNK_COUNT,
            "chunks": chunk_manifest,
            "eoa_write_count": (
                EXPECTED_EOA_WRITE_COUNT
            ),
            "batch_start_nonce": (
                start_nonce
            ),
            "batch_end_nonce": (
                start_nonce
                + EXPECTED_EOA_WRITE_COUNT
                - 1
            ),
            "settlement_vault_address": (
                settlement_vault
            ),
        },
    )

    deployer_factory = (
        get_contract_factory(
            contract_file_path=(
                "accord402_core_chunk_deployer.py"
            )
        )
    )

    factory_sha = hashlib.sha256(
        deployer_factory.contract_code.encode(
            "utf-8"
        )
    ).hexdigest()

    assert (
        factory_sha
        == authorized_factory_sha
    )

    client = get_gl_client()
    account = get_default_account()

    assert int(
        client.chain.id
    ) == EXPECTED_CHAIN_ID

    assert (
        account.address.lower()
        == authorized_worker.lower()
    )

    #
    # STEP 1 — factory deploy, nonce N.
    #
    latest, pending = _nonce_gate(
        client,
        account,
        start_nonce,
    )

    factory_tx = client.deploy_contract(
        code=deployer_factory.contract_code,
        account=account,
        args=[
            settlement_vault
        ],
        leader_only=False,
    )

    _persist_step_submission(
        evidence_dir,
        step=1,
        kind="factory-deploy",
        tx_id=factory_tx,
        expected_nonce=start_nonce,
        latest_nonce=latest,
        pending_nonce=pending,
        extra={
            "factory_source_sha256": (
                factory_sha
            ),
            "settlement_vault_address": (
                settlement_vault
            ),
        },
    )

    factory_receipt = _wait_finalized(
        client,
        factory_tx,
    )

    _persist_step_receipt(
        evidence_dir,
        step=1,
        kind="factory-deploy",
        receipt=factory_receipt,
    )

    factory_address = (
        _extract_deployment_address(
            factory_receipt
        )
    )

    #
    # STEPS 2..5 — exact ordered source chunks.
    #
    for index, chunk in enumerate(
        chunks
    ):
        step = index + 2
        expected_nonce = (
            start_nonce
            + index
            + 1
        )

        latest, pending = _nonce_gate(
            client,
            account,
            expected_nonce,
        )

        chunk_tx = client.write_contract(
            address=factory_address,
            function_name="append_chunk",
            account=account,
            args=[
                index,
                chunk,
            ],
            leader_only=False,
        )

        chunk_bytes = chunk.encode(
            "ascii"
        )

        _persist_step_submission(
            evidence_dir,
            step=step,
            kind=f"chunk-{index}",
            tx_id=chunk_tx,
            expected_nonce=expected_nonce,
            latest_nonce=latest,
            pending_nonce=pending,
            extra={
                "factory_address": (
                    factory_address
                ),
                "chunk_index": index,
                "chunk_byte_length": (
                    len(chunk_bytes)
                ),
                "chunk_sha256": (
                    hashlib.sha256(
                        chunk_bytes
                    ).hexdigest()
                ),
            },
        )

        chunk_receipt = _wait_finalized(
            client,
            chunk_tx,
        )

        _persist_step_receipt(
            evidence_dir,
            step=step,
            kind=f"chunk-{index}",
            receipt=chunk_receipt,
        )

    #
    # STEP 6 — trigger exact child deployment, nonce N+5.
    #
    trigger_nonce = (
        start_nonce
        + EXPECTED_EOA_WRITE_COUNT
        - 1
    )

    latest, pending = _nonce_gate(
        client,
        account,
        trigger_nonce,
    )

    trigger_tx = client.write_contract(
        address=factory_address,
        function_name="deploy_core",
        account=account,
        args=[],
        leader_only=False,
    )

    _persist_step_submission(
        evidence_dir,
        step=6,
        kind="deploy-trigger",
        tx_id=trigger_tx,
        expected_nonce=trigger_nonce,
        latest_nonce=latest,
        pending_nonce=pending,
        extra={
            "factory_address": (
                factory_address
            ),
            "core_source_sha256": (
                core_sha
            ),
        },
    )

    trigger_receipt = _wait_finalized(
        client,
        trigger_tx,
    )

    _persist_step_receipt(
        evidence_dir,
        step=6,
        kind="deploy-trigger",
        receipt=trigger_receipt,
    )

    #
    # Child creation is protocol-triggered after trigger finalization.
    # From here onward all operations are read-only.
    #
    child_tx_id = (
        _wait_for_one_triggered_child(
            client,
            trigger_tx,
        )
    )

    _atomic_json(
        evidence_dir
        / "child-deployment-identity.json",
        {
            "schema": (
                "accord402-bradbury-core-child-"
                "identity-v1"
            ),
            "trigger_transaction_id": (
                _hex_text(
                    trigger_tx
                )
            ),
            "child_transaction_id": (
                child_tx_id
            ),
        },
    )

    child_receipt = _wait_finalized(
        client,
        child_tx_id,
    )

    _atomic_json(
        evidence_dir
        / "child-deployment-finalized-receipt.json",
        child_receipt,
    )

    decoded = child_receipt.get(
        "tx_data_decoded"
    )

    assert isinstance(
        decoded,
        dict,
    ), child_receipt

    assert (
        decoded.get("type")
        == "deploy"
    ), decoded

    code_hex = decoded.get(
        "code"
    )

    assert isinstance(
        code_hex,
        str,
    ), decoded

    child_code = Web3.to_bytes(
        hexstr=code_hex
    )

    child_code_sha = hashlib.sha256(
        child_code
    ).hexdigest()

    assert child_code == core_bytes
    assert child_code_sha == core_sha

    constructor_args = decoded.get(
        "constructor_args"
    )

    assert (
        json.dumps(
            constructor_args,
            sort_keys=True,
            default=str,
        ).lower()
        ==
        json.dumps(
            {
                "args": [
                    settlement_vault
                ]
            },
            sort_keys=True,
        ).lower()
    ), constructor_args

    child_address = (
        _extract_deployment_address(
            child_receipt
        )
    )

    final_latest = int(
        client.get_transaction_count(
            account.address,
            "latest",
        )
    )

    final_pending = int(
        client.get_transaction_count(
            account.address,
            "pending",
        )
    )

    expected_final_nonce = (
        start_nonce
        + EXPECTED_EOA_WRITE_COUNT
    )

    assert (
        final_latest
        == expected_final_nonce
    )

    assert (
        final_pending
        == expected_final_nonce
    )

    _atomic_json(
        evidence_dir
        / "deployment-result.json",
        {
            "schema": (
                "accord402-bradbury-chunked-core-"
                "deployment-result-v1"
            ),
            "result": "PASS",
            "network": EXPECTED_NETWORK,
            "chain_id": EXPECTED_CHAIN_ID,
            "rpc": EXPECTED_RPC,
            "release_commit": (
                release_commit
            ),
            "core_source_path": (
                "contracts/accord402.py"
            ),
            "core_source_sha256": (
                core_sha
            ),
            "core_source_bytes": (
                len(core_bytes)
            ),
            "factory_source_sha256": (
                factory_sha
            ),
            "factory_address": (
                factory_address
            ),
            "settlement_vault_address": (
                settlement_vault
            ),
            "sender_address": (
                account.address
            ),
            "batch_start_nonce": (
                start_nonce
            ),
            "authorized_eoa_write_count": (
                EXPECTED_EOA_WRITE_COUNT
            ),
            "batch_final_nonce": (
                expected_final_nonce
            ),
            "trigger_transaction_id": (
                _hex_text(
                    trigger_tx
                )
            ),
            "child_transaction_id": (
                child_tx_id
            ),
            "child_contract_address": (
                child_address
            ),
            "child_source_sha256": (
                child_code_sha
            ),
            "child_finalized_status": 7,
            "child_execution_result": 1,
            "child_execution_result_name": (
                "FINISHED_WITH_RETURN"
            ),
            "child_execution_success": True,
        },
    )
