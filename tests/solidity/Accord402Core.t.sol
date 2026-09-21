// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Accord402Registry} from "../../contracts/Accord402Registry.sol";
import {Accord402Core} from "../../contracts/Accord402Core.sol";

interface Vm {
    function warp(uint256 timestamp) external;
    function prank(address sender) external;
    function deal(address account, uint256 newBalance) external;
    function log(string calldata message) external;
}

contract MockSettlementVault {
    mapping(address => bool) public registered;
    mapping(bytes32 => bool) public delivered;
    uint256 public lastAmount;
    address public lastRecipient;

    function register(address recipient) external {
        registered[recipient] = true;
    }

    function is_registered_payout(address recipient) external view returns (bool) {
        return registered[recipient];
    }

    function credit(uint256 covenantId, address, address recipient) external payable {
        bytes32 key = keccak256(abi.encode(msg.sender, covenantId));
        require(!delivered[key], "duplicate");
        delivered[key] = true;
        lastAmount = msg.value;
        lastRecipient = recipient;
        (bool ok,) = payable(recipient).call{value: msg.value}("");
        require(ok, "transfer");
    }
}

contract Accord402CoreTest {
    Vm private constant vm = Vm(address(uint160(uint256(keccak256("hevm cheat code")))));
    address private constant BUYER = address(0x1001);
    address private constant PROVIDER = address(0x1002);
    address private constant BUYER_PAYOUT = address(0x1003);
    address private constant PROVIDER_PAYOUT = address(0x1004);

    Accord402Registry private registry;
    Accord402Core private core;
    MockSettlementVault private vault;

    function setUp() public {
        vm.warp(1_700_000_000);
        registry = new Accord402Registry();
        vault = new MockSettlementVault();
        vault.register(BUYER_PAYOUT);
        vault.register(PROVIDER_PAYOUT);
        core = new Accord402Core(address(registry), address(this), address(vault));
        vm.deal(BUYER, 10 ether);
        vm.deal(address(this), 10 ether);
    }

    function _terms() private view returns (Accord402Core.OpenCovenantParams memory terms) {
        Accord402Registry.CriterionInput[] memory criteria = new Accord402Registry.CriterionInput[](1);
        criteria[0] =
            Accord402Registry.CriterionInput("delivery_matches", "The delivery contains the contracted report.");
        Accord402Registry.AuthorityBindingInput[] memory authorities = new Accord402Registry.AuthorityBindingInput[](2);
        authorities[0] = Accord402Registry.AuthorityBindingInput(
            "primary", 1, "PRIMARY", "GITHUB_REPOSITORY", "owner-primary/repo", "https://raw.githubusercontent.com"
        );
        authorities[1] = Accord402Registry.AuthorityBindingInput(
            "corroborator",
            1,
            "CORROBORATOR",
            "GITHUB_REPOSITORY",
            "owner-corroborator/repo",
            "https://raw.githubusercontent.com"
        );
        terms.provider = PROVIDER;
        terms.principal = 1 ether;
        terms.serviceSpec = "Deliver the contracted report before the deadline.";
        terms.acceptanceDeadline = uint64(block.timestamp + 120);
        terms.deliveryDeadline = uint64(block.timestamp + 600);
        terms.challengeDuration = 120;
        terms.absoluteDisputeDeadline = uint64(block.timestamp + 10000);
        terms.evidenceRepairWindow = 120;
        terms.reviewRetryWindow = 120;
        terms.maxReviewGenerations = 2;
        terms.maxEvidenceAge = 900;
        terms.requiredCorroborationCount = 1;
        terms.repairAllowedFieldMask = 252;
        terms.replayScope = "COVENANT";
        terms.criteria = criteria;
        terms.authorityBindings = authorities;
    }

    function _evidence(uint64 observedAt) private pure returns (Accord402Registry.EvidenceInput[] memory evidence) {
        evidence = new Accord402Registry.EvidenceInput[](2);
        evidence[0] = Accord402Registry.EvidenceInput(
            "primary-v1",
            "primary",
            1,
            "report",
            "PAGE",
            "IMMUTABLE",
            "https://raw.githubusercontent.com/owner-primary/repo/1111111111111111111111111111111111111111/report.json",
            "1111111111111111111111111111111111111111",
            observedAt - 10,
            observedAt,
            observedAt + 600,
            bytes32(uint256(1)),
            true
        );
        evidence[1] = Accord402Registry.EvidenceInput(
            "corroborator-v1",
            "corroborator",
            1,
            "report",
            "PAGE",
            "IMMUTABLE",
            "https://raw.githubusercontent.com/owner-corroborator/repo/2222222222222222222222222222222222222222/report.json",
            "2222222222222222222222222222222222222222",
            observedAt - 10,
            observedAt,
            observedAt + 600,
            bytes32(uint256(2)),
            false
        );
    }

    function _openAcceptedAndDelivered() private returns (uint64 covenantId) {
        Accord402Core.OpenCovenantParams memory terms = _terms();
        vm.prank(BUYER);
        covenantId = core.openCovenant{value: terms.principal}(terms, BUYER_PAYOUT);
        vm.prank(PROVIDER);
        core.acceptCovenant(covenantId, PROVIDER_PAYOUT);
        vm.prank(PROVIDER);
        core.submitDelivery(covenantId, "report delivered", _evidence(1_700_000_000));
    }

    function testFullDeterministicLifecycleAndSettlement() public {
        Accord402Core.OpenCovenantParams memory terms = _terms();
        vm.prank(BUYER);
        uint64 covenantId = core.openCovenant{value: terms.principal}(terms, BUYER_PAYOUT);
        vm.prank(PROVIDER);
        core.acceptCovenant(covenantId, PROVIDER_PAYOUT);
        vm.prank(PROVIDER);
        core.submitDelivery(covenantId, "report delivered", _evidence(uint64(block.timestamp)));

        string[] memory challenged = new string[](1);
        challenged[0] = "delivery_matches";
        vm.prank(BUYER);
        core.challengeDelivery(covenantId, "The report is disputed.", challenged);

        string[] memory failed = new string[](0);
        string[] memory repairIds = new string[](0);
        uint32[] memory repairMasks = new uint32[](0);
        core.applyAdjudicationResult(
            covenantId,
            _coreSnapshotHash(covenantId),
            _registrySnapshotHash(covenantId),
            core.getEvidencePolicyHashHex(covenantId),
            core.getActiveEvidenceSetHashHex(covenantId),
            1,
            "SERVICE_VERIFIED",
            challenged,
            failed,
            "",
            repairIds,
            repairMasks
        );

        Accord402Core.Covenant memory beforeClaim = core.getCovenant(covenantId);
        require(_same(beforeClaim.state, "SETTLEMENT_AUTHORIZED_PROVIDER"), "provider not authorized");
        core.claimSettlement(covenantId);
        Accord402Core.Covenant memory closed = core.getCovenant(covenantId);
        require(_same(closed.state, "CLOSED_PROVIDER"), "not closed");
        require(closed.outstandingAmount == 0, "outstanding");
        require(vault.lastAmount() == 1 ether, "wrong payout");
        require(vault.lastRecipient() == PROVIDER_PAYOUT, "wrong recipient");
        (uint256 funded, uint256 providerClosed, uint256 buyerClosed, uint256 outstanding) = core.getAccountingTotals();
        require(funded == providerClosed + buyerClosed + outstanding, "accounting");

        (bool ok,) = address(core).call(abi.encodeWithSelector(core.claimSettlement.selector, covenantId));
        require(!ok, "duplicate claim accepted");
    }

    function testSubmitDeliveryNormalizesObservedAtToExecutionTimestamp() public {
        Accord402Core.OpenCovenantParams memory terms = _terms();
        vm.prank(BUYER);
        uint64 covenantId = core.openCovenant{value: terms.principal}(terms, BUYER_PAYOUT);
        vm.prank(PROVIDER);
        core.acceptCovenant(covenantId, PROVIDER_PAYOUT);

        uint64 callerObservedAt = uint64(block.timestamp - 60);
        require(callerObservedAt != uint64(block.timestamp), "delivery fixture must differ");
        Accord402Registry.EvidenceInput[] memory evidence = _evidence(callerObservedAt);

        vm.prank(PROVIDER);
        core.submitDelivery(covenantId, "normalized delivery timestamp", evidence);

        require(_same(core.getReviewState(covenantId), "DELIVERED"), "delivery normalization failed");
    }

    function testFinalizedCallbackBindingsRejectStaleGeneration() public {
        Accord402Core.OpenCovenantParams memory terms = _terms();
        vm.prank(BUYER);
        uint64 covenantId = core.openCovenant{value: terms.principal}(terms, BUYER_PAYOUT);
        vm.prank(PROVIDER);
        core.acceptCovenant(covenantId, PROVIDER_PAYOUT);
        vm.prank(PROVIDER);
        core.submitDelivery(covenantId, "report delivered", _evidence(uint64(block.timestamp)));
        string[] memory challenged = new string[](1);
        challenged[0] = "delivery_matches";
        vm.prank(BUYER);
        core.challengeDelivery(covenantId, "dispute", challenged);
        string[] memory empty = new string[](0);
        (bool ok,) = address(core)
            .call(
                abi.encodeWithSelector(
                    core.applyAdjudicationResult.selector,
                    covenantId,
                    _hex(core.getServiceSpecHash(covenantId)),
                    _hex(core.getDeliveryHash(covenantId)),
                    core.getEvidencePolicyHashHex(covenantId),
                    core.getActiveEvidenceSetHashHex(covenantId),
                    2,
                    "SERVICE_VERIFIED",
                    challenged,
                    empty,
                    "",
                    empty,
                    empty
                )
            );
        require(!ok, "stale result accepted");
    }

    function testOnlyPinnedAdjudicatorCanApplyFinalizedCallback() public {
        uint64 covenantId = _openAcceptedAndDelivered();
        string[] memory challenged = new string[](1);
        challenged[0] = "delivery_matches";
        vm.prank(BUYER);
        core.challengeDelivery(covenantId, "unauthorized callback", challenged);
        string[] memory empty = new string[](0);
        string memory serviceHash = _hex(core.getServiceSpecHash(covenantId));
        string memory deliveryHash = _hex(core.getDeliveryHash(covenantId));
        string memory policyHash = core.getEvidencePolicyHashHex(covenantId);
        string memory evidenceSetHash = core.getActiveEvidenceSetHashHex(covenantId);
        vm.prank(BUYER);
        (bool ok,) = address(core)
            .call(
                abi.encodeWithSelector(
                    core.applyAdjudicationResult.selector,
                    covenantId,
                    serviceHash,
                    deliveryHash,
                    policyHash,
                    evidenceSetHash,
                    1,
                    "SERVICE_VERIFIED",
                    challenged,
                    empty,
                    "",
                    empty,
                    empty
                )
            );
        require(!ok, "unauthorized callback accepted");
    }

    function testEvidenceIdsAreScopedToEachCovenant() public {
        Accord402Core.OpenCovenantParams memory first = _terms();
        vm.prank(BUYER);
        uint64 firstId = core.openCovenant{value: first.principal}(first, BUYER_PAYOUT);
        vm.prank(PROVIDER);
        core.acceptCovenant(firstId, PROVIDER_PAYOUT);
        vm.prank(PROVIDER);
        core.submitDelivery(firstId, "first report", _evidence(uint64(block.timestamp)));

        Accord402Core.OpenCovenantParams memory second = _terms();
        vm.prank(BUYER);
        uint64 secondId = core.openCovenant{value: second.principal}(second, BUYER_PAYOUT);
        vm.prank(PROVIDER);
        core.acceptCovenant(secondId, PROVIDER_PAYOUT);
        vm.prank(PROVIDER);
        core.submitDelivery(secondId, "second report", _evidence(uint64(block.timestamp)));

        require(_same(core.getReviewState(firstId), "DELIVERED"), "first isolation");
        require(_same(core.getReviewState(secondId), "DELIVERED"), "second isolation");
    }

    function testAcceptanceExpiryReturnsBuyerAndPreservesAccounting() public {
        Accord402Core.OpenCovenantParams memory terms = _terms();
        vm.prank(BUYER);
        uint64 covenantId = core.openCovenant{value: terms.principal}(terms, BUYER_PAYOUT);
        vm.warp(block.timestamp + 121);
        core.expireUnaccepted(covenantId);
        core.claimSettlement(covenantId);
        Accord402Core.Covenant memory closed = core.getCovenant(covenantId);
        require(_same(closed.state, "CLOSED_BUYER"), "buyer not refunded");
        require(vault.lastRecipient() == BUYER_PAYOUT, "wrong refund recipient");
        require(vault.lastAmount() == terms.principal, "wrong refund amount");
        (uint256 funded, uint256 providerClosed, uint256 buyerClosed, uint256 outstanding) = core.getAccountingTotals();
        require(funded == providerClosed + buyerClosed + outstanding, "accounting");
    }

    function testEvidenceMustUseBoundAuthorityOrigin() public {
        Accord402Core.OpenCovenantParams memory terms = _terms();
        vm.prank(BUYER);
        uint64 covenantId = core.openCovenant{value: terms.principal}(terms, BUYER_PAYOUT);
        vm.prank(PROVIDER);
        core.acceptCovenant(covenantId, PROVIDER_PAYOUT);
        Accord402Registry.EvidenceInput[] memory evidence = _evidence(uint64(block.timestamp));
        evidence[0].canonicalSource = "https://attacker.example/report.json";
        (bool ok,) = address(core)
            .call(abi.encodeWithSelector(core.submitDelivery.selector, covenantId, "report delivered", evidence));
        require(!ok, "unbound evidence origin accepted");
    }

    function testAuthorityIdentitiesMustBeIndependent() public {
        Accord402Core.OpenCovenantParams memory terms = _terms();
        terms.authorityBindings[1].identityValue = terms.authorityBindings[0].identityValue;
        (bool ok,) = address(core).call{value: terms.principal}(
            abi.encodeWithSelector(core.openCovenant.selector, terms, BUYER_PAYOUT)
        );
        require(!ok, "duplicate authority identity accepted");
    }

    function testNonDeliveryExpiryReturnsBuyer() public {
        Accord402Core.OpenCovenantParams memory terms = _terms();
        vm.prank(BUYER);
        uint64 covenantId = core.openCovenant{value: terms.principal}(terms, BUYER_PAYOUT);
        vm.prank(PROVIDER);
        core.acceptCovenant(covenantId, PROVIDER_PAYOUT);
        vm.warp(1_700_000_601);
        core.expireNonDelivery(covenantId);
        core.claimSettlement(covenantId);
        require(_same(core.getReviewState(covenantId), "CLOSED_BUYER"), "non-delivery not refunded");
        require(vault.lastRecipient() == BUYER_PAYOUT, "wrong non-delivery recipient");
    }

    function testUnchallengedDeliverySettlesProvider() public {
        uint64 covenantId = _openAcceptedAndDelivered();
        vm.warp(1_700_000_121);
        core.authorizeUnchallengedSettlement(covenantId);
        core.claimSettlement(covenantId);
        require(_same(core.getReviewState(covenantId), "CLOSED_PROVIDER"), "unchallenged not settled");
        require(vault.lastRecipient() == PROVIDER_PAYOUT, "wrong unchallenged recipient");
        require(vault.lastAmount() == 1 ether, "wrong unchallenged amount");
    }

    function testTransientReviewCanAdvanceExactlyOneGeneration() public {
        uint64 covenantId = _openAcceptedAndDelivered();
        string[] memory challenged = new string[](1);
        challenged[0] = "delivery_matches";
        vm.prank(BUYER);
        core.challengeDelivery(covenantId, "temporary review failure", challenged);
        string[] memory empty = new string[](0);
        core.applyAdjudicationResult(
            covenantId,
            _coreSnapshotHash(covenantId),
            _registrySnapshotHash(covenantId),
            core.getEvidencePolicyHashHex(covenantId),
            core.getActiveEvidenceSetHashHex(covenantId),
            1,
            "REVIEW_RETRY_REQUIRED",
            challenged,
            empty,
            "TRANSIENT_REVIEW_FAILURE",
            empty,
            new uint32[](0)
        );
        core.retryReview(covenantId);
        Accord402Core.Covenant memory retried = core.getCovenant(covenantId);
        require(_same(retried.state, "CHALLENGED"), "retry did not reopen review");
        require(retried.reviewGeneration == 2, "retry generation not incremented");
    }

    function testRepairAppendsFreshEvidenceAndIncrementsGeneration() public {
        Accord402Core.OpenCovenantParams memory terms = _terms();
        vm.prank(BUYER);
        uint64 covenantId = core.openCovenant{value: terms.principal}(terms, BUYER_PAYOUT);
        vm.prank(PROVIDER);
        core.acceptCovenant(covenantId, PROVIDER_PAYOUT);
        vm.prank(PROVIDER);
        core.submitDelivery(covenantId, "report delivered", _evidence(uint64(block.timestamp)));
        string[] memory challenged = new string[](1);
        challenged[0] = "delivery_matches";
        vm.prank(BUYER);
        core.challengeDelivery(covenantId, "evidence needs repair", challenged);
        bytes32 deliveryHashBefore = core.getDeliveryHash(covenantId);

        string[] memory empty = new string[](0);
        string[] memory repairIds = new string[](1);
        repairIds[0] = "primary-v1";
        uint32[] memory repairMasks = new uint32[](1);
        repairMasks[0] = 160;
        core.applyAdjudicationResult(
            covenantId,
            _coreSnapshotHash(covenantId),
            _registrySnapshotHash(covenantId),
            core.getEvidencePolicyHashHex(covenantId),
            core.getActiveEvidenceSetHashHex(covenantId),
            1,
            "EVIDENCE_REPAIR_REQUIRED",
            challenged,
            empty,
            "REPAIRABLE_EVIDENCE_DEFECT",
            repairIds,
            repairMasks
        );
        vm.warp(block.timestamp + 10);
        Accord402Registry.EvidenceReplacementInput[] memory replacement =
            new Accord402Registry.EvidenceReplacementInput[](1);
        replacement[0] = Accord402Registry.EvidenceReplacementInput(
            "primary-v1",
            "primary-v2",
            "primary",
            1,
            "report",
            "PAGE",
            "IMMUTABLE",
            "https://raw.githubusercontent.com/owner-primary/repo/1111111111111111111111111111111111111111/report.json",
            "1111111111111111111111111111111111111111",
            uint64(1_699_999_990),
            uint64(1_699_999_999),
            uint64(1_700_000_600),
            bytes32(uint256(3)),
            true
        );
        require(
            replacement[0].observedAt != uint64(block.timestamp),
            "repair fixture must differ"
        );
        vm.prank(PROVIDER);
        core.submitEvidenceRepair(covenantId, replacement);
        Accord402Core.Covenant memory repaired = core.getCovenant(covenantId);
        require(_same(repaired.state, "CHALLENGED"), "repair did not reopen review");
        require(repaired.reviewGeneration == 2, "generation not incremented");
        require(repaired.deliveryHash == deliveryHashBefore, "delivery hash mutated");
        require(repaired.activeEvidenceSetHash != bytes32(0), "missing active evidence hash");
    }

    function _coreSnapshotHash(uint64 covenantId) private view returns (string memory) {
        return _hex(sha256(bytes(core.getAdjudicationSnapshot(covenantId))));
    }

    function _registrySnapshotHash(uint64 covenantId) private view returns (string memory) {
        return _hex(sha256(bytes(registry.getAdjudicationSnapshot(address(core), covenantId))));
    }

    function _hex(bytes32 value) private pure returns (string memory) {
        bytes16 symbols = "0123456789abcdef";
        bytes memory out = new bytes(64);
        for (uint256 i; i < 32; ++i) {
            uint8 b = uint8(value[i]);
            out[i * 2] = symbols[b >> 4];
            out[i * 2 + 1] = symbols[b & 0x0f];
        }
        return string(out);
    }

    function _same(string memory a, string memory b) private pure returns (bool) {
        return keccak256(bytes(a)) == keccak256(bytes(b));
    }
}
