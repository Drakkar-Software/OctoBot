#  Drakkar-Software OctoBot-Tentacles
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

import octobot_trading.lending_protocols as lending_protocols

import tentacles.Trading.Lending_protocol.aave_v3_polygon.aave_v3_constants as aave_v3_constants
import tentacles.Trading.Lending_protocol.aave_v3_polygon.aave_v3_abis as aave_v3_abis


class AaveV3PolygonLendingProtocol(lending_protocols.AbstractLendingProtocol):
    """
    Aave V3 lending protocol integration for Polygon mainnet.
    Provides health factor monitoring and liquidation execution capabilities.
    """
    PROTOCOL = "aave_v3_polygon"
    CHAIN_ID = aave_v3_constants.POLYGON_CHAIN_ID

    POOL_ADDRESS = aave_v3_constants.AAVE_V3_POOL_ADDRESS
    ORACLE_ADDRESS = aave_v3_constants.AAVE_V3_ORACLE_ADDRESS
    POOL_DATA_PROVIDER_ADDRESS = aave_v3_constants.AAVE_V3_POOL_DATA_PROVIDER_ADDRESS

    async def get_user_account_data(
        self, user_address: str
    ) -> lending_protocols.LendingPosition:
        """
        Query a user's lending position on Aave V3 Polygon.

        TODO: Implement the following steps:
        1. Create pool contract instance:
           pool = self.wallet.w3.eth.contract(
               address=Web3.to_checksum_address(self.POOL_ADDRESS),
               abi=aave_v3_abis.AAVE_V3_POOL_ABI
           )
        2. Call getUserAccountData:
           result = await pool.functions.getUserAccountData(
               Web3.to_checksum_address(user_address)
           ).call()
        3. Parse the 6-tuple:
           total_collateral_base = Decimal(result[0]) / Decimal(10**8)  # 8 decimals
           total_debt_base = Decimal(result[1]) / Decimal(10**8)
           health_factor = Decimal(result[5]) / Decimal(10**18)  # 18 decimals
        4. To get per-asset breakdown, iterate over known reserve tokens:
           For each token, call PoolDataProvider.getUserReserveData(token, user)
           to get currentATokenBalance and currentVariableDebt
        5. Return LendingPosition with all data
        """
        raise NotImplementedError(
            "get_user_account_data is not yet implemented for Aave V3 Polygon. "
            "See docstring for implementation steps."
        )

    async def get_liquidatable_positions(
        self, min_debt_usd: decimal.Decimal = decimal.Decimal("0")
    ) -> list[lending_protocols.LiquidatablePosition]:
        """
        Find all liquidatable positions on Aave V3 Polygon.

        TODO: Implement the following strategy:

        Option A (Simple polling - recommended for MVP):
        1. Maintain a list of known borrower addresses (from configuration or
           by scanning past Borrow events).
        2. For each address, call get_user_account_data().
        3. Filter for health_factor < 1.0 and total_debt_usd >= min_debt_usd.
        4. For each liquidatable position:
           a. Query PoolDataProvider.getReserveConfigurationData(asset)
              to get liquidationBonus (in basis points, e.g., 10500 = 5% bonus)
           b. Calculate max_liquidatable_debt = total_debt * close_factor (50%)
           c. Return LiquidatablePosition with all fields populated

        Option B (Event indexing - production grade):
        1. Index Borrow, Repay, Supply, Withdraw events to track active borrowers.
        2. Listen for price oracle updates to trigger health factor recalculations.
        3. Maintain an in-memory sorted set of positions by health factor.

        Option C (Subgraph - if available):
        1. Query Aave V3 Polygon subgraph for users with healthFactor < threshold.
        2. Validate on-chain before attempting liquidation.
        """
        raise NotImplementedError(
            "get_liquidatable_positions is not yet implemented for Aave V3 Polygon. "
            "See docstring for implementation strategies."
        )

    async def build_liquidation_tx(
        self,
        position: lending_protocols.LiquidatablePosition,
        debt_asset: str,
        debt_to_cover: decimal.Decimal,
        collateral_asset: str,
    ) -> dict:
        """
        Build a liquidation transaction for Aave V3 Polygon.

        TODO: Implement the following steps:
        1. Resolve token addresses:
           debt_token_address = aave_v3_constants.POLYGON_TOKEN_ADDRESSES[debt_asset]
           collateral_token_address = aave_v3_constants.POLYGON_TOKEN_ADDRESSES[collateral_asset]
        2. Check and set allowance (ERC20.approve):
           debt_contract = w3.eth.contract(debt_token_address, abi=ERC20_ABI)
           current_allowance = await debt_contract.functions.allowance(
               wallet_address, POOL_ADDRESS).call()
           if current_allowance < debt_amount_raw:
               approve_tx = debt_contract.functions.approve(POOL_ADDRESS, MAX_UINT256)
               await self.wallet.build_and_send_contract_tx(...)
        3. Build liquidationCall transaction:
           pool = w3.eth.contract(POOL_ADDRESS, abi=POOL_ABI)
           tx = pool.functions.liquidationCall(
               collateral_token_address,
               debt_token_address,
               position.user_address,
               debt_amount_raw,  # in token decimals
               False  # receiveAToken=False to get underlying asset
           )
        4. Estimate gas and return tx params dict:
           return {"to": POOL_ADDRESS, "data": tx._encode_transaction_data(),
                   "value": 0, "gas": estimated_gas}
        """
        raise NotImplementedError(
            "build_liquidation_tx is not yet implemented for Aave V3 Polygon. "
            "See docstring for implementation steps."
        )

    async def estimate_liquidation_profit(
        self,
        position: lending_protocols.LiquidatablePosition,
        debt_asset: str,
        collateral_asset: str,
    ) -> lending_protocols.LiquidationEstimate:
        """
        Estimate profitability of liquidating a position on Aave V3 Polygon.

        TODO: Implement the following calculation:
        1. Get asset prices from Aave Oracle:
           oracle = w3.eth.contract(ORACLE_ADDRESS, abi=ORACLE_ABI)
           debt_price = await oracle.functions.getAssetPrice(debt_token_addr).call()
           collateral_price = await oracle.functions.getAssetPrice(collateral_addr).call()
           (prices are in USD with 8 decimals)
        2. Calculate maximum liquidatable amount:
           user_debt = position.debt_assets[debt_asset]
           max_debt_to_cover = user_debt * Decimal(DEFAULT_CLOSE_FACTOR) / Decimal(100)
        3. Get liquidation bonus:
           config = await data_provider.functions.getReserveConfigurationData(
               collateral_addr).call()
           bonus_bps = config[3]  # e.g., 10500 means 5% bonus
           bonus_multiplier = Decimal(bonus_bps) / Decimal(10000)
        4. Calculate collateral received:
           debt_value_usd = max_debt_to_cover * debt_price / 10**8
           collateral_received_usd = debt_value_usd * bonus_multiplier
           collateral_received = collateral_received_usd * 10**8 / collateral_price
        5. Calculate profit:
           gross_profit_usd = collateral_received_usd - debt_value_usd
           gas_estimate = 350_000  # typical for Polygon liquidation
           gas_price = await w3.eth.gas_price
           gas_cost_native = gas_estimate * gas_price / 10**18
           native_price = await oracle.functions.getAssetPrice(WMATIC_addr).call()
           gas_cost_usd = gas_cost_native * native_price / 10**8
           net_profit_usd = gross_profit_usd - gas_cost_usd
        6. Return LiquidationEstimate with all values
        """
        raise NotImplementedError(
            "estimate_liquidation_profit is not yet implemented for Aave V3 Polygon. "
            "See docstring for calculation steps."
        )
