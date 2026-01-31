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

import octobot_trading.exchanges.connectors.ccxt.ccxt_client_util as ccxt_client_util


def parse_markets(exchange_name: str, additional_client_config: dict, market_filter) -> dict:
    exchange_class = ccxt_client_util.ccxt_exchange_class_factory(exchange_name)
    config = {
        **additional_client_config,
        **ccxt_client_util.get_custom_domain_config(exchange_class)
    }
    client = exchange_class(config)
    ccxt_client_util.load_markets_from_cache(client, False, market_filter)
    return client.markets


def get_fees(market_status) -> dict:
    return ccxt_client_util.get_fees(market_status)


def get_contract_size(market_status: dict) -> decimal.Decimal:
    return decimal.Decimal(str(ccxt_client_util.get_market_status_contract_size(market_status)))
