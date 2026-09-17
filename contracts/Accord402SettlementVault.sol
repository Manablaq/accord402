// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// Accord402 native-GEN settlement router.
///
/// Payout destinations must self-register as code-free default accounts in two
/// different blocks. The two-step rule prevents a contract constructor from
/// exploiting `address(this).code.length == 0` during construction.
///
/// The router never retains settlement credit after a successful route.
contract Accord402SettlementVault {
    mapping(address => uint256) private _registrationReadyBlock;
    mapping(address => bool) private _registeredPayout;
    mapping(bytes32 => bool) private _delivered;
    bool private _entered;

    event PayoutRegistrationBegun(
        address indexed recipient,
        uint256 readyBlock
    );
    event PayoutRecipientRegistered(address indexed recipient);
    event SettlementRouted(
        address indexed source,
        uint256 indexed covenantId,
        address indexed beneficiary,
        address recipient,
        uint256 amount
    );

    error PayoutRecipientHasCode();
    error RegistrationNotStarted();
    error RegistrationNotReady();
    error UnregisteredPayoutRecipient();
    error ZeroBeneficiary();
    error ZeroRecipient();
    error ZeroCovenantId();
    error ZeroAmount();
    error DuplicateSettlement();
    error ReentrantCall();
    error TransferFailed();
    error UnattributedValue();

    modifier nonReentrant() {
        if (_entered) revert ReentrantCall();
        _entered = true;
        _;
        _entered = false;
    }

    function begin_payout_registration() external {
        if (msg.sender.code.length != 0) revert PayoutRecipientHasCode();

        uint256 readyBlock = block.number + 1;
        _registrationReadyBlock[msg.sender] = readyBlock;

        emit PayoutRegistrationBegun(msg.sender, readyBlock);
    }

    function confirm_payout_registration() external {
        if (msg.sender.code.length != 0) revert PayoutRecipientHasCode();

        uint256 readyBlock = _registrationReadyBlock[msg.sender];
        if (readyBlock == 0) revert RegistrationNotStarted();
        if (block.number < readyBlock) revert RegistrationNotReady();

        delete _registrationReadyBlock[msg.sender];
        _registeredPayout[msg.sender] = true;

        emit PayoutRecipientRegistered(msg.sender);
    }

    function is_registered_payout(address recipient)
        public
        view
        returns (bool)
    {
        return (
            recipient != address(0)
            && _registeredPayout[recipient]
            && recipient.code.length == 0
        );
    }

    function delivery_key(address source, uint256 covenantId)
        public
        pure
        returns (bytes32)
    {
        return keccak256(abi.encode(source, covenantId));
    }

    function credit(
        uint256 covenantId,
        address beneficiary,
        address recipient
    ) external payable nonReentrant {
        if (covenantId == 0) revert ZeroCovenantId();
        if (beneficiary == address(0)) revert ZeroBeneficiary();
        if (recipient == address(0)) revert ZeroRecipient();
        if (msg.value == 0) revert ZeroAmount();
        if (!is_registered_payout(recipient)) {
            revert UnregisteredPayoutRecipient();
        }

        bytes32 key = delivery_key(msg.sender, covenantId);
        if (_delivered[key]) revert DuplicateSettlement();

        _delivered[key] = true;

        (bool ok, ) = payable(recipient).call{value: msg.value}("");
        if (!ok) revert TransferFailed();

        emit SettlementRouted(
            msg.sender,
            covenantId,
            beneficiary,
            recipient,
            msg.value
        );
    }

    function was_delivered(address source, uint256 covenantId)
        external
        view
        returns (bool)
    {
        return _delivered[delivery_key(source, covenantId)];
    }

    receive() external payable {
        revert UnattributedValue();
    }
}
