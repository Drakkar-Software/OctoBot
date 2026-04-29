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

import octobot_trading.enums as enums
import octobot_trading.constants as constants
import octobot_trading.personal_data.transactions.transaction as transaction


class RealisedPnlTransaction(transaction.Transaction):
    def __init__(
        self,
        exchange_name: str,
        creation_time: float,
        transaction_type: enums.TransactionType,
        currency: str,
        symbol: str,
        realised_pnl: decimal.Decimal = constants.ZERO,
        closed_quantity: decimal.Decimal = constants.ZERO,
        cumulated_closed_quantity: decimal.Decimal = constants.ZERO,
        first_entry_time: float = 0,
        average_entry_price: decimal.Decimal = constants.ZERO,
        average_exit_price: decimal.Decimal = constants.ZERO,
        order_exit_price: decimal.Decimal = constants.ZERO,
        leverage: decimal.Decimal = constants.ZERO,
        trigger_source: enums.PNLTransactionSource = enums.PNLTransactionSource.UNKNOWN,
        side: enums.PositionSide = enums.PositionSide.UNKNOWN,
        transaction_id: typing.Optional[str] = None
    ):
        super().__init__(
            exchange_name, creation_time, transaction_type, currency, symbol=symbol, transaction_id=transaction_id
        )
        self.realised_pnl: decimal.Decimal = realised_pnl
        self.closed_quantity: decimal.Decimal = closed_quantity
        self.cumulated_closed_quantity: decimal.Decimal = cumulated_closed_quantity
        self.first_entry_time: float = first_entry_time
        self.average_entry_price: decimal.Decimal = average_entry_price
        self.average_exit_price: decimal.Decimal = average_exit_price
        self.order_exit_price: decimal.Decimal = order_exit_price
        self.leverage: decimal.Decimal = leverage
        self.trigger_source: enums.PNLTransactionSource = trigger_source
        self.side: enums.PositionSide = side

    def is_closed_pnl(self) -> bool:
        return self.transaction_type is enums.TransactionType.CLOSE_REALISED_PNL
