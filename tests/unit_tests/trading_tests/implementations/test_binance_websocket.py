from tests.test_utils.config import load_test_config
from trading.exchanges.websockets_exchanges import BinanceWebSocketClient


class TestBinanceWebSocketClient:
    @staticmethod
    def init_default():
        config = load_test_config()
        binance_web_socket = BinanceWebSocketClient(config)
        return config, binance_web_socket

    @staticmethod
    def _update_order_message(symbol, side, price, quantity, type, filled_qty, status):
        msg = {
            "e": "executionReport",  # Event type
            "E": 1499405658658,  # Event time
            "s": symbol,  # Symbol
            "c": "mUvoqJxFIILMdfAW5iGSOW",  # Client order ID
            "S": side,  # Side
            "o": type,  # Order type
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

        return msg

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

    def test_update_portfolio(self):
        _, binance_web_socket = self.init_default()

        origin_pf = binance_web_socket.get_portfolio()

        # test with empty request
        binance_web_socket.user_callback(self._update_portfolio_message([]))
        new_pf = binance_web_socket.get_portfolio()

        assert origin_pf == new_pf

    def test_update_order(self):
        _, binance_web_socket = self.init_default()

        msg = self._update_order_message(None, None, None, None, None, None, None)
        binance_web_socket.user_callback(msg)

    def test_add_price(self):
        pass

    def test_set_ticker(self):
        pass
