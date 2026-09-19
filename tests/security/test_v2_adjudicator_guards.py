from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from types import ModuleType, SimpleNamespace
import hashlib
import importlib.util
import json
import sys

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "contracts" / "Accord402Adjudicator.py"
NOW = 1_789_640_000
PRIMARY_COMMIT = "1" * 40
CORR_COMMIT = "2" * 40
PRIMARY_IDENTITY = "owner-primary/repo"
CORR_IDENTITY = "owner-corroborator/repo"
PRIMARY_URL = f"https://raw.githubusercontent.com/{PRIMARY_IDENTITY}/{PRIMARY_COMMIT}/evidence.json"
CORR_URL = f"https://raw.githubusercontent.com/{CORR_IDENTITY}/{CORR_COMMIT}/evidence.json"

class _DummyAddress:
    def __init__(self, value="0x" + "11" * 20): self.as_hex = str(value)

class _DummyEvm:
    @staticmethod
    def contract_interface(cls): return cls

class _DummyPublic:
    @staticmethod
    def write(fn): return fn

class _DummyWeb:
    responses = {}
    @classmethod
    def get(cls, url, *args, **kwargs): return cls.responses[url]
    @classmethod
    def post(cls, *args, **kwargs): raise AssertionError("unexpected post")

class _DummyReturn:
    def __init__(self, calldata=None): self.calldata = calldata

def _load():
    fake = ModuleType("genlayer")
    fake.Address = _DummyAddress
    fake.u64 = int
    fake.u32 = int
    fake.gl = SimpleNamespace(
        Contract=object, evm=_DummyEvm(), public=_DummyPublic(),
        nondet=SimpleNamespace(web=_DummyWeb, exec_prompt=lambda _: '{"failed_criterion_ids":[]}'),
        vm=SimpleNamespace(UserError=ValueError, Return=_DummyReturn, run_nondet_unsafe=lambda l, v: l()),
        message_raw={"datetime": datetime.fromtimestamp(NOW, tz=timezone.utc).isoformat().replace("+00:00", "Z")},
    )
    sys.modules["genlayer"] = fake
    spec = importlib.util.spec_from_file_location("accord402_v2_adjudicator_test_module", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    # E23-R3-R7 TEMP-MIRROR-ONLY v0.3 compatibility bridge.
    import types as _accord402_types

    _accord402_root = sys.modules.get("genlayer")
    if not isinstance(_accord402_root, _accord402_types.ModuleType):
        raise RuntimeError("E23_R3_R7_ROOT_GENLAYER_NOT_MODULE")

    _accord402_child = getattr(_accord402_root, "gl", None)
    if _accord402_child is None:
        raise RuntimeError("E23_R3_R7_ROOT_GL_CHILD_MISSING")

    for _name in ("Contract", "evm", "nondet"):
        if not hasattr(_accord402_child, _name):
            raise RuntimeError("E23_R3_R7_CHILD_SURFACE_MISSING_" + _name)

    _accord402_conflicts = []
    for _name in dir(_accord402_child):
        if _name.startswith("__") or _name == "contract":
            continue
        _value = getattr(_accord402_child, _name)
        if hasattr(_accord402_root, _name):
            _existing = getattr(_accord402_root, _name)
            if _existing is not _value and _existing != _value:
                _accord402_conflicts.append(_name)
        else:
            setattr(_accord402_root, _name, _value)

    if _accord402_conflicts:
        raise RuntimeError(
            "E23_R3_R7_ROOT_SURFACE_CONFLICTS="
            + ",".join(sorted(_accord402_conflicts))
        )

    _accord402_contract_mod = _accord402_types.ModuleType("genlayer.contract")
    _accord402_contract_mod.Contract = getattr(_accord402_child, "Contract")
    _accord402_root.contract = _accord402_contract_mod

    _accord402_types_mod = _accord402_types.ModuleType("genlayer.types")
    _accord402_types_mod.__package__ = "genlayer"
    _accord402_required_types = ["Address", "u32", "u64"]
    _accord402_origins = []
    _accord402_missing = []

    for _name in _accord402_required_types:
        if hasattr(_accord402_root, _name):
            _value = getattr(_accord402_root, _name)
            _origin = "root"
        elif hasattr(_accord402_child, _name):
            _value = getattr(_accord402_child, _name)
            _origin = "child"
        else:
            _accord402_missing.append(_name)
            continue
        setattr(_accord402_types_mod, _name, _value)
        _accord402_origins.append(_name + ":" + _origin)

    if _accord402_missing:
        raise RuntimeError(
            "E23_R3_R7_REQUIRED_TYPES_MISSING="
            + ",".join(sorted(_accord402_missing))
        )

    _accord402_types_mod.__all__ = list(_accord402_required_types)
    _accord402_storage_mod = _accord402_types.ModuleType("genlayer.storage")
    _accord402_storage_mod.__package__ = "genlayer"

    _accord402_root.__path__ = []
    _accord402_root.types = _accord402_types_mod
    _accord402_root.storage = _accord402_storage_mod

    sys.modules["genlayer.types"] = _accord402_types_mod
    sys.modules["genlayer.storage"] = _accord402_storage_mod
    sys.modules["genlayer.contract"] = _accord402_contract_mod

    for _name in _accord402_required_types:
        _expected = (
            getattr(_accord402_root, _name)
            if hasattr(_accord402_root, _name)
            else getattr(_accord402_child, _name)
        )
        if getattr(_accord402_types_mod, _name) is not _expected:
            raise RuntimeError("E23_R3_R7_TYPE_IDENTITY_MISMATCH_" + _name)

    print("R7_HARNESS_TYPES_ORIGINS=" + ",".join(_accord402_origins))
    print("R7_HARNESS_TYPE_IDENTITY=PASS")
    print("R7_HARNESS_ROOT_SURFACE_IDENTITY=PASS")

    spec.loader.exec_module(module)
    return module

def _manifest(identity, url, commit, payload="qualified evidence"):
    value = {
        "schema": "ACCORD402_EVIDENCE_MANIFEST_V1",
        "authority_identity": identity, "canonical_source": url, "record_id": commit,
        "subject": "report", "kind": "PAGE", "published_at": NOW - 100,
        "expires_at": NOW + 900, "payload": payload,
    }
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()

def _evidence(evidence_id, authority_id, url, commit, body, is_primary):
    return {
        "evidence_id": evidence_id, "authority_id": authority_id, "authority_revision": 1,
        "subject": "report", "kind": "PAGE", "source_kind": "IMMUTABLE",
        "canonical_source": url, "version": commit, "published_at": NOW - 100,
        "observed_at": NOW, "expires_at": NOW + 900,
        "content_digest": hashlib.sha256(body).hexdigest(),
        "is_primary": is_primary, "replaces_evidence_id": "",
    }

def _snapshot(module, primary_body, corr_body):
    return {
        "authorities": [
            {"authority_id": "primary", "authority_revision": 1, "role": "PRIMARY",
             "identity_kind": module.EVIDENCE_IDENTITY_KIND, "identity_value": PRIMARY_IDENTITY,
             "canonical_origin": module.EVIDENCE_ORIGIN},
            {"authority_id": "corroborator", "authority_revision": 1, "role": "CORROBORATOR",
             "identity_kind": module.EVIDENCE_IDENTITY_KIND, "identity_value": CORR_IDENTITY,
             "canonical_origin": module.EVIDENCE_ORIGIN},
        ],
        "history": [
            _evidence("primary-v1", "primary", PRIMARY_URL, PRIMARY_COMMIT, primary_body, True),
            _evidence("corr-v1", "corroborator", CORR_URL, CORR_COMMIT, corr_body, False),
        ],
        "active_evidence_ids": ["primary-v1", "corr-v1"],
        "max_evidence_age": 900, "required_corroboration_count": 1,
        "repair_allowed_field_mask": module.FULL_REPAIR_MASK,
        "replay_scope": "COVENANT", "absolute_dispute_deadline": NOW + 3600,
    }

def _response(status, body, *, date=None, content_range=None):
    headers = {}
    if date is not None: headers["Date"] = date
    if content_range is not None: headers["Content-Range"] = content_range
    return SimpleNamespace(status=status, body=body, headers=headers)

def _http_date(epoch):
    return datetime.fromtimestamp(epoch, tz=timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")

def _valid_response(body):
    return _response(206, body, date=_http_date(NOW), content_range=f"bytes 0-{len(body)-1}/{len(body)}")

def test_github_source_requires_exact_commit_and_repository():
    module = _load()
    assert module._valid_github_source(PRIMARY_URL, PRIMARY_IDENTITY, PRIMARY_COMMIT)
    assert not module._valid_github_source(PRIMARY_URL.replace(PRIMARY_COMMIT, "main"), PRIMARY_IDENTITY, PRIMARY_COMMIT)
    assert not module._valid_github_source(PRIMARY_URL, "another-owner/repo", PRIMARY_COMMIT)

def test_valid_primary_and_independent_corroborator_pass():
    module = _load()
    primary = _manifest(PRIMARY_IDENTITY, PRIMARY_URL, PRIMARY_COMMIT)
    corr = _manifest(CORR_IDENTITY, CORR_URL, CORR_COMMIT)
    _DummyWeb.responses = {PRIMARY_URL: _valid_response(primary), CORR_URL: _valid_response(corr)}
    payloads, repairs, transient = module._fetch_evidence(_snapshot(module, primary, corr), NOW)
    assert transient is False and repairs == [] and len(payloads) == 2

def test_http_200_is_retry_not_terminal_evidence():
    module = _load()
    primary = _manifest(PRIMARY_IDENTITY, PRIMARY_URL, PRIMARY_COMMIT)
    corr = _manifest(CORR_IDENTITY, CORR_URL, CORR_COMMIT)
    _DummyWeb.responses = {
        PRIMARY_URL: _response(200, primary, date=_http_date(NOW), content_range=f"bytes 0-{len(primary)-1}/{len(primary)}"),
        CORR_URL: _valid_response(corr),
    }
    payloads, repairs, transient = module._fetch_evidence(_snapshot(module, primary, corr), NOW)
    assert transient is True and payloads is None and repairs is None

def test_missing_content_range_is_retry():
    module = _load()
    primary = _manifest(PRIMARY_IDENTITY, PRIMARY_URL, PRIMARY_COMMIT)
    corr = _manifest(CORR_IDENTITY, CORR_URL, CORR_COMMIT)
    _DummyWeb.responses = {PRIMARY_URL: _response(206, primary, date=_http_date(NOW)), CORR_URL: _valid_response(corr)}
    payloads, repairs, transient = module._fetch_evidence(_snapshot(module, primary, corr), NOW)
    assert transient is True and payloads is None and repairs is None

def test_stale_server_date_is_retry():
    module = _load()
    primary = _manifest(PRIMARY_IDENTITY, PRIMARY_URL, PRIMARY_COMMIT)
    corr = _manifest(CORR_IDENTITY, CORR_URL, CORR_COMMIT)
    _DummyWeb.responses = {
        PRIMARY_URL: _response(206, primary, date=_http_date(NOW - module.MAX_SERVER_DATE_SKEW - 1),
                               content_range=f"bytes 0-{len(primary)-1}/{len(primary)}"),
        CORR_URL: _valid_response(corr),
    }
    payloads, repairs, transient = module._fetch_evidence(_snapshot(module, primary, corr), NOW)
    assert transient is True and payloads is None and repairs is None

def test_payload_over_2048_bytes_requires_repair():
    module = _load()
    primary = _manifest(PRIMARY_IDENTITY, PRIMARY_URL, PRIMARY_COMMIT, "x" * (module.MAX_EVIDENCE_PAYLOAD_BYTES + 1))
    corr = _manifest(CORR_IDENTITY, CORR_URL, CORR_COMMIT)
    _DummyWeb.responses = {PRIMARY_URL: _valid_response(primary), CORR_URL: _valid_response(corr)}
    _, repairs, transient = module._fetch_evidence(_snapshot(module, primary, corr), NOW)
    assert transient is False and repairs == ["primary-v1"]

def test_http_404_requires_repair():
    module = _load()
    primary = _manifest(PRIMARY_IDENTITY, PRIMARY_URL, PRIMARY_COMMIT)
    corr = _manifest(CORR_IDENTITY, CORR_URL, CORR_COMMIT)
    _DummyWeb.responses = {PRIMARY_URL: _response(404, b""), CORR_URL: _valid_response(corr)}
    _, repairs, transient = module._fetch_evidence(_snapshot(module, primary, corr), NOW)
    assert transient is False and repairs == ["primary-v1"]
