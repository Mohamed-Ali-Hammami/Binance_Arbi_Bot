// SPDX-License-Identifier: MIT
pragma solidity 0.8.21;

import "https://github.com/aave/aave-v3-core/blob/master/contracts/flashloan/base/FlashLoanSimpleReceiverBase.sol";
import "https://github.com/aave/aave-v3-core/blob/master/contracts/interfaces/IPoolAddressesProvider.sol";
import "https://github.com/aave/aave-v3-core/blob/master/contracts/dependencies/openzeppelin/contracts/IERC20.sol";

contract SimpleFlashLoan is FlashLoanSimpleReceiverBase {
    address payable owner;

    constructor(address _addressProvider)
        FlashLoanSimpleReceiverBase(IPoolAddressesProvider(_addressProvider))
    {
        owner = payable(msg.sender);
    }

    function fn_RequestFlashLoan(address _token, uint256 _amount) public {
        address receiverAddress = address(this);
        address asset = _token;
        uint256 amount = _amount;
        bytes memory params = "";
        uint16 referralCode = 0;

        POOL.flashLoanSimple(
            receiverAddress,
            asset,
            amount,
            params,
            referralCode
        );
    }

    // This function is called after your contract has received the flash loaned amount
    function executeOperation(
        address asset,
        uint256 amount,
        uint256 premium,
        address initiator,
        bytes calldata params
    ) external override returns (bool) {
        // Ensure that only the Aave pool can call this function
        require(msg.sender == address(POOL), "Caller is not the Aave pool");

        // Extract token addresses from the params
        (address tokenA, address tokenB, address tokenC) = abi.decode(params, (address, address, address));

        // Example: Swap TokenA for TokenB
        IERC20(tokenA).approve(address(DEX), amount);
        DEX.swapExactTokensForTokens(amount, 0, getPathForSwap(tokenA, tokenB), address(this), block.timestamp);

        // Example: Swap TokenB for TokenC
        uint256 tokenBBalance = IERC20(tokenB).balanceOf(address(this));
        IERC20(tokenB).approve(address(DEX), tokenBBalance);
        DEX.swapExactTokensForTokens(tokenBBalance, 0, getPathForSwap(tokenB, tokenC), address(this), block.timestamp);

        // Example: Swap TokenC for TokenA
        uint256 tokenCBalance = IERC20(tokenC).balanceOf(address(this));
        IERC20(tokenC).approve(address(DEX), tokenCBalance);
        DEX.swapExactTokensForTokens(tokenCBalance, 0, getPathForSwap(tokenC, tokenA), address(this), block.timestamp);

        // Repay the flash loan
        uint256 totalAmount = amount + premium;
        IERC20(asset).transferFrom(initiator, address(this), totalAmount);

        // Return true to indicate a successful execution
        return true;
    }

    // Utility function to get the path for a Uniswap swap
    function getPathForSwap(address fromToken, address toToken) internal pure returns (address[] memory) {
        address[] memory path = new address[](2);
        path[0] = fromToken;
        path[1] = toToken;
        return path;
    }

    // Additional functions can be added as needed
    receive() external payable {}
}
