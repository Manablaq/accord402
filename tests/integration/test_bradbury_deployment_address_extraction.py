# Regression coverage for Bradbury deployment-receipt address extraction.

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
RUNTIME_TEST = ROOT / "tests" / "integration" / "test_accord402_adjudicator_bradbury_runtime.py"


def _load_runtime_module():
    spec = importlib.util.spec_from_file_location(
        "accord402_bradbury_runtime_test_module",
        RUNTIME_TEST,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_bradbury_null_decoded_uses_finalized_recipient() -> None:
    module = _load_runtime_module()
    recipient = "0x55BecA2ba6D2feeFFaE50c298315b0A75dc5C69b"
    assert module._extract_deployment_address(
        {"tx_data_decoded": None, "data": None, "recipient": recipient}
    ) == recipient


def test_decoded_contract_address_is_preferred_when_present() -> None:
    module = _load_runtime_module()
    decoded = "0x1111111111111111111111111111111111111111"
    recipient = "0x2222222222222222222222222222222222222222"
    assert module._extract_deployment_address(
        {"tx_data_decoded": {"contract_address": decoded}, "recipient": recipient}
    ) == decoded


def test_camel_case_decoded_contract_address_is_supported() -> None:
    module = _load_runtime_module()
    decoded = "0x3333333333333333333333333333333333333333"
    assert module._extract_deployment_address(
        {
            "tx_data_decoded": {"contractAddress": decoded},
            "recipient": "0x4444444444444444444444444444444444444444",
        }
    ) == decoded


def test_missing_or_invalid_deployment_address_is_rejected() -> None:
    module = _load_runtime_module()
    with pytest.raises(AssertionError):
        module._extract_deployment_address(
            {"tx_data_decoded": None, "data": None, "recipient": None}
        )


class _FakeProcessedEvent:
    def __init__(self, rows):
        self._rows = rows

    def process_receipt(self, receipt, errors=None):
        return list(self._rows)


class _FakeEvents:
    def __init__(self, new_rows, created_rows):
        self._new_rows = new_rows
        self._created_rows = created_rows

    def NewTransaction(self):
        return _FakeProcessedEvent(self._new_rows)

    def CreatedTransaction(self):
        return _FakeProcessedEvent(self._created_rows)


class _FakeConsensus:
    def __init__(self, new_rows, created_rows):
        self.events = _FakeEvents(
            new_rows,
            created_rows,
        )


class _FakeEth:
    def __init__(
        self,
        *,
        tx,
        receipt,
        new_rows,
        created_rows,
    ):
        self._tx = tx
        self._receipt = receipt
        self._consensus = _FakeConsensus(
            new_rows,
            created_rows,
        )

    def contract(self, address=None, abi=None):
        return self._consensus

    def get_block(
        self,
        block_number,
        full_transactions=False,
    ):
        if block_number == self._receipt["blockNumber"]:
            return {"transactions": [self._tx]}

        return {"transactions": []}

    def get_transaction_receipt(self, tx_hash):
        assert tx_hash == self._tx["hash"]

        return self._receipt


class _FakeWeb3:
    def __init__(self, eth):
        self.eth = eth


def test_outer_submission_binds_new_transaction_recipient() -> None:
    module = _load_runtime_module()

    sender = module.EXPECTED_SENDER
    tx_id = "0x" + "ab" * 32
    outer_hash = "0x" + "cd" * 32
    recipient = "0x1111111111111111111111111111111111111111"
    activator = "0x2222222222222222222222222222222222222222"

    tx = {
        "from": sender,
        "nonce": 1303,
        "to": module.EXPECTED_CONSENSUS_MAIN,
        "hash": outer_hash,
    }

    receipt = {
        "status": 1,
        "blockNumber": 500,
    }

    fake = _FakeWeb3(
        _FakeEth(
            tx=tx,
            receipt=receipt,
            new_rows=[
                {
                    "args": {
                        "txId": tx_id,
                        "recipient": recipient,
                        "activator": activator,
                    }
                }
            ],
            created_rows=[],
        )
    )

    result = module._find_outer_submission(
        fake,
        sender=sender,
        nonce=1303,
        from_block=499,
        to_block=501,
        expected_tx_id=tx_id,
    )

    assert result["outer_evm_tx_hash"] == outer_hash
    assert result["outer_evm_block_number"] == 500
    assert result["outer_evm_receipt_status"] == 1
    assert result["creation_event_type"] == "NewTransaction"
    assert result["transaction_id"] == tx_id

    assert (
        result["provisional_contract_address"]
        == recipient
    )

    assert result["event_activator"] == activator


def test_outer_submission_rejects_created_transaction_without_address() -> None:
    module = _load_runtime_module()

    sender = module.EXPECTED_SENDER
    tx_id = "0x" + "ef" * 32
    outer_hash = "0x" + "12" * 32

    tx = {
        "from": sender,
        "nonce": 1303,
        "to": module.EXPECTED_CONSENSUS_MAIN,
        "hash": outer_hash,
    }

    receipt = {
        "status": 1,
        "blockNumber": 600,
    }

    fake = _FakeWeb3(
        _FakeEth(
            tx=tx,
            receipt=receipt,
            new_rows=[],
            created_rows=[
                {
                    "args": {
                        "txId": tx_id,
                        "txSlot": 9,
                    }
                }
            ],
        )
    )

    with pytest.raises(
        AssertionError,
        match="dependent Core must not be submitted",
    ):
        module._find_outer_submission(
            fake,
            sender=sender,
            nonce=1303,
            from_block=599,
            to_block=601,
            expected_tx_id=tx_id,
        )
