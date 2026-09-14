from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import hashlib
import re
import sys

import pytest


ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "contracts" / "accord402.py"
EXPECTED_CONTRACT_SHA256 = "d6f52562d0686ff213eb33773f201441f50f15a15190533306afd0a91ccf50c4"

BASE = 1_700_000_000
PRINCIPAL = 1_000_000

PRIMARY_URL = "https://example.com/evidence/v1/report"
CORR_URL = "https://example.org/evidence/v2/report"
PRIMARY_BODY = b'{"authority":"primary","fact":"pricing-current"}'
CORR_BODY = b'{"authority":"corroborator","fact":"pricing-current"}'


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _iso(epoch: int) -> str:
    return (
        datetime.fromtimestamp(epoch, tz=timezone.utc)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _module(contract):
    module_name = type(contract).__module__
    module = sys.modules.get(module_name)
    assert module is not None, f"loaded contract module unavailable: {module_name}"
    return module


def _raw_instance(contract):
    """Return the in-memory contract instance behind the frozen Direct Mode proxy.

    genlayer-test@9c09578... calldata-roundtrips public args but does not
    reconstruct dataclass parameters after decode. Use the raw instance only
    for public methods whose ABI parameter is a structured dataclass/list of
    dataclasses. Primitive-only public methods continue through the proxy.
    """
    try:
        return object.__getattribute__(contract, "_instance")
    except AttributeError:
        return contract


def _structured_call(contract, method_name: str, *args):
    return getattr(_raw_instance(contract), method_name)(*args)


def _as_address(mod, value):
    if hasattr(value, "as_bytes"):
        return value
    return mod.Address(value)


def _address_bytes(value) -> bytes:
    if isinstance(value, bytes):
        return value
    if hasattr(value, "as_bytes"):
        return bytes(value.as_bytes)
    return bytes(value)


def _install_frozen_raw_llm_mock_compat(contract, vm):
    """Preserve raw mocked strings for plain gl.nondet.exec_prompt calls.

    Frozen genlayer-test@9c09578... eagerly json.loads() every mocked string
    before returning it from _handle_llm_request(). Accord402 intentionally
    calls exec_prompt(prompt) without response_format="json" and then performs
    its own strict JSON parsing. The frozen mock adapter therefore changes the
    API type from str to dict and falsely drives REVIEW_RETRY_REQUIRED.

    This compatibility shim changes only the registered-string-mock success
    path. Unmatched mocks, non-string mock responses, live-handler behavior,
    strict-mode behavior, and every other WASI operation remain delegated to
    the exact frozen implementation.
    """
    from gltest.direct import wasi_mock

    current = wasi_mock._handle_llm_request
    if getattr(current, "__accord402_raw_llm_mock_compat__", False):
        return

    def compat(vm_ctx, data):
        prompt = data.get("prompt", "") if isinstance(data, dict) else ""
        response = vm_ctx._match_llm_mock(prompt)

        if isinstance(response, str):
            # Plain exec_prompt must receive the exact raw model string.
            return {"ok": response}

        # Preserve every other frozen-path behavior exactly.
        return current(vm_ctx, data)

    compat.__accord402_raw_llm_mock_compat__ = True
    compat.__accord402_raw_llm_mock_original__ = current
    wasi_mock._handle_llm_request = compat


def _install_frozen_message_datetime_compat(contract, vm):
    """Synchronize the frozen Direct Mode clock into gl.message_raw.

    genlayer-test@9c09578... updates vm._datetime in vm.warp(), but its
    _refresh_gl_message() refreshes sender/origin/value/chain context without
    updating gl.message_raw["datetime"]. Accord402 intentionally reads the
    transaction timestamp from gl.message_raw["datetime"].

    Patch only this VM instance's refresh hook. Every existing refresh action
    still runs first; then the exact vm._datetime string is copied into the
    already-loaded contract SDK message_raw dict.
    """
    mod = _module(contract)
    original_refresh = vm._refresh_gl_message

    if getattr(original_refresh, "__accord402_datetime_compat__", False):
        return

    def compat_refresh():
        original_refresh()

        raw = getattr(mod.gl, "message_raw", None)
        if not isinstance(raw, dict):
            raise AssertionError(
                "frozen Direct Mode gl.message_raw is unavailable"
            )

        current = getattr(vm, "_datetime", None)
        if not isinstance(current, str) or current == "":
            raise AssertionError(
                "frozen Direct Mode vm._datetime is unavailable"
            )

        raw["datetime"] = current

    compat_refresh.__accord402_datetime_compat__ = True
    compat_refresh.__accord402_datetime_original__ = original_refresh
    vm._refresh_gl_message = compat_refresh

    # Synchronize the current deployment-time value immediately.
    vm._refresh_gl_message()

    raw = getattr(mod.gl, "message_raw", None)
    assert isinstance(raw, dict)
    assert raw.get("datetime") == vm._datetime


def _install_frozen_dynarray_inmem_compat(contract):
    """Patch one frozen-SDK Direct Mode host bug without changing contract logic.

    In the v0.6.0-rc5 stdlib, inmem_allocate(DynArray[T]) successfully builds
    the type descriptor and in-memory instance, then mistakenly falls back to
    typing._GenericAlias.__init__, which raises before the empty DynArray can
    be returned. Real contract code is left untouched.

    This shim applies ONLY to:
      * a fully-instantiated DynArray[...] generic,
      * zero positional initialization arguments,
      * zero keyword initialization arguments,
      * and ONLY when the original helper raises the exact GenericAlias bug.

    Every other storage allocation is delegated to the frozen SDK unchanged.
    """
    mod = _module(contract)
    storage = mod.gl.storage
    original = storage.inmem_allocate

    if getattr(original, "__accord402_direct_dynarray_compat__", False):
        return

    build = getattr(storage, "_storage_build", None)
    inmem_manager = getattr(storage, "InmemManager", None)
    root_slot_id = getattr(storage, "ROOT_SLOT_ID", None)

    assert callable(build), "frozen SDK _storage_build unavailable"
    assert inmem_manager is not None, "frozen SDK InmemManager unavailable"
    assert root_slot_id is not None, "frozen SDK ROOT_SLOT_ID unavailable"

    def compat(t, *init_args, **init_kwargs):
        origin = getattr(t, "__origin__", None)
        origin_name = getattr(origin, "__name__", "")

        if origin_name != "DynArray" or init_args or init_kwargs:
            return original(t, *init_args, **init_kwargs)

        try:
            return original(t)
        except TypeError as exc:
            message = str(exc)
            if (
                "_GenericAlias.__init__()" not in message
                or "required positional argument" not in message
            ):
                raise

            # Exact frozen v0.6.0-rc5 allocator body through instance creation.
            # The only omitted operation is the erroneous GenericAlias.__init__.
            td = build(t, {})
            manager = inmem_manager()
            return td.get(manager.get_store_slot(root_slot_id), 0)

    compat.__accord402_direct_dynarray_compat__ = True
    compat.__accord402_direct_dynarray_original__ = original
    storage.inmem_allocate = compat


class _TransferCapture:
    transfers: list[tuple[object, int]] = []

    def __init__(self, address):
        self.address = address

    def emit_transfer(self, *, value):
        type(self).transfers.append((_address_bytes(self.address), int(value)))


def _install_transfer_capture(contract):
    mod = _module(contract)
    _TransferCapture.transfers = []
    mod._Recipient = _TransferCapture
    return _TransferCapture.transfers


def _deploy(direct_vm, direct_deploy, buyer):
    assert _sha256(CONTRACT) == EXPECTED_CONTRACT_SHA256
    direct_vm.sender = buyer
    direct_vm.value = 0
    direct_vm.warp(_iso(BASE))
    contract = direct_deploy(str(CONTRACT))
    _install_frozen_raw_llm_mock_compat(contract, direct_vm)
    _install_frozen_message_datetime_compat(contract, direct_vm)
    _install_frozen_dynarray_inmem_compat(contract)
    transfers = _install_transfer_capture(contract)
    return contract, _module(contract), transfers


def _criteria(mod):
    return [
        mod.CriterionInput(
            criterion_id="accuracy",
            criterion_text="Current pricing is correct",
        ),
        mod.CriterionInput(
            criterion_id="freshness",
            criterion_text="Evidence is recent",
        ),
    ]


def _bindings(mod):
    return [
        mod.AuthorityBindingInput(
            authority_id="primary",
            authority_revision=1,
            role="PRIMARY",
            identity_kind="DOMAIN",
            identity_value="example.com",
            canonical_origin="https://example.com",
        ),
        mod.AuthorityBindingInput(
            authority_id="corroborator",
            authority_revision=1,
            role="CORROBORATOR",
            identity_kind="DOMAIN",
            identity_value="example.org",
            canonical_origin="https://example.org",
        ),
    ]


def _terms(
    mod,
    provider,
    now: int,
    *,
    principal: int = PRINCIPAL,
    max_evidence_age: int = 1800,
    required_corroboration_count: int = 1,
    max_review_generations: int = 3,
):
    return mod.OpenCovenantInput(
        provider=_as_address(mod, provider),
        principal=principal,
        service_spec="Deliver an accurate and fresh pricing report.",
        acceptance_deadline=now + 3600,
        delivery_deadline=now + 7200,
        challenge_duration=3600,
        absolute_dispute_deadline=now + 20_000,
        evidence_repair_window=600,
        review_retry_window=600,
        max_review_generations=max_review_generations,
        max_evidence_age=max_evidence_age,
        required_corroboration_count=required_corroboration_count,
        repair_allowed_field_mask=255,
        replay_scope="COVENANT",
        criteria=_criteria(mod),
        authority_bindings=_bindings(mod),
    )


def _assert_contract_clock(contract, vm, expected_epoch: int):
    mod = _module(contract)
    raw = getattr(mod.gl, "message_raw", None)
    assert isinstance(raw, dict)
    assert raw.get("datetime") == _iso(expected_epoch)


def _open(
    contract,
    mod,
    vm,
    buyer,
    provider,
    *,
    now: int = BASE,
    principal: int = PRINCIPAL,
    max_evidence_age: int = 1800,
):
    vm.warp(_iso(now))
    _assert_contract_clock(contract, vm, now)
    vm.sender = buyer
    vm.value = principal
    covenant_id = _structured_call(
        contract,
        "open_covenant",
        _terms(
            mod,
            provider,
            now,
            principal=principal,
            max_evidence_age=max_evidence_age,
        ),
    )
    vm.value = 0
    return int(covenant_id)


def _evidence(
    mod,
    at: int,
    *,
    primary_body: bytes = PRIMARY_BODY,
    corr_body: bytes = CORR_BODY,
    observed_at: int | None = None,
    expires_at: int | None = None,
):
    observed = at - 30 if observed_at is None else observed_at
    expires = at + 5000 if expires_at is None else expires_at
    published = min(at - 120, observed)
    return [
        mod.EvidenceInput(
            evidence_id="ev-primary",
            authority_id="primary",
            authority_revision=1,
            subject="pricing",
            kind="PAGE",
            source_kind="IMMUTABLE",
            canonical_source=PRIMARY_URL,
            immutable_version_or_record_id="v1",
            published_at=published,
            observed_at=observed,
            expires_at=expires,
            content_digest=hashlib.sha256(primary_body).hexdigest(),
            is_primary=True,
        ),
        mod.EvidenceInput(
            evidence_id="ev-corr",
            authority_id="corroborator",
            authority_revision=1,
            subject="pricing",
            kind="PAGE",
            source_kind="VERSIONED",
            canonical_source=CORR_URL,
            immutable_version_or_record_id="v2",
            published_at=published,
            observed_at=observed,
            expires_at=expires,
            content_digest=hashlib.sha256(corr_body).hexdigest(),
            is_primary=False,
        ),
    ]


def _replacement_evidence(
    mod,
    *,
    published_at: int,
    observed_at: int,
    expires_at: int,
):
    published = published_at
    return [
        mod.EvidenceReplacementInput(
            replaces_evidence_id="ev-primary",
            evidence_id="ev-primary-r1",
            authority_id="primary",
            authority_revision=1,
            subject="pricing",
            kind="PAGE",
            source_kind="IMMUTABLE",
            canonical_source=PRIMARY_URL,
            immutable_version_or_record_id="v1",
            published_at=published,
            observed_at=observed_at,
            expires_at=expires_at,
            content_digest=hashlib.sha256(PRIMARY_BODY).hexdigest(),
            is_primary=True,
        ),
        mod.EvidenceReplacementInput(
            replaces_evidence_id="ev-corr",
            evidence_id="ev-corr-r1",
            authority_id="corroborator",
            authority_revision=1,
            subject="pricing",
            kind="PAGE",
            source_kind="VERSIONED",
            canonical_source=CORR_URL,
            immutable_version_or_record_id="v2",
            published_at=published,
            observed_at=observed_at,
            expires_at=expires_at,
            content_digest=hashlib.sha256(CORR_BODY).hexdigest(),
            is_primary=False,
        ),
    ]


def _accept(contract, vm, provider, covenant_id: int, at: int = BASE + 60):
    vm.warp(_iso(at))
    _assert_contract_clock(contract, vm, at)
    vm.sender = provider
    vm.value = 0
    contract.accept_covenant(covenant_id)


def _deliver(
    contract,
    mod,
    vm,
    provider,
    covenant_id: int,
    *,
    at: int = BASE + 120,
    evidence=None,
):
    vm.warp(_iso(at))
    _assert_contract_clock(contract, vm, at)
    vm.sender = provider
    vm.value = 0
    if evidence is None:
        evidence = _evidence(mod, at)
    _structured_call(
        contract,
        "submit_delivery",
        covenant_id,
        "report delivered",
        evidence,
    )
    return at


def _challenge(
    contract,
    vm,
    buyer,
    covenant_id: int,
    criterion_ids,
    *,
    at: int = BASE + 180,
):
    vm.warp(_iso(at))
    _assert_contract_clock(contract, vm, at)
    vm.sender = buyer
    vm.value = 0
    contract.challenge_delivery(
        covenant_id,
        "The submitted report may not satisfy the challenged criteria.",
        list(criterion_ids),
    )


def _web_mock(vm, url: str, status: int, body: bytes):
    vm.mock_web(
        rf"^{re.escape(url)}$",
        {
            "response": {
                "status": status,
                "headers": {},
                "body": body,
            },
            "method": "GET",
        },
    )


def _mock_success(vm, failed_ids):
    _web_mock(vm, PRIMARY_URL, 200, PRIMARY_BODY)
    _web_mock(vm, CORR_URL, 200, CORR_BODY)
    import json

    vm.mock_llm(
        r".*",
        json.dumps(
            {"failed_criterion_ids": list(failed_ids)},
            sort_keys=True,
            separators=(",", ":"),
        ),
    )


def _mock_http_failure(vm, status: int):
    _web_mock(vm, PRIMARY_URL, status, b"upstream failure")
    _web_mock(vm, CORR_URL, status, b"upstream failure")


def _list_strings(value):
    return [str(item) for item in value]


def _claim(contract, vm, caller, covenant_id: int):
    vm.sender = caller
    vm.value = 0
    contract.claim_settlement(covenant_id)

def _open_terms(contract, vm, buyer, terms, *, now: int):
    vm.warp(_iso(now))
    _assert_contract_clock(contract, vm, now)
    vm.sender = buyer
    vm.value = int(terms.principal)
    covenant_id = _structured_call(contract, "open_covenant", terms)
    vm.value = 0
    return int(covenant_id)


def _enter_full_challenge(
    contract,
    mod,
    vm,
    buyer,
    provider,
    *,
    open_at: int = BASE,
    max_evidence_age: int = 1800,
):
    covenant_id = _open(
        contract,
        mod,
        vm,
        buyer,
        provider,
        now=open_at,
        max_evidence_age=max_evidence_age,
    )
    _accept(contract, vm, provider, covenant_id, at=open_at + 60)
    _deliver(
        contract,
        mod,
        vm,
        provider,
        covenant_id,
        at=open_at + 120,
    )
    _challenge(
        contract,
        vm,
        buyer,
        covenant_id,
        ["accuracy", "freshness"],
        at=open_at + 180,
    )
    return covenant_id


def _enter_stale_repair_required(
    contract,
    mod,
    vm,
    buyer,
    provider,
    caller,
    *,
    terms=None,
):
    if terms is None:
        covenant_id = _open(
            contract,
            mod,
            vm,
            buyer,
            provider,
            max_evidence_age=300,
        )
    else:
        covenant_id = _open_terms(contract, vm, buyer, terms, now=BASE)

    _accept(contract, vm, provider, covenant_id, at=BASE + 60)

    delivery_at = BASE + 120
    initial = _evidence(
        mod,
        delivery_at,
        observed_at=delivery_at,
        expires_at=delivery_at + 5000,
    )
    _deliver(
        contract,
        mod,
        vm,
        provider,
        covenant_id,
        at=delivery_at,
        evidence=initial,
    )
    _challenge(
        contract,
        vm,
        buyer,
        covenant_id,
        ["accuracy", "freshness"],
        at=BASE + 180,
    )

    adjudicate_at = BASE + 500
    vm.clear_mocks()
    _mock_success(vm, [])
    vm.warp(_iso(adjudicate_at))
    _assert_contract_clock(contract, vm, adjudicate_at)
    vm.sender = caller
    contract.adjudicate_challenge(covenant_id)
    assert vm.run_validator() is True

    cov = contract.get_covenant(covenant_id)
    assert cov.state == "EVIDENCE_REPAIR_REQUIRED"
    auths = list(contract.get_repair_authorizations(covenant_id))
    assert [a.evidence_id for a in auths[-2:]] == ["ev-primary", "ev-corr"]
    assert [int(a.field_mask) for a in auths[-2:]] == [32, 32]
    return covenant_id, delivery_at, adjudicate_at


def _assert_no_merit_reputation(contract, mod, buyer, provider):
    p = contract.get_provider_stats(_as_address(mod, provider))
    b = contract.get_buyer_stats(_as_address(mod, buyer))
    assert int(p.disputes_won) == 0
    assert int(p.disputes_lost) == 0
    assert int(b.valid_challenges) == 0
    assert int(b.invalid_challenges) == 0


def test_open_rejects_duplicate_criteria_and_correlated_corroboration_atomically(
    direct_vm,
    direct_deploy,
    direct_alice,
    direct_bob,
):
    buyer, provider = direct_alice, direct_bob
    contract, mod, _ = _deploy(direct_vm, direct_deploy, buyer)

    duplicate = _terms(mod, provider, BASE)
    duplicate.criteria[1].criterion_id = duplicate.criteria[0].criterion_id

    direct_vm.sender = buyer
    direct_vm.value = PRINCIPAL
    with pytest.raises(Exception):
        _structured_call(contract, "open_covenant", duplicate)
    direct_vm.value = 0

    assert int(contract.get_covenant_count()) == 0
    totals = contract.get_accounting_totals()
    assert int(totals.total_funded) == 0
    assert int(totals.total_outstanding) == 0

    correlated = _terms(mod, provider, BASE)
    correlated.authority_bindings[1].identity_value = "example.com"
    correlated.authority_bindings[1].canonical_origin = "https://example.com"

    direct_vm.sender = buyer
    direct_vm.value = PRINCIPAL
    with pytest.raises(Exception):
        _structured_call(contract, "open_covenant", correlated)
    direct_vm.value = 0

    assert int(contract.get_covenant_count()) == 0
    totals = contract.get_accounting_totals()
    assert int(totals.total_funded) == 0
    assert int(totals.total_outstanding) == 0


def test_delivery_rejects_duplicate_ids_and_wrong_authority_origin_without_side_effects(
    direct_vm,
    direct_deploy,
    direct_alice,
    direct_bob,
):
    buyer, provider = direct_alice, direct_bob
    contract, mod, _ = _deploy(direct_vm, direct_deploy, buyer)
    covenant_id = _open(contract, mod, direct_vm, buyer, provider)
    _accept(contract, direct_vm, provider, covenant_id)

    duplicate = _evidence(mod, BASE + 120)
    duplicate[1].evidence_id = duplicate[0].evidence_id

    direct_vm.warp(_iso(BASE + 120))
    direct_vm.sender = provider
    with pytest.raises(Exception):
        _structured_call(
            contract,
            "submit_delivery",
            covenant_id,
            "report delivered",
            duplicate,
        )

    cov = contract.get_covenant(covenant_id)
    assert cov.state == "SERVICE_ACCEPTED"
    assert len(list(contract.get_evidence_history(covenant_id))) == 0
    assert _list_strings(contract.get_active_evidence_ids(covenant_id)) == []

    wrong_origin = _evidence(mod, BASE + 120)
    wrong_origin[0].canonical_source = "https://evil.example/evidence/v1/report"

    with pytest.raises(Exception):
        _structured_call(
            contract,
            "submit_delivery",
            covenant_id,
            "report delivered",
            wrong_origin,
        )

    cov = contract.get_covenant(covenant_id)
    assert cov.state == "SERVICE_ACCEPTED"
    assert len(list(contract.get_evidence_history(covenant_id))) == 0
    assert _list_strings(contract.get_active_evidence_ids(covenant_id)) == []


def test_global_replay_scope_blocks_cross_covenant_evidence_reuse(
    direct_vm,
    direct_deploy,
    direct_alice,
    direct_bob,
):
    buyer, provider = direct_alice, direct_bob
    contract, mod, _ = _deploy(direct_vm, direct_deploy, buyer)

    first_terms = _terms(mod, provider, BASE)
    first_terms.replay_scope = "GLOBAL"
    second_terms = _terms(mod, provider, BASE)
    second_terms.replay_scope = "GLOBAL"

    first = _open_terms(contract, direct_vm, buyer, first_terms, now=BASE)
    second = _open_terms(contract, direct_vm, buyer, second_terms, now=BASE)

    _accept(contract, direct_vm, provider, first, at=BASE + 60)
    _accept(contract, direct_vm, provider, second, at=BASE + 60)
    _deliver(contract, mod, direct_vm, provider, first, at=BASE + 120)

    direct_vm.warp(_iso(BASE + 120))
    direct_vm.sender = provider
    with pytest.raises(Exception):
        _structured_call(
            contract,
            "submit_delivery",
            second,
            "second report",
            _evidence(mod, BASE + 120),
        )

    assert contract.get_covenant(first).state == "DELIVERED"
    assert contract.get_covenant(second).state == "SERVICE_ACCEPTED"
    assert len(list(contract.get_evidence_history(second))) == 0


def test_challenge_rejects_duplicate_out_of_order_and_unknown_criteria_atomically(
    direct_vm,
    direct_deploy,
    direct_alice,
    direct_bob,
):
    buyer, provider = direct_alice, direct_bob
    contract, mod, _ = _deploy(direct_vm, direct_deploy, buyer)
    covenant_id = _open(contract, mod, direct_vm, buyer, provider)
    _accept(contract, direct_vm, provider, covenant_id)
    _deliver(contract, mod, direct_vm, provider, covenant_id)

    direct_vm.warp(_iso(BASE + 180))
    direct_vm.sender = buyer

    for ids in (
        ["accuracy", "accuracy"],
        ["freshness", "accuracy"],
        ["unknown"],
    ):
        with direct_vm.expect_revert():
            contract.challenge_delivery(
                covenant_id,
                "malformed challenge",
                ids,
            )
        cov = contract.get_covenant(covenant_id)
        assert cov.state == "DELIVERED"
        assert int(cov.review_generation) == 0
        assert _list_strings(
            contract.get_challenged_criterion_ids(covenant_id)
        ) == []


def test_malicious_model_extra_fields_cannot_authorize_settlement(
    direct_vm,
    direct_deploy,
    direct_alice,
    direct_bob,
    direct_charlie,
):
    buyer, provider, caller = direct_alice, direct_bob, direct_charlie
    contract, mod, transfers = _deploy(direct_vm, direct_deploy, buyer)
    covenant_id = _enter_full_challenge(
        contract,
        mod,
        direct_vm,
        buyer,
        provider,
    )

    direct_vm.clear_mocks()
    _web_mock(direct_vm, PRIMARY_URL, 200, PRIMARY_BODY)
    _web_mock(direct_vm, CORR_URL, 200, CORR_BODY)
    direct_vm.mock_llm(
        r".*",
        '{"failed_criterion_ids":[],"recipient":"attacker"}',
    )

    direct_vm.warp(_iso(BASE + 200))
    direct_vm.sender = caller
    contract.adjudicate_challenge(covenant_id)

    assert direct_vm.run_validator() is True
    cov = contract.get_covenant(covenant_id)
    assert cov.state == "REVIEW_RETRY_REQUIRED"
    assert cov.adjudication_decision == "REVIEW_RETRY_REQUIRED"
    assert cov.failure_classification == "TRANSIENT_REVIEW_FAILURE"
    assert cov.settlement_direction == ""
    assert int(cov.outstanding_amount) == PRINCIPAL
    assert transfers == []


def test_adjudication_wire_rejects_hash_generation_and_extra_key_tampering(
    direct_vm,
    direct_deploy,
    direct_alice,
    direct_bob,
):
    buyer, provider = direct_alice, direct_bob
    contract, mod, _ = _deploy(direct_vm, direct_deploy, buyer)
    covenant_id = _enter_full_challenge(
        contract,
        mod,
        direct_vm,
        buyer,
        provider,
    )

    direct_vm.clear_mocks()
    _mock_success(direct_vm, [])
    review_at = BASE + 200
    direct_vm.warp(_iso(review_at))
    raw = _raw_instance(contract)
    key, cov = raw._require_covenant(covenant_id)
    wire = raw._execute_review_consensus(key, cov, review_at, 1)
    base_obj = mod.json.loads(wire)

    mutations = []

    wrong_hash = dict(base_obj)
    wrong_hash["delivery_hash"] = "0" * 64
    mutations.append(wrong_hash)

    wrong_generation = dict(base_obj)
    wrong_generation["review_generation"] = 2
    mutations.append(wrong_generation)

    extra_key = dict(base_obj)
    extra_key["recipient"] = "attacker"
    mutations.append(extra_key)

    for obj in mutations:
        tampered = mod._canonical_json(obj)
        with pytest.raises(Exception):
            raw._validate_consensus_wire(
                key,
                cov,
                tampered,
                1,
            )

    assert contract.get_covenant(covenant_id).state == "CHALLENGED"


def test_validator_disagreement_is_detected_for_same_challenge_snapshot(
    direct_vm,
    direct_deploy,
    direct_alice,
    direct_bob,
    direct_charlie,
):
    buyer, provider, caller = direct_alice, direct_bob, direct_charlie
    contract, mod, _ = _deploy(direct_vm, direct_deploy, buyer)
    covenant_id = _enter_full_challenge(
        contract,
        mod,
        direct_vm,
        buyer,
        provider,
    )

    snap = direct_vm.snapshot()

    direct_vm.clear_mocks()
    _mock_success(direct_vm, [])
    direct_vm.warp(_iso(BASE + 200))
    direct_vm.sender = caller
    contract.adjudicate_challenge(covenant_id)

    direct_vm.clear_mocks()
    _mock_success(direct_vm, ["accuracy"])
    assert direct_vm.run_validator() is False

    direct_vm.revert(snap)
    cov = contract.get_covenant(covenant_id)
    assert cov.state == "CHALLENGED"
    assert cov.settlement_direction == ""
    assert int(cov.outstanding_amount) == PRINCIPAL


def test_repair_rejects_incomplete_set_and_nonrepairable_field_change_atomically(
    direct_vm,
    direct_deploy,
    direct_alice,
    direct_bob,
    direct_charlie,
):
    buyer, provider, caller = direct_alice, direct_bob, direct_charlie
    contract, mod, _ = _deploy(direct_vm, direct_deploy, buyer)
    covenant_id, delivery_at, adjudicate_at = _enter_stale_repair_required(
        contract,
        mod,
        direct_vm,
        buyer,
        provider,
        caller,
    )

    repair_at = adjudicate_at + 10
    valid = _replacement_evidence(
        mod,
        published_at=delivery_at - 120,
        observed_at=repair_at,
        expires_at=delivery_at + 5000,
    )

    direct_vm.warp(_iso(repair_at))
    direct_vm.sender = provider

    with pytest.raises(Exception):
        _structured_call(
            contract,
            "submit_evidence_repair",
            covenant_id,
            valid[:1],
        )

    altered = _replacement_evidence(
        mod,
        published_at=delivery_at - 120,
        observed_at=repair_at,
        expires_at=delivery_at + 5000,
    )
    altered[0].subject = "different-subject"

    with pytest.raises(Exception):
        _structured_call(
            contract,
            "submit_evidence_repair",
            covenant_id,
            altered,
        )

    cov = contract.get_covenant(covenant_id)
    assert cov.state == "EVIDENCE_REPAIR_REQUIRED"
    assert int(cov.review_generation) == 1
    assert cov.repair_authorization_active is True
    assert len(list(contract.get_evidence_history(covenant_id))) == 2
    assert _list_strings(contract.get_active_evidence_ids(covenant_id)) == [
        "ev-primary",
        "ev-corr",
    ]


def test_repair_rejects_overbroad_field_change_and_replayed_evidence_id(
    direct_vm,
    direct_deploy,
    direct_alice,
    direct_bob,
    direct_charlie,
):
    buyer, provider, caller = direct_alice, direct_bob, direct_charlie
    contract, mod, _ = _deploy(direct_vm, direct_deploy, buyer)
    covenant_id, delivery_at, adjudicate_at = _enter_stale_repair_required(
        contract,
        mod,
        direct_vm,
        buyer,
        provider,
        caller,
    )

    repair_at = adjudicate_at + 10
    direct_vm.warp(_iso(repair_at))
    direct_vm.sender = provider

    overbroad = _replacement_evidence(
        mod,
        published_at=delivery_at - 120,
        observed_at=repair_at,
        expires_at=delivery_at + 5000,
    )
    overbroad[0].expires_at = delivery_at + 5001

    with pytest.raises(Exception):
        _structured_call(
            contract,
            "submit_evidence_repair",
            covenant_id,
            overbroad,
        )

    replayed = _replacement_evidence(
        mod,
        published_at=delivery_at - 120,
        observed_at=repair_at,
        expires_at=delivery_at + 5000,
    )
    replayed[0].evidence_id = "ev-primary"

    with pytest.raises(Exception):
        _structured_call(
            contract,
            "submit_evidence_repair",
            covenant_id,
            replayed,
        )

    cov = contract.get_covenant(covenant_id)
    assert cov.state == "EVIDENCE_REPAIR_REQUIRED"
    assert int(cov.review_generation) == 1
    assert len(list(contract.get_evidence_history(covenant_id))) == 2


def test_retry_generation_exhaustion_closes_neutrally_to_buyer(
    direct_vm,
    direct_deploy,
    direct_alice,
    direct_bob,
    direct_charlie,
):
    buyer, provider, outsider = direct_alice, direct_bob, direct_charlie
    contract, mod, transfers = _deploy(direct_vm, direct_deploy, buyer)

    terms = _terms(
        mod,
        provider,
        BASE,
        max_review_generations=1,
    )
    covenant_id = _open_terms(contract, direct_vm, buyer, terms, now=BASE)
    _accept(contract, direct_vm, provider, covenant_id, at=BASE + 60)
    _deliver(contract, mod, direct_vm, provider, covenant_id, at=BASE + 120)
    _challenge(
        contract,
        direct_vm,
        buyer,
        covenant_id,
        ["accuracy", "freshness"],
        at=BASE + 180,
    )

    direct_vm.clear_mocks()
    _mock_http_failure(direct_vm, 503)
    direct_vm.warp(_iso(BASE + 200))
    direct_vm.sender = outsider
    contract.adjudicate_challenge(covenant_id)
    assert direct_vm.run_validator() is True

    cov = contract.get_covenant(covenant_id)
    assert cov.state == "REVIEW_RETRY_REQUIRED"
    assert int(cov.review_generation) == 1

    direct_vm.warp(_iso(BASE + 210))
    direct_vm.sender = outsider
    with direct_vm.expect_revert():
        contract.retry_review(covenant_id)

    contract.expire_review(covenant_id)
    cov = contract.get_covenant(covenant_id)
    assert cov.state == "SETTLEMENT_AUTHORIZED_BUYER"
    assert cov.closure_reason == "REVIEW_EXPIRED"

    _claim(contract, direct_vm, outsider, covenant_id)
    assert transfers == [(buyer, PRINCIPAL)]
    _assert_no_merit_reputation(contract, mod, buyer, provider)


def test_repair_generation_exhaustion_closes_neutrally_to_buyer(
    direct_vm,
    direct_deploy,
    direct_alice,
    direct_bob,
    direct_charlie,
):
    buyer, provider, outsider = direct_alice, direct_bob, direct_charlie
    contract, mod, transfers = _deploy(direct_vm, direct_deploy, buyer)

    terms = _terms(
        mod,
        provider,
        BASE,
        max_evidence_age=300,
        max_review_generations=1,
    )
    covenant_id, delivery_at, adjudicate_at = _enter_stale_repair_required(
        contract,
        mod,
        direct_vm,
        buyer,
        provider,
        outsider,
        terms=terms,
    )

    replacements = _replacement_evidence(
        mod,
        published_at=delivery_at - 120,
        observed_at=adjudicate_at + 10,
        expires_at=delivery_at + 5000,
    )

    direct_vm.warp(_iso(adjudicate_at + 10))
    direct_vm.sender = provider
    with pytest.raises(Exception):
        _structured_call(
            contract,
            "submit_evidence_repair",
            covenant_id,
            replacements,
        )

    direct_vm.sender = outsider
    contract.expire_review(covenant_id)
    cov = contract.get_covenant(covenant_id)
    assert cov.state == "SETTLEMENT_AUTHORIZED_BUYER"
    assert cov.closure_reason == "REVIEW_EXPIRED"

    _claim(contract, direct_vm, outsider, covenant_id)
    assert transfers == [(buyer, PRINCIPAL)]
    _assert_no_merit_reputation(contract, mod, buyer, provider)


def test_repair_deadline_expiry_is_permissionless_buyer_recovery(
    direct_vm,
    direct_deploy,
    direct_alice,
    direct_bob,
    direct_charlie,
):
    buyer, provider, outsider = direct_alice, direct_bob, direct_charlie
    contract, mod, transfers = _deploy(direct_vm, direct_deploy, buyer)
    covenant_id, _, _ = _enter_stale_repair_required(
        contract,
        mod,
        direct_vm,
        buyer,
        provider,
        outsider,
    )

    cov = contract.get_covenant(covenant_id)
    direct_vm.warp(_iso(int(cov.repair_deadline) + 1))
    direct_vm.sender = outsider
    contract.expire_repair(covenant_id)

    cov = contract.get_covenant(covenant_id)
    assert cov.state == "SETTLEMENT_AUTHORIZED_BUYER"
    assert cov.closure_reason == "REPAIR_EXPIRED"

    _claim(contract, direct_vm, outsider, covenant_id)
    assert transfers == [(buyer, PRINCIPAL)]


def test_absolute_review_deadline_is_permissionless_buyer_recovery(
    direct_vm,
    direct_deploy,
    direct_alice,
    direct_bob,
    direct_charlie,
):
    buyer, provider, outsider = direct_alice, direct_bob, direct_charlie
    contract, mod, transfers = _deploy(direct_vm, direct_deploy, buyer)
    covenant_id = _enter_full_challenge(
        contract,
        mod,
        direct_vm,
        buyer,
        provider,
    )

    cov = contract.get_covenant(covenant_id)
    direct_vm.warp(_iso(int(cov.absolute_dispute_deadline) + 1))
    direct_vm.sender = outsider
    contract.expire_review(covenant_id)

    cov = contract.get_covenant(covenant_id)
    assert cov.state == "SETTLEMENT_AUTHORIZED_BUYER"
    assert cov.closure_reason == "REVIEW_EXPIRED"

    _claim(contract, direct_vm, outsider, covenant_id)
    assert transfers == [(buyer, PRINCIPAL)]


def test_outsider_claim_cannot_redirect_provider_settlement_or_double_claim(
    direct_vm,
    direct_deploy,
    direct_alice,
    direct_bob,
    direct_charlie,
):
    buyer, provider, outsider = direct_alice, direct_bob, direct_charlie
    contract, mod, transfers = _deploy(direct_vm, direct_deploy, buyer)
    covenant_id = _open(contract, mod, direct_vm, buyer, provider)
    _accept(contract, direct_vm, provider, covenant_id)
    _deliver(contract, mod, direct_vm, provider, covenant_id)

    cov = contract.get_covenant(covenant_id)
    direct_vm.warp(_iso(int(cov.challenge_deadline) + 1))
    direct_vm.sender = outsider
    contract.authorize_unchallenged_settlement(covenant_id)

    _claim(contract, direct_vm, outsider, covenant_id)
    assert transfers == [(provider, PRINCIPAL)]

    totals_before = contract.get_accounting_totals()
    p_before = contract.get_provider_stats(_as_address(mod, provider))
    b_before = contract.get_buyer_stats(_as_address(mod, buyer))

    direct_vm.sender = buyer
    with direct_vm.expect_revert():
        contract.claim_settlement(covenant_id)

    totals_after = contract.get_accounting_totals()
    p_after = contract.get_provider_stats(_as_address(mod, provider))
    b_after = contract.get_buyer_stats(_as_address(mod, buyer))

    assert int(totals_after.total_funded) == int(totals_before.total_funded)
    assert int(totals_after.total_closed_to_provider) == int(
        totals_before.total_closed_to_provider
    )
    assert int(totals_after.total_closed_to_buyer) == int(
        totals_before.total_closed_to_buyer
    )
    assert int(totals_after.total_outstanding) == int(
        totals_before.total_outstanding
    )
    assert [int(x) for x in (
        p_after.accepted_covenants,
        p_after.deliveries,
        p_after.non_deliveries,
        p_after.disputes_won,
        p_after.disputes_lost,
    )] == [int(x) for x in (
        p_before.accepted_covenants,
        p_before.deliveries,
        p_before.non_deliveries,
        p_before.disputes_won,
        p_before.disputes_lost,
    )]
    assert [int(x) for x in (
        b_after.funded_covenants,
        b_after.challenges_filed,
        b_after.valid_challenges,
        b_after.invalid_challenges,
    )] == [int(x) for x in (
        b_before.funded_covenants,
        b_before.challenges_filed,
        b_before.valid_challenges,
        b_before.invalid_challenges,
    )]
    assert len(transfers) == 1


def test_immutable_digest_mismatch_requires_exact_reanchor_mask_not_settlement(
    direct_vm,
    direct_deploy,
    direct_alice,
    direct_bob,
    direct_charlie,
):
    buyer, provider, caller = direct_alice, direct_bob, direct_charlie
    contract, mod, transfers = _deploy(direct_vm, direct_deploy, buyer)
    covenant_id = _enter_full_challenge(
        contract,
        mod,
        direct_vm,
        buyer,
        provider,
    )

    direct_vm.clear_mocks()
    _web_mock(direct_vm, PRIMARY_URL, 200, b"tampered-primary")
    _web_mock(direct_vm, CORR_URL, 200, b"tampered-corroborator")
    direct_vm.warp(_iso(BASE + 200))
    direct_vm.sender = caller
    contract.adjudicate_challenge(covenant_id)

    assert direct_vm.run_validator() is True
    cov = contract.get_covenant(covenant_id)
    assert cov.state == "EVIDENCE_REPAIR_REQUIRED"
    assert cov.settlement_direction == ""
    auths = list(contract.get_repair_authorizations(covenant_id))
    assert [int(a.field_mask) for a in auths[-2:]] == [140, 140]
    assert transfers == []


def test_repairable_http_404_requires_canonical_source_mask_not_breach(
    direct_vm,
    direct_deploy,
    direct_alice,
    direct_bob,
    direct_charlie,
):
    buyer, provider, caller = direct_alice, direct_bob, direct_charlie
    contract, mod, transfers = _deploy(direct_vm, direct_deploy, buyer)
    covenant_id = _enter_full_challenge(
        contract,
        mod,
        direct_vm,
        buyer,
        provider,
    )

    direct_vm.clear_mocks()
    _mock_http_failure(direct_vm, 404)
    direct_vm.warp(_iso(BASE + 200))
    direct_vm.sender = caller
    contract.adjudicate_challenge(covenant_id)

    assert direct_vm.run_validator() is True
    cov = contract.get_covenant(covenant_id)
    assert cov.state == "EVIDENCE_REPAIR_REQUIRED"
    assert cov.adjudication_decision == "EVIDENCE_REPAIR_REQUIRED"
    auths = list(contract.get_repair_authorizations(covenant_id))
    assert [int(a.field_mask) for a in auths[-2:]] == [4, 4]
    assert cov.settlement_direction == ""
    assert transfers == []


def test_transient_fetch_failure_has_precedence_over_known_stale_repairs(
    direct_vm,
    direct_deploy,
    direct_alice,
    direct_bob,
    direct_charlie,
):
    buyer, provider, caller = direct_alice, direct_bob, direct_charlie
    contract, mod, transfers = _deploy(direct_vm, direct_deploy, buyer)
    covenant_id = _open(
        contract,
        mod,
        direct_vm,
        buyer,
        provider,
        max_evidence_age=300,
    )
    _accept(contract, direct_vm, provider, covenant_id, at=BASE + 60)

    delivery_at = BASE + 120
    _deliver(
        contract,
        mod,
        direct_vm,
        provider,
        covenant_id,
        at=delivery_at,
        evidence=_evidence(
            mod,
            delivery_at,
            observed_at=delivery_at,
            expires_at=delivery_at + 5000,
        ),
    )
    _challenge(
        contract,
        direct_vm,
        buyer,
        covenant_id,
        ["accuracy", "freshness"],
        at=BASE + 180,
    )

    direct_vm.clear_mocks()
    _web_mock(direct_vm, PRIMARY_URL, 200, PRIMARY_BODY)
    _web_mock(direct_vm, CORR_URL, 503, b"temporarily unavailable")
    direct_vm.warp(_iso(BASE + 500))
    direct_vm.sender = caller
    contract.adjudicate_challenge(covenant_id)

    assert direct_vm.run_validator() is True
    cov = contract.get_covenant(covenant_id)
    assert cov.state == "REVIEW_RETRY_REQUIRED"
    assert cov.failure_classification == "TRANSIENT_REVIEW_FAILURE"
    assert len(list(contract.get_repair_authorizations(covenant_id))) == 0
    assert cov.settlement_direction == ""
    assert transfers == []


def test_unrepairable_stale_evidence_produces_no_accepted_consequential_wire(
    direct_vm,
    direct_deploy,
    direct_alice,
    direct_bob,
    direct_charlie,
):
    buyer, provider, caller = direct_alice, direct_bob, direct_charlie
    contract, mod, transfers = _deploy(direct_vm, direct_deploy, buyer)

    terms = _terms(
        mod,
        provider,
        BASE,
        max_evidence_age=300,
    )
    terms.repair_allowed_field_mask = 0

    covenant_id = _open_terms(contract, direct_vm, buyer, terms, now=BASE)
    _accept(contract, direct_vm, provider, covenant_id, at=BASE + 60)

    delivery_at = BASE + 120
    _deliver(
        contract,
        mod,
        direct_vm,
        provider,
        covenant_id,
        at=delivery_at,
        evidence=_evidence(
            mod,
            delivery_at,
            observed_at=delivery_at,
            expires_at=delivery_at + 5000,
        ),
    )
    _challenge(
        contract,
        direct_vm,
        buyer,
        covenant_id,
        ["accuracy", "freshness"],
        at=BASE + 180,
    )

    direct_vm.clear_mocks()
    _mock_success(direct_vm, [])
    direct_vm.warp(_iso(BASE + 500))
    direct_vm.sender = caller

    with direct_vm.expect_revert():
        contract.adjudicate_challenge(covenant_id)

    cov = contract.get_covenant(covenant_id)
    assert cov.state == "CHALLENGED"
    assert cov.adjudication_decision == ""
    assert cov.settlement_direction == ""
    assert int(cov.outstanding_amount) == PRINCIPAL
    assert transfers == []
