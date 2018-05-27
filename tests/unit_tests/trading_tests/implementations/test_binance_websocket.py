from tests.test_utils.config import load_test_config
from trading.exchanges.websockets_exchanges import BinanceWebSocketClient


class TestBinanceWebSocketClient:
    @staticmethod
    def init_default():
        config = load_test_config()
        binance_web_socket = BinanceWebSocketClient(config)
        return config, binance_web_socket

    def test_update_portfolio(self):
        _, binance_web_socket = self.init_default()

        msg = {
          "e": "outboundAccountInfo",
          "E": 1499405658849,
          "m": 0,
          "t": 0,
          "b": 0,                       # Buyer commission rate (bips)
          "s": 0,                       # Seller commission rate (bips)
          "T": True,                    # Can trade?
          "W": True,                    # Can withdraw?
          "D": True,                    # Can deposit?
          "u": 1499405658848,           # Time of last account update
          "B": [                        # Balances array
            {
              "a": "LTC",               # Asset
              "f": "17366.18538083",    # Free amount
              "l": "0.00000000"         # Locked amount
            },
            {
              "a": "BTC",
              "f": "10537.85314051",
              "l": "2.19464093"
            },
            {
              "a": "ETH",
              "f": "17902.35190619",
              "l": "0.00000000"
            },
            {
              "a": "BNC",
              "f": "1114503.29769312",
              "l": "0.00000000"
            },
            {
              "a": "NEO",
              "f": "0.00000000",
              "l": "0.00000000"
            }
          ]
        }

        binance_web_socket.user_callback(msg)

    def test_update_order(self):
        _, binance_web_socket = self.init_default()
        
        msg = {
          "e": "executionReport",        # Event type
          "E": 1499405658658,            # Event time
          "s": "ETHBTC",                 # Symbol
          "c": "mUvoqJxFIILMdfAW5iGSOW", # Client order ID
          "S": "BUY",                    # Side
          "o": "LIMIT",                  # Order type
          "f": "GTC",                    # Time in force
          "q": "1.00000000",             # Order quantity
          "p": "0.10264410",             # Order price
          "P": "0.00000000",             # Stop price
          "F": "0.00000000",             # Iceberg quantity
          "g": -1,                       # Ignore
          "C": "null",                   # Original client order ID; This is the ID of the order being canceled
          "x": "NEW",                    # Current execution type
          "X": "NEW",                    # Current order status
          "r": "NONE",                   # Order reject reason; will be an error code.
          "i": 4293153,                  # Order ID
          "l": "0.00000000",             # Last executed quantity
          "z": "0.00000000",             # Cumulative filled quantity
          "L": "0.00000000",             # Last executed price
          "n": "0",                      # Commission amount
          "N": None,                     # Commission asset
          "T": 1499405658657,            # Transaction time
          "t": -1,                       # Trade ID
          "I": 8641984,                  # Ignore
          "w": True,                     # Is the order working? Stops will have
          "m": False,                    # Is this trade the maker side?
          "M": False                     # Ignore
        }

        binance_web_socket.user_callback(msg)

    def test_add_price(self):
        pass

    def test_set_ticker(self):
        pass

