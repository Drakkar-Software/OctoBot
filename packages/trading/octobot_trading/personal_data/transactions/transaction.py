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
import uuid
import typing

import octobot_trading.enums as enums


class Transaction:

    def __init__(
        self,
        exchange_name: str,
        creation_time: float,
        transaction_type: enums.TransactionType,
        currency: str,
        symbol: typing.Optional[str] = None,
        transaction_id: typing.Optional[str] = None
    ):
        self.transaction_id: str = transaction_id or str(uuid.uuid4()) # generate default transaction id if not provided
        self.transaction_type: enums.TransactionType = transaction_type
        self.creation_time: float = creation_time

        self.exchange_name: str = exchange_name
        self.symbol: typing.Optional[str] = symbol
        self.currency: str = currency

    def set_transaction_id(self, new_id):
        """
        Shouldn't be called outside of TransactionsManager.update_transaction_id
        to maintain TransactionsManager.transactions integrity
        :param new_id: the new transaction id
        """
        self.transaction_id = new_id
