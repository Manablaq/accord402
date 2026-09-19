from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import re
import sys

import pytest


ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "contracts" / "accord402.py"
EXPECTED_CONTRACT_SHA256 = "60ac857d566e49ae912a384c7ce0a11da3bc3201d7349de3fe24bee0cd095692"

BASE = 1_700_000_000
PRINCIPAL = 1_000_000

RAW_ORIGIN = "https://raw.githubusercontent.com"
PRIMARY_REPO = "accord402-primary/evidence"
CORR_REPO = "accord402-corroborator/evidence"
PRIMARY_COMMIT = "1" * 40
CORR_COMMIT = "2" * 40
PRIMARY_URL = f"{RAW_ORIGIN}/{PRIMARY_REPO}/{PRIMARY_COMMIT}/pricing.json"
CORR_URL = f"{RAW_ORIGIN}/{CORR_REPO}/{CORR_COMMIT}/pricing.json"
PRIMARY_PAYLOAD = '{"authority":"primary","fact":"pricing-current"}'
CORR_PAYLOAD = '{"authority":"corroborator","fact":"pricing-current"}'

def _manifest_body(repo, url, commit, published_at, expires_at, payload):
    return json.dumps(
        {
            "schema": "ACCORD402_EVIDENCE_MANIFEST_V2",
            "authority_identity": repo,
            "subject": "pricing",
            "kind": "PAGE",
            "published_at": int(published_at),
            "expires_at": int(expires_at),
            "payload": payload,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")

PRIMARY_BODY = _manifest_body(PRIMARY_REPO, PRIMARY_URL, PRIMARY_COMMIT, BASE, BASE + 5120, PRIMARY_PAYLOAD)
CORR_BODY = _manifest_body(CORR_REPO, CORR_URL, CORR_COMMIT, BASE, BASE + 5120, CORR_PAYLOAD)
_CURRENT_BODIES = {PRIMARY_URL: PRIMARY_BODY, CORR_URL: CORR_BODY}


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


class _VaultEmission:
    def __init__(self, sink, details, amount):
        self.sink = sink
        self.details = details
        self.amount = int(amount)

    def credit(self, covenant_id, beneficiary, recipient):
        recipient_bytes = _address_bytes(recipient)
        beneficiary_bytes = _address_bytes(beneficiary)
        self.sink.append((recipient_bytes, self.amount))
        self.details.append(
            (int(covenant_id), beneficiary_bytes, recipient_bytes, self.amount)
        )


class _VaultCapture:
    credits: list[tuple[object, int]] = []
    details: list[tuple[int, object, object, int]] = []
    unregistered: set[bytes] = set()

    def __init__(self, address):
        self.address = address

    def view(self):
        return self

    def is_registered_payout(self, recipient):
        raw = _address_bytes(recipient)
        return raw != b"\x00" * 20 and raw not in type(self).unregistered

    def emit(self, *, value):
        return _VaultEmission(
            type(self).credits,
            type(self).details,
            value,
        )


def _install_transfer_capture(contract):
    mod = _module(contract)
    _VaultCapture.credits = []
    _VaultCapture.details = []
    _VaultCapture.unregistered = set()
    mod._SettlementVault = _VaultCapture
    return _VaultCapture.credits


def _deploy(direct_vm, direct_deploy, buyer):
    assert _sha256(CONTRACT) == EXPECTED_CONTRACT_SHA256
    direct_vm.sender = buyer
    direct_vm.value = 0
    direct_vm.warp(_iso(BASE))
    contract = direct_deploy(str(CONTRACT), buyer)
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
            identity_kind="GITHUB_REPOSITORY",
            identity_value=PRIMARY_REPO,
            canonical_origin=RAW_ORIGIN,
        ),
        mod.AuthorityBindingInput(
            authority_id="corroborator",
            authority_revision=1,
            role="CORROBORATOR",
            identity_kind="GITHUB_REPOSITORY",
            identity_value=CORR_REPO,
            canonical_origin=RAW_ORIGIN,
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
        repair_allowed_field_mask=252,
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
    covenant_id = _structured_call(contract, 'open_covenant', _terms(mod, provider, now, principal=principal, max_evidence_age=max_evidence_age), _as_address(mod, buyer))
    vm.value = 0
    return int(covenant_id)


def _evidence(
    mod,
    at: int,
    *,
    primary_body: bytes | None = None,
    corr_body: bytes | None = None,
    observed_at: int | None = None,
    expires_at: int | None = None,
):
    observed = at if observed_at is None else observed_at
    expires = at + 5000 if expires_at is None else expires_at
    published = min(at - 120, observed)
    pbody = primary_body or _manifest_body(PRIMARY_REPO, PRIMARY_URL, PRIMARY_COMMIT, published, expires, PRIMARY_PAYLOAD)
    cbody = corr_body or _manifest_body(CORR_REPO, CORR_URL, CORR_COMMIT, published, expires, CORR_PAYLOAD)
    _CURRENT_BODIES[PRIMARY_URL] = pbody
    _CURRENT_BODIES[CORR_URL] = cbody
    return [
        mod.EvidenceInput(
            evidence_id="ev-primary", authority_id="primary", authority_revision=1,
            subject="pricing", kind="PAGE", source_kind="IMMUTABLE",
            canonical_source=PRIMARY_URL, immutable_version_or_record_id=PRIMARY_COMMIT,
            published_at=published, observed_at=observed, expires_at=expires,
            content_digest=hashlib.sha256(pbody).hexdigest(), is_primary=True,
        ),
        mod.EvidenceInput(
            evidence_id="ev-corr", authority_id="corroborator", authority_revision=1,
            subject="pricing", kind="PAGE", source_kind="IMMUTABLE",
            canonical_source=CORR_URL, immutable_version_or_record_id=CORR_COMMIT,
            published_at=published, observed_at=observed, expires_at=expires,
            content_digest=hashlib.sha256(cbody).hexdigest(), is_primary=False,
        ),
    ]


def _replacement_evidence(
    mod,
    *,
    published_at: int,
    observed_at: int,
    expires_at: int,
):
    pbody = _manifest_body(PRIMARY_REPO, PRIMARY_URL, PRIMARY_COMMIT, published_at, expires_at, PRIMARY_PAYLOAD)
    cbody = _manifest_body(CORR_REPO, CORR_URL, CORR_COMMIT, published_at, expires_at, CORR_PAYLOAD)
    _CURRENT_BODIES[PRIMARY_URL] = pbody
    _CURRENT_BODIES[CORR_URL] = cbody
    return [
        mod.EvidenceReplacementInput(
            replaces_evidence_id="ev-primary", evidence_id="ev-primary-r1",
            authority_id="primary", authority_revision=1, subject="pricing", kind="PAGE",
            source_kind="IMMUTABLE", canonical_source=PRIMARY_URL,
            immutable_version_or_record_id=PRIMARY_COMMIT, published_at=published_at,
            observed_at=observed_at, expires_at=expires_at,
            content_digest=hashlib.sha256(pbody).hexdigest(), is_primary=True,
        ),
        mod.EvidenceReplacementInput(
            replaces_evidence_id="ev-corr", evidence_id="ev-corr-r1",
            authority_id="corroborator", authority_revision=1, subject="pricing", kind="PAGE",
            source_kind="IMMUTABLE", canonical_source=CORR_URL,
            immutable_version_or_record_id=CORR_COMMIT, published_at=published_at,
            observed_at=observed_at, expires_at=expires_at,
            content_digest=hashlib.sha256(cbody).hexdigest(), is_primary=False,
        ),
    ]


def _accept(contract, vm, provider, covenant_id: int, at: int = BASE + 60):
    vm.warp(_iso(at))
    _assert_contract_clock(contract, vm, at)
    vm.sender = provider
    vm.value = 0
    contract.accept_covenant(covenant_id, _as_address(_module(contract), provider))


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


def _http_date(epoch: int) -> str:
    return datetime.fromtimestamp(epoch, tz=timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")


def _web_mock(vm, url: str, status: int, body: bytes, *, fetch_at: int = BASE + 500):
    actual_status = 206 if status == 200 else status
    headers = {}
    if actual_status == 206:
        headers = {
            "date": _http_date(fetch_at),
            "content-range": f"bytes 0-{len(body)-1}/{len(body)}",
        }
    vm.mock_web(
        rf"^{re.escape(url)}$",
        {"response": {"status": actual_status, "headers": headers, "body": body}, "method": "GET"},
    )


def _mock_success(vm, failed_ids, *, fetch_at: int = BASE + 500):
    _web_mock(vm, PRIMARY_URL, 200, _CURRENT_BODIES[PRIMARY_URL], fetch_at=fetch_at)
    _web_mock(vm, CORR_URL, 200, _CURRENT_BODIES[CORR_URL], fetch_at=fetch_at)
    vm.mock_llm(
        r".*",
        json.dumps({"failed_criterion_ids": list(failed_ids)}, sort_keys=True, separators=(",", ":")),
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


def test_initial_state_and_valid_funding(
    direct_vm,
    direct_deploy,
    direct_alice,
    direct_bob,
):
    contract, mod, _ = _deploy(direct_vm, direct_deploy, direct_alice)

    assert int(contract.get_covenant_count()) == 0
    covenant_id = _open(contract, mod, direct_vm, direct_alice, direct_bob)

    assert covenant_id == 1
    assert int(contract.get_covenant_count()) == 1

    cov = contract.get_covenant(covenant_id)
    assert _address_bytes(cov.buyer) == _address_bytes(direct_alice)
    assert _address_bytes(cov.provider) == _address_bytes(direct_bob)
    assert int(cov.funded_amount) == PRINCIPAL
    assert int(cov.outstanding_amount) == PRINCIPAL
    assert int(cov.provider_settlement) == 0
    assert int(cov.buyer_settlement) == 0
    assert cov.state == "FUNDED"
    assert int(cov.review_generation) == 0

    totals = contract.get_accounting_totals()
    assert int(totals.total_funded) == PRINCIPAL
    assert int(totals.total_closed_to_provider) == 0
    assert int(totals.total_closed_to_buyer) == 0
    assert int(totals.total_outstanding) == PRINCIPAL


def test_zero_and_wrong_funding_revert_atomically(
    direct_vm,
    direct_deploy,
    direct_alice,
    direct_bob,
):
    contract, mod, _ = _deploy(direct_vm, direct_deploy, direct_alice)

    direct_vm.sender = direct_alice
    direct_vm.value = 0
    with pytest.raises(Exception) as zero_exc:
        _structured_call(contract, 'open_covenant', _terms(mod, direct_bob, BASE, principal=0), _as_address(mod, buyer))
    assert not isinstance(zero_exc.value, (AttributeError, TypeError))

    direct_vm.value = PRINCIPAL - 1
    with pytest.raises(Exception) as wrong_value_exc:
        _structured_call(contract, 'open_covenant', _terms(mod, direct_bob, BASE, principal=PRINCIPAL), _as_address(mod, buyer))
    assert not isinstance(wrong_value_exc.value, (AttributeError, TypeError))
    direct_vm.value = 0

    assert int(contract.get_covenant_count()) == 0
    totals = contract.get_accounting_totals()
    assert int(totals.total_funded) == 0
    assert int(totals.total_outstanding) == 0


def test_provider_only_acceptance_delivery_and_buyer_only_challenge(
    direct_vm,
    direct_deploy,
    direct_alice,
    direct_bob,
    direct_charlie,
):
    buyer, provider, outsider = direct_alice, direct_bob, direct_charlie
    contract, mod, _ = _deploy(direct_vm, direct_deploy, buyer)
    covenant_id = _open(contract, mod, direct_vm, buyer, provider)

    direct_vm.sender = buyer
    with direct_vm.expect_revert():
        contract.accept_covenant(covenant_id, _as_address(_module(contract), provider))

    _accept(contract, direct_vm, provider, covenant_id)

    direct_vm.sender = buyer
    direct_vm.warp(_iso(BASE + 120))
    with direct_vm.expect_revert():
        _structured_call(
            contract,
            "submit_delivery",
            covenant_id,
            "unauthorized delivery",
            _evidence(mod, BASE + 120),
        )

    _deliver(contract, mod, direct_vm, provider, covenant_id)

    direct_vm.sender = outsider
    direct_vm.warp(_iso(BASE + 180))
    with direct_vm.expect_revert():
        contract.challenge_delivery(
            covenant_id,
            "outsider challenge",
            ["accuracy"],
        )

    direct_vm.sender = provider
    with direct_vm.expect_revert():
        contract.challenge_delivery(
            covenant_id,
            "provider challenge",
            ["accuracy"],
        )

    _challenge(
        contract,
        direct_vm,
        buyer,
        covenant_id,
        ["accuracy"],
    )
    cov = contract.get_covenant(covenant_id)
    assert cov.state == "CHALLENGED"
    assert int(cov.review_generation) == 1
    assert _list_strings(contract.get_challenged_criterion_ids(covenant_id)) == [
        "accuracy"
    ]


def test_unaccepted_expiry_refunds_buyer_and_duplicate_claim_reverts(
    direct_vm,
    direct_deploy,
    direct_alice,
    direct_bob,
    direct_charlie,
):
    buyer, provider, caller = direct_alice, direct_bob, direct_charlie
    contract, mod, transfers = _deploy(direct_vm, direct_deploy, buyer)
    covenant_id = _open(contract, mod, direct_vm, buyer, provider)
    cov = contract.get_covenant(covenant_id)

    direct_vm.warp(_iso(int(cov.acceptance_deadline) + 1))
    direct_vm.sender = caller
    contract.expire_unaccepted(covenant_id)

    cov = contract.get_covenant(covenant_id)
    assert cov.state == "SETTLEMENT_AUTHORIZED_BUYER"
    assert cov.closure_reason == "UNACCEPTED_EXPIRED"
    assert int(cov.outstanding_amount) == PRINCIPAL

    _claim(contract, direct_vm, caller, covenant_id)
    cov = contract.get_covenant(covenant_id)
    assert cov.state == "CLOSED_BUYER"
    assert int(cov.buyer_settlement) == PRINCIPAL
    assert int(cov.outstanding_amount) == 0
    assert transfers == [(buyer, PRINCIPAL)]

    with direct_vm.expect_revert():
        _claim(contract, direct_vm, caller, covenant_id)
    assert transfers == [(buyer, PRINCIPAL)]


def test_non_delivery_expiry_refunds_buyer(
    direct_vm,
    direct_deploy,
    direct_alice,
    direct_bob,
    direct_charlie,
):
    buyer, provider, caller = direct_alice, direct_bob, direct_charlie
    contract, mod, transfers = _deploy(direct_vm, direct_deploy, buyer)
    covenant_id = _open(contract, mod, direct_vm, buyer, provider)
    _accept(contract, direct_vm, provider, covenant_id)

    cov = contract.get_covenant(covenant_id)
    direct_vm.warp(_iso(int(cov.delivery_deadline) + 1))
    direct_vm.sender = caller
    contract.expire_non_delivery(covenant_id)

    assert contract.get_covenant(covenant_id).closure_reason == "NON_DELIVERY_EXPIRED"
    _claim(contract, direct_vm, caller, covenant_id)

    cov = contract.get_covenant(covenant_id)
    assert cov.state == "CLOSED_BUYER"
    assert transfers == [(buyer, PRINCIPAL)]

    provider_stats = contract.get_provider_stats(_as_address(mod, provider))
    buyer_stats = contract.get_buyer_stats(_as_address(mod, buyer))
    assert int(provider_stats.accepted_covenants) == 1
    assert int(provider_stats.non_deliveries) == 1
    assert int(buyer_stats.funded_covenants) == 1


def test_unchallenged_delivery_authorizes_and_pays_provider(
    direct_vm,
    direct_deploy,
    direct_alice,
    direct_bob,
    direct_charlie,
):
    buyer, provider, caller = direct_alice, direct_bob, direct_charlie
    contract, mod, transfers = _deploy(direct_vm, direct_deploy, buyer)
    covenant_id = _open(contract, mod, direct_vm, buyer, provider)
    _accept(contract, direct_vm, provider, covenant_id)
    _deliver(contract, mod, direct_vm, provider, covenant_id)

    cov = contract.get_covenant(covenant_id)
    direct_vm.warp(_iso(int(cov.challenge_deadline) + 1))
    direct_vm.sender = caller
    contract.authorize_unchallenged_settlement(covenant_id)

    cov = contract.get_covenant(covenant_id)
    assert cov.state == "SETTLEMENT_AUTHORIZED_PROVIDER"
    assert cov.closure_reason == "UNCHALLENGED"

    _claim(contract, direct_vm, caller, covenant_id)
    cov = contract.get_covenant(covenant_id)
    assert cov.state == "CLOSED_PROVIDER"
    assert int(cov.provider_settlement) == PRINCIPAL
    assert transfers == [(provider, PRINCIPAL)]


def test_full_challenge_no_failures_service_verified_provider_win_and_validator_agrees(
    direct_vm,
    direct_deploy,
    direct_alice,
    direct_bob,
    direct_charlie,
):
    buyer, provider, caller = direct_alice, direct_bob, direct_charlie
    contract, mod, transfers = _deploy(direct_vm, direct_deploy, buyer)
    covenant_id = _open(contract, mod, direct_vm, buyer, provider)
    _accept(contract, direct_vm, provider, covenant_id)
    _deliver(contract, mod, direct_vm, provider, covenant_id)
    _challenge(
        contract,
        direct_vm,
        buyer,
        covenant_id,
        ["accuracy", "freshness"],
    )

    direct_vm.clear_mocks()
    _mock_success(direct_vm, [])
    direct_vm.warp(_iso(BASE + 240))
    direct_vm.sender = caller
    contract.adjudicate_challenge(covenant_id)

    assert direct_vm.run_validator() is True
    cov = contract.get_covenant(covenant_id)
    assert cov.state == "SETTLEMENT_AUTHORIZED_PROVIDER"
    assert cov.adjudication_decision == "SERVICE_VERIFIED"
    assert cov.failure_classification == ""
    assert cov.closure_reason == "SERVICE_VERIFIED"
    assert _list_strings(contract.get_failed_criterion_ids(covenant_id)) == []

    _claim(contract, direct_vm, caller, covenant_id)
    assert transfers == [(provider, PRINCIPAL)]


def test_failed_challenged_criterion_provider_breach_buyer_win_and_validator_agrees(
    direct_vm,
    direct_deploy,
    direct_alice,
    direct_bob,
    direct_charlie,
):
    buyer, provider, caller = direct_alice, direct_bob, direct_charlie
    contract, mod, transfers = _deploy(direct_vm, direct_deploy, buyer)
    covenant_id = _open(contract, mod, direct_vm, buyer, provider)
    _accept(contract, direct_vm, provider, covenant_id)
    _deliver(contract, mod, direct_vm, provider, covenant_id)
    _challenge(
        contract,
        direct_vm,
        buyer,
        covenant_id,
        ["accuracy", "freshness"],
    )

    direct_vm.clear_mocks()
    _mock_success(direct_vm, ["accuracy"])
    direct_vm.warp(_iso(BASE + 240))
    direct_vm.sender = caller
    contract.adjudicate_challenge(covenant_id)

    assert direct_vm.run_validator() is True
    cov = contract.get_covenant(covenant_id)
    assert cov.state == "SETTLEMENT_AUTHORIZED_BUYER"
    assert cov.adjudication_decision == "PROVIDER_BREACH"
    assert cov.failure_classification == "SUBSTANTIVE_PROVIDER_BREACH"
    assert cov.closure_reason == "PROVIDER_BREACH"
    assert _list_strings(contract.get_failed_criterion_ids(covenant_id)) == [
        "accuracy"
    ]

    _claim(contract, direct_vm, caller, covenant_id)
    assert transfers == [(buyer, PRINCIPAL)]


def test_partial_challenge_no_failures_is_invalid_buyer_claim(
    direct_vm,
    direct_deploy,
    direct_alice,
    direct_bob,
    direct_charlie,
):
    buyer, provider, caller = direct_alice, direct_bob, direct_charlie
    contract, mod, _ = _deploy(direct_vm, direct_deploy, buyer)
    covenant_id = _open(contract, mod, direct_vm, buyer, provider)
    _accept(contract, direct_vm, provider, covenant_id)
    _deliver(contract, mod, direct_vm, provider, covenant_id)
    _challenge(contract, direct_vm, buyer, covenant_id, ["accuracy"])

    direct_vm.clear_mocks()
    _mock_success(direct_vm, [])
    direct_vm.warp(_iso(BASE + 240))
    direct_vm.sender = caller
    contract.adjudicate_challenge(covenant_id)

    assert direct_vm.run_validator() is True
    cov = contract.get_covenant(covenant_id)
    assert cov.state == "SETTLEMENT_AUTHORIZED_PROVIDER"
    assert cov.adjudication_decision == "BUYER_CLAIM_INVALID"
    assert cov.failure_classification == ""
    assert cov.closure_reason == "BUYER_CLAIM_INVALID"


def test_stale_evidence_requires_complete_provider_repair_then_can_verify(
    direct_vm,
    direct_deploy,
    direct_alice,
    direct_bob,
    direct_charlie,
):
    buyer, provider, caller = direct_alice, direct_bob, direct_charlie
    contract, mod, _ = _deploy(direct_vm, direct_deploy, buyer)
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
    initial = _evidence(
        mod,
        delivery_at,
        observed_at=delivery_at,
        expires_at=delivery_at + 5000,
    )
    _deliver(
        contract,
        mod,
        direct_vm,
        provider,
        covenant_id,
        at=delivery_at,
        evidence=initial,
    )
    _challenge(
        contract,
        direct_vm,
        buyer,
        covenant_id,
        ["accuracy", "freshness"],
        at=BASE + 180,
    )

    adjudicate_at = BASE + 500
    direct_vm.clear_mocks()
    _mock_success(direct_vm, [])
    direct_vm.warp(_iso(adjudicate_at))
    direct_vm.sender = caller
    contract.adjudicate_challenge(covenant_id)

    assert direct_vm.run_validator() is True
    cov = contract.get_covenant(covenant_id)
    assert cov.state == "EVIDENCE_REPAIR_REQUIRED"
    assert cov.adjudication_decision == "EVIDENCE_REPAIR_REQUIRED"
    assert cov.failure_classification == "REPAIRABLE_EVIDENCE_DEFECT"
    assert int(cov.review_generation) == 1

    auths = list(contract.get_repair_authorizations(covenant_id))
    assert [a.evidence_id for a in auths[-2:]] == ["ev-primary", "ev-corr"]
    assert [int(a.field_mask) for a in auths[-2:]] == [32, 32]

    repair_at = adjudicate_at + 10
    replacements = _replacement_evidence(
        mod,
        published_at=delivery_at - 120,
        observed_at=repair_at,
        expires_at=delivery_at + 5000,
    )

    direct_vm.warp(_iso(repair_at))
    direct_vm.sender = buyer
    with direct_vm.expect_revert():
        _structured_call(
            contract,
            "submit_evidence_repair",
            covenant_id,
            replacements,
        )

    direct_vm.sender = provider
    _structured_call(
        contract,
        "submit_evidence_repair",
        covenant_id,
        replacements,
    )

    cov = contract.get_covenant(covenant_id)
    assert cov.state == "CHALLENGED"
    assert int(cov.review_generation) == 2
    assert cov.repair_authorization_active is False
    assert _list_strings(contract.get_active_evidence_ids(covenant_id)) == [
        "ev-primary-r1",
        "ev-corr-r1",
    ]
    assert len(list(contract.get_evidence_history(covenant_id))) == 4

    direct_vm.clear_mocks()
    _mock_success(direct_vm, [])
    direct_vm.warp(_iso(repair_at + 20))
    direct_vm.sender = caller
    contract.adjudicate_challenge(covenant_id)

    assert direct_vm.run_validator() is True
    cov = contract.get_covenant(covenant_id)
    assert cov.state == "SETTLEMENT_AUTHORIZED_PROVIDER"
    assert cov.adjudication_decision == "SERVICE_VERIFIED"


def test_transient_http_5xx_enters_retry_then_next_generation_can_verify(
    direct_vm,
    direct_deploy,
    direct_alice,
    direct_bob,
    direct_charlie,
):
    buyer, provider, caller = direct_alice, direct_bob, direct_charlie
    contract, mod, _ = _deploy(direct_vm, direct_deploy, buyer)
    covenant_id = _open(contract, mod, direct_vm, buyer, provider)
    _accept(contract, direct_vm, provider, covenant_id)
    _deliver(contract, mod, direct_vm, provider, covenant_id)
    _challenge(
        contract,
        direct_vm,
        buyer,
        covenant_id,
        ["accuracy", "freshness"],
    )

    first_review = BASE + 240
    direct_vm.clear_mocks()
    _mock_http_failure(direct_vm, 503)
    direct_vm.warp(_iso(first_review))
    direct_vm.sender = caller
    contract.adjudicate_challenge(covenant_id)

    assert direct_vm.run_validator() is True
    cov = contract.get_covenant(covenant_id)
    assert cov.state == "REVIEW_RETRY_REQUIRED"
    assert cov.adjudication_decision == "REVIEW_RETRY_REQUIRED"
    assert cov.failure_classification == "TRANSIENT_REVIEW_FAILURE"
    assert int(cov.review_generation) == 1

    retry_at = first_review + 10
    direct_vm.clear_mocks()
    _mock_success(direct_vm, [])
    direct_vm.warp(_iso(retry_at))
    direct_vm.sender = caller
    contract.retry_review(covenant_id)

    assert direct_vm.run_validator() is True
    cov = contract.get_covenant(covenant_id)
    assert cov.state == "SETTLEMENT_AUTHORIZED_PROVIDER"
    assert cov.adjudication_decision == "SERVICE_VERIFIED"
    assert int(cov.review_generation) == 2


def test_two_simultaneous_covenants_accounting_isolation(
    direct_vm,
    direct_deploy,
    direct_alice,
    direct_bob,
    direct_charlie,
):
    buyer = direct_alice
    provider_one = direct_bob
    provider_two = direct_charlie
    contract, mod, transfers = _deploy(direct_vm, direct_deploy, buyer)

    first = _open(
        contract,
        mod,
        direct_vm,
        buyer,
        provider_one,
        now=BASE,
        principal=400_000,
    )
    second = _open(
        contract,
        mod,
        direct_vm,
        buyer,
        provider_two,
        now=BASE + 10,
        principal=600_000,
    )

    totals = contract.get_accounting_totals()
    assert int(totals.total_funded) == 1_000_000
    assert int(totals.total_outstanding) == 1_000_000

    first_cov = contract.get_covenant(first)
    direct_vm.warp(_iso(int(first_cov.acceptance_deadline) + 1))
    direct_vm.sender = provider_two
    contract.expire_unaccepted(first)
    _claim(contract, direct_vm, provider_two, first)

    totals = contract.get_accounting_totals()
    assert int(totals.total_funded) == 1_000_000
    assert int(totals.total_closed_to_buyer) == 400_000
    assert int(totals.total_closed_to_provider) == 0
    assert int(totals.total_outstanding) == 600_000

    assert int(contract.get_covenant(first).outstanding_amount) == 0
    assert contract.get_covenant(first).state == "CLOSED_BUYER"
    assert int(contract.get_covenant(second).outstanding_amount) == 600_000
    assert contract.get_covenant(second).state == "FUNDED"
    assert transfers == [(buyer, 400_000)]


def test_snapshot_revert_restores_direct_mode_storage(
    direct_vm,
    direct_deploy,
    direct_alice,
    direct_bob,
):
    contract, mod, _ = _deploy(direct_vm, direct_deploy, direct_alice)
    snap = direct_vm.snapshot()

    _open(contract, mod, direct_vm, direct_alice, direct_bob)
    assert int(contract.get_covenant_count()) == 1

    direct_vm.revert(snap)
    assert int(contract.get_covenant_count()) == 0
    totals = contract.get_accounting_totals()
    assert int(totals.total_funded) == 0
    assert int(totals.total_outstanding) == 0
