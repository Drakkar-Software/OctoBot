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
import typing

import octobot_trading.enums as enums
import octobot_trading.personal_data.transactions.transaction as transaction


class TransferTransaction(transaction.Transaction):
    def __init__(
        self,
        exchange_name: str,
        creation_time: float,
        currency: str,
        symbol: str,
        transaction_id: typing.Optional[str] = None
    ):
        super().__init__(
            exchange_name,
            creation_time,
            transaction_type=enums.TransactionType.TRANSFER,
            currency=currency,
            symbol=symbol,
            transaction_id=transaction_id
        )
