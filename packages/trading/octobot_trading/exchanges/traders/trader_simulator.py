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
import time
import uuid

import octobot_trading.constants
import octobot_trading.enums as enums
import octobot_trading.exchanges.traders.trader as trader
import octobot_trading.util as util
import octobot_trading.personal_data.orders.order_util as order_util


class TraderSimulator(trader.Trader):
    """
    TraderSimulator has a role of exchange response simulator
    - During order creation / filling / canceling process
    """

    NO_HISTORY_MESSAGE = "Starting a fresh new trading simulation session using trader simulator initial portfolio " \
                         "in configuration."

    def __init__(self, config, exchange_manager):
        self.simulate = True
        super().__init__(config, exchange_manager)

        self.trader_type_str = octobot_trading.constants.SIMULATOR_TRADER_STR

    @staticmethod
    def enabled(config):
        return util.is_trader_simulator_enabled(config)

    def parse_order_id(self, order_id):
        return order_util.generate_order_id() if order_id is None else order_id

    async def get_deposit_address(self, asset: str, params: dict = None) -> dict:
        # mocked deposit address
        return {
            enums.ExchangeConstantsDepositAddressColumns.ADDRESS.value: f"{octobot_trading.constants.SIMULATED_DEPOSIT_ADDRESS}_{asset}",
            enums.ExchangeConstantsDepositAddressColumns.TAG.value: "",
            enums.ExchangeConstantsDepositAddressColumns.NETWORK.value: octobot_trading.constants.SIMULATED_BLOCKCHAIN_NETWORK,
            enums.ExchangeConstantsDepositAddressColumns.CURRENCY.value: asset,
        }

    async def _withdraw_on_exchange(
        self, asset: str, amount: decimal.Decimal, network: str, address: str, tag: str = "", params: dict = None
    ) -> dict:
        deposit_address = await self.get_deposit_address(asset)
        transaction_id = str(uuid.uuid4())
        return {
            enums.ExchangeConstantsTransactionColumns.TXID.value: transaction_id,
            enums.ExchangeConstantsTransactionColumns.TIMESTAMP.value: time.time(),
            enums.ExchangeConstantsTransactionColumns.ADDRESS_FROM.value: deposit_address[enums.ExchangeConstantsDepositAddressColumns.ADDRESS.value],
            enums.ExchangeConstantsTransactionColumns.ADDRESS_TO.value: address,
            enums.ExchangeConstantsTransactionColumns.AMOUNT.value: amount,
            enums.ExchangeConstantsTransactionColumns.CURRENCY.value: asset,
            enums.ExchangeConstantsTransactionColumns.ID.value: transaction_id,
            enums.ExchangeConstantsTransactionColumns.FEE.value: {
                enums.FeePropertyColumns.RATE.value: octobot_trading.constants.ZERO,
                enums.FeePropertyColumns.COST.value: octobot_trading.constants.ZERO,
                enums.FeePropertyColumns.CURRENCY.value: asset,
            },
            enums.ExchangeConstantsTransactionColumns.STATUS.value: enums.BlockchainTransactionStatus.SUCCESS.value,
            enums.ExchangeConstantsTransactionColumns.TAG.value: tag,
            enums.ExchangeConstantsTransactionColumns.TYPE.value: enums.TransactionType.BLOCKCHAIN_WITHDRAWAL.value,
            enums.ExchangeConstantsTransactionColumns.NETWORK.value: network,
            enums.ExchangeConstantsTransactionColumns.COMMENT.value: "",
            enums.ExchangeConstantsTransactionColumns.INTERNAL.value: False,            
        }
