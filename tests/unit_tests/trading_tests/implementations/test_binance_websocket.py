#  Drakkar-Software OctoBot
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

from copy import deepcopy
import pytest

import ccxt

from tests.test_utils.config import load_test_config
from octobot_trading.exchanges import ExchangeManager
from octobot_trading.exchanges.websockets.binance_websocket import BinanceWebSocketClient


# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


class TestBinanceWebSocketClient:
    @staticmethod
    async def init_default():
        config = load_test_config()
        exchange_manager = ExchangeManager(config, ccxt.binance, True)
        await exchange_manager.initialize()
        binance_web_socket = BinanceWebSocketClient(config, exchange_manager)
        return config, binance_web_socket

    @staticmethod
    def price_message_header(stream, data):
        return {
            "stream": stream,
            "data": data
        }

    @staticmethod
    def _ticker_message(symbol):
        return TestBinanceWebSocketClient.price_message_header("@ticker", {
            "e": "24hrTicker",  # Event type
            "E": 123456789,  # Event time
            "s": symbol,  # Symbol
            "p": "0.0015",  # Price change
            "P": "250.00",  # Price change percent
            "w": "0.0018",  # Weighted average price
            "x": "0.0009",  # Previous day's close price
            "c": "0.0025",  # Current day's close price
            "Q": "10",  # Close trade's quantity
            "b": "0.0024",  # Best bid price
            "B": "10",  # Best bid quantity
            "a": "0.0026",  # Best ask price
            "A": "100",  # Best ask quantity
            "o": "0.0010",  # Open price
            "h": "0.0025",  # High price
            "l": "0.0010",  # Low price
            "v": "10000",  # Total traded base asset volume
            "q": "18",  # Total traded quote asset volume
            "O": 0,  # Statistics open time
            "C": 86400000,  # Statistics close time
            "F": 0,  # First trade ID
            "L": 18150,  # Last trade Id
            "n": 18151  # Total number of trades
        })

    @staticmethod
    def _kline_message(symbol, open_price, close_price, high_price, low_price, start_time, interval):
        return TestBinanceWebSocketClient.price_message_header("@kline", {
            "e": "kline",  # Event type
            "E": 123456789,  # Event time
            "s": symbol,  # Symbol
            "k": {
                "t": start_time,  # Kline start time
                "T": 123460000,  # Kline close time
                "s": "BNBBTC",  # Symbol
                "i": interval,  # Interval
                "f": 100,  # First trade ID
                "L": 200,  # Last trade ID
                "o": open_price,  # Open price
                "c": close_price,  # Close price
                "h": high_price,  # High price
                "l": low_price,  # Low price
                "v": "1000",  # Base asset volume
                "n": 100,  # Number of trades
                "x": False,  # Is this kline closed?
                "q": "1.0000",  # Quote asset volume
                "V": "500",  # Taker buy base asset volume
                "Q": "0.500",  # Taker buy quote asset volume
                "B": "123456"  # Ignore
            }
        })

    @staticmethod
    def _update_order_message(symbol, side, price, quantity, order_type, filled_qty, status):
        return {
            "e": "executionReport",  # Event type
            "E": 1499405658658,  # Event time
            "s": symbol,  # Symbol
            "c": "mUvoqJxFIILMdfAW5iGSOW",  # Client order ID
            "S": side,  # Side
            "o": order_type,  # Order type
            "f": "GTC",  # Time in force
            "q": quantity,  # Order quantity
            "p": price,  # Order price
            "P": "0.00000000",  # Stop price
            "F": "0.00000000",  # Iceberg quantity
            "g": -1,  # Ignore
            "C": "null",  # Original client order ID; This is the ID of the order being canceled
            "x": "NEW",  # Current execution type
            "X": status,  # Current order status
            "r": "NONE",  # Order reject reason; will be an error code.
            "i": 4293153,  # Order ID
            "l": "0.00000000",  # Last executed quantity
            "z": filled_qty,  # Cumulative filled quantity
            "L": "0.00000000",  # Last executed price
            "n": "0",  # Commission amount
            "N": None,  # Commission asset
            "T": 1499405658657,  # Transaction time
            "t": -1,  # Trade ID
            "I": 8641984,  # Ignore
            "w": True,  # Is the order working? Stops will have
            "m": False,  # Is this trade the maker side?
            "M": False  # Ignore
        }

    @staticmethod
    def _update_portfolio_message(symbols_data):
        msg = {
            "e": "outboundAccountInfo",
            "E": 1499405658849,
            "m": 0,
            "t": 0,
            "b": 0,  # Buyer commission rate (bips)
            "s": 0,  # Seller commission rate (bips)
            "T": True,  # Can trade?
            "W": True,  # Can withdraw?
            "D": True,  # Can deposit?
            "u": 1499405658848,  # Time of last account update
            "B": []
        }

        for symbol_data in symbols_data:
            msg["B"].append({
                "a": symbol_data["asset"],
                "f": symbol_data["free"],
                "l": symbol_data["locked"],
            })

        return msg

    async def test_update_portfolio(self):
        _, binance_web_socket = await self.init_default()

        binance_web_socket.get_personal_data().init_portfolio()

        origin_pf = deepcopy(binance_web_socket.get_personal_data().get_portfolio())

        # test with empty request
        binance_web_socket.user_callback(self._update_portfolio_message([]))
        new_pf = binance_web_socket.get_personal_data().get_portfolio()
        assert origin_pf == new_pf

        # test with not empty request
        binance_web_socket.user_callback(self._update_portfolio_message([{
            "asset": "BTC",
            "free": 0.5,
            "locked": 1,
        }]))
        new_pf = binance_web_socket.get_personal_data().get_portfolio()
        assert origin_pf != new_pf

        new_origin_pf = deepcopy(binance_web_socket.get_personal_data().get_portfolio())

        # test with empty request
        binance_web_socket.user_callback(self._update_portfolio_message([]))
        new_pf = binance_web_socket.get_personal_data().get_portfolio()
        assert new_origin_pf == new_pf

        # test with not empty request and not empty pf
        binance_web_socket.user_callback(self._update_portfolio_message([{
            "asset": "BTC",
            "free": 0.2,
            "locked": 15,
        }]))
        new_pf = binance_web_socket.get_personal_data().get_portfolio()
        assert new_origin_pf != new_pf
        new_origin_pf = deepcopy(binance_web_socket.get_personal_data().get_portfolio())

        # test with not empty request and diff symbol
        binance_web_socket.user_callback(self._update_portfolio_message([{
            "asset": "ETH",
            "free": 25.69,
            "locked": 31547,
        }]))
        new_pf = binance_web_socket.get_personal_data().get_portfolio()
        assert new_origin_pf["BTC"] == new_pf["BTC"]
        new_origin_pf = deepcopy(binance_web_socket.get_personal_data().get_portfolio())

        # test with not empty request and multiple symbol
        binance_web_socket.user_callback(self._update_portfolio_message([{
            "asset": "XRP",
            "free": 25978,
            "locked": 315047,
        }, {
            "asset": "LTC",
            "free": 25478.5877,
            "locked": 14875.1445,
        }, {
            "asset": "BCH",
            "free": 0.00015,
            "locked": 0.1055456,
        }]))
        new_pf = binance_web_socket.get_personal_data().get_portfolio()
        assert new_origin_pf["BTC"] == new_pf["BTC"]
        assert new_origin_pf["ETH"] == new_pf["ETH"]
        assert new_pf["XRP"]["free"] == 25978
        assert new_pf["LTC"]["used"] == 14875.1445
        assert new_pf["BCH"]["total"] == 0.00015 + 0.1055456

    async def test_set_ticker(self):
        _, binance_web_socket = await self.init_default()

        symbol = "BTCUSDT"

        symbol_data = binance_web_socket.get_symbol_data(symbol)
        symbol_data.update_symbol_ticker({})

        msg = self._ticker_message(symbol)
        binance_web_socket.all_currencies_prices_callback(msg)

        # assert symbol == symbol_data.symbol_ticker["symbol"]
        # assert symbol_data.symbol_ticker["info"] == msg["data"]
