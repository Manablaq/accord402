// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @title Accord402Registry
/// @notice Deterministic policy, authority, and evidence registry for Accord402.
/// @dev The caller is the namespace. Core is the only intended writer; no
///      registry record can affect another caller's namespace.
contract Accord402Registry {
    uint256 public constant MAX_CRITERIA = 16;
    uint256 public constant MAX_AUTHORITIES = 16;
    uint256 public constant MAX_EVIDENCE = 16;
    uint256 public constant MAX_STRING_BYTES = 8192;
    uint256 public constant MAX_EVIDENCE_ID_BYTES = 128;
    uint256 public constant MAX_CRITERION_ID_BYTES = 64;
    uint256 public constant MAX_CRITERION_TEXT_BYTES = 2048;
    uint256 public constant MAX_AUTHORITY_ID_BYTES = 128;
    uint256 public constant MAX_ROLE_BYTES = 32;
    uint256 public constant MAX_IDENTITY_KIND_BYTES = 64;
    uint256 public constant MAX_IDENTITY_VALUE_BYTES = 512;
    uint256 public constant MAX_SOURCE_BYTES = 2048;
    uint256 public constant MAX_VERSION_BYTES = 128;
    uint32 public constant MAX_REPAIR_MASK = 252;
    string public constant EVIDENCE_IDENTITY_KIND = "GITHUB_REPOSITORY";
    string public constant EVIDENCE_SOURCE_KIND = "IMMUTABLE";
    string public constant EVIDENCE_ORIGIN = "https://raw.githubusercontent.com";

    uint32 public constant MASK_CANONICAL_SOURCE = 4;
    uint32 public constant MASK_VERSION = 8;
    uint32 public constant MASK_PUBLISHED_AT = 16;
    uint32 public constant MASK_OBSERVED_AT = 32;
    uint32 public constant MASK_EXPIRES_AT = 64;
    uint32 public constant MASK_CONTENT_DIGEST = 128;

    bytes32 private constant SERVICE_DOMAIN = "ACCORD402:SERVICE_SPEC:V1";
    bytes32 private constant POLICY_DOMAIN = "ACCORD402:EVIDENCE_POLICY:V1";
    bytes32 private constant EVIDENCE_DOMAIN = "ACCORD402:ACTIVE_EVIDENCE_SET:V1";

    struct CriterionInput {
        string criterionId;
        string criterionText;
    }

    struct AuthorityBindingInput {
        string authorityId;
        uint32 authorityRevision;
        string role;
        string identityKind;
        string identityValue;
        string canonicalOrigin;
    }

    struct EvidenceInput {
        string evidenceId;
        string authorityId;
        uint32 authorityRevision;
        string subject;
        string kind;
        string sourceKind;
        string canonicalSource;
        string immutableVersionOrRecordId;
        uint64 publishedAt;
        uint64 observedAt;
        uint64 expiresAt;
        bytes32 contentDigest;
        bool isPrimary;
    }

    struct EvidenceReplacementInput {
        string replacesEvidenceId;
        string evidenceId;
        string authorityId;
        uint32 authorityRevision;
        string subject;
        string kind;
        string sourceKind;
        string canonicalSource;
        string immutableVersionOrRecordId;
        uint64 publishedAt;
        uint64 observedAt;
        uint64 expiresAt;
        bytes32 contentDigest;
        bool isPrimary;
    }

    struct RepairAuthorizationInput {
        string evidenceId;
        uint32 fieldMask;
    }

    struct CriterionRecord {
        uint64 covenantId;
        string criterionId;
        string criterionText;
    }

    struct AuthorityBinding {
        uint64 covenantId;
        string authorityId;
        uint32 authorityRevision;
        string role;
        string identityKind;
        string identityValue;
        string canonicalOrigin;
    }

    struct EvidenceRecord {
        uint64 covenantId;
        uint32 generation;
        string evidenceId;
        string authorityId;
        uint32 authorityRevision;
        string subject;
        string kind;
        string sourceKind;
        string canonicalSource;
        string immutableVersionOrRecordId;
        uint64 publishedAt;
        uint64 observedAt;
        uint64 expiresAt;
        bytes32 contentDigest;
        bool isPrimary;
        string replacesEvidenceId;
    }

    struct Policy {
        bool exists;
        uint64 covenantId;
        string serviceSpec;
        bytes32 serviceSpecHash;
        bytes32 evidencePolicyHash;
        uint64 maxEvidenceAge;
        uint32 requiredCorroborationCount;
        uint32 repairAllowedFieldMask;
        string replayScope;
    }

    mapping(address => mapping(uint64 => Policy)) private _policies;
    mapping(address => mapping(uint64 => CriterionRecord[])) private _criteria;
    mapping(address => mapping(uint64 => AuthorityBinding[])) private _authorities;
    mapping(address => mapping(uint64 => EvidenceRecord[])) private _evidenceHistory;
    mapping(address => mapping(uint64 => string[])) private _activeEvidenceIds;
    mapping(address => mapping(uint64 => mapping(bytes32 => bool))) private _activeEvidence;
    mapping(address => mapping(uint64 => mapping(bytes32 => uint256))) private _evidenceIndex;
    mapping(address => mapping(uint64 => mapping(bytes32 => bool))) private _reservedEvidenceIds;
    mapping(bytes32 => bool) private _replayReservations;

    error InvalidNamespace();
    error InvalidCovenantId();
    error PolicyAlreadyExists();
    error PolicyMissing();
    error EmptyValue();
    error StringTooLong();
    error TooManyRecords();
    error DuplicateCriterion();
    error DuplicateAuthorityBinding();
    error DuplicateAuthorityIdentity();
    error InvalidAuthorityRole();
    error InvalidAuthorityOrigin();
    error InvalidAuthorityIdentity();
    error InvalidEvidenceAuthority();
    error InvalidEvidenceRole();
    error DuplicateEvidenceId();
    error EvidenceIdAlreadyReserved();
    error EvidenceReplay();
    error InvalidEvidenceTimes();
    error InvalidEvidenceSource();
    error InvalidEvidenceDigest();
    error InvalidEvidenceStructure();
    error InvalidReplayScope();
    error InvalidRepairSet();
    error UnauthorizedRepairMutation();
    error RepairHasNoEffect();
    error InvalidChallengeCriteria();

    event PolicyCreated(
        address indexed core, uint64 indexed covenantId, bytes32 serviceSpecHash, bytes32 evidencePolicyHash
    );
    event DeliveryEvidenceRecorded(address indexed core, uint64 indexed covenantId, bytes32 activeEvidenceSetHash);
    event EvidenceRepaired(
        address indexed core, uint64 indexed covenantId, uint32 generation, bytes32 activeEvidenceSetHash
    );

    modifier validNamespace() {
        if (msg.sender == address(0)) revert InvalidNamespace();
        _;
    }

    function createPolicy(
        uint64 covenantId,
        string calldata serviceSpec,
        CriterionInput[] calldata criteria,
        AuthorityBindingInput[] calldata authorities,
        uint64 maxEvidenceAge,
        uint32 requiredCorroborationCount,
        uint32 repairAllowedFieldMask,
        string calldata replayScope
    ) external validNamespace returns (bytes32 serviceSpecHash, bytes32 evidencePolicyHash) {
        if (covenantId == 0) revert InvalidCovenantId();
        Policy storage policy = _policies[msg.sender][covenantId];
        if (policy.exists) revert PolicyAlreadyExists();
        if (criteria.length == 0 || criteria.length > MAX_CRITERIA) revert TooManyRecords();
        if (authorities.length == 0 || authorities.length > MAX_AUTHORITIES) revert TooManyRecords();
        _requireNonEmpty(serviceSpec, MAX_STRING_BYTES);
        _requireNonEmpty(replayScope, 32);
        if (!_same(replayScope, "COVENANT")) revert InvalidReplayScope();
        if (maxEvidenceAge == 0 || requiredCorroborationCount == 0 || requiredCorroborationCount > 8) {
            revert InvalidEvidenceStructure();
        }
        if (repairAllowedFieldMask != MAX_REPAIR_MASK) revert InvalidRepairSet();

        uint256 primaryCount;
        uint256 distinctCorroboratorCount;
        bytes32[] memory seenAuthorityPairs = new bytes32[](authorities.length);
        bytes32[] memory seenOwners = new bytes32[](authorities.length);

        for (uint256 i; i < criteria.length; ++i) {
            _requireNonEmpty(criteria[i].criterionId, MAX_CRITERION_ID_BYTES);
            _requireNonEmpty(criteria[i].criterionText, MAX_CRITERION_TEXT_BYTES);
            for (uint256 j; j < i; ++j) {
                if (_same(criteria[i].criterionId, criteria[j].criterionId)) revert DuplicateCriterion();
            }
            _criteria[msg.sender][covenantId].push(
                CriterionRecord(covenantId, criteria[i].criterionId, criteria[i].criterionText)
            );
        }

        for (uint256 i; i < authorities.length; ++i) {
            AuthorityBindingInput calldata input = authorities[i];
            _requireNonEmpty(input.authorityId, MAX_AUTHORITY_ID_BYTES);
            _requireNonEmpty(input.role, MAX_ROLE_BYTES);
            _requireNonEmpty(input.identityKind, MAX_IDENTITY_KIND_BYTES);
            _requireNonEmpty(input.identityValue, MAX_IDENTITY_VALUE_BYTES);
            if (!_same(input.role, "PRIMARY") && !_same(input.role, "CORROBORATOR")) revert InvalidAuthorityRole();
            if (!_same(input.identityKind, EVIDENCE_IDENTITY_KIND) || !_validGithubIdentity(input.identityValue)) {
                revert InvalidAuthorityIdentity();
            }
            if (!_same(input.canonicalOrigin, EVIDENCE_ORIGIN)) revert InvalidAuthorityOrigin();

            bytes32 pair = keccak256(abi.encode(input.authorityId, input.authorityRevision));
            for (uint256 j; j < i; ++j) {
                if (seenAuthorityPairs[j] == pair) revert DuplicateAuthorityBinding();
            }
            seenAuthorityPairs[i] = pair;

            bytes32 ownerKey = keccak256(bytes(_githubOwner(input.identityValue)));
            for (uint256 j; j < i; ++j) {
                if (seenOwners[j] == ownerKey) revert DuplicateAuthorityIdentity();
            }
            seenOwners[i] = ownerKey;

            if (_same(input.role, "PRIMARY")) {
                ++primaryCount;
            } else {
                ++distinctCorroboratorCount;
            }

            _authorities[msg.sender][covenantId].push(
                AuthorityBinding(
                    covenantId,
                    input.authorityId,
                    input.authorityRevision,
                    input.role,
                    input.identityKind,
                    input.identityValue,
                    input.canonicalOrigin
                )
            );
        }

        if (primaryCount == 0 || distinctCorroboratorCount < requiredCorroborationCount) {
            revert InvalidEvidenceStructure();
        }

        serviceSpecHash = _serviceSpecHash(serviceSpec, criteria);
        evidencePolicyHash = _policyHash(
            maxEvidenceAge,
            requiredCorroborationCount,
            repairAllowedFieldMask,
            replayScope,
            _authorities[msg.sender][covenantId]
        );
        policy.exists = true;
        policy.covenantId = covenantId;
        policy.serviceSpec = serviceSpec;
        policy.serviceSpecHash = serviceSpecHash;
        policy.evidencePolicyHash = evidencePolicyHash;
        policy.maxEvidenceAge = maxEvidenceAge;
        policy.requiredCorroborationCount = requiredCorroborationCount;
        policy.repairAllowedFieldMask = repairAllowedFieldMask;
        policy.replayScope = replayScope;
        emit PolicyCreated(msg.sender, covenantId, serviceSpecHash, evidencePolicyHash);
    }

    function recordDeliveryEvidence(
        uint64 covenantId,
        EvidenceInput[] calldata evidence,
        uint64 deliveryTimestamp,
        bytes32 deliveryHash
    ) external validNamespace returns (bytes32 activeEvidenceSetHash) {
        Policy storage policy = _policies[msg.sender][covenantId];
        if (!policy.exists) revert PolicyMissing();
        if (evidence.length == 0 || evidence.length > MAX_EVIDENCE) revert TooManyRecords();
        if (deliveryHash == bytes32(0)) revert InvalidEvidenceDigest();

        for (uint256 i; i < evidence.length; ++i) {
            _validateEvidence(msg.sender, covenantId, policy, evidence[i], deliveryTimestamp);
            bytes32 idKey = keccak256(bytes(evidence[i].evidenceId));
            if (_reservedEvidenceIds[msg.sender][covenantId][idKey]) revert EvidenceIdAlreadyReserved();
            for (uint256 j; j < i; ++j) {
                if (_same(evidence[i].evidenceId, evidence[j].evidenceId)) revert DuplicateEvidenceId();
            }
        }

        uint256 primaryCount;
        uint256 corroboratorCount;
        bytes32[] memory corroboratorIdentities = new bytes32[](evidence.length);
        for (uint256 i; i < evidence.length; ++i) {
            (AuthorityBinding memory authority, bool found) =
                _authority(msg.sender, covenantId, evidence[i].authorityId, evidence[i].authorityRevision);
            if (!found) revert InvalidEvidenceAuthority();
            if (evidence[i].isPrimary) {
                if (!_same(authority.role, "PRIMARY")) revert InvalidEvidenceRole();
                ++primaryCount;
            } else {
                if (!_same(authority.role, "CORROBORATOR")) revert InvalidEvidenceRole();
                bytes32 identity = keccak256(abi.encode(authority.identityKind, authority.identityValue));
                bool duplicateIdentity;
                for (uint256 j; j < corroboratorCount; ++j) {
                    if (corroboratorIdentities[j] == identity) duplicateIdentity = true;
                }
                if (!duplicateIdentity) corroboratorIdentities[corroboratorCount++] = identity;
            }
        }
        if (primaryCount == 0 || corroboratorCount < policy.requiredCorroborationCount) {
            revert InvalidEvidenceStructure();
        }

        for (uint256 i; i < evidence.length; ++i) {
            EvidenceInput calldata input = evidence[i];
            _reserve(msg.sender, covenantId, policy.replayScope, input.evidenceId, input.authorityId);
            _reservedEvidenceIds[msg.sender][covenantId][keccak256(bytes(input.evidenceId))] = true;
            _evidenceHistory[msg.sender][covenantId].push(
                EvidenceRecord(
                    covenantId,
                    0,
                    input.evidenceId,
                    input.authorityId,
                    input.authorityRevision,
                    input.subject,
                    input.kind,
                    input.sourceKind,
                    input.canonicalSource,
                    input.immutableVersionOrRecordId,
                    input.publishedAt,
                    input.observedAt,
                    input.expiresAt,
                    input.contentDigest,
                    input.isPrimary,
                    ""
                )
            );
            _activeEvidenceIds[msg.sender][covenantId].push(input.evidenceId);
            _activeEvidence[msg.sender][covenantId][keccak256(bytes(input.evidenceId))] = true;
            _evidenceIndex[msg.sender][covenantId][keccak256(bytes(input.evidenceId))] =
            _evidenceHistory[msg.sender][covenantId].length;
        }
        activeEvidenceSetHash = _activeEvidenceSetHash(msg.sender, covenantId, deliveryHash, policy.evidencePolicyHash);
        emit DeliveryEvidenceRecorded(msg.sender, covenantId, activeEvidenceSetHash);
    }

    function applyEvidenceRepair(
        uint64 covenantId,
        EvidenceReplacementInput[] calldata replacements,
        RepairAuthorizationInput[] calldata authorizations,
        uint32 newGeneration,
        uint64 repairTimestamp,
        bytes32 deliveryHash
    ) external validNamespace returns (bytes32 activeEvidenceSetHash) {
        Policy storage policy = _policies[msg.sender][covenantId];
        if (!policy.exists || newGeneration == 0) revert PolicyMissing();
        if (
            replacements.length == 0 || replacements.length != authorizations.length
                || replacements.length > MAX_EVIDENCE
        ) {
            revert InvalidRepairSet();
        }

        _validateRepairSet(msg.sender, covenantId, policy, replacements, authorizations, repairTimestamp);

        _appendRepairs(msg.sender, covenantId, policy.replayScope, replacements, newGeneration);
        activeEvidenceSetHash = _activeEvidenceSetHash(msg.sender, covenantId, deliveryHash, policy.evidencePolicyHash);
        emit EvidenceRepaired(msg.sender, covenantId, newGeneration, activeEvidenceSetHash);
    }

    function validateChallengedCriteria(uint64 covenantId, string[] calldata challengedIds)
        external
        view
        validNamespace
        returns (bool)
    {
        if (challengedIds.length == 0 || challengedIds.length > MAX_CRITERIA) {
            revert InvalidChallengeCriteria();
        }
        uint256 cursor;
        for (uint256 i; i < challengedIds.length; ++i) {
            bool found;
            for (uint256 j = cursor; j < _criteria[msg.sender][covenantId].length; ++j) {
                if (_same(challengedIds[i], _criteria[msg.sender][covenantId][j].criterionId)) {
                    found = true;
                    cursor = j + 1;
                    break;
                }
            }
            if (!found) revert InvalidChallengeCriteria();
        }
        return true;
    }

    function getActiveEvidenceIds(address core, uint64 covenantId) external view returns (string[] memory) {
        return _activeEvidenceIds[core][covenantId];
    }

    function getServiceSpec(address core, uint64 covenantId) external view returns (string memory) {
        return _policies[core][covenantId].serviceSpec;
    }

    function getMaxEvidenceAge(address core, uint64 covenantId) external view returns (uint64) {
        return _policies[core][covenantId].maxEvidenceAge;
    }

    function getRequiredCorroborationCount(address core, uint64 covenantId) external view returns (uint32) {
        return _policies[core][covenantId].requiredCorroborationCount;
    }

    function getRepairAllowedFieldMask(address core, uint64 covenantId) external view returns (uint32) {
        return _policies[core][covenantId].repairAllowedFieldMask;
    }

    function getCriterionCount(address core, uint64 covenantId) external view returns (uint256) {
        return _criteria[core][covenantId].length;
    }

    function getAuthorityCount(address core, uint64 covenantId) external view returns (uint256) {
        return _authorities[core][covenantId].length;
    }

    function getEvidenceCount(address core, uint64 covenantId) external view returns (uint256) {
        return _evidenceHistory[core][covenantId].length;
    }

    function getCriterionPacked(address core, uint64 covenantId, uint256 index) external view returns (string memory) {
        CriterionRecord storage criterion = _criteria[core][covenantId][index];
        return string(abi.encodePacked(_packField(criterion.criterionId), _packField(criterion.criterionText)));
    }

    function getAuthorityPacked(address core, uint64 covenantId, uint256 index) external view returns (string memory) {
        AuthorityBinding storage authority = _authorities[core][covenantId][index];
        return string(
            abi.encodePacked(
                _packField(authority.authorityId),
                _packField(_uintToString(authority.authorityRevision)),
                _packField(authority.role),
                _packField(authority.identityKind),
                _packField(authority.identityValue),
                _packField(authority.canonicalOrigin)
            )
        );
    }

    function getEvidencePacked(address core, uint64 covenantId, uint256 index) external view returns (string memory) {
        EvidenceRecord storage evidence = _evidenceHistory[core][covenantId][index];
        return string(
            abi.encodePacked(
                _packField(_uintToString(evidence.generation)),
                _packField(evidence.evidenceId),
                _packField(evidence.authorityId),
                _packField(_uintToString(evidence.authorityRevision)),
                _packField(evidence.subject),
                _packField(evidence.kind),
                _packField(evidence.sourceKind),
                _packField(evidence.canonicalSource),
                _packField(evidence.immutableVersionOrRecordId),
                _packField(_uintToString(evidence.publishedAt)),
                _packField(_uintToString(evidence.observedAt)),
                _packField(_uintToString(evidence.expiresAt)),
                _packField(_bytes32Hex(evidence.contentDigest)),
                _packField(evidence.isPrimary ? "1" : "0"),
                _packField(evidence.replacesEvidenceId)
            )
        );
    }

    /// @notice Compact deterministic review bundle for the GenLayer adjudicator.
    /// @dev Every value is length-prefixed; counts delimit variable sections.
    function getAdjudicationSnapshot(address core, uint64 covenantId) external view returns (string memory) {
        Policy storage policy = _policies[core][covenantId];
        bytes memory encoded = abi.encodePacked(
            _packField(policy.serviceSpec),
            _packField(_uintToString(policy.maxEvidenceAge)),
            _packField(_uintToString(policy.requiredCorroborationCount)),
            _packField(_uintToString(policy.repairAllowedFieldMask)),
            _packField(policy.replayScope),
            _packField(_uintToString(_criteria[core][covenantId].length))
        );
        for (uint256 i; i < _criteria[core][covenantId].length; ++i) {
            encoded = bytes.concat(encoded, _packField(this.getCriterionPacked(core, covenantId, i)));
        }
        encoded = bytes.concat(encoded, _packField(_uintToString(_authorities[core][covenantId].length)));
        for (uint256 i; i < _authorities[core][covenantId].length; ++i) {
            encoded = bytes.concat(encoded, _packField(this.getAuthorityPacked(core, covenantId, i)));
        }
        encoded = bytes.concat(encoded, _packField(_uintToString(_evidenceHistory[core][covenantId].length)));
        for (uint256 i; i < _evidenceHistory[core][covenantId].length; ++i) {
            encoded = bytes.concat(encoded, _packField(this.getEvidencePacked(core, covenantId, i)));
        }
        encoded = bytes.concat(encoded, _packField(_uintToString(_activeEvidenceIds[core][covenantId].length)));
        for (uint256 i; i < _activeEvidenceIds[core][covenantId].length; ++i) {
            encoded = bytes.concat(encoded, _packField(_activeEvidenceIds[core][covenantId][i]));
        }
        return string(encoded);
    }

    function _validateEvidence(
        address core,
        uint64 covenantId,
        Policy storage policy,
        EvidenceInput memory input,
        uint64 nowTimestamp
    ) internal view {
        _requireNonEmpty(input.evidenceId, MAX_EVIDENCE_ID_BYTES);
        _requireNonEmpty(input.authorityId, MAX_AUTHORITY_ID_BYTES);
        _requireNonEmpty(input.subject, MAX_STRING_BYTES);
        _requireNonEmpty(input.kind, MAX_STRING_BYTES);
        _requireNonEmpty(input.sourceKind, MAX_STRING_BYTES);
        _requireNonEmpty(input.canonicalSource, MAX_SOURCE_BYTES);
        if (input.contentDigest == bytes32(0)) revert InvalidEvidenceDigest();
        if (
            input.observedAt != nowTimestamp || input.publishedAt > input.observedAt
                || input.expiresAt <= input.observedAt
        ) {
            revert InvalidEvidenceTimes();
        }
        if (input.observedAt - input.publishedAt > policy.maxEvidenceAge) revert InvalidEvidenceTimes();
        (AuthorityBinding memory authority, bool found) =
            _authority(core, covenantId, input.authorityId, input.authorityRevision);
        if (!found) revert InvalidEvidenceAuthority();
        if (
            !_same(input.sourceKind, EVIDENCE_SOURCE_KIND)
                || !_same(authority.identityKind, EVIDENCE_IDENTITY_KIND)
                || !_same(authority.canonicalOrigin, EVIDENCE_ORIGIN)
                || !_validGithubSource(
                    input.canonicalSource,
                    authority.identityValue,
                    input.immutableVersionOrRecordId
                )
        ) revert InvalidEvidenceSource();
    }

    function _validateRepairSet(
        address core,
        uint64 covenantId,
        Policy storage policy,
        EvidenceReplacementInput[] calldata replacements,
        RepairAuthorizationInput[] calldata authorizations,
        uint64 repairTimestamp
    ) internal view {
        for (uint256 i; i < replacements.length; ++i) {
            EvidenceReplacementInput calldata input = replacements[i];
            RepairAuthorizationInput calldata authorization = authorizations[i];
            if (!_same(input.replacesEvidenceId, authorization.evidenceId)) revert InvalidRepairSet();
            bytes32 oldKey = keccak256(bytes(input.replacesEvidenceId));
            if (!_activeEvidence[core][covenantId][oldKey]) revert InvalidRepairSet();
            if (
                authorization.fieldMask == 0 || authorization.fieldMask > MAX_REPAIR_MASK
                    || (authorization.fieldMask & 3) != 0
            ) revert InvalidRepairSet();
            if ((authorization.fieldMask & ~policy.repairAllowedFieldMask) != 0) revert InvalidRepairSet();
            if (_reservedEvidenceIds[core][covenantId][keccak256(bytes(input.evidenceId))]) {
                revert EvidenceIdAlreadyReserved();
            }
            for (uint256 j; j < i; ++j) {
                if (
                    _same(input.replacesEvidenceId, replacements[j].replacesEvidenceId)
                        || _same(input.evidenceId, replacements[j].evidenceId)
                ) revert InvalidRepairSet();
            }
            EvidenceRecord storage oldRecord =
                _evidenceHistory[core][covenantId][_evidenceIndex[core][covenantId][oldKey] - 1];
            if (
                !_same(oldRecord.authorityId, input.authorityId)
                    || oldRecord.authorityRevision != input.authorityRevision
                    || !_same(oldRecord.subject, input.subject) || !_same(oldRecord.kind, input.kind)
                    || !_same(oldRecord.sourceKind, input.sourceKind) || oldRecord.isPrimary != input.isPrimary
            ) revert UnauthorizedRepairMutation();
            bool changed;
            changed = _checkRepairString(
                oldRecord.canonicalSource, input.canonicalSource, authorization.fieldMask, MASK_CANONICAL_SOURCE
            ) || changed;
            changed = _checkRepairString(
                oldRecord.immutableVersionOrRecordId,
                input.immutableVersionOrRecordId,
                authorization.fieldMask,
                MASK_VERSION
            ) || changed;
            changed = _checkRepairUint(
                oldRecord.publishedAt, input.publishedAt, authorization.fieldMask, MASK_PUBLISHED_AT
            ) || changed;
            changed = _checkRepairUint(
                    oldRecord.observedAt, input.observedAt, authorization.fieldMask, MASK_OBSERVED_AT
                ) || changed;
            changed = _checkRepairUint(oldRecord.expiresAt, input.expiresAt, authorization.fieldMask, MASK_EXPIRES_AT)
                || changed;
            changed = _checkRepairDigest(
                oldRecord.contentDigest, input.contentDigest, authorization.fieldMask, MASK_CONTENT_DIGEST
            ) || changed;
            if (!changed) revert RepairHasNoEffect();
            _validateEvidence(core, covenantId, policy, _replacementAsEvidence(input), repairTimestamp);
        }
    }

    function _appendRepairs(
        address core,
        uint64 covenantId,
        string memory replayScope,
        EvidenceReplacementInput[] calldata replacements,
        uint32 newGeneration
    ) internal {
        for (uint256 i; i < replacements.length; ++i) {
            EvidenceReplacementInput calldata input = replacements[i];
            _reserve(core, covenantId, replayScope, input.evidenceId, input.authorityId);
            bytes32 newKey = keccak256(bytes(input.evidenceId));
            _reservedEvidenceIds[core][covenantId][newKey] = true;
            _evidenceHistory[core][covenantId].push(
                EvidenceRecord(
                    covenantId,
                    newGeneration,
                    input.evidenceId,
                    input.authorityId,
                    input.authorityRevision,
                    input.subject,
                    input.kind,
                    input.sourceKind,
                    input.canonicalSource,
                    input.immutableVersionOrRecordId,
                    input.publishedAt,
                    input.observedAt,
                    input.expiresAt,
                    input.contentDigest,
                    input.isPrimary,
                    input.replacesEvidenceId
                )
            );
            _evidenceIndex[core][covenantId][newKey] = _evidenceHistory[core][covenantId].length;
            bytes32 oldKey = keccak256(bytes(input.replacesEvidenceId));
            _activeEvidence[core][covenantId][oldKey] = false;
            _activeEvidence[core][covenantId][newKey] = true;
            for (uint256 j; j < _activeEvidenceIds[core][covenantId].length; ++j) {
                if (_same(_activeEvidenceIds[core][covenantId][j], input.replacesEvidenceId)) {
                    _activeEvidenceIds[core][covenantId][j] = input.evidenceId;
                    break;
                }
            }
        }
    }

    function _replacementAsEvidence(EvidenceReplacementInput calldata input)
        internal
        pure
        returns (EvidenceInput memory)
    {
        return EvidenceInput(
            input.evidenceId,
            input.authorityId,
            input.authorityRevision,
            input.subject,
            input.kind,
            input.sourceKind,
            input.canonicalSource,
            input.immutableVersionOrRecordId,
            input.publishedAt,
            input.observedAt,
            input.expiresAt,
            input.contentDigest,
            input.isPrimary
        );
    }

    function _authority(address core, uint64 covenantId, string memory id, uint32 revision)
        internal
        view
        returns (AuthorityBinding memory binding, bool found)
    {
        for (uint256 i; i < _authorities[core][covenantId].length; ++i) {
            AuthorityBinding storage candidate = _authorities[core][covenantId][i];
            if (_same(candidate.authorityId, id) && candidate.authorityRevision == revision) return (candidate, true);
        }
    }

    function _reserve(
        address core,
        uint64 covenantId,
        string memory scope,
        string memory evidenceId,
        string memory authorityId
    ) internal {
        bytes32 key = _replayKey(core, covenantId, scope, evidenceId, authorityId);
        if (_replayReservations[key]) revert EvidenceReplay();
        _replayReservations[key] = true;
    }

    function _replayKey(
        address core,
        uint64 covenantId,
        string memory scope,
        string memory evidenceId,
        string memory authorityId
    ) internal pure returns (bytes32) {
        if (_same(scope, "GLOBAL")) {
            return keccak256(abi.encode("G", authorityId, evidenceId));
        }
        return keccak256(abi.encode("C", core, covenantId, authorityId, evidenceId));
    }

    function _activeEvidenceSetHash(address core, uint64 covenantId, bytes32 deliveryHash, bytes32 policyHash)
        internal
        view
        returns (bytes32)
    {
        bytes memory encoded = abi.encode(EVIDENCE_DOMAIN, covenantId, deliveryHash, policyHash);
        string[] storage ids = _activeEvidenceIds[core][covenantId];
        for (uint256 i; i < ids.length; ++i) {
            EvidenceRecord storage record =
                _evidenceHistory[core][covenantId][_evidenceIndex[core][covenantId][keccak256(bytes(ids[i]))] - 1];
            encoded = bytes.concat(
                encoded,
                abi.encode(
                    record.evidenceId,
                    record.authorityId,
                    record.authorityRevision,
                    record.subject,
                    record.kind,
                    record.sourceKind,
                    record.canonicalSource,
                    record.immutableVersionOrRecordId,
                    record.publishedAt,
                    record.observedAt,
                    record.expiresAt,
                    record.contentDigest,
                    record.isPrimary
                )
            );
        }
        return sha256(encoded);
    }

    function _serviceSpecHash(string calldata serviceSpec, CriterionInput[] calldata criteria)
        internal
        pure
        returns (bytes32)
    {
        bytes memory encoded = abi.encode(SERVICE_DOMAIN, serviceSpec, criteria.length);
        for (uint256 i; i < criteria.length; ++i) {
            encoded = bytes.concat(encoded, abi.encode(i, criteria[i].criterionId, criteria[i].criterionText));
        }
        return sha256(encoded);
    }

    function _policyHash(
        uint64 maxEvidenceAge,
        uint32 requiredCorroborationCount,
        uint32 repairAllowedFieldMask,
        string calldata replayScope,
        AuthorityBinding[] storage authorities
    ) internal view returns (bytes32) {
        bytes memory encoded = abi.encode(
            POLICY_DOMAIN, maxEvidenceAge, requiredCorroborationCount, repairAllowedFieldMask, replayScope
        );
        for (uint256 i; i < authorities.length; ++i) {
            encoded = bytes.concat(
                encoded,
                abi.encode(
                    authorities[i].authorityId,
                    authorities[i].authorityRevision,
                    authorities[i].role,
                    authorities[i].identityKind,
                    authorities[i].identityValue,
                    authorities[i].canonicalOrigin
                )
            );
        }
        return sha256(encoded);
    }

    function _checkRepairString(string storage oldValue, string calldata newValue, uint32 mask, uint32 bit)
        internal
        view
        returns (bool)
    {
        bool changed = keccak256(bytes(oldValue)) != keccak256(bytes(newValue));
        if (changed && (mask & bit) == 0) revert UnauthorizedRepairMutation();
        if (!changed && (mask & bit) != 0) return false;
        return changed;
    }

    function _checkRepairUint(uint64 oldValue, uint64 newValue, uint32 mask, uint32 bit) internal pure returns (bool) {
        bool changed = oldValue != newValue;
        if (changed && (mask & bit) == 0) revert UnauthorizedRepairMutation();
        return changed;
    }

    function _checkRepairDigest(bytes32 oldValue, bytes32 newValue, uint32 mask, uint32 bit)
        internal
        pure
        returns (bool)
    {
        bool changed = oldValue != newValue;
        if (changed && (mask & bit) == 0) revert UnauthorizedRepairMutation();
        return changed;
    }

    function _validGithubIdentity(string memory identity) internal pure returns (bool) {
        bytes memory value = bytes(identity);
        uint256 slash = type(uint256).max;
        for (uint256 i; i < value.length; ++i) {
            if (value[i] == "/") {
                if (slash != type(uint256).max) return false;
                slash = i;
            }
        }
        if (slash == type(uint256).max || slash == 0 || slash + 1 >= value.length) return false;
        uint256 ownerLength = slash;
        uint256 repoLength = value.length - slash - 1;
        if (ownerLength > 39 || repoLength > 100) return false;
        if (value[0] == "-" || value[slash - 1] == "-") return false;
        for (uint256 i; i < ownerLength; ++i) {
            uint8 ch = uint8(value[i]);
            if (!((ch >= 48 && ch <= 57) || (ch >= 97 && ch <= 122) || ch == 45)) return false;
        }
        if (repoLength == 1 && value[slash + 1] == ".") return false;
        if (repoLength == 2 && value[slash + 1] == "." && value[slash + 2] == ".") return false;
        for (uint256 i = slash + 1; i < value.length; ++i) {
            uint8 ch = uint8(value[i]);
            if (
                !((ch >= 48 && ch <= 57) || (ch >= 97 && ch <= 122) || ch == 45 || ch == 46 || ch == 95)
            ) return false;
        }
        return true;
    }

    function _githubOwner(string memory identity) internal pure returns (string memory) {
        bytes memory value = bytes(identity);
        uint256 slash;
        while (slash < value.length && value[slash] != "/") ++slash;
        bytes memory owner = new bytes(slash);
        for (uint256 i; i < slash; ++i) owner[i] = value[i];
        return string(owner);
    }

    function _isLowerHex40(string memory value) internal pure returns (bool) {
        bytes memory chars = bytes(value);
        if (chars.length != 40) return false;
        for (uint256 i; i < 40; ++i) {
            uint8 ch = uint8(chars[i]);
            if (!((ch >= 48 && ch <= 57) || (ch >= 97 && ch <= 102))) return false;
        }
        return true;
    }

    function _validGithubPathSegment(bytes memory source, uint256 start, uint256 end) internal pure returns (bool) {
        if (start >= end) return false;
        if (end - start == 1 && source[start] == ".") return false;
        if (end - start == 2 && source[start] == "." && source[start + 1] == ".") return false;
        for (uint256 i = start; i < end; ++i) {
            uint8 ch = uint8(source[i]);
            if (
                !((ch >= 48 && ch <= 57) || (ch >= 65 && ch <= 90) || (ch >= 97 && ch <= 122)
                    || ch == 45 || ch == 46 || ch == 95 || ch == 126)
            ) return false;
        }
        return true;
    }

    function _validGithubSource(string memory source, string memory identity, string memory versionId)
        internal
        pure
        returns (bool)
    {
        if (!_validGithubIdentity(identity) || !_isLowerHex40(versionId)) return false;
        bytes memory raw = bytes(source);
        bytes memory prefix = bytes(string.concat(EVIDENCE_ORIGIN, "/", identity, "/", versionId, "/"));
        if (raw.length <= prefix.length) return false;
        for (uint256 i; i < prefix.length; ++i) {
            if (raw[i] != prefix[i]) return false;
        }
        uint256 segmentStart = prefix.length;
        for (uint256 i = segmentStart; i <= raw.length; ++i) {
            if (i == raw.length || raw[i] == "/") {
                if (!_validGithubPathSegment(raw, segmentStart, i)) return false;
                segmentStart = i + 1;
            } else {
                uint8 ch = uint8(raw[i]);
                if (ch <= 32 || ch == 127 || ch == 35 || ch == 37 || ch == 63 || ch == 92) return false;
            }
        }
        return segmentStart == raw.length + 1;
    }

    function _validHttpsOrigin(string memory origin) internal pure returns (bool) {
        bytes memory value = bytes(origin);
        if (
            value.length < 12 || value[0] != "h" || value[1] != "t" || value[2] != "t" || value[3] != "p"
                || value[4] != "s" || value[5] != ":" || value[6] != "/" || value[7] != "/"
        ) return false;
        bool dot;
        for (uint256 i = 8; i < value.length; ++i) {
            uint8 c = uint8(value[i]);
            if (c == 46) dot = true;
            if (c <= 32 || c == 127 || c == 47 || c == 63 || c == 35 || c == 64 || c == 58 || c == 92) return false;
            if (!((c >= 48 && c <= 57) || (c >= 65 && c <= 90) || (c >= 97 && c <= 122) || c == 46 || c == 45)) {
                return false;
            }
        }
        return dot && value[value.length - 1] != "." && value[8] != "." && value[8] != "-";
    }

    function _validCanonicalSource(string memory source) internal pure returns (bool) {
        bytes memory value = bytes(source);
        if (
            value.length < 13 || value[0] != "h" || value[1] != "t" || value[2] != "t" || value[3] != "p"
                || value[4] != "s" || value[5] != ":" || value[6] != "/" || value[7] != "/"
        ) return false;
        bool hasPath;
        bool previousSlash;
        bool hostDot;
        for (uint256 i = 8; i < value.length; ++i) {
            uint8 c = uint8(value[i]);
            if (c == 47) {
                if (previousSlash || i == 8 || i == value.length - 1 || !hostDot) return false;
                hasPath = true;
                previousSlash = true;
                continue;
            }
            if (c <= 32 || c == 127 || c == 63 || c == 35 || c == 37 || c == 92) return false;
            if (c > 126) return false;
            if (!hasPath) {
                if (c == 46) hostDot = true;
                if (!((c >= 48 && c <= 57) || (c >= 97 && c <= 122) || c == 46 || c == 45)) return false;
            }
            previousSlash = false;
        }
        return hasPath;
    }

    function _sameOrigin(string memory source, string memory origin) internal pure returns (bool) {
        bytes memory sourceBytes = bytes(source);
        bytes memory originBytes = bytes(origin);
        if (sourceBytes.length <= originBytes.length || sourceBytes[originBytes.length] != "/") return false;
        for (uint256 i; i < originBytes.length; ++i) {
            if (sourceBytes[i] != originBytes[i]) return false;
        }
        return true;
    }

    function _requireNonEmpty(string memory value, uint256 maxBytes) internal pure {
        uint256 length = bytes(value).length;
        if (length == 0) revert EmptyValue();
        if (length > maxBytes) revert StringTooLong();
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

    function _bytes32Hex(bytes32 value) internal pure returns (string memory) {
        bytes memory alphabet = "0123456789abcdef";
        bytes memory output = new bytes(64);
        for (uint256 i; i < 32; ++i) {
            uint8 current = uint8(value[i]);
            output[i * 2] = alphabet[current >> 4];
            output[i * 2 + 1] = alphabet[current & 15];
        }
        return string(output);
    }
}
