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
import cachetools
import ccxt.async_support as async_ccxt

import octobot_trading.exchanges.connectors.ccxt.ccxt_client_util as ccxt_client_util
import octobot_trading.enums as enums


def parse_markets(exchange_name: str, additional_client_config: dict, market_filter) -> dict:
    client = _temp_client(exchange_name, additional_client_config=additional_client_config)
    ccxt_client_util.load_markets_from_cache(client, False, market_filter)
    return client.markets


def get_fees(market_status) -> dict:
    return ccxt_client_util.get_fees(market_status)


def get_contract_size(market_status: dict) -> decimal.Decimal:
    return decimal.Decimal(str(ccxt_client_util.get_market_status_contract_size(market_status)))


@cachetools.cached(cachetools.LRUCache(maxsize=256))
def get_option_value(
    exchange_name: str, option_key: enums.ExchangeClientOptions
) -> typing.Union[bool, float, int, str, None]:
    return ccxt_client_util.get_option_value(_temp_client(exchange_name), option_key)


@cachetools.cached(cachetools.LRUCache(maxsize=256))
def supports_bundled_orders(exchange_name: str, exchange_type: enums.ExchangeTypes, order_type: enums.TradeOrderType) -> bool:
    return ccxt_client_util.supports_bundled_orders(
        _temp_client(exchange_name), exchange_type, order_type
    )


def _temp_client(exchange_name: str, additional_client_config: typing.Optional[dict] = None) -> async_ccxt.Exchange:
    exchange_class = ccxt_client_util.ccxt_exchange_class_factory(exchange_name)
    config = {
        **(additional_client_config or {}),
        **ccxt_client_util.get_custom_domain_config(exchange_class)
    }
    return exchange_class(config)
