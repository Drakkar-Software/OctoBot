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


class Htx(exchanges.RestExchange):
    FIX_MARKET_STATUS = True
    REMOVE_MARKET_STATUS_PRICE_LIMITS = True
    # set True when create_market_buy_order_with_cost should be used to create buy market orders
    # (useful to predict the exact spent amount)
    ENABLE_SPOT_BUY_MARKET_WITH_COST = True
    ADJUST_FOR_TIME_DIFFERENCE = True  # set True when the client needs to adjust its requests for time difference with the server

    @classmethod
    def get_name(cls):
        return 'htx'

    def get_adapter_class(self):
        return HtxCCXTAdapter

    def get_additional_connector_config(self):
        # tell ccxt to use amount as provided and not to compute it by multiplying it by price which is done here
        # (price should not be sent to market orders). Only used for buy market orders
        return {
            ccxt_constants.CCXT_OPTIONS: {
                "createMarketBuyOrderRequiresPrice": False  # disable quote conversion
            }
        }

    async def get_symbol_prices(self, symbol, time_frame, limit: int = 500, **kwargs: dict):
        history_param = "useHistoricalEndpointForSpot"
        if limit and history_param not in kwargs:
            # required to handle limits
            kwargs[history_param] = False
        return await super().get_symbol_prices(symbol, time_frame, limit=limit, **kwargs)


class HtxCCXTAdapter(exchanges.CCXTAdapter):

    def fix_order(self, raw, **kwargs):
        fixed = super().fix_order(raw, **kwargs)
        self.adapt_amount_from_filled_or_cost(fixed)
        return fixed
