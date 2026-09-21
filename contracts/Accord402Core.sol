// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Accord402Registry} from "./Accord402Registry.sol";

interface IAccord402SettlementVault {
    function is_registered_payout(address recipient) external view returns (bool);
    function credit(uint256 covenantId, address beneficiary, address recipient) external payable;
}

/// @title Accord402Core
/// @notice The deterministic escrow and covenant state machine.
/// @dev Semantic adjudication is deliberately outside this contract. Only the
///      immutable Adjudicator address may submit a finalized result.
contract Accord402Core {
    string internal constant FUNDED = "FUNDED";
    string internal constant SERVICE_ACCEPTED = "SERVICE_ACCEPTED";
    string internal constant DELIVERED = "DELIVERED";
    string internal constant CHALLENGED = "CHALLENGED";
    string internal constant EVIDENCE_REPAIR_REQUIRED = "EVIDENCE_REPAIR_REQUIRED";
    string internal constant REVIEW_RETRY_REQUIRED = "REVIEW_RETRY_REQUIRED";
    string internal constant SETTLEMENT_AUTHORIZED_PROVIDER = "SETTLEMENT_AUTHORIZED_PROVIDER";
    string internal constant SETTLEMENT_AUTHORIZED_BUYER = "SETTLEMENT_AUTHORIZED_BUYER";
    string internal constant CLOSED_PROVIDER = "CLOSED_PROVIDER";
    string internal constant CLOSED_BUYER = "CLOSED_BUYER";

    string internal constant SERVICE_VERIFIED = "SERVICE_VERIFIED";
    string internal constant PROVIDER_BREACH = "PROVIDER_BREACH";
    string internal constant BUYER_CLAIM_INVALID = "BUYER_CLAIM_INVALID";
    string internal constant REPAIRABLE_EVIDENCE_DEFECT = "REPAIRABLE_EVIDENCE_DEFECT";
    string internal constant TRANSIENT_REVIEW_FAILURE = "TRANSIENT_REVIEW_FAILURE";

    uint64 internal constant MIN_ACCEPTANCE_LEAD = 60;
    uint64 internal constant MAX_ACCEPTANCE_LEAD = 604800;
    uint64 internal constant MAX_DELIVERY_LEAD = 1209600;
    uint64 internal constant MIN_CHALLENGE_DURATION = 60;
    uint64 internal constant MAX_CHALLENGE_DURATION = 604800;
    uint64 internal constant MIN_REPAIR_WINDOW = 60;
    uint64 internal constant MAX_REPAIR_WINDOW = 86400;
    uint64 internal constant MIN_RETRY_WINDOW = 60;
    uint64 internal constant MAX_RETRY_WINDOW = 86400;
    uint64 internal constant MIN_MAX_EVIDENCE_AGE = 1;
    uint64 internal constant MAX_MAX_EVIDENCE_AGE = 2592000;
    uint64 internal constant MAX_ABSOLUTE_HORIZON = 2592000;
    uint64 internal constant REVIEW_GUARD_TIME = 3600;

    struct OpenCovenantParams {
        address provider;
        uint256 principal;
        string serviceSpec;
        uint64 acceptanceDeadline;
        uint64 deliveryDeadline;
        uint64 challengeDuration;
        uint64 absoluteDisputeDeadline;
        uint64 evidenceRepairWindow;
        uint64 reviewRetryWindow;
        uint32 maxReviewGenerations;
        uint64 maxEvidenceAge;
        uint32 requiredCorroborationCount;
        uint32 repairAllowedFieldMask;
        string replayScope;
        Accord402Registry.CriterionInput[] criteria;
        Accord402Registry.AuthorityBindingInput[] authorityBindings;
    }

    struct Covenant {
        bool exists;
        uint64 covenantId;
        address buyer;
        address provider;
        address buyerSettlementRecipient;
        address providerSettlementRecipient;
        uint256 fundedAmount;
        uint256 outstandingAmount;
        uint256 providerSettlement;
        uint256 buyerSettlement;
        string state;
        bytes32 serviceSpecHash;
        bytes32 evidencePolicyHash;
        uint64 openedAt;
        uint64 acceptanceDeadline;
        uint64 deliveryDeadline;
        uint64 challengeDuration;
        uint64 absoluteDisputeDeadline;
        uint64 evidenceRepairWindow;
        uint64 reviewRetryWindow;
        uint32 maxReviewGenerations;
        uint64 maxEvidenceAge;
        uint32 requiredCorroborationCount;
        uint32 repairAllowedFieldMask;
        string replayScope;
        uint64 acceptedAt;
        uint64 deliveredAt;
        uint64 challengeDeadline;
        uint64 challengedAt;
        uint64 repairDeadline;
        uint64 retryDeadline;
        uint64 closedAt;
        string deliveryPayload;
        bytes32 deliveryHash;
        bytes32 activeEvidenceSetHash;
        uint32 repairAuthorizationGeneration;
        bool repairAuthorizationActive;
        string challengeClaim;
        uint32 reviewGeneration;
        string adjudicationDecision;
        string failureClassification;
        string closureReason;
        string settlementDirection;
        bool settlementClaimed;
    }

    struct RepairAuthorization {
        string evidenceId;
        uint32 fieldMask;
    }

    Accord402Registry public immutable registry;
    address public immutable adjudicator;
    IAccord402SettlementVault public immutable settlementVault;

    uint64 public covenantCount;
    uint256 public totalFunded;
    uint256 public totalClosedToProvider;
    uint256 public totalClosedToBuyer;
    uint256 public totalOutstanding;

    mapping(uint64 => Covenant) private _covenants;
    mapping(uint64 => string[]) private _challengedCriterionIds;
    mapping(uint64 => string[]) private _failedCriterionIds;
    mapping(uint64 => RepairAuthorization[]) private _repairAuthorizations;

    error ZeroDependency();
    error InvalidValue();
    error InvalidProvider();
    error SelfCovenant();
    error InvalidState();
    error UnauthorizedCaller();
    error DeadlinePassed();
    error DeadlineNotPassed();
    error InvalidDeadline();
    error InvalidGeneration();
    error InvalidInput();
    error UnregisteredPayoutRecipient();
    error InvalidAdjudicationCaller();
    error StaleAdjudicationResult();
    error InvalidAdjudicationWire();
    error InvalidRepairAuthorization();
    error SettlementAlreadyClaimed();
    error AccountingUnderflow();
    error SettlementTransferFailed();

    event CovenantOpened(uint64 indexed covenantId, address indexed buyer, address indexed provider, uint256 principal);
    event CovenantAccepted(uint64 indexed covenantId, address indexed provider, address payoutRecipient);
    event DeliverySubmitted(uint64 indexed covenantId, bytes32 deliveryHash, bytes32 activeEvidenceSetHash);
    event DeliveryChallenged(uint64 indexed covenantId, uint32 reviewGeneration);
    event SettlementAuthorized(uint64 indexed covenantId, string direction, string reason);
    event AdjudicationApplied(uint64 indexed covenantId, uint32 reviewGeneration, string decision);
    event EvidenceRepairRequired(uint64 indexed covenantId, uint32 reviewGeneration, uint64 deadline);
    event ReviewRetryRequired(uint64 indexed covenantId, uint32 reviewGeneration, uint64 deadline);
    event SettlementClaimed(
        uint64 indexed covenantId, address indexed beneficiary, address indexed recipient, uint256 amount
    );

    constructor(address registryAddress, address adjudicatorAddress, address vaultAddress) {
        if (registryAddress == address(0) || adjudicatorAddress == address(0) || vaultAddress == address(0)) {
            revert ZeroDependency();
        }
        registry = Accord402Registry(registryAddress);
        adjudicator = adjudicatorAddress;
        settlementVault = IAccord402SettlementVault(vaultAddress);
    }

    function openCovenant(OpenCovenantParams calldata terms, address buyerSettlementRecipient)
        external
        payable
        returns (uint64 covenantId)
    {
        if (terms.provider == address(0) || terms.provider == msg.sender) revert InvalidProvider();
        if (terms.principal == 0 || msg.value != terms.principal) revert InvalidValue();
        if (!settlementVault.is_registered_payout(buyerSettlementRecipient)) revert UnregisteredPayoutRecipient();
        uint64 nowTimestamp = _now();
        if (
            terms.acceptanceDeadline < nowTimestamp + MIN_ACCEPTANCE_LEAD
                || terms.acceptanceDeadline > nowTimestamp + MAX_ACCEPTANCE_LEAD
        ) revert InvalidDeadline();
        if (
            terms.deliveryDeadline <= terms.acceptanceDeadline
                || terms.deliveryDeadline > nowTimestamp + MAX_DELIVERY_LEAD
        ) revert InvalidDeadline();
        if (terms.challengeDuration < MIN_CHALLENGE_DURATION || terms.challengeDuration > MAX_CHALLENGE_DURATION) {
            revert InvalidDeadline();
        }
        if (terms.evidenceRepairWindow < MIN_REPAIR_WINDOW || terms.evidenceRepairWindow > MAX_REPAIR_WINDOW) {
            revert InvalidDeadline();
        }
        if (terms.reviewRetryWindow < MIN_RETRY_WINDOW || terms.reviewRetryWindow > MAX_RETRY_WINDOW) {
            revert InvalidDeadline();
        }
        if (
            terms.absoluteDisputeDeadline <= terms.deliveryDeadline + terms.challengeDuration + REVIEW_GUARD_TIME
                || terms.absoluteDisputeDeadline > nowTimestamp + MAX_ABSOLUTE_HORIZON
        ) revert InvalidDeadline();
        if (
            terms.maxReviewGenerations == 0 || terms.maxReviewGenerations > 4
                || terms.maxEvidenceAge < MIN_MAX_EVIDENCE_AGE || terms.maxEvidenceAge > MAX_MAX_EVIDENCE_AGE
        ) revert InvalidInput();
        if (
            terms.criteria.length == 0 || terms.criteria.length > 16 || terms.authorityBindings.length == 0
                || terms.authorityBindings.length > 16
        ) revert InvalidInput();
        if (covenantCount == type(uint64).max) revert InvalidInput();

        covenantId = ++covenantCount;
        (bytes32 serviceHash, bytes32 evidenceHash) = registry.createPolicy(
            covenantId,
            terms.serviceSpec,
            terms.criteria,
            terms.authorityBindings,
            terms.maxEvidenceAge,
            terms.requiredCorroborationCount,
            terms.repairAllowedFieldMask,
            terms.replayScope
        );

        Covenant storage covenant = _covenants[covenantId];
        covenant.exists = true;
        covenant.covenantId = covenantId;
        covenant.buyer = msg.sender;
        covenant.provider = terms.provider;
        covenant.buyerSettlementRecipient = buyerSettlementRecipient;
        covenant.fundedAmount = terms.principal;
        covenant.outstandingAmount = terms.principal;
        covenant.state = FUNDED;
        covenant.serviceSpecHash = serviceHash;
        covenant.evidencePolicyHash = evidenceHash;
        covenant.openedAt = nowTimestamp;
        covenant.acceptanceDeadline = terms.acceptanceDeadline;
        covenant.deliveryDeadline = terms.deliveryDeadline;
        covenant.challengeDuration = terms.challengeDuration;
        covenant.absoluteDisputeDeadline = terms.absoluteDisputeDeadline;
        covenant.evidenceRepairWindow = terms.evidenceRepairWindow;
        covenant.reviewRetryWindow = terms.reviewRetryWindow;
        covenant.maxReviewGenerations = terms.maxReviewGenerations;
        covenant.maxEvidenceAge = terms.maxEvidenceAge;
        covenant.requiredCorroborationCount = terms.requiredCorroborationCount;
        covenant.repairAllowedFieldMask = terms.repairAllowedFieldMask;
        covenant.replayScope = terms.replayScope;
        totalFunded += terms.principal;
        totalOutstanding += terms.principal;
        emit CovenantOpened(covenantId, msg.sender, terms.provider, terms.principal);
    }

    function acceptCovenant(uint64 covenantId, address providerSettlementRecipient) external {
        Covenant storage covenant = _requireCovenant(covenantId);
        if (!_same(covenant.state, FUNDED)) revert InvalidState();
        if (msg.sender != covenant.provider) revert UnauthorizedCaller();
        if (_now() > covenant.acceptanceDeadline) revert DeadlinePassed();
        if (!settlementVault.is_registered_payout(providerSettlementRecipient)) revert UnregisteredPayoutRecipient();
        covenant.providerSettlementRecipient = providerSettlementRecipient;
        covenant.acceptedAt = _now();
        covenant.state = SERVICE_ACCEPTED;
        emit CovenantAccepted(covenantId, msg.sender, providerSettlementRecipient);
    }

    function expireUnaccepted(uint64 covenantId) external {
        Covenant storage covenant = _requireCovenant(covenantId);
        if (!_same(covenant.state, FUNDED)) revert InvalidState();
        if (_now() <= covenant.acceptanceDeadline) revert DeadlineNotPassed();
        _authorizeBuyer(covenant, "UNACCEPTED_EXPIRED");
    }

    function submitDelivery(
        uint64 covenantId,
        string calldata deliveryPayload,
        Accord402Registry.EvidenceInput[] calldata evidence
    ) external {
        Covenant storage covenant = _requireCovenant(covenantId);
        if (!_same(covenant.state, SERVICE_ACCEPTED)) revert InvalidState();
        if (msg.sender != covenant.provider) revert UnauthorizedCaller();
        uint64 nowTimestamp = _now();
        if (nowTimestamp > covenant.deliveryDeadline) revert DeadlinePassed();
        if (
            bytes(deliveryPayload).length == 0 || bytes(deliveryPayload).length > 65536 || evidence.length == 0
                || evidence.length > 16
        ) revert InvalidInput();
        Accord402Registry.EvidenceInput[] memory normalizedEvidence =
            new Accord402Registry.EvidenceInput[](evidence.length);
        for (uint256 i; i < evidence.length; ++i) {
            normalizedEvidence[i] = evidence[i];
            normalizedEvidence[i].observedAt = nowTimestamp;
        }

        bytes32 deliveryHash =
            sha256(abi.encode("ACCORD402:DELIVERY:V1", covenantId, covenant.provider, nowTimestamp, deliveryPayload));
        bytes32 activeEvidenceSetHash =
            registry.recordDeliveryEvidence(covenantId, normalizedEvidence, nowTimestamp, deliveryHash);
        covenant.deliveryPayload = deliveryPayload;
        covenant.deliveryHash = deliveryHash;
        covenant.activeEvidenceSetHash = activeEvidenceSetHash;
        covenant.deliveredAt = nowTimestamp;
        covenant.challengeDeadline = nowTimestamp + covenant.challengeDuration;
        covenant.state = DELIVERED;
        emit DeliverySubmitted(covenantId, deliveryHash, activeEvidenceSetHash);
    }

    function expireNonDelivery(uint64 covenantId) external {
        Covenant storage covenant = _requireCovenant(covenantId);
        if (!_same(covenant.state, SERVICE_ACCEPTED)) revert InvalidState();
        if (_now() <= covenant.deliveryDeadline) revert DeadlineNotPassed();
        _authorizeBuyer(covenant, "NON_DELIVERY_EXPIRED");
    }

    function challengeDelivery(
        uint64 covenantId,
        string calldata challengeClaim,
        string[] calldata challengedCriterionIds
    ) external {
        Covenant storage covenant = _requireCovenant(covenantId);
        if (!_same(covenant.state, DELIVERED)) revert InvalidState();
        if (msg.sender != covenant.buyer) revert UnauthorizedCaller();
        if (_now() > covenant.challengeDeadline) revert DeadlinePassed();
        if (bytes(challengeClaim).length == 0 || bytes(challengeClaim).length > 8192) revert InvalidInput();
        registry.validateChallengedCriteria(covenantId, challengedCriterionIds);
        for (uint256 i; i < challengedCriterionIds.length; ++i) {
            for (uint256 j; j < i; ++j) {
                if (_same(challengedCriterionIds[i], challengedCriterionIds[j])) revert InvalidInput();
            }
            _challengedCriterionIds[covenantId].push(challengedCriterionIds[i]);
        }
        covenant.challengeClaim = challengeClaim;
        covenant.challengedAt = _now();
        covenant.reviewGeneration = 1;
        covenant.state = CHALLENGED;
        emit DeliveryChallenged(covenantId, 1);
    }

    function authorizeUnchallengedSettlement(uint64 covenantId) external {
        Covenant storage covenant = _requireCovenant(covenantId);
        if (!_same(covenant.state, DELIVERED)) revert InvalidState();
        if (_now() <= covenant.challengeDeadline) revert DeadlineNotPassed();
        _authorizeProvider(covenant, "UNCHALLENGED");
    }

    function submitEvidenceRepair(uint64 covenantId, Accord402Registry.EvidenceReplacementInput[] calldata replacements)
        external
    {
        Covenant storage covenant = _requireCovenant(covenantId);
        if (!_same(covenant.state, EVIDENCE_REPAIR_REQUIRED)) revert InvalidState();
        if (msg.sender != covenant.provider) revert UnauthorizedCaller();
        uint64 nowTimestamp = _now();
        if (nowTimestamp > covenant.repairDeadline) revert DeadlinePassed();
        if (covenant.reviewGeneration >= covenant.maxReviewGenerations || !covenant.repairAuthorizationActive) {
            revert InvalidRepairAuthorization();
        }
        if (replacements.length == 0 || replacements.length != _repairAuthorizations[covenantId].length) {
            revert InvalidRepairAuthorization();
        }

        Accord402Registry.RepairAuthorizationInput[] memory authorizations =
            new Accord402Registry.RepairAuthorizationInput[](replacements.length);
        Accord402Registry.EvidenceReplacementInput[] memory normalizedReplacements =
            new Accord402Registry.EvidenceReplacementInput[](replacements.length);
        for (uint256 i; i < replacements.length; ++i) {
            RepairAuthorization storage authorization = _repairAuthorizations[covenantId][i];
            authorizations[i] =
                Accord402Registry.RepairAuthorizationInput(authorization.evidenceId, authorization.fieldMask);
            if (!_same(replacements[i].replacesEvidenceId, authorization.evidenceId)) {
                revert InvalidRepairAuthorization();
            }
            normalizedReplacements[i] = replacements[i];
            normalizedReplacements[i].observedAt = nowTimestamp;
        }
        bytes32 newEvidenceSetHash = registry.applyEvidenceRepair(
            covenantId,
            normalizedReplacements,
            authorizations,
            covenant.reviewGeneration + 1,
            nowTimestamp,
            covenant.deliveryHash
        );
        covenant.activeEvidenceSetHash = newEvidenceSetHash;
        covenant.reviewGeneration += 1;
        covenant.repairAuthorizationActive = false;
        covenant.repairAuthorizationGeneration = 0;
        delete _repairAuthorizations[covenantId];
        covenant.repairDeadline = 0;
        covenant.retryDeadline = 0;
        covenant.state = CHALLENGED;
    }

    function retryReview(uint64 covenantId) external {
        Covenant storage covenant = _requireCovenant(covenantId);
        if (!_same(covenant.state, REVIEW_RETRY_REQUIRED)) revert InvalidState();
        uint64 nowTimestamp = _now();
        if (nowTimestamp > covenant.retryDeadline || nowTimestamp > covenant.absoluteDisputeDeadline) {
            revert DeadlinePassed();
        }
        if (covenant.reviewGeneration >= covenant.maxReviewGenerations) revert InvalidGeneration();
        covenant.reviewGeneration += 1;
        covenant.retryDeadline = 0;
        covenant.state = CHALLENGED;
    }

    function expireRepair(uint64 covenantId) external {
        Covenant storage covenant = _requireCovenant(covenantId);
        if (!_same(covenant.state, EVIDENCE_REPAIR_REQUIRED)) revert InvalidState();
        if (covenant.reviewGeneration >= covenant.maxReviewGenerations) revert InvalidGeneration();
        if (_now() <= covenant.repairDeadline) revert DeadlineNotPassed();
        delete _repairAuthorizations[covenantId];
        covenant.repairAuthorizationActive = false;
        _authorizeBuyer(covenant, "REPAIR_EXPIRED");
    }

    function expireReview(uint64 covenantId) external {
        Covenant storage covenant = _requireCovenant(covenantId);
        uint64 nowTimestamp = _now();
        bool absoluteExpired = nowTimestamp > covenant.absoluteDisputeDeadline;
        bool generationExhausted = covenant.reviewGeneration >= covenant.maxReviewGenerations;
        if (_same(covenant.state, CHALLENGED)) {
            if (!absoluteExpired) revert DeadlineNotPassed();
        } else if (_same(covenant.state, EVIDENCE_REPAIR_REQUIRED)) {
            if (!absoluteExpired && !generationExhausted) revert DeadlineNotPassed();
            delete _repairAuthorizations[covenantId];
            covenant.repairAuthorizationActive = false;
        } else if (_same(covenant.state, REVIEW_RETRY_REQUIRED)) {
            if (!absoluteExpired && !generationExhausted && nowTimestamp <= covenant.retryDeadline) {
                revert DeadlineNotPassed();
            }
        } else {
            revert InvalidState();
        }
        _authorizeBuyer(covenant, "REVIEW_EXPIRED");
    }

    /// @notice Sole authenticated entry point for a finalized Adjudicator result.
    function applyAdjudicationResult(
        uint64 covenantId,
        string calldata coreSnapshotHash,
        string calldata registrySnapshotHash,
        string calldata evidencePolicyHash,
        string calldata activeEvidenceSetHash,
        uint32 reviewGeneration,
        string calldata decision,
        string[] calldata challengedCriterionIds,
        string[] calldata failedCriterionIds,
        string calldata failureClassification,
        string[] calldata repairEvidenceIds,
        uint32[] calldata repairFieldMasks
    ) external {
        if (msg.sender != adjudicator) revert InvalidAdjudicationCaller();
        Covenant storage covenant = _requireCovenant(covenantId);
        if (!_same(covenant.state, CHALLENGED)) revert InvalidState();
        if (
            reviewGeneration != covenant.reviewGeneration
                || !_hashMatches(sha256(bytes(getAdjudicationSnapshot(covenantId))), coreSnapshotHash)
                || !_hashMatches(
                    sha256(bytes(registry.getAdjudicationSnapshot(address(this), covenantId))), registrySnapshotHash
                ) || !_hashMatches(covenant.evidencePolicyHash, evidencePolicyHash)
                || !_hashMatches(covenant.activeEvidenceSetHash, activeEvidenceSetHash)
        ) revert StaleAdjudicationResult();
        if (
            reviewGeneration == 0 || challengedCriterionIds.length != _challengedCriterionIds[covenantId].length
                || failedCriterionIds.length > challengedCriterionIds.length
        ) revert InvalidAdjudicationWire();
        for (uint256 i; i < challengedCriterionIds.length; ++i) {
            if (!_same(challengedCriterionIds[i], _challengedCriterionIds[covenantId][i])) {
                revert InvalidAdjudicationWire();
            }
        }
        for (uint256 i; i < failedCriterionIds.length; ++i) {
            for (uint256 previous; previous < i; ++previous) {
                if (_same(failedCriterionIds[i], failedCriterionIds[previous])) revert InvalidAdjudicationWire();
            }
            bool found;
            for (uint256 j; j < challengedCriterionIds.length; ++j) {
                if (_same(failedCriterionIds[i], challengedCriterionIds[j])) found = true;
            }
            if (!found) revert InvalidAdjudicationWire();
            _failedCriterionIds[covenantId].push(failedCriterionIds[i]);
        }

        if (_same(decision, SERVICE_VERIFIED) || _same(decision, BUYER_CLAIM_INVALID)) {
            if (
                failedCriterionIds.length != 0 || bytes(failureClassification).length != 0
                    || repairEvidenceIds.length != 0 || repairFieldMasks.length != 0
            ) revert InvalidAdjudicationWire();
            _authorizeProvider(covenant, _same(decision, SERVICE_VERIFIED) ? "SERVICE_VERIFIED" : "BUYER_CLAIM_INVALID");
        } else if (_same(decision, PROVIDER_BREACH)) {
            if (
                failedCriterionIds.length == 0 || !_same(failureClassification, "SUBSTANTIVE_PROVIDER_BREACH")
                    || repairEvidenceIds.length != 0 || repairFieldMasks.length != 0
            ) revert InvalidAdjudicationWire();
            _authorizeBuyer(covenant, "PROVIDER_BREACH");
        } else if (_same(decision, EVIDENCE_REPAIR_REQUIRED)) {
            if (
                failedCriterionIds.length != 0 || !_same(failureClassification, REPAIRABLE_EVIDENCE_DEFECT)
                    || repairEvidenceIds.length == 0 || repairEvidenceIds.length != repairFieldMasks.length
                    || repairEvidenceIds.length > 16
            ) revert InvalidAdjudicationWire();
            _storeRepairAuthorizations(covenantId, repairEvidenceIds, repairFieldMasks);
            covenant.adjudicationDecision = decision;
            covenant.failureClassification = failureClassification;
            covenant.repairAuthorizationGeneration = reviewGeneration;
            covenant.repairAuthorizationActive = true;
            covenant.repairDeadline = _min(_now() + covenant.evidenceRepairWindow, covenant.absoluteDisputeDeadline);
            covenant.retryDeadline = 0;
            covenant.state = EVIDENCE_REPAIR_REQUIRED;
            emit EvidenceRepairRequired(covenantId, reviewGeneration, covenant.repairDeadline);
        } else if (_same(decision, "REVIEW_RETRY_REQUIRED")) {
            if (
                failedCriterionIds.length != 0 || !_same(failureClassification, TRANSIENT_REVIEW_FAILURE)
                    || repairEvidenceIds.length != 0 || repairFieldMasks.length != 0
            ) revert InvalidAdjudicationWire();
            covenant.adjudicationDecision = decision;
            covenant.failureClassification = failureClassification;
            covenant.retryDeadline = _min(_now() + covenant.reviewRetryWindow, covenant.absoluteDisputeDeadline);
            covenant.repairDeadline = 0;
            covenant.state = REVIEW_RETRY_REQUIRED;
            emit ReviewRetryRequired(covenantId, reviewGeneration, covenant.retryDeadline);
        } else {
            revert InvalidAdjudicationWire();
        }
        if (!_same(decision, EVIDENCE_REPAIR_REQUIRED) && !_same(decision, "REVIEW_RETRY_REQUIRED")) {
            covenant.adjudicationDecision = decision;
            covenant.failureClassification = failureClassification;
        }
        emit AdjudicationApplied(covenantId, reviewGeneration, decision);
    }

    function claimSettlement(uint64 covenantId) external {
        Covenant storage covenant = _requireCovenant(covenantId);
        if (covenant.settlementClaimed || covenant.outstandingAmount == 0) revert SettlementAlreadyClaimed();
        address beneficiary;
        address recipient;
        bool providerSide;
        if (_same(covenant.state, SETTLEMENT_AUTHORIZED_PROVIDER)) {
            beneficiary = covenant.provider;
            recipient = covenant.providerSettlementRecipient;
            providerSide = true;
        } else if (_same(covenant.state, SETTLEMENT_AUTHORIZED_BUYER)) {
            beneficiary = covenant.buyer;
            recipient = covenant.buyerSettlementRecipient;
        } else {
            revert InvalidState();
        }
        uint256 amount = covenant.outstandingAmount;
        covenant.outstandingAmount = 0;
        covenant.settlementClaimed = true;
        covenant.closedAt = _now();
        if (providerSide) {
            covenant.providerSettlement = amount;
            covenant.state = CLOSED_PROVIDER;
            totalClosedToProvider += amount;
        } else {
            covenant.buyerSettlement = amount;
            covenant.state = CLOSED_BUYER;
            totalClosedToBuyer += amount;
        }
        if (totalOutstanding < amount) revert AccountingUnderflow();
        totalOutstanding -= amount;
        settlementVault.credit{value: amount}(covenantId, beneficiary, recipient);
        emit SettlementClaimed(covenantId, beneficiary, recipient, amount);
    }

    function getCovenant(uint64 covenantId) external view returns (Covenant memory) {
        return _covenants[covenantId];
    }

    /// @notice Compact deterministic review bundle for the GenLayer adjudicator.
    /// @dev Every value is length-prefixed; the final count delimits challenged IDs.
    function getAdjudicationSnapshot(uint64 covenantId) public view returns (string memory) {
        Covenant storage covenant = _covenants[covenantId];
        bytes memory encoded = abi.encodePacked(
            _packField(covenant.state),
            _packField(_bytes32Hex(covenant.serviceSpecHash)),
            _packField(_bytes32Hex(covenant.deliveryHash)),
            _packField(_bytes32Hex(covenant.evidencePolicyHash)),
            _packField(_bytes32Hex(covenant.activeEvidenceSetHash)),
            _packField(_uintToString(covenant.reviewGeneration)),
            _packField(covenant.deliveryPayload),
            _packField(covenant.challengeClaim),
            _packField(_uintToString(covenant.absoluteDisputeDeadline)),
            _packField(_uintToString(_challengedCriterionIds[covenantId].length))
        );
        for (uint256 i; i < _challengedCriterionIds[covenantId].length; ++i) {
            encoded = bytes.concat(encoded, _packField(_challengedCriterionIds[covenantId][i]));
        }
        return string(encoded);
    }

    function getReviewState(uint64 covenantId) external view returns (string memory) {
        return _covenants[covenantId].state;
    }

    function getServiceSpecHash(uint64 covenantId) external view returns (bytes32) {
        return _covenants[covenantId].serviceSpecHash;
    }

    function getDeliveryHash(uint64 covenantId) external view returns (bytes32) {
        return _covenants[covenantId].deliveryHash;
    }

    function getEvidencePolicyHashHex(uint64 covenantId) external view returns (string memory) {
        return _bytes32Hex(_covenants[covenantId].evidencePolicyHash);
    }

    function getActiveEvidenceSetHashHex(uint64 covenantId) external view returns (string memory) {
        return _bytes32Hex(_covenants[covenantId].activeEvidenceSetHash);
    }

    function getAccountingTotals() external view returns (uint256, uint256, uint256, uint256) {
        return (totalFunded, totalClosedToProvider, totalClosedToBuyer, totalOutstanding);
    }

    function _storeRepairAuthorizations(uint64 covenantId, string[] calldata evidenceIds, uint32[] calldata fieldMasks)
        internal
    {
        delete _repairAuthorizations[covenantId];
        string[] memory activeIds = registry.getActiveEvidenceIds(address(this), covenantId);
        uint256 previousIndex;
        for (uint256 i; i < evidenceIds.length; ++i) {
            bool found;
            uint256 index;
            for (uint256 j; j < activeIds.length; ++j) {
                if (_same(evidenceIds[i], activeIds[j])) {
                    found = true;
                    index = j;
                    break;
                }
            }
            if (
                !found || (i > 0 && index <= previousIndex) || fieldMasks[i] == 0
                    || (fieldMasks[i] & ~covenantMask(covenantId)) != 0
            ) revert InvalidAdjudicationWire();
            previousIndex = index;
            _repairAuthorizations[covenantId].push(RepairAuthorization(evidenceIds[i], fieldMasks[i]));
        }
    }

    function covenantMask(uint64 covenantId) internal view returns (uint32) {
        return _covenants[covenantId].repairAllowedFieldMask;
    }

    function _authorizeProvider(Covenant storage covenant, string memory reason) internal {
        covenant.state = SETTLEMENT_AUTHORIZED_PROVIDER;
        covenant.settlementDirection = "PROVIDER";
        covenant.closureReason = reason;
        covenant.repairAuthorizationActive = false;
        emit SettlementAuthorized(covenant.covenantId, "PROVIDER", reason);
    }

    function _authorizeBuyer(Covenant storage covenant, string memory reason) internal {
        covenant.state = SETTLEMENT_AUTHORIZED_BUYER;
        covenant.settlementDirection = "BUYER";
        covenant.closureReason = reason;
        covenant.repairAuthorizationActive = false;
        emit SettlementAuthorized(covenant.covenantId, "BUYER", reason);
    }

    function _requireCovenant(uint64 covenantId) internal view returns (Covenant storage covenant) {
        covenant = _covenants[covenantId];
        if (!covenant.exists) revert InvalidInput();
    }

    function _now() internal view returns (uint64) {
        if (block.timestamp > type(uint64).max) revert InvalidDeadline();
        return uint64(block.timestamp);
    }

    function _min(uint64 a, uint64 b) internal pure returns (uint64) {
        return a < b ? a : b;
    }

    function _hashMatches(bytes32 expected, string calldata supplied) internal pure returns (bool) {
        return keccak256(bytes(_bytes32Hex(expected))) == keccak256(bytes(supplied));
    }

    function _bytes32Hex(bytes32 value) internal pure returns (string memory) {
        bytes memory alphabet = "0123456789abcdef";
        bytes memory output = new bytes(64);
        for (uint256 i; i < 32; ++i) {
            output[i * 2] = alphabet[uint8(value[i] >> 4)];
            output[i * 2 + 1] = alphabet[uint8(value[i] & 0x0f)];
        }
        return string(output);
    }

    function _packField(string memory value) internal pure returns (bytes memory) {
        return abi.encodePacked(_uintToString(bytes(value).length), ":", value);
    }

    function _uintToString(uint256 value) internal pure returns (string memory) {
        if (value == 0) return "0";
        uint256 digits;
        uint256 copy = value;
        while (copy != 0) {
            ++digits;
            copy /= 10;
        }
        bytes memory buffer = new bytes(digits);
        while (value != 0) {
            buffer[--digits] = bytes1(uint8(48 + value % 10));
            value /= 10;
        }
        return string(buffer);
    }

    function _same(string memory a, string memory b) internal pure returns (bool) {
        return keccak256(bytes(a)) == keccak256(bytes(b));
    }
}
