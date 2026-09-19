from __future__ import annotations

import ast
import hashlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

CORE = ROOT / "contracts" / "accord402.py"

DEPLOYER = (
    ROOT
    / "contracts"
    / "accord402_core_chunk_deployer.py"
)

INTEGRATION = (
    ROOT
    / "tests"
    / "integration"
    / "test_accord402_core_bradbury_runtime.py"
)

RUNNER = (
    ROOT
    / "scripts"
    / "run_bradbury_core_runtime_integration.sh"
)

EXPECTED_CORE_SHA = (
    "60ac857d566e49ae912a384c7ce0a11da3bc3201d7349de3fe24bee0cd095692"
)

EXPECTED_CORE_BYTES = 51757
EXPECTED_CHUNK_SIZE = 14336
EXPECTED_CHUNK_COUNT = 4
EXPECTED_FINAL_CHUNK = 8749


def test_exact_core_chunk_partition_is_byte_preserving() -> None:
    source = CORE.read_bytes()

    assert len(source) == EXPECTED_CORE_BYTES

    assert hashlib.sha256(
        source
    ).hexdigest() == EXPECTED_CORE_SHA

    text = source.decode(
        "ascii",
        errors="strict",
    )

    chunks = [
        text[
            offset:
            offset + EXPECTED_CHUNK_SIZE
        ].encode(
            "ascii"
        )
        for offset in range(
            0,
            len(text),
            EXPECTED_CHUNK_SIZE,
        )
    ]

    assert len(
        chunks
    ) == EXPECTED_CHUNK_COUNT

    assert [
        len(chunk)
        for chunk in chunks
    ] == [
        EXPECTED_CHUNK_SIZE,
        EXPECTED_CHUNK_SIZE,
        EXPECTED_CHUNK_SIZE,
        EXPECTED_FINAL_CHUNK,
    ]

    assert b"".join(
        chunks
    ) == source


def test_deployer_is_exact_source_bound_and_finalized_only() -> None:
    source = DEPLOYER.read_text(
        encoding="utf-8"
    )

    tree = ast.parse(source)

    deploy_calls = [
        node
        for node in ast.walk(tree)
        if isinstance(
            node,
            ast.Call,
        )
        and isinstance(
            node.func,
            ast.Attribute,
        )
        and isinstance(
            node.func.value,
            ast.Name,
        )
        and node.func.value.id == "gl"
        and node.func.attr == "deploy_contract"
    ]

    assert len(
        deploy_calls
    ) == 1

    call = deploy_calls[0]

    keywords = {
        item.arg: item.value
        for item in call.keywords
    }

    assert (
        isinstance(
            keywords["on"],
            ast.Constant,
        )
        and keywords["on"].value
        == "finalized"
    )

    assert ast.unparse(
        keywords["args"]
    ) == "[self.settlement_vault]"

    assert ast.unparse(
        keywords["salt_nonce"]
    ) == "u256(1)"

    assert (
        f'CORE_SOURCE_SHA256 = "{EXPECTED_CORE_SHA}"'
        in source
    )

    assert (
        f"CORE_SOURCE_BYTES = {EXPECTED_CORE_BYTES}"
        in source
    )

    assert (
        f"CHUNK_SIZE = {EXPECTED_CHUNK_SIZE}"
        in source
    )

    assert (
        f"CHUNK_COUNT = {EXPECTED_CHUNK_COUNT}"
        in source
    )

    assert (
        f"FINAL_CHUNK_SIZE = {EXPECTED_FINAL_CHUNK}"
        in source
    )

    for token in (
        "OWNER_ONLY",
        "DEPLOYER_SEALED",
        "CHUNK_INDEX_MISMATCH",
        "TOO_MANY_CHUNKS",
        "CHUNK_SIZE_MISMATCH",
        "CHUNKS_INCOMPLETE",
        "SOURCE_LENGTH_MISMATCH",
        "SOURCE_SHA256_MISMATCH",
    ):
        assert token in source


def test_live_harness_has_exact_bounded_write_shape() -> None:
    source = INTEGRATION.read_text(
        encoding="utf-8"
    )

    tree = ast.parse(source)

    deploy_calls = [
        node
        for node in ast.walk(tree)
        if isinstance(
            node,
            ast.Call,
        )
        and isinstance(
            node.func,
            ast.Attribute,
        )
        and node.func.attr == "deploy_contract"
    ]

    write_calls = [
        node
        for node in ast.walk(tree)
        if isinstance(
            node,
            ast.Call,
        )
        and isinstance(
            node.func,
            ast.Attribute,
        )
        and node.func.attr == "write_contract"
    ]

    triggered_reads = [
        node
        for node in ast.walk(tree)
        if isinstance(
            node,
            ast.Call,
        )
        and isinstance(
            node.func,
            ast.Attribute,
        )
        and node.func.attr == "get_triggered_transaction_ids"
    ]

    assert len(
        deploy_calls
    ) == 1

    assert len(
        write_calls
    ) == 2

    assert len(
        triggered_reads
    ) == 1

    assert (
        "EXPECTED_EOA_WRITE_COUNT = 6"
        in source
    )

    assert (
        'function_name="append_chunk"'
        in source
    )

    assert (
        'function_name="deploy_core"'
        in source
    )

    assert (
        "child_code == core_bytes"
        in source
    )

    assert (
        "child_code_sha == core_sha"
        in source
    )

    assert (
        "exactly one triggered child transaction"
        in source
    )

    assert (
        "ACCORD402_BRADBURY_CHUNKED_CORE_WRITE_AUTHORIZED"
        in source
    )


def test_runner_consumes_distinct_six_write_batch_authorization() -> None:
    source = RUNNER.read_text(
        encoding="utf-8"
    )

    required = (
        "ACCORD402_BRADBURY_CHUNKED_CORE_WRITE_AUTHORIZED",
        "ACCORD402_AUTHORIZED_FACTORY_SHA256",
        "ACCORD402_AUTHORIZED_BATCH_START_NONCE",
        "ACCORD402_AUTHORIZED_EOA_WRITE_COUNT",
        "ACCORD402_BRADBURY_CHUNKED_CORE_WRITE_AUTHORIZATION_ID",
        "EXPECTED_EOA_WRITE_COUNT=\"6\"",
        "IMMEDIATE_BATCH_NONCE_BINDING=PASS",
        "CHUNKED_CORE_BATCH_AUTHORIZATION_CONSUMED=YES",
        "THIS_BATCH_RUNNER_MUST_NEVER_BE_RERUN=YES",
        "RETRY_OR_REBROADCAST_AUTHORIZED=NO",
    )

    for token in required:
        assert token in source

    assert (
        source.index(
            "IMMEDIATE_BATCH_NONCE_BINDING=PASS"
        )
        <
        source.index(
            "CHUNKED_CORE_BATCH_AUTHORIZATION_CONSUMED=YES"
        )
    )
