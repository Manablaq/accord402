# Regression coverage for Bradbury / Consensus v0.6 deployment receipts.

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


def test_v06_null_decoded_uses_finalized_recipient() -> None:
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
