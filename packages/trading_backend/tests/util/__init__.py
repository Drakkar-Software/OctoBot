#  Drakkar-Software trading-backend
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
import contextlib
import mock


def _ccxt_market_mock(symbol: str):
    return {
        'id': symbol, 'lowercaseId': None, 'symbol': symbol, 'base': 'BTC', 'quote': 'USDT',
        'settle': None, 'baseId': 'BTC', 'quoteId': 'USDT', 'settleId': None, 'type': 'spot',
        'spot': True, 'margin': None, 'swap': False, 'future': False, 'option': False,
        'index': None, 'active': True, 'contract': False, 'linear': None, 'inverse': None,
        'subType': None, 'taker': 0.006, 'maker': 0.004, 'contractSize': None, 'expiry': None,
        'expiryDatetime': None, 'strike': None, 'optionType': None,
        'precision': {'amount': 1e-08, 'price': 0.01, 'cost': None, 'base': None, 'quote': None},
        'limits': {'leverage': {'min': None, 'max': None}, 'amount': {'min': 1e-08, 'max': 3400.0},
                   'price': {'min': None, 'max': None}, 'cost': {'min': 1.0, 'max': 150000000.0}},
        'created': None, 'info': {'product_id': symbol, 'price': '71252',
                                  'price_percentage_change_24h': '-0.18659329945143',
                                  'volume_24h': '9777.87301488',
                                  'volume_percentage_change_24h': '13.17432199869977',
                                  'base_increment': '0.00000001', 'quote_increment': '0.01',
                                  'quote_min_size': '1', 'quote_max_size': '150000000',
                                  'base_min_size': '0.00000001', 'base_max_size': '3400',
                                  'base_name': 'Bitcoin', 'quote_name': 'USDT', 'watched': False,
                                  'is_disabled': False, 'new': False, 'status': 'online',
                                  'cancel_only': False,
                                  'limit_only': True,
                                  'post_only': False,
                                  'trading_disabled': False, 'auction_mode': False,
                                  'product_type': 'SPOT', 'quote_currency_id': 'USDT',
                                  'base_currency_id': 'BTC', 'fcm_trading_session_details': None,
                                  'mid_market_price': '', 'alias': symbol, 'alias_to': [],
                                  'base_display_symbol': 'BTC', 'quote_display_symbol': 'USD',
                                  'view_only': False, 'price_increment': '0.01',
                                  'display_name': symbol, 'product_venue': 'CBE',
                                  'approximate_quote_24h_volume': '696693008.06'},
        'percentage': True, 'tierBased': True, 'tiers': {
            'taker': [[0.0, 0.006], [10000.0, 0.004], [50000.0, 0.0025], [100000.0, 0.002],
                      [1000000.0, 0.0018], [15000000.0, 0.0016], [75000000.0, 0.0012],
                      [250000000.0, 0.0008], [400000000.0, 0.0005]],
            'maker': [[0.0, 0.004], [10000.0, 0.0025], [50000.0, 0.0015], [100000.0, 0.001],
                      [1000000.0, 0.0008], [15000000.0, 0.0006], [75000000.0, 0.0003], [250000000.0, 0.0],
                      [400000000.0, 0.0]]}
    }


@contextlib.contextmanager
def mocked_load_markets(exchange):
    def load_markets():
        exchange._exchange.connector.client.markets = {
            exchange._get_symbol(): _ccxt_market_mock(exchange._get_symbol())
        }
    with mock.patch.object(exchange._exchange.connector.client, "load_markets", mock.AsyncMock(side_effect=load_markets)) as load_markets_mock:
        yield load_markets_mock
