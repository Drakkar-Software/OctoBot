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
import tentacles.Trading.Exchange.binance as binance_tentacle
import octobot_trading.enums as trading_enums
import octobot_trading.constants as trading_constants
import octobot_trading.exchanges.connectors.ccxt.constants as ccxt_constants


class BinanceUS(binance_tentacle.Binance):

    # should be overridden locally to match exchange support
    SUPPORTED_ELEMENTS = {
        trading_enums.ExchangeTypes.FUTURE.value: {
            # order that should be self-managed by OctoBot
            trading_enums.ExchangeSupportedElements.UNSUPPORTED_ORDERS.value: [
                trading_enums.TraderOrderType.STOP_LOSS,
                trading_enums.TraderOrderType.STOP_LOSS_LIMIT,
                trading_enums.TraderOrderType.TAKE_PROFIT,
                trading_enums.TraderOrderType.TAKE_PROFIT_LIMIT,
                trading_enums.TraderOrderType.TRAILING_STOP,
                trading_enums.TraderOrderType.TRAILING_STOP_LIMIT
            ],
            # order that can be bundled together to create them all in one request
            # not supported or need custom mechanics with batch orders
            trading_enums.ExchangeSupportedElements.SUPPORTED_BUNDLED_ORDERS.value: {},
        },
        trading_enums.ExchangeTypes.SPOT.value: {
            # order that should be self-managed by OctoBot
            trading_enums.ExchangeSupportedElements.UNSUPPORTED_ORDERS.value: [
                trading_enums.TraderOrderType.STOP_LOSS,    # unsupported on binance.us, only stop limit orders are supported https://docs.binance.us/#create-new-order-trade
                trading_enums.TraderOrderType.STOP_LOSS_LIMIT,
                trading_enums.TraderOrderType.TAKE_PROFIT,
                trading_enums.TraderOrderType.TAKE_PROFIT_LIMIT,
                trading_enums.TraderOrderType.TRAILING_STOP,
                trading_enums.TraderOrderType.TRAILING_STOP_LIMIT
            ],
            # order that can be bundled together to create them all in one request
            trading_enums.ExchangeSupportedElements.SUPPORTED_BUNDLED_ORDERS.value: {},
        }
    }

    @classmethod
    def get_name(cls):
        return 'binanceus'

    @classmethod
    def get_supported_exchange_types(cls) -> list:
        """
        :return: The list of supported exchange types
        """
        return [
            trading_enums.ExchangeTypes.SPOT,
        ]

    @staticmethod
    def get_default_reference_market(exchange_name: str) -> str:
        return "USDT"

    def get_additional_connector_config(self):
        config = super().get_additional_connector_config()
        # override to fix ccxt values
        config[ccxt_constants.CCXT_FEES] = {
            'trading': {
                'tierBased': True,
                'percentage': True,
                # ccxt replaced values
                # 'taker': float('0.001'),  # 0.1% trading fee, zero fees for all trading pairs before November 1.
                # 'maker': float('0.001'),  # 0.1% trading fee, zero fees for all trading pairs before November 1.
                # 03/03/2025 values https://www.binance.us/fees
                'taker': float('0.006'),  # 0.600%
                'maker': float('0.004'),  # 0.400%
            },
        }
        return config

    async def get_account_id(self, **kwargs: dict) -> str:
        # not available on binance.us
        # see https://docs.binance.us/#get-user-account-information-user_data
        # vs "uid" in regular binance https://binance-docs.github.io/apidocs/spot/en/#spot-account-endpoints
        return trading_constants.DEFAULT_ACCOUNT_ID
