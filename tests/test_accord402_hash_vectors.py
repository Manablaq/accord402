from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import ast
import hashlib

import pytest


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts" / "accord402.py"

EXPECTED_CONTRACT_SHA256 = "60ac857d566e49ae912a384c7ce0a11da3bc3201d7349de3fe24bee0cd095692"

SERVICE_DOMAIN = b"ACCORD402:SERVICE_SPEC:V1\x00"
POLICY_DOMAIN = b"ACCORD402:EVIDENCE_POLICY:V1\x00"
DELIVERY_DOMAIN = b"ACCORD402:DELIVERY:V1\x00"
EVIDENCE_DOMAIN = b"ACCORD402:ACTIVE_EVIDENCE_SET:V1\x00"

EVIDENCE_POLICY_VERSION = 1
REPAIR_POLICY_VERSION = 1
ADJUDICATION_CRITERIA_VERSION = 1
SETTLEMENT_RULE_VERSION = 1

MAX_U32 = (1 << 32) - 1
MAX_U64 = (1 << 64) - 1
MAX_U256 = (1 << 256) - 1

SERVICE_HASH = "24ed8bf8f78af3c9cd79a45c40cc568b8d40c43297773ebc1693b678acfa74eb"
POLICY_HASH = "ce9a1834a6e7e10dae1eb402d05b2388505010c252716afaba1148cbf4e068bb"
DELIVERY_HASH = "de39b250f0060babd6fcfd6d6a845ed062171a843f1f361eb9a300102146123a"
ACTIVE_HASH = "6dc04221bb31250fd0f38f48500d35591f2d0f022b3feaf9a1c446af215cef55"


class ContractReject(Exception):
    pass


class MockAddress:
    def __init__(self, raw: bytes):
        self.as_bytes = raw


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _find_function(tree: ast.Module, name: str) -> ast.FunctionDef:
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError(f"contract helper missing: {name}")


def _contract_runtime() -> dict[str, object]:
    text = CONTRACT.read_text(encoding="utf-8")
    tree = ast.parse(text)
    names = [
        "_utf8",
        "_int_u32",
        "_int_u64",
        "_u32_bytes",
        "_u64_bytes",
        "_str_bytes",
        "_is_lower_hex64",
        "_hex32",
        "_bool_byte",
        "_count_bytes",
        "_sha256_hex",
        "_criterion_bytes",
        "_authority_bytes",
        "_evidence_bytes",
        "_service_hash",
        "_policy_hash",
        "_delivery_hash",
        "_active_evidence_hash",
    ]
    module = ast.Module(
        body=[_find_function(tree, name) for name in names],
        type_ignores=[],
    )
    ast.fix_missing_locations(module)

    def fail(code: str):
        raise ContractReject(code)

    runtime: dict[str, object] = {
        "_A": fail,
        "hashlib": hashlib,
        "MAX_U32": MAX_U32,
        "MAX_U64": MAX_U64,
        "SERVICE_DOMAIN": SERVICE_DOMAIN,
        "POLICY_DOMAIN": POLICY_DOMAIN,
        "DELIVERY_DOMAIN": DELIVERY_DOMAIN,
        "EVIDENCE_DOMAIN": EVIDENCE_DOMAIN,
        "EVIDENCE_POLICY_VERSION": EVIDENCE_POLICY_VERSION,
        "REPAIR_POLICY_VERSION": REPAIR_POLICY_VERSION,
        "ADJUDICATION_CRITERIA_VERSION": ADJUDICATION_CRITERIA_VERSION,
    }
    exec(compile(module, "<accord402-hash-helpers>", "exec"), runtime)
    return runtime


@pytest.fixture(scope="module")
def contract():
    assert _sha256(CONTRACT) == EXPECTED_CONTRACT_SHA256
    return _contract_runtime()


# Independent normative reference codec. These functions do not call contract helpers.
def ref_u32(x: int) -> bytes:
    if type(x) is not int or x < 0 or x > MAX_U32:
        raise ValueError("u32")
    return x.to_bytes(4, "big")


def ref_u64(x: int) -> bytes:
    if type(x) is not int or x < 0 or x > MAX_U64:
        raise ValueError("u64")
    return x.to_bytes(8, "big")


def ref_u256(x: int) -> bytes:
    if type(x) is not int or x < 0 or x > MAX_U256:
        raise ValueError("u256")
    return x.to_bytes(32, "big")


def ref_str(s: str) -> bytes:
    if type(s) is not str:
        raise ValueError("str")
    raw = s.encode("utf-8", errors="strict")
    return ref_u32(len(raw)) + raw


def ref_hex32(h: str) -> bytes:
    if (
        type(h) is not str
        or len(h) != 64
        or any(ch not in "0123456789abcdef" for ch in h)
    ):
        raise ValueError("hex32")
    return bytes.fromhex(h)


def ref_bool(value: bool) -> bytes:
    if type(value) is not bool:
        raise ValueError("bool")
    return b"\x01" if value else b"\x00"


def ref_criterion(c) -> bytes:
    return ref_str(c.criterion_id) + ref_str(c.criterion_text)


def ref_authority(a) -> bytes:
    return (
        ref_str(a.authority_id)
        + ref_u32(a.authority_revision)
        + ref_str(a.role)
        + ref_str(a.identity_kind)
        + ref_str(a.identity_value)
        + ref_str(a.canonical_origin)
    )


def ref_evidence(e) -> bytes:
    return (
        ref_u64(e.covenant_id)
        + ref_u32(e.generation)
        + ref_str(e.evidence_id)
        + ref_str(e.authority_id)
        + ref_u32(e.authority_revision)
        + ref_str(e.subject)
        + ref_str(e.kind)
        + ref_str(e.source_kind)
        + ref_str(e.canonical_source)
        + ref_str(e.immutable_version_or_record_id)
        + ref_u64(e.published_at)
        + ref_u64(e.observed_at)
        + ref_u64(e.expires_at)
        + ref_hex32(e.content_digest)
        + ref_bool(e.is_primary)
        + ref_str(e.replaces_evidence_id)
    )


def ref_service_hash(service_spec: str, criteria) -> str:
    preimage = (
        SERVICE_DOMAIN
        + ref_str(service_spec)
        + ref_u32(ADJUDICATION_CRITERIA_VERSION)
        + ref_u32(len(criteria))
        + b"".join(ref_criterion(c) for c in criteria)
    )
    return hashlib.sha256(preimage).hexdigest()


def ref_policy_hash(
    max_evidence_age: int,
    required_corroboration_count: int,
    repair_allowed_field_mask: int,
    replay_scope: str,
    authorities,
) -> str:
    preimage = (
        POLICY_DOMAIN
        + ref_u32(EVIDENCE_POLICY_VERSION)
        + ref_u64(max_evidence_age)
        + ref_u32(required_corroboration_count)
        + ref_u32(REPAIR_POLICY_VERSION)
        + ref_u32(repair_allowed_field_mask)
        + ref_str(replay_scope)
        + ref_u32(ADJUDICATION_CRITERIA_VERSION)
        + ref_u32(len(authorities))
        + b"".join(ref_authority(a) for a in authorities)
    )
    return hashlib.sha256(preimage).hexdigest()


def ref_delivery_hash(
    covenant_id: int,
    provider_raw: bytes,
    service_hash: str,
    delivered_at: int,
    delivery_payload: str,
) -> str:
    if len(provider_raw) != 20:
        raise ValueError("address")
    preimage = (
        DELIVERY_DOMAIN
        + ref_u64(covenant_id)
        + provider_raw
        + ref_hex32(service_hash)
        + ref_u64(delivered_at)
        + ref_str(delivery_payload)
    )
    return hashlib.sha256(preimage).hexdigest()


def ref_active_hash(
    covenant_id: int,
    delivery_hash: str,
    policy_hash: str,
    records,
) -> str:
    for record in records:
        if record.covenant_id != covenant_id:
            raise ValueError("foreign evidence")
    preimage = (
        EVIDENCE_DOMAIN
        + ref_u64(covenant_id)
        + ref_hex32(delivery_hash)
        + ref_hex32(policy_hash)
        + ref_u32(len(records))
        + b"".join(ref_evidence(r) for r in records)
    )
    return hashlib.sha256(preimage).hexdigest()


def vector_criteria():
    return [
        SimpleNamespace(
            criterion_id="accuracy",
            criterion_text="Current pricing is correct",
        ),
        SimpleNamespace(
            criterion_id="freshness",
            criterion_text="Evidence is recent",
        ),
    ]


def vector_authorities():
    return [
        SimpleNamespace(
            authority_id="primary",
            authority_revision=1,
            role="PRIMARY",
            identity_kind="DOMAIN",
            identity_value="example.com",
            canonical_origin="https://example.com",
        ),
        SimpleNamespace(
            authority_id="corroborator",
            authority_revision=1,
            role="CORROBORATOR",
            identity_kind="DOMAIN",
            identity_value="example.org",
            canonical_origin="https://example.org",
        ),
    ]


def vector_record(**changes):
    data = dict(
        covenant_id=7,
        generation=0,
        evidence_id="ev-1",
        authority_id="primary",
        authority_revision=1,
        subject="pricing",
        kind="PAGE",
        source_kind="LIVE",
        canonical_source="https://example.com/pricing",
        immutable_version_or_record_id="v1",
        published_at=1699999900,
        observed_at=1699999950,
        expires_at=1700001000,
        content_digest="0" * 64,
        is_primary=True,
        replaces_evidence_id="",
    )
    data.update(changes)
    return SimpleNamespace(**data)


def test_primitive_binary_codec_vectors(contract):
    assert contract["_u32_bytes"](0x01020304) == b"\x01\x02\x03\x04"
    assert contract["_u64_bytes"](0x0102030405060708) == bytes.fromhex(
        "0102030405060708"
    )
    assert contract["_str_bytes"]("é") == b"\x00\x00\x00\x02\xc3\xa9"
    assert contract["_bool_byte"](False) == b"\x00"
    assert contract["_bool_byte"](True) == b"\x01"
    assert contract["_count_bytes"](2) == b"\x00\x00\x00\x02"
    assert contract["_hex32"]("ab" * 32) == bytes.fromhex("ab" * 32)
    assert ref_u256(1) == b"\x00" * 31 + b"\x01"


@pytest.mark.parametrize("value", [-1, MAX_U32 + 1])
def test_u32_range_rejection(contract, value):
    with pytest.raises(ContractReject):
        contract["_u32_bytes"](value)


@pytest.mark.parametrize("value", [-1, MAX_U64 + 1])
def test_u64_range_rejection(contract, value):
    with pytest.raises(ContractReject):
        contract["_u64_bytes"](value)


@pytest.mark.parametrize("digest", ["A" * 64, "0" * 63, "g" * 64, "0x" + "0" * 64])
def test_hex32_strict_lowercase_exact_length(contract, digest):
    with pytest.raises(ContractReject):
        contract["_hex32"](digest)


def test_service_reference_vector_matches_contract_and_independent_reference(contract):
    criteria = vector_criteria()
    independent = ref_service_hash("report-v1", criteria)
    implementation = contract["_service_hash"]("report-v1", criteria)
    assert independent == SERVICE_HASH
    assert implementation == SERVICE_HASH
    assert implementation == independent


def test_policy_reference_vector_matches_contract_and_independent_reference(contract):
    authorities = vector_authorities()
    independent = ref_policy_hash(1800, 1, 255, "COVENANT", authorities)
    implementation = contract["_policy_hash"](
        1800, 1, 255, "COVENANT", authorities
    )
    assert independent == POLICY_HASH
    assert implementation == POLICY_HASH
    assert implementation == independent


def test_delivery_reference_vector_matches_contract_and_independent_reference(contract):
    raw = b"\x11" * 20
    independent = ref_delivery_hash(7, raw, SERVICE_HASH, 1700000000, "done")
    implementation = contract["_delivery_hash"](
        7, MockAddress(raw), SERVICE_HASH, 1700000000, "done"
    )
    assert independent == DELIVERY_HASH
    assert implementation == DELIVERY_HASH
    assert implementation == independent


def test_active_evidence_reference_vector_matches_contract_and_independent_reference(contract):
    records = [vector_record()]
    independent = ref_active_hash(7, DELIVERY_HASH, POLICY_HASH, records)
    implementation = contract["_active_evidence_hash"](
        7, DELIVERY_HASH, POLICY_HASH, records
    )
    assert independent == ACTIVE_HASH
    assert implementation == ACTIVE_HASH
    assert implementation == independent


def test_criteria_order_is_consequential(contract):
    criteria = vector_criteria()
    forward = contract["_service_hash"]("report-v1", criteria)
    reverse = contract["_service_hash"]("report-v1", list(reversed(criteria)))
    assert forward == SERVICE_HASH
    assert reverse != forward
    assert ref_service_hash("report-v1", list(reversed(criteria))) == reverse


def test_authority_order_is_consequential(contract):
    authorities = vector_authorities()
    forward = contract["_policy_hash"](1800, 1, 255, "COVENANT", authorities)
    reverse = contract["_policy_hash"](
        1800, 1, 255, "COVENANT", list(reversed(authorities))
    )
    assert forward == POLICY_HASH
    assert reverse != forward
    assert (
        ref_policy_hash(1800, 1, 255, "COVENANT", list(reversed(authorities)))
        == reverse
    )


def test_active_evidence_order_is_consequential(contract):
    first = vector_record(evidence_id="ev-1", content_digest="0" * 64)
    second = vector_record(
        evidence_id="ev-2",
        authority_id="corroborator",
        canonical_source="https://example.org/pricing",
        immutable_version_or_record_id="v2",
        content_digest="1" * 64,
        is_primary=False,
    )
    forward_records = [first, second]
    reverse_records = [second, first]

    forward = contract["_active_evidence_hash"](
        7, DELIVERY_HASH, POLICY_HASH, forward_records
    )
    reverse = contract["_active_evidence_hash"](
        7, DELIVERY_HASH, POLICY_HASH, reverse_records
    )
    assert forward != reverse
    assert ref_active_hash(7, DELIVERY_HASH, POLICY_HASH, forward_records) == forward
    assert ref_active_hash(7, DELIVERY_HASH, POLICY_HASH, reverse_records) == reverse


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("canonical_source", "https://example.com/pricing-v2"),
        ("immutable_version_or_record_id", "v2"),
        ("content_digest", "1" * 64),
        ("observed_at", 1699999951),
        ("is_primary", False),
    ],
)
def test_active_hash_changes_when_consequential_record_field_changes(contract, field, value):
    original = [vector_record()]
    changed = [vector_record(**{field: value})]
    original_hash = contract["_active_evidence_hash"](
        7, DELIVERY_HASH, POLICY_HASH, original
    )
    changed_hash = contract["_active_evidence_hash"](
        7, DELIVERY_HASH, POLICY_HASH, changed
    )
    assert original_hash == ACTIVE_HASH
    assert changed_hash != original_hash
    assert ref_active_hash(7, DELIVERY_HASH, POLICY_HASH, changed) == changed_hash


def test_domain_separation_changes_digest():
    criteria = vector_criteria()
    normal = ref_service_hash("report-v1", criteria)
    wrong_preimage = (
        POLICY_DOMAIN
        + ref_str("report-v1")
        + ref_u32(ADJUDICATION_CRITERIA_VERSION)
        + ref_u32(len(criteria))
        + b"".join(ref_criterion(c) for c in criteria)
    )
    assert normal == SERVICE_HASH
    assert hashlib.sha256(wrong_preimage).hexdigest() != normal


def test_delivery_rejects_non_20_byte_address(contract):
    with pytest.raises(ContractReject):
        contract["_delivery_hash"](
            7,
            MockAddress(b"\x11" * 19),
            SERVICE_HASH,
            1700000000,
            "done",
        )
    with pytest.raises(ContractReject):
        contract["_delivery_hash"](
            7,
            MockAddress(b"\x11" * 21),
            SERVICE_HASH,
            1700000000,
            "done",
        )


def test_active_hash_rejects_foreign_evidence_record(contract):
    foreign = [vector_record(covenant_id=8)]
    with pytest.raises(ContractReject):
        contract["_active_evidence_hash"](
            7, DELIVERY_HASH, POLICY_HASH, foreign
        )
    with pytest.raises(ValueError):
        ref_active_hash(7, DELIVERY_HASH, POLICY_HASH, foreign)


def test_hash_outputs_are_lowercase_hex64(contract):
    outputs = [
        contract["_service_hash"]("report-v1", vector_criteria()),
        contract["_policy_hash"](
            1800, 1, 255, "COVENANT", vector_authorities()
        ),
        contract["_delivery_hash"](
            7, MockAddress(b"\x11" * 20), SERVICE_HASH, 1700000000, "done"
        ),
        contract["_active_evidence_hash"](
            7, DELIVERY_HASH, POLICY_HASH, [vector_record()]
        ),
    ]
    for digest in outputs:
        assert len(digest) == 64
        assert digest == digest.lower()
        assert all(ch in "0123456789abcdef" for ch in digest)
