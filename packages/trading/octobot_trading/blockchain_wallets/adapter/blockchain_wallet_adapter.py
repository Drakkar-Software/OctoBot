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
import octobot_trading.exchanges.adapters as adapters
import octobot_trading.personal_data as personal_data
import octobot_trading.constants as constants
import octobot_trading.enums as enums
import octobot_trading.blockchain_wallets.adapter.types as types

class BlockchainWalletAdapter(adapters.AbstractAdapter):

    def parse_balance(self, fixed: dict[str, types.Balance], **kwargs) -> dict:
        portfolio = {
            asset: { 
                constants.CONFIG_PORTFOLIO_FREE: balance.free,
                constants.CONFIG_PORTFOLIO_USED: balance.used,
                constants.CONFIG_PORTFOLIO_TOTAL: balance.total,
            }
            for asset, balance in fixed.items()
        }
        return personal_data.parse_decimal_portfolio(portfolio)

    def parse_transaction(self, fixed: types.Transaction, **kwargs) -> dict:
        # CCXT standard transaction parsing logic
        return {
            enums.ExchangeConstantsTransactionColumns.ID.value: fixed.id,
            enums.ExchangeConstantsTransactionColumns.TXID.value: fixed.txid,
            enums.ExchangeConstantsTransactionColumns.TIMESTAMP.value: fixed.timestamp,
            enums.ExchangeConstantsTransactionColumns.ADDRESS_FROM.value: fixed.address_from,
            enums.ExchangeConstantsTransactionColumns.ADDRESS_TO.value: fixed.address_to,
            enums.ExchangeConstantsTransactionColumns.TAG.value: fixed.tag,
            enums.ExchangeConstantsTransactionColumns.TYPE.value: fixed.type,
            enums.ExchangeConstantsTransactionColumns.AMOUNT.value: fixed.amount,
            enums.ExchangeConstantsTransactionColumns.CURRENCY.value: fixed.currency,
            enums.ExchangeConstantsTransactionColumns.STATUS.value: fixed.status,
            enums.ExchangeConstantsTransactionColumns.FEE.value: fixed.fee,
            enums.ExchangeConstantsTransactionColumns.NETWORK.value: fixed.network,
            enums.ExchangeConstantsTransactionColumns.COMMENT.value: fixed.comment,
            enums.ExchangeConstantsTransactionColumns.INTERNAL.value: fixed.internal,
        }

    def parse_deposit_address(self, fixed: types.DepositAddress, **kwargs) -> dict:
        # CCXT standard deposit_address parsing logic
        return {
            enums.ExchangeConstantsDepositAddressColumns.CURRENCY.value: fixed.currency,
            enums.ExchangeConstantsDepositAddressColumns.NETWORK.value: fixed.network,
            enums.ExchangeConstantsDepositAddressColumns.ADDRESS.value: fixed.address,
            enums.ExchangeConstantsDepositAddressColumns.TAG.value: fixed.tag,
        }
