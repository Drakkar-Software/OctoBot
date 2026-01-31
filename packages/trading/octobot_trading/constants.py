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
#  License along with this library
import decimal
import os

import octobot_trading.enums as enums
import octobot_commons.enums as commons_enums
import octobot_commons.constants as commons_constants
import octobot_commons.os_util as os_util

# Strings
CURRENT_PORTFOLIO_STRING = "Current Portfolio :"
CONFIG_PORTFOLIO_FREE = "free"
CONFIG_PORTFOLIO_USED = "used"
CONFIG_PORTFOLIO_TOTAL = "total"
CONFIG_PORTFOLIO_MARGIN = "margin"
REAL_TRADER_STR = "[Real Trader] "
SIMULATOR_TRADER_STR = "[Simulator] "

# Trader
DEFAULT_REFERENCE_MARKET = "BTC"
CURRENCY_DEFAULT_MAX_PRICE_DIGITS = 8
ALLOW_SIMULATED_ORDERS_INSTANT_FILL = os_util.parse_boolean_environment_var(
    "ALLOW_SIMULATED_ORDERS_INSTANT_FILL", "False"
)

# Order creation
ORDER_DATA_FETCHING_TIMEOUT = 5 * commons_constants.MINUTE_TO_SECONDS
ACTIVE_ORDER_STRATEGY_SWAP_TIMEOUT = 2 * commons_constants.MINUTE_TO_SECONDS
CHAINED_ORDER_PRICE_FETCHING_TIMEOUT = 1    # should be instant or ignored
CHAINED_ORDERS_OUTDATED_PRICE_ALLOWANCE = decimal.Decimal("0.005")  # allows 0.5% outdated price error
# create instantly filled limit orders 0.5% beyond market
INSTANT_FILLED_LIMIT_ORDER_PRICE_DELTA = decimal.Decimal("0.005")
CREATED_ORDER_FORCED_UPDATE_PERIOD = 5
DEFAULT_MAX_DEFAULT_ORDERS_COUNT = 100
DEFAULT_MAX_STOP_ORDERS_COUNT = 10
INCLUDE_DUSTS_IN_SELL_ORDERS_WHEN_POSSIBLE = os_util.parse_boolean_environment_var(
    "INCLUDE_DUSTS_IN_SELL_ORDERS_WHEN_POSSIBLE", "true"
)

# Portfolio
MAX_PORTFOLIO_SYNC_ATTEMPTS = 1
EXPECTED_PORTFOLIO_UPDATE_TIMEOUT = 1 * commons_constants.MINUTE_TO_SECONDS
SUB_PORTFOLIO_ALLOWED_MISSING_RATIO = decimal.Decimal("0.01")   # Allow 1% missing funds
SUB_PORTFOLIO_ALLOWED_DELTA_RATIO = decimal.Decimal("0.05")   # Allow 5% delta compared to filled orders
MAX_ORDER_INFERENCE_QUICK_CHECK_COMBINATIONS_COUNT = 10000
MAX_ORDER_SECONDARY_INFERENCE_COMBINATIONS_COUNT = 500000 # no more than 500.000 combinations to check to avoid overloads
MAX_NO_THREAD_WORSE_CASE_SCENARIO_FULLY_HANLDED_INFERENCE = 15 # 7 filled orders out of 15 is 6.435 combinations, 16 is 12.870 combinations (>10.000)
MAX_ORDERS_WORSE_CASE_SCENARIO_FULLY_HANLDED_INFERENCE = 21 # 10(or 11) filled orders out of 21 is 352.716 combinations, 22 is 705.432 combinations (>500.000)
MAX_ORDER_INFERENCE_ITERATIONS_DURATION = 1
ORDER_INFERENCE_SLEEP_TIME = 1

# Tentacles
TRADING_MODE_REQUIRED_STRATEGIES = "required_strategies"
TRADING_MODE_REQUIRED_STRATEGIES_MIN_COUNT = "required_strategies_min_count"
TENTACLES_TRADING_MODE_PATH = "Mode"
CONFIG_CANDLES_HISTORY_SIZE_TITLE = "Candles history size"
CONFIG_CANDLES_HISTORY_SIZE_KEY = CONFIG_CANDLES_HISTORY_SIZE_TITLE.replace(" ", "_")
CONFIG_BUY_ORDER_AMOUNT = "buy_order_amount"
CONFIG_SELL_ORDER_AMOUNT = "sell_order_amount"
CONFIG_LEVERAGE = "leverage"
TRADING_MODE_ACTIVITY_REASON = "reason"

# Exchange
DEFAULT_EXCHANGE_TIME_LAG = 10
DEFAULT_BACKTESTING_TIME_LAG = 0
INFINITE_MAX_HANDLED_PAIRS_WITH_TIMEFRAME = -1
DEFAULT_CANDLE_HISTORY_SIZE = 200
NO_DATA_LIMIT = -1
DEFAULT_FAILED_REQUEST_RETRY_TIME = 1
FAILED_NETWORK_REQUEST_RETRY_ATTEMPTS = 5
FAILED_PROXY_NETWORK_REQUEST_RETRY_ATTEMPTS = 2
TOOLS_FAILED_NETWORK_REQUEST_ATTEMPTS = int(os.getenv("TOOLS_FAILED_NETWORK_REQUEST_ATTEMPTS", "2"))
TOOLS_FAILED_NETWORK_REQUEST_RETRY_DELAY = int(os.getenv("TOOLS_FAILED_NETWORK_REQUEST_RETRY_DELAY", "5"))
DEFAULT_REQUEST_TIMEOUT = int(os.getenv("DEFAULT_REQUEST_TIMEOUT", "20000"))    # default ccxt is 10s, use 20
ENABLE_EXCHANGE_HTTP_PROXY_FROM_ENV = os_util.parse_boolean_environment_var(
    "ENABLE_EXCHANGE_HTTP_PROXY_FROM_ENV", "True"
)
EXCHANGE_HTTP_PROXY_AUTHENTICATED_URL = os.getenv("EXCHANGE_HTTP_PROXY_AUTHENTICATED_URL")
EXCHANGE_HTTPS_PROXY_AUTHENTICATED_URL = os.getenv("EXCHANGE_HTTPS_PROXY_AUTHENTICATED_URL")
EXCHANGE_SOCKS_PROXY_AUTHENTICATED_URL = os.getenv("EXCHANGE_SOCKS_PROXY_AUTHENTICATED_URL")
ENABLE_CCXT_VERBOSE = os_util.parse_boolean_environment_var("ENABLE_CCXT_VERBOSE", "False")
ENABLE_CCXT_RATE_LIMIT = os_util.parse_boolean_environment_var("ENABLE_CCXT_RATE_LIMIT", "True")
ENABLE_CCXT_REQUESTS_COUNTER = os_util.parse_boolean_environment_var("ENABLE_CCXT_REQUESTS_COUNTER", "False")
FETCH_MIN_EXCHANGE_MARKETS = os_util.parse_boolean_environment_var("FETCH_MIN_EXCHANGE_MARKETS", "False")
CCXT_DEFAULT_CACHE_LIMIT = int(os.getenv("CCXT_DEFAULT_CACHE_LIMIT", "1000"))  # 1000: default ccxt value
CCXT_TRADES_CACHE_LIMIT = int(os.getenv("CCXT_TRADES_CACHE_LIMIT", str(CCXT_DEFAULT_CACHE_LIMIT)))
CCXT_ORDERS_CACHE_LIMIT = int(os.getenv("CCXT_ORDERS_CACHE_LIMIT", str(CCXT_DEFAULT_CACHE_LIMIT)))
CCXT_OHLCV_CACHE_LIMIT = int(os.getenv("CCXT_OHLCV_CACHE_LIMIT", str(CCXT_DEFAULT_CACHE_LIMIT)))
CCXT_WATCH_ORDER_BOOK_LIMIT = int(os.getenv("CCXT_WATCH_ORDER_BOOK_LIMIT", str(CCXT_DEFAULT_CACHE_LIMIT)))
CCXT_TIMEOUT_ON_EXIT_MS = 100
THROTTLED_WS_UPDATES = float(os.getenv("THROTTLED_WS_UPDATES", "0.1"))  # avoid spamming CPU
MAX_CANDLES_IN_RAM = int(os.getenv("MAX_CANDLES_IN_RAM", "3000"))    # max candles per CandlesManager
STORAGE_ORIGIN_VALUE = "origin_value"
DISPLAY_TIME_FRAME = commons_enums.TimeFrames.ONE_HOUR
DEFAULT_SUBACCOUNT_ID = "default_subaccount_id"
DEFAULT_ACCOUNT_ID = "default_account_id"
ALLOW_FUNDS_TRANSFER = os_util.parse_boolean_environment_var("ALLOW_FUNDS_TRANSFER", "False")
SIMULATED_DEPOSIT_ADDRESS = "0x123_simulated_deposit_address"
SIMULATED_BLOCKCHAIN_NETWORK = "SIMULATED"

# Storage
ENABLE_LIVE_CANDLES_STORAGE = os_util.parse_boolean_environment_var("ENABLE_LIVE_CANDLES_STORAGE", "False")
ENABLE_HISTORICAL_ORDERS_UPDATES_STORAGE = os_util.parse_boolean_environment_var("ENABLE_HISTORICAL_ORDERS_UPDATES_STORAGE", "False")
ENABLE_SIMULATED_ORDERS_STORAGE = os_util.parse_boolean_environment_var("ENABLE_SIMULATED_ORDERS_STORAGE", "False")
AUTH_UPDATE_DEBOUNCE_DURATION = float(os.getenv("AUTH_UPDATE_DEBOUNCE_DURATION", "10"))

# Decimal default values (decimals are immutable, can be stored as constant)
ZERO = decimal.Decimal(0)
ONE = decimal.Decimal(1)
ONE_HUNDRED = decimal.Decimal(100)
NaN = decimal.Decimal("nan")
NINETY_FIVE_PERCENT = decimal.Decimal("0.95")

# exchanges where test_get_historical_symbol_prices is successful can be listed here
FULL_CANDLE_HISTORY_EXCHANGES = [
    "ascendex",
    "binance",
    "bitfinex",
    "bitstamp",
    "bybit",
    "bingx",
    "hollaex",
    "htx",
    "kucoin",
    "okcoin",
    "okx",
    "myokx",
    "okxus",
    "mexc",
    "coinbase",
    "binanceus",
    "bitmart",
    "bitmex",
    "lbank",
]

DEFAULT_FUTURE_EXCHANGES = ["binanceusdm", "bybit"]
TESTED_EXCHANGES = [
    "binance",
    "kucoin",
    "okx",
] + sorted([
    "binanceus",
    "coinbase",
    "cryptocom",
    "htx",
    "hyperliquid",
    "bitget",
    "gateio",
    "ascendex",
    "bybit",
    "phemex",
    "hollaex",
    "mexc",
    "bingx",
    "coinex",
    "bitmart",
    "lbank",
])
DEFAULT_FUTURE_EXCHANGES = sorted(["bybit"])
SIMULATOR_TESTED_EXCHANGES = sorted(["bitfinex", "bithumb", "bitstamp", "bitmex",
                              "hitbtc", "kraken", "poloniex", "bitso", "ndax", "upbit",
                              "myokx", "okxus",
                              "wavesexchange",])


# exchanges
CONFIG_DEFAULT_FEES = 0.001
CONFIG_DEFAULT_SIMULATOR_FEES = 0
FEES_SAFETY_MARGIN = decimal.Decimal("1.25")    # allow 25% error margin when simulating fees

DEFAULT_SYMBOL_LEVERAGE = ONE
DEFAULT_SYMBOL_MAX_LEVERAGE = ONE_HUNDRED
DEFAULT_SYMBOL_MARGIN_TYPE = enums.MarginType.ISOLATED
DEFAULT_SYMBOL_FUTURE_CONTRACT_TYPE = enums.FutureContractType.LINEAR_PERPETUAL
DEFAULT_SYMBOL_OPTION_CONTRACT_TYPE = enums.OptionContractType.LINEAR_EXPIRABLE
DEFAULT_SYMBOL_CONTRACT_SIZE = ONE
DEFAULT_SYMBOL_POSITION_MODE = enums.PositionMode.ONE_WAY
DEFAULT_SYMBOL_FUNDING_RATE = decimal.Decimal("0.00005")
DEFAULT_SYMBOL_MAINTENANCE_MARGIN_RATE = decimal.Decimal("0.01")
RETRIABLE_EXCHANGE_ERRORS_DESC: set[str] = set(os.getenv(
    "RETRIABLE_EXCHANGE_ERRORS_DESC", (
        'Internal Server Error:Bad gateway:socket hang up'
        ':read ECONNRESET:read ETIMEDOUT'
    )
).split(":"))

# exchange proxy
RETRIABLE_EXCHANGE_PROXY_ERRORS_DESC: set[str] = set(os.getenv(
    "RETRIABLE_EXCHANGE_PROXY_ERRORS_DESC", "message='Service Unavailable'"
).split(":"))

# used to force margin type update before positions init (if necessary)
FORCED_MARGIN_TYPE = enums.MarginType(os.getenv("FORCED_MARGIN_TYPE", enums.MarginType.ISOLATED.value))

# API
API_LOGGER_TAG = "TradingApi"

# Channels
# Exchange public data
TICKER_CHANNEL = "Ticker"
MINI_TICKER_CHANNEL = "MiniTicker"
RECENT_TRADES_CHANNEL = "RecentTrade"
LIQUIDATIONS_CHANNEL = "Liquidations"
ORDER_BOOK_CHANNEL = "OrderBook"
ORDER_BOOK_TICKER_CHANNEL = "OrderBookTicker"
KLINE_CHANNEL = "Kline"
MARKETS_CHANNEL = "Markets"
OHLCV_CHANNEL = "OHLCV"
MARK_PRICE_CHANNEL = "MarkPrice"
FUNDING_CHANNEL = "Funding"

# Exchange personal data
TRADES_CHANNEL = "Trades"
ORDERS_CHANNEL = "Orders"
BALANCE_CHANNEL = "Balance"
BALANCE_PROFITABILITY_CHANNEL = "BalanceProfitability"
POSITIONS_CHANNEL = "Positions"
INDIVIDUAL_ORDER_SYNC_TIMEOUT = 1 * commons_constants.MINUTE_TO_SECONDS
MAX_TRADES_COUNT = int(os.getenv("MAX_TRADES_COUNT", "10000"))    # larger values can use a large part of ram

# History
DEFAULT_SAVED_HISTORICAL_TIMEFRAMES = [commons_enums.TimeFrames.ONE_DAY]
HISTORICAL_CANDLES_FETCH_DEFAULT_TIMEOUT = 30

# 946742400 is 01/01/2000, if trade time is lower, there is an issue.
MINIMUM_VAL_TRADE_TIME = 946688400

# Internal
MODE_CHANNEL = "Mode"

WEBSOCKET_FEEDS_TO_TRADING_CHANNELS = {
    TICKER_CHANNEL: [enums.WebsocketFeeds.TICKER],
    MINI_TICKER_CHANNEL: [enums.WebsocketFeeds.MINI_TICKER],
    RECENT_TRADES_CHANNEL: [enums.WebsocketFeeds.TRADES],
    LIQUIDATIONS_CHANNEL: [enums.WebsocketFeeds.LIQUIDATIONS],
    ORDER_BOOK_CHANNEL: [enums.WebsocketFeeds.L2_BOOK, enums.WebsocketFeeds.L3_BOOK],
    ORDER_BOOK_TICKER_CHANNEL: [enums.WebsocketFeeds.BOOK_TICKER],
    KLINE_CHANNEL: [enums.WebsocketFeeds.KLINE],
    MARKETS_CHANNEL: [enums.WebsocketFeeds.MARKETS],
    OHLCV_CHANNEL: [enums.WebsocketFeeds.CANDLE],
    TRADES_CHANNEL: [enums.WebsocketFeeds.TRADE],
    ORDERS_CHANNEL: [enums.WebsocketFeeds.ORDERS],
    MARK_PRICE_CHANNEL: [enums.WebsocketFeeds.MARK_PRICE],
    BALANCE_CHANNEL: [enums.WebsocketFeeds.PORTFOLIO],
    POSITIONS_CHANNEL: [enums.WebsocketFeeds.POSITION],
    FUNDING_CHANNEL: [enums.WebsocketFeeds.FUNDING]
}

ALWAYS_STARTED_REST_PRODUCER_CHANNELS = [
    TICKER_CHANNEL, # use to force mark price update when necessary: should always be reachable
]

FILL_ORDER_STATUS_SCOPE = [enums.OrderStatus.CLOSED,
                           enums.OrderStatus.FILLED,
                           enums.OrderStatus.PARTIALLY_FILLED]
CANCEL_ORDER_STATUS_SCOPE = [enums.OrderStatus.PENDING_CANCEL,
                             enums.OrderStatus.CANCELED,
                             enums.OrderStatus.EXPIRED,
                             enums.OrderStatus.REJECTED]

DEFAULT_INITIALIZATION_EVENT_TOPICS = [
    commons_enums.InitializationEventExchangeTopics.BALANCE,
    commons_enums.InitializationEventExchangeTopics.PROFITABILITY,
    commons_enums.InitializationEventExchangeTopics.ORDERS,
    commons_enums.InitializationEventExchangeTopics.TRADES,
    commons_enums.InitializationEventExchangeTopics.CANDLES,
    commons_enums.InitializationEventExchangeTopics.PRICE,
    commons_enums.InitializationEventExchangeTopics.MARKETS,
]

DEFAULT_FUTURES_INITIALIZATION_EVENT_TOPICS = DEFAULT_INITIALIZATION_EVENT_TOPICS + [
    commons_enums.InitializationEventExchangeTopics.POSITIONS,
    commons_enums.InitializationEventExchangeTopics.CONTRACTS,
    commons_enums.InitializationEventExchangeTopics.FUNDING,
]
