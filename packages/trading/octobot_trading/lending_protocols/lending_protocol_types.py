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
import dataclasses
import decimal
import typing


@dataclasses.dataclass
class LendingPosition:
    """Represents a user's position in a lending protocol."""
    user_address: str
    health_factor: decimal.Decimal  # < 1.0 means liquidatable
    total_collateral_usd: decimal.Decimal
    total_debt_usd: decimal.Decimal
    collateral_assets: dict[str, decimal.Decimal]  # token symbol -> amount
    debt_assets: dict[str, decimal.Decimal]  # token symbol -> amount


@dataclasses.dataclass
class LiquidatablePosition(LendingPosition):
    """A lending position that is eligible for liquidation (health_factor < 1.0)."""
    liquidation_bonus_percent: decimal.Decimal = decimal.Decimal("0")
    max_liquidatable_debt_usd: decimal.Decimal = decimal.Decimal("0")  # close_factor * total_debt


@dataclasses.dataclass
class LiquidationEstimate:
    """Estimated profitability of a liquidation opportunity."""
    position: LiquidatablePosition
    debt_asset: str
    debt_to_cover: decimal.Decimal
    collateral_asset: str
    collateral_to_receive: decimal.Decimal
    estimated_gas: int
    gas_cost_usd: decimal.Decimal
    gross_profit_usd: decimal.Decimal
    net_profit_usd: decimal.Decimal  # gross_profit - gas_cost
