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
import typing

import octobot_trading.exchanges as exchanges
import octobot_trading.enums as trading_enums
import octobot_trading.exchanges.connectors.ccxt.constants as ccxt_constants


class HyperliquidConnector(exchanges.CCXTConnector):

    def _client_factory(
        self,
        force_unauth,
        keys_adapter: typing.Callable[[exchanges.ExchangeCredentialsData], exchanges.ExchangeCredentialsData]=None
    ) -> tuple:
        return super()._client_factory(force_unauth, keys_adapter=self._keys_adapter)

    def _keys_adapter(self, creds: exchanges.ExchangeCredentialsData) -> exchanges.ExchangeCredentialsData:
        # use api key and secret as wallet address and private key
        creds.wallet_address = creds.api_key
        creds.private_key = creds.secret
        creds.api_key = creds.secret = None
        return creds


class Hyperliquid(exchanges.RestExchange):
    DESCRIPTION = ""
    DEFAULT_CONNECTOR_CLASS = HyperliquidConnector

    FIX_MARKET_STATUS = True
    REQUIRE_ORDER_FEES_FROM_TRADES = True  # set True when get_order is not giving fees on closed orders and fees
    # should be fetched using recent trades.

    @classmethod
    def get_name(cls):
        return 'hyperliquid'

    def get_adapter_class(self):
        return HyperLiquidCCXTAdapter

    def get_additional_connector_config(self):
        return {
            ccxt_constants.CCXT_OPTIONS: {
                "fetchMarkets": {
                    "types": ["spot"],  # only hyperliquid spot markets are supported
                }
            }
        }


class HyperLiquidCCXTAdapter(exchanges.CCXTAdapter):

    def fix_ticker(self, raw, **kwargs):
        fixed = super().fix_ticker(raw, **kwargs)
        fixed[trading_enums.ExchangeConstantsTickersColumns.TIMESTAMP.value] = \
            fixed.get(trading_enums.ExchangeConstantsTickersColumns.TIMESTAMP.value) or self.connector.client.seconds()
        return fixed

    def fix_market_status(self, raw, remove_price_limits=False, **kwargs):
        fixed = super().fix_market_status(raw, remove_price_limits=remove_price_limits, **kwargs)
        if not fixed:
            return fixed
        # hyperliquid min cost should be increased by 10% (a few cents above min cost is refused)
        limits = fixed[trading_enums.ExchangeConstantsMarketStatusColumns.LIMITS.value]
        limits[trading_enums.ExchangeConstantsMarketStatusColumns.LIMITS_COST.value][
            trading_enums.ExchangeConstantsMarketStatusColumns.LIMITS_COST_MIN.value
        ] = limits[trading_enums.ExchangeConstantsMarketStatusColumns.LIMITS_COST.value][
            trading_enums.ExchangeConstantsMarketStatusColumns.LIMITS_COST_MIN.value
        ] * 1.1

        return fixed
