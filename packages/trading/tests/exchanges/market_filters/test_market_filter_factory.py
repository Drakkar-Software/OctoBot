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
import octobot_commons.symbols as commons_symbols
import octobot_trading.constants as trading_constants
import octobot_trading.enums as trading_enums
import octobot_trading.exchanges as exchanges
import octobot_trading.util.test_tools.exchange_data as exchange_data_import


def _market(base, quote, m_type):
    return {
        trading_enums.ExchangeConstantsMarketStatusColumns.SYMBOL.value: commons_symbols.merge_currencies(
            base, quote
        ),
        trading_enums.ExchangeConstantsMarketStatusColumns.CURRENCY.value: base,
        trading_enums.ExchangeConstantsMarketStatusColumns.MARKET.value: quote,
        trading_enums.ExchangeConstantsMarketStatusColumns.TYPE.value: m_type,
    }


def _get_market_symbols(markets):
    return [
        commons_symbols.merge_currencies(
            m[trading_enums.ExchangeConstantsMarketStatusColumns.CURRENCY.value],
            m[trading_enums.ExchangeConstantsMarketStatusColumns.MARKET.value],
        )
        for m in markets
    ]


MARKETS = [
    _market(base, quote, m_type)
    for base, quote, m_type in [
        ("BTC", "USDT", trading_enums.ExchangeTypes.SPOT.value),
        ("BTC", "USDC", trading_enums.ExchangeTypes.SPOT.value),
        ("ETH", "USDT", trading_enums.ExchangeTypes.SPOT.value),
        ("USDC", "USDT", trading_enums.ExchangeTypes.SPOT.value),
        ("ETH", "BTC", trading_enums.ExchangeTypes.SPOT.value),
        ("DAI", "USDT", trading_enums.ExchangeTypes.SPOT.value),
        ("DAI", "BUSD", trading_enums.ExchangeTypes.SPOT.value),
        ("ZEC", "ETH", trading_enums.ExchangeTypes.SPOT.value),
        ("ZEC", "BTC", trading_enums.ExchangeTypes.SPOT.value),
        ("USDT", "BNB", trading_enums.ExchangeTypes.SPOT.value),
        ("XBY", "DAI", trading_enums.ExchangeTypes.SPOT.value),
        ("NANO", "JPUSD", trading_enums.ExchangeTypes.SPOT.value),
        ("NANO", "USDT", trading_enums.ExchangeTypes.SPOT.value),
    ]
]


def test_create_market_filter():
    empty_exchange_data = exchange_data_import.ExchangeData()

    assert _get_market_symbols(
        [m for m in MARKETS if exchanges.create_market_filter(empty_exchange_data, "BTC")(m)]
    ) == ['BTC/USDT', 'BTC/USDC', 'USDC/USDT', 'ETH/BTC', 'DAI/USDT', 'DAI/BUSD', 'ZEC/BTC', 'USDT/BNB']

    assert _get_market_symbols(
        [m for m in MARKETS if exchanges.create_market_filter(empty_exchange_data, "USDT")(m)]
    ) == ['BTC/USDT', 'ETH/USDT', 'USDC/USDT', 'DAI/USDT', 'DAI/BUSD', 'USDT/BNB', 'NANO/USDT']

    exchange_data_with_orders = exchange_data_import.ExchangeData()
    exchange_data_with_orders.orders_details.open_orders = [
        {
            trading_constants.STORAGE_ORIGIN_VALUE: {
                trading_enums.ExchangeConstantsOrderColumns.SYMBOL.value: "XBY/DAI",
            }
        }
    ]
    exchange_data_with_orders.orders_details.missing_orders = [
        {
            trading_constants.STORAGE_ORIGIN_VALUE: {
                trading_enums.ExchangeConstantsOrderColumns.SYMBOL.value: "NANO/JPUSD",
            }
        }
    ]

    assert _get_market_symbols(
        [m for m in MARKETS if exchanges.create_market_filter(exchange_data_with_orders, "USDT")(m)]
    ) == [
        'BTC/USDT', 'ETH/USDT', 'USDC/USDT', 'DAI/USDT', 'DAI/BUSD',
        'USDT/BNB', "XBY/DAI", "NANO/JPUSD", "NANO/USDT",
    ]

    assert _get_market_symbols(
        [
            m
            for m in MARKETS
            if exchanges.create_market_filter(
                exchange_data_with_orders,
                "USDT",
                to_keep_symbols={"ZEC/BTC"},
            )(m)
        ]
    ) == [
        'BTC/USDT', 'ETH/USDT', 'USDC/USDT', 'DAI/USDT', 'DAI/BUSD',
        'ZEC/BTC', 'USDT/BNB', "XBY/DAI", "NANO/JPUSD", "NANO/USDT",
    ]

    assert _get_market_symbols(
        [
            m
            for m in MARKETS
            if exchanges.create_market_filter(
                exchange_data_with_orders,
                "USDT",
                to_keep_symbols={"ZEC/BTC"},
                to_keep_quotes={"USDC"},
            )(m)
        ]
    ) == [
        'BTC/USDT', 'BTC/USDC', 'ETH/USDT', 'USDC/USDT', 'DAI/USDT', 'DAI/BUSD',
        'ZEC/BTC', 'USDT/BNB', "XBY/DAI", "NANO/JPUSD", "NANO/USDT",
    ]

    exchange_data_with_markets = exchange_data_import.ExchangeData()
    exchange_data_with_markets.markets = [
        exchange_data_import.MarketDetails(symbol="ZEC/BTC"),
    ]

    assert _get_market_symbols(
        [m for m in MARKETS if exchanges.create_market_filter(exchange_data_with_markets, "USDT")(m)]
    ) == [
        'BTC/USDT', 'ETH/USDT', 'USDC/USDT', 'DAI/USDT', 'DAI/BUSD',
        'ZEC/BTC',  # from markets
        'USDT/BNB', "NANO/USDT",
    ]
