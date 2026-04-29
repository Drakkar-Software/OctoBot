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
import octobot_trading.exchanges as exchanges
import octobot_trading.exchanges.connectors.ccxt.constants as ccxt_constants
import octobot_trading.enums as trading_enums


class Bitget(exchanges.RestExchange):
    DESCRIPTION = ""

    FIX_MARKET_STATUS = True
    REMOVE_MARKET_STATUS_PRICE_LIMITS = True
    # set True when create_market_buy_order_with_cost should be used to create buy market orders
    # (useful to predict the exact spent amount)
    ENABLE_SPOT_BUY_MARKET_WITH_COST = True

    @classmethod
    def get_name(cls):
        return 'bitget'

    def get_adapter_class(self):
        return BitgetCCXTAdapter

    def get_additional_connector_config(self):
        # tell ccxt to use amount as provided and not to compute it by multiplying it by price which is done here
        # (price should not be sent to market orders). Only used for buy market orders
        return {
            ccxt_constants.CCXT_OPTIONS: {
                "createMarketBuyOrderRequiresPrice": False  # disable quote conversion
            }
        }


class BitgetCCXTAdapter(exchanges.CCXTAdapter):

    def fix_order(self, raw, **kwargs):
        fixed = super().fix_order(raw, **kwargs)
        self.adapt_amount_from_filled_or_cost(fixed)
        return fixed

    def fix_trades(self, raw, **kwargs):
        raw = super().fix_trades(raw, **kwargs)
        for trade in raw:
            fee = trade[trading_enums.ExchangeConstantsOrderColumns.FEE.value]
            if trading_enums.FeePropertyColumns.CURRENCY.value not in fee:
                fee[trading_enums.FeePropertyColumns.CURRENCY.value] = fee.get("code")
        return raw
