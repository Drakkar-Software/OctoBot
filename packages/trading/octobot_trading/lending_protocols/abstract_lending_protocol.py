#  Drakkar-Software OctoBot-Trading
#  Copyright (c) Drakkar-Software, All rights reserved.
#
#  This library is free software; you can redistribute it and/or
#  modify it under the terms of the GNU Lesser General Public
#  License as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  This library is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public
#  License along with this library.
import decimal
import typing

import octobot_commons.tentacles_management as tentacles_management
import octobot_trading.lending_protocols.lending_protocol_types as lending_protocol_types

if typing.TYPE_CHECKING:
    import octobot_trading.blockchain_wallets.blockchain_wallet as blockchain_wallet


class AbstractLendingProtocol(tentacles_management.AbstractTentacle):
    """
    Base class for all DeFi lending protocol integrations.
    Subclasses implement protocol-specific logic (e.g., Aave V3, Compound V3).
    Discovered via get_all_classes_from_parent() in the lending protocol factory,
    following the same pattern as BlockchainWallet.
    """
    PROTOCOL: str = None  # type: ignore  # e.g., "aave_v3_polygon"
    CHAIN_ID: int = None  # type: ignore  # e.g., 137 for Polygon

    def __init__(self, wallet: "blockchain_wallet.BlockchainWallet"):
        super().__init__()
        self.wallet = wallet

    async def get_user_account_data(
        self, user_address: str
    ) -> lending_protocol_types.LendingPosition:
        """
        Query a user's lending position (collateral, debt, health factor).
        TODO: Implement in subclass. For Aave V3, call
        pool.functions.getUserAccountData(user_address).call() and parse the
        6-tuple: (totalCollateralBase, totalDebtBase, availableBorrowsBase,
        currentLiquidationThreshold, ltv, healthFactor). Divide healthFactor
        by 1e18 to get the decimal value.
        """
        raise NotImplementedError("get_user_account_data is not implemented")

    async def get_liquidatable_positions(
        self, min_debt_usd: decimal.Decimal = decimal.Decimal("0")
    ) -> list[lending_protocol_types.LiquidatablePosition]:
        """
        Find all positions eligible for liquidation (health_factor < 1.0).
        TODO: Implement in subclass. Strategies include:
        1. Event-based: Index Borrow/Supply events to track active borrowers,
           then query getUserAccountData for each when prices change.
        2. Subgraph: Query Aave's official subgraph for users with low health.
        3. Direct polling: Periodically query known borrower addresses.
        Filter results by min_debt_usd to skip unprofitable small positions.
        """
        raise NotImplementedError("get_liquidatable_positions is not implemented")

    async def build_liquidation_tx(
        self,
        position: lending_protocol_types.LiquidatablePosition,
        debt_asset: str,
        debt_to_cover: decimal.Decimal,
        collateral_asset: str,
    ) -> dict:
        """
        Build transaction parameters for executing a liquidation.
        Returns a dict with: to, data, value, gas (estimated).
        TODO: Implement in subclass. For Aave V3:
        1. Approve debt token to Pool contract (ERC20.approve)
        2. Encode Pool.liquidationCall(collateralAsset, debtAsset, user,
           debtToCover, receiveAToken=False)
        3. Estimate gas via eth_estimateGas
        """
        raise NotImplementedError("build_liquidation_tx is not implemented")

    async def estimate_liquidation_profit(
        self,
        position: lending_protocol_types.LiquidatablePosition,
        debt_asset: str,
        collateral_asset: str,
    ) -> lending_protocol_types.LiquidationEstimate:
        """
        Estimate the profitability of liquidating a position.
        TODO: Implement in subclass. Calculation:
        1. max_debt_to_cover = close_factor * user_debt_for_asset
        2. collateral_received = debt_to_cover * (1 + liquidation_bonus) *
           (debt_price / collateral_price)
        3. gross_profit = collateral_value - debt_to_cover_value
        4. net_profit = gross_profit - gas_cost_usd
        """
        raise NotImplementedError("estimate_liquidation_profit is not implemented")

    def get_protocol_name(self) -> str:
        """Return the protocol identifier string."""
        return self.PROTOCOL

    def get_chain_id(self) -> int:
        """Return the chain ID this protocol operates on."""
        return self.CHAIN_ID
