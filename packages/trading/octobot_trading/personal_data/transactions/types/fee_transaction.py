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

import octobot_trading.constants as constants
import octobot_trading.enums as enums
import octobot_trading.personal_data.transactions.transaction as transaction


class FeeTransaction(transaction.Transaction):
    def __init__(
        self,
        exchange_name: str,
        creation_time: float,
        transaction_type: enums.TransactionType,
        currency: str,
        symbol: str,
        quantity: decimal.Decimal = constants.ZERO,
        order_id: typing.Optional[str] = None,
        funding_rate: typing.Optional[decimal.Decimal] = None
    ):
        self.quantity: decimal.Decimal = quantity
        self.order_id: typing.Optional[str] = order_id
        self.funding_rate: typing.Optional[decimal.Decimal] = funding_rate
        super().__init__(exchange_name, creation_time, transaction_type, currency, symbol=symbol)

    def is_funding_fee(self) -> bool:
        return self.transaction_type is enums.TransactionType.FUNDING_FEE

    def is_trading_fee(self) -> bool:
        return self.transaction_type is enums.TransactionType.TRADING_FEE
