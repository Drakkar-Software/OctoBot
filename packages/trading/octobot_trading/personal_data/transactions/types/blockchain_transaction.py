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
import decimal

import octobot_trading.constants as constants
import octobot_trading.enums as enums
import octobot_trading.personal_data.transactions.transaction as transaction


class BlockchainTransaction(transaction.Transaction):
    def __init__(
        self,
        exchange_name: str,
        creation_time: float,
        transaction_type: enums.TransactionType,
        currency: str,
        blockchain_network: str,
        blockchain_transaction_id: str,
        blockchain_transaction_status: enums.BlockchainTransactionStatus = enums.BlockchainTransactionStatus.CREATED,
        source_address: typing.Optional[str] = None,
        destination_address: typing.Optional[str] = None,
        quantity: decimal.Decimal = constants.ZERO,
        transaction_fee: typing.Optional[dict] = None,
    ):
        self.source_address: typing.Optional[str] = source_address
        self.destination_address: typing.Optional[str] = destination_address
        self.blockchain_transaction_id: str = blockchain_transaction_id
        self.blockchain_network: str = blockchain_network
        self.blockchain_transaction_status: enums.BlockchainTransactionStatus = blockchain_transaction_status
        self.quantity: decimal.Decimal = quantity
        self.transaction_fee: typing.Optional[dict] = transaction_fee
        super().__init__(
            exchange_name,
            creation_time,
            transaction_type,
            currency,
            symbol=None,
            transaction_id=self.blockchain_transaction_id
        )

    def is_deposit(self) -> bool:
        return self.transaction_type is enums.TransactionType.BLOCKCHAIN_DEPOSIT

    def is_withdrawal(self) -> bool:
        return self.transaction_type is enums.TransactionType.BLOCKCHAIN_WITHDRAWAL

    def is_pending(self) -> bool:
        return self.blockchain_transaction_status is enums.BlockchainTransactionStatus.CONFIRMING

    def is_validated(self) -> bool:
        return self.blockchain_transaction_status is enums.BlockchainTransactionStatus.SUCCESS
