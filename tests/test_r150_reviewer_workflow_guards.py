from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")

def test_adjudication_application_reachability():
    helper = read("frontend/lib/adjudicator-write.ts")
    wallet = read("frontend/components/wallet-action-panel.tsx")
    required_helper = [
        'createClient',
        'testnetBradbury',
        'functionName: "adjudicate"',
        'new CalldataAddress',
        'BigInt(covenantId)',
        'value: BigInt(0)',
        'TX_ID',
    ]
    for marker in required_helper:
        assert marker in helper
    required_wallet = [
        'state === "CHALLENGED"',
        'label: "Adjudicate challenged delivery"',
        'functionName: "adjudicate"',
        'hash = await submitAdjudicationWrite({',
        'onTransactionSubmitted(hash)',
    ]
    for marker in required_wallet:
        assert marker in wallet

def test_core_repair_abi_field_order():
    abi = read("frontend/lib/accord402-abi.ts")
    start = abi.index('name: "submitEvidenceRepair"')
    end = abi.index('name: "retryReview"', start)
    block = abi[start:end]
    fields = [
        'replacesEvidenceId',
        'evidenceId',
        'authorityId',
        'authorityRevision',
        'subject',
        'kind',
        'sourceKind',
        'canonicalSource',
        'immutableVersionOrRecordId',
        'publishedAt',
        'observedAt',
        'expiresAt',
        'contentDigest',
        'isPrimary',
    ]
    positions = [block.index(f'name: "{field}"') for field in fields]
    assert positions == sorted(positions)
    assert 'type: "tuple[]"' in block

def test_provider_and_generation_repair_guards():
    wallet = read("frontend/components/wallet-action-panel.tsx")
    parser = read("frontend/lib/evidence-repair.ts")
    required_wallet = [
        'state === "EVIDENCE_REPAIR_REQUIRED"',
        'covenant.repairAuthorizationActive',
        'covenant.repairAuthorizationGeneration === covenant.reviewGeneration',
        'selected.toLowerCase() !== covenant.provider.toLowerCase()',
        'functionName: "submitEvidenceRepair"',
        'parseEvidenceRepairJson(repairEvidenceJson)',
        'onTransactionSubmitted(hash)',
    ]
    for marker in required_wallet:
        assert marker in wallet
    required_parser = [
        'export function parseEvidenceRepairJson',
        '"replacesEvidenceId"',
        'sourceKind !== "IMMUTABLE"',
        'RAW_GITHUB_PREFIX',
        '40-character lowercase commit version',
        'non-zero 32-byte contentDigest',
    ]
    for marker in required_parser:
        assert marker in parser

def test_finality_and_core_refresh_guards():
    transaction = read("frontend/lib/transaction.ts")
    observer = read("frontend/components/transaction-observer.tsx")
    app = read("frontend/components/accord402-app.tsx")
    assert 'finalized && executionSucceeded' in transaction
    assert 'submittedTxId' in observer
    assert 'observation.canonicalSuccess' in observer
    assert 'submittedTxId={submittedTxId}' in app
    assert 'onCanonicalSuccess={() => setCovenantRefreshToken((value) => value + 1)}' in app

def test_contract_review_repair_semantics():
    core = read("contracts/Accord402Core.sol")
    adjudicator = read("contracts/Accord402Adjudicator.py")
    required_core = [
        'function submitEvidenceRepair(',
        'if (!_same(covenant.state, EVIDENCE_REPAIR_REQUIRED)) revert InvalidState();',
        'if (msg.sender != covenant.provider) revert UnauthorizedCaller();',
        'covenant.reviewGeneration += 1;',
        'covenant.repairAuthorizationActive = false;',
        'covenant.state = CHALLENGED;',
        'covenant.repairAuthorizationActive = true;',
        'covenant.state = EVIDENCE_REPAIR_REQUIRED;',
    ]
    for marker in required_core:
        assert marker in core
    assert '@gl.public.write' in adjudicator
    assert 'def adjudicate(self, core_address: Address, covenant_id: u64) -> None:' in adjudicator
    assert 'CoreEvm(core_address).emit().applyAdjudicationResult' in adjudicator

def test_deadline_boundary_and_resulting_core_state_guards():
    wallet = read("frontend/components/wallet-action-panel.tsx")
    app = read("frontend/components/accord402-app.tsx")
    observer = read("frontend/components/transaction-observer.tsx")

    required_wallet = [
        "Number(covenant.retryDeadline) >= now",
        "Number(covenant.challengeDeadline) < now",
        "Number(covenant.acceptanceDeadline) < now",
        "Number(covenant.deliveryDeadline) < now",
        "Number(covenant.absoluteDisputeDeadline) < now",
        "address.toLowerCase() === covenant.buyer.toLowerCase()",
        "selected.toLowerCase() !== covenant.buyer.toLowerCase()",
        "if (seconds === 0) return \"available until this second\";",
    ]
    for marker in required_wallet:
        assert marker in wallet

    assert "Read-only by design." not in app
    assert "re-read from Core" in app
    assert "re-read from Core" in observer

def test_core_normalizes_observed_at_at_execution():
    core = read("contracts/Accord402Core.sol")
    registry = read("contracts/Accord402Registry.sol")
    solidity_test = read("tests/solidity/Accord402Core.t.sol")
    assert "normalizedEvidence[i].observedAt = nowTimestamp;" in core
    assert "normalizedReplacements[i].observedAt = nowTimestamp;" in core
    assert "registry.recordDeliveryEvidence(covenantId, normalizedEvidence, nowTimestamp, deliveryHash)" in core
    assert "input.observedAt != nowTimestamp" in registry
    assert "testSubmitDeliveryNormalizesObservedAtToExecutionTimestamp" in solidity_test
    assert "repair fixture must differ" in solidity_test

def test_r150_frontend_starts_without_assuming_seeded_covenant():
    case_lookup = read("frontend/components/case-lookup.tsx")
    app = read("frontend/components/accord402-app.tsx")
    config = read("frontend/lib/config.ts")
    client = read("frontend/lib/client.ts")

    assert "configuredCovenantId" not in case_lookup
    assert "NEXT_PUBLIC_ACCORD402_COVENANT_ID" not in config
    assert "configuredCovenantId" not in client
    assert 'const [id, setId] = useState("");' in case_lookup
    assert "void loadCase(DEFAULT_ID)" not in case_lookup
    assert "R150 does not assume a pre-seeded covenant." in case_lookup
    assert "R150 release surface" in app
    assert "deployed R150 covenant engine" in app


def test_r150_reviewer_facing_docs_are_current():
    root = read("README.md")
    docs_index = read("docs/README.md")
    status = read("docs/IMPLEMENTATION_V2_STATUS.md")
    current_deployment = read("docs/BRADBURY_CANONICAL_DEPLOYMENT_R150.md")
    current_handoff = read("docs/SUBMISSION_HANDOFF_R150.md")
    historical_deployment = read("docs/BRADBURY_CANONICAL_DEPLOYMENT_V3.md")
    historical_handoff = read("docs/SUBMISSION_HANDOFF_R149.md")

    assert "Current reviewer release: R150" in root
    assert "Current R150 reviewer evidence" in docs_index
    assert "R150 IS THE CURRENT REVIEWER RELEASE" in status
    assert "CURRENT CANONICAL R150 REVIEWER RELEASE" in current_deployment
    assert "CURRENT REVIEWER RESUBMISSION REFERENCE" in current_handoff
    assert "HISTORICAL R149 GRAPH" in historical_deployment
    assert "HISTORICAL R149 SUBMISSION SNAPSHOT" in historical_handoff

    assert "**Canonical Bradbury release:** R149" not in root
    assert "## Current canonical Bradbury deployment — R149" not in root
    assert "## Current Bradbury R149 evidence" not in docs_index
    assert "R149 CURRENT CANONICAL GRAPH" not in status
