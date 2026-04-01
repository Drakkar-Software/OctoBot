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
import dataclasses
import decimal
import enum
import time
import typing


class LiquidationStatus(enum.Enum):
    DETECTED = "detected"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclasses.dataclass
class LiquidationContainer:
    """
    Tracks the lifecycle of a liquidation opportunity.
    Created by the producer when a profitable liquidation is detected,
    passed to the consumer for execution, and updated with results.
    Follows the same pattern as ArbitrageContainer.
    """
    borrower_address: str
    collateral_asset: str
    debt_asset: str
    debt_to_cover: decimal.Decimal
    estimated_collateral_received: decimal.Decimal
    estimated_profit_usd: decimal.Decimal
    estimated_gas: int
    health_factor: decimal.Decimal
    status: LiquidationStatus = LiquidationStatus.DETECTED
    tx_hash: typing.Optional[str] = None
    error: typing.Optional[str] = None
    timestamp: float = dataclasses.field(default_factory=time.time)

    def is_similar(self, other_borrower: str, other_debt_asset: str) -> bool:
        """Check if this container targets the same position."""
        return (
            self.borrower_address == other_borrower
            and self.debt_asset == other_debt_asset
        )
