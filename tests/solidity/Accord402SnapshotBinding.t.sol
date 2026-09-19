// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Accord402Core} from "../../contracts/Accord402Core.sol";
import {Accord402Registry} from "../../contracts/Accord402Registry.sol";

interface VmSnapshot {
    function prank(address) external;
    function warp(uint256) external;
    function deal(address, uint256) external;
}

contract SnapshotVault {
    mapping(address => bool) public registered;

    function register(address recipient) external {
        registered[recipient] = true;
    }

    function is_registered_payout(address recipient) external view returns (bool) {
        return registered[recipient];
    }

    function credit(uint256, address, address recipient) external payable {
        (bool ok,) = payable(recipient).call{value: msg.value}("");
        require(ok);
    }
}

contract Accord402SnapshotBindingTest {
    VmSnapshot private constant VM =
        VmSnapshot(address(uint160(uint256(keccak256("hevm cheat code")))));

    address private constant BUYER = address(0xB0B);
    address private constant PROVIDER = address(0xA11CE);
    address private constant BUYER_PAYOUT = address(0xB001);
    address private constant PROVIDER_PAYOUT = address(0xA002);

    Accord402Registry private registry;
    SnapshotVault private vault;
    Accord402Core private core;

    function setUp() public {
        VM.warp(1_700_000_000);
        registry = new Accord402Registry();
        vault = new SnapshotVault();
        vault.register(BUYER_PAYOUT);
        vault.register(PROVIDER_PAYOUT);
        core = new Accord402Core(address(registry), address(this), address(vault));
        VM.deal(BUYER, 10 ether);
    }

    function _openChallenged() private returns (uint64 covenantId, string[] memory challenged) {
        Accord402Registry.CriterionInput[] memory criteria = new Accord402Registry.CriterionInput[](1);
        criteria[0] = Accord402Registry.CriterionInput("delivery_matches", "Delivery matches the covenant.");

        Accord402Registry.AuthorityBindingInput[] memory authorities =
            new Accord402Registry.AuthorityBindingInput[](2);
        authorities[0] = Accord402Registry.AuthorityBindingInput(
            "primary", 1, "PRIMARY", "GITHUB_REPOSITORY",
            "owner-primary/repo", "https://raw.githubusercontent.com"
        );
        authorities[1] = Accord402Registry.AuthorityBindingInput(
            "corroborator", 1, "CORROBORATOR", "GITHUB_REPOSITORY",
            "owner-corroborator/repo", "https://raw.githubusercontent.com"
        );

        Accord402Core.OpenCovenantParams memory terms;
        terms.provider = PROVIDER;
        terms.principal = 1 ether;
        terms.serviceSpec = "deliver report";
        terms.acceptanceDeadline = uint64(block.timestamp + 120);
        terms.deliveryDeadline = uint64(block.timestamp + 600);
        terms.challengeDuration = 120;
        terms.absoluteDisputeDeadline = uint64(block.timestamp + 7200);
        terms.evidenceRepairWindow = 120;
        terms.reviewRetryWindow = 120;
        terms.maxReviewGenerations = 3;
        terms.maxEvidenceAge = 900;
        terms.requiredCorroborationCount = 1;
        terms.repairAllowedFieldMask = 252;
        terms.replayScope = "COVENANT";
        terms.criteria = criteria;
        terms.authorityBindings = authorities;

        VM.prank(BUYER);
        covenantId = core.openCovenant{value: 1 ether}(terms, BUYER_PAYOUT);

        VM.prank(PROVIDER);
        core.acceptCovenant(covenantId, PROVIDER_PAYOUT);

        Accord402Registry.EvidenceInput[] memory evidence = new Accord402Registry.EvidenceInput[](2);
        evidence[0] = Accord402Registry.EvidenceInput(
            "primary-v1", "primary", 1, "report", "PAGE", "IMMUTABLE",
            "https://raw.githubusercontent.com/owner-primary/repo/1111111111111111111111111111111111111111/report.json",
            "1111111111111111111111111111111111111111",
            uint64(block.timestamp - 10), uint64(block.timestamp), uint64(block.timestamp + 600),
            bytes32(uint256(1)), true
        );
        evidence[1] = Accord402Registry.EvidenceInput(
            "corr-v1", "corroborator", 1, "report", "PAGE", "IMMUTABLE",
            "https://raw.githubusercontent.com/owner-corroborator/repo/2222222222222222222222222222222222222222/report.json",
            "2222222222222222222222222222222222222222",
            uint64(block.timestamp - 10), uint64(block.timestamp), uint64(block.timestamp + 600),
            bytes32(uint256(2)), false
        );

        VM.prank(PROVIDER);
        core.submitDelivery(covenantId, "report delivered", evidence);

        challenged = new string[](1);
        challenged[0] = "delivery_matches";
        VM.prank(BUYER);
        core.challengeDelivery(covenantId, "buyer disputes delivery", challenged);
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

    function _apply(
        uint64 covenantId,
        string memory coreHash,
        string memory registryHash,
        string[] memory challenged
    ) private returns (bool ok) {
        string[] memory empty = new string[](0);
        uint32[] memory emptyMasks = new uint32[](0);
        (ok,) = address(core).call(
            abi.encodeWithSelector(
                core.applyAdjudicationResult.selector,
                covenantId,
                coreHash,
                registryHash,
                core.getEvidencePolicyHashHex(covenantId),
                core.getActiveEvidenceSetHashHex(covenantId),
                uint32(1),
                "SERVICE_VERIFIED",
                challenged,
                empty,
                "",
                empty,
                emptyMasks
            )
        );
    }

    function testRejectsTamperedCoreSnapshotHash() public {
        (uint64 covenantId, string[] memory challenged) = _openChallenged();
        string memory registryHash =
            _hex(sha256(bytes(registry.getAdjudicationSnapshot(address(core), covenantId))));
        require(!_apply(covenantId, _hex(bytes32(uint256(1))), registryHash, challenged), "tampered core snapshot accepted");
    }

    function testRejectsTamperedRegistrySnapshotHash() public {
        (uint64 covenantId, string[] memory challenged) = _openChallenged();
        string memory coreHash = _hex(sha256(bytes(core.getAdjudicationSnapshot(covenantId))));
        require(!_apply(covenantId, coreHash, _hex(bytes32(uint256(2))), challenged), "tampered registry snapshot accepted");
    }

    function testAcceptsExactSnapshotHashes() public {
        (uint64 covenantId, string[] memory challenged) = _openChallenged();
        string memory coreHash = _hex(sha256(bytes(core.getAdjudicationSnapshot(covenantId))));
        string memory registryHash =
            _hex(sha256(bytes(registry.getAdjudicationSnapshot(address(core), covenantId))));
        require(_apply(covenantId, coreHash, registryHash, challenged), "exact snapshots rejected");
    }
}
