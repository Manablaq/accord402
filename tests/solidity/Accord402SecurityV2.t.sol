// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Accord402Registry} from "../../contracts/Accord402Registry.sol";

contract Accord402SecurityV2Test {
    Accord402Registry private registry;

    function setUp() public { registry = new Accord402Registry(); }

    function _criteria() private pure returns (Accord402Registry.CriterionInput[] memory criteria) {
        criteria = new Accord402Registry.CriterionInput[](1);
        criteria[0] = Accord402Registry.CriterionInput("delivery_matches", "Delivery matches the covenant.");
    }

    function _authorities(string memory corroboratorIdentity)
        private pure returns (Accord402Registry.AuthorityBindingInput[] memory authorities)
    {
        authorities = new Accord402Registry.AuthorityBindingInput[](2);
        authorities[0] = Accord402Registry.AuthorityBindingInput(
            "primary", 1, "PRIMARY", "GITHUB_REPOSITORY",
            "owner-primary/repo", "https://raw.githubusercontent.com"
        );
        authorities[1] = Accord402Registry.AuthorityBindingInput(
            "corroborator", 1, "CORROBORATOR", "GITHUB_REPOSITORY",
            corroboratorIdentity, "https://raw.githubusercontent.com"
        );
    }

    function _create(Accord402Registry.AuthorityBindingInput[] memory authorities) private returns (bool ok) {
        (ok,) = address(registry).call(
            abi.encodeWithSelector(
                registry.createPolicy.selector,
                uint64(1), "service", _criteria(), authorities,
                uint64(900), uint32(1), uint32(252), "COVENANT"
            )
        );
    }

    function testRejectsGenericIdentityKind() public {
        Accord402Registry.AuthorityBindingInput[] memory authorities = _authorities("owner-corroborator/repo");
        authorities[0].identityKind = "DOMAIN";
        require(!_create(authorities), "generic identity kind accepted");
    }

    function testRejectsNonGithubOrigin() public {
        Accord402Registry.AuthorityBindingInput[] memory authorities = _authorities("owner-corroborator/repo");
        authorities[0].canonicalOrigin = "https://example.com";
        require(!_create(authorities), "non-GitHub origin accepted");
    }

    function testRejectsSameGithubOwnerAcrossRepositories() public {
        Accord402Registry.AuthorityBindingInput[] memory authorities = _authorities("owner-primary/other-repo");
        require(!_create(authorities), "same-owner corroboration accepted");
    }
}
