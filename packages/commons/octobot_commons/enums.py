# pylint: disable=C0103
#  Drakkar-Software OctoBot-Commons
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
import enum


class TimeFrames(enum.Enum):
    """
    OctoBot supported time frames values
    """

    ONE_MINUTE = "1m"
    THREE_MINUTES = "3m"
    FIVE_MINUTES = "5m"
    FIFTEEN_MINUTES = "15m"
    THIRTY_MINUTES = "30m"
    ONE_HOUR = "1h"
    TWO_HOURS = "2h"
    THREE_HOURS = "3h"
    FOUR_HOURS = "4h"
    SIX_HOURS = "6h"
    HEIGHT_HOURS = "8h"
    TWELVE_HOURS = "12h"
    ONE_DAY = "1d"
    THREE_DAYS = "3d"
    ONE_WEEK = "1w"
    ONE_MONTH = "1M"
    ONE_YEAR = "1y"


TimeFramesMinutes = {
    TimeFrames.ONE_MINUTE: 1,
    TimeFrames.THREE_MINUTES: 3,
    TimeFrames.FIVE_MINUTES: 5,
    TimeFrames.FIFTEEN_MINUTES: 15,
    TimeFrames.THIRTY_MINUTES: 30,
    TimeFrames.ONE_HOUR: 60,
    TimeFrames.TWO_HOURS: 120,
    TimeFrames.THREE_HOURS: 180,
    TimeFrames.FOUR_HOURS: 240,
    TimeFrames.SIX_HOURS: 360,
    TimeFrames.HEIGHT_HOURS: 480,
    TimeFrames.TWELVE_HOURS: 720,
    TimeFrames.ONE_DAY: 1440,
    TimeFrames.THREE_DAYS: 4320,
    TimeFrames.ONE_WEEK: 10080,
    TimeFrames.ONE_MONTH: 43200,
    TimeFrames.ONE_YEAR: 524160,
}


class PriceIndexes(enum.Enum):
    """
    Default candle price index correspondence
    """

    IND_PRICE_TIME = 0
    IND_PRICE_OPEN = 1
    IND_PRICE_HIGH = 2
    IND_PRICE_LOW = 3
    IND_PRICE_CLOSE = 4
    IND_PRICE_VOL = 5


class PriceStrings(enum.Enum):
    """
    Default candle price str
    """

    STR_PRICE_TIME = "time"
    STR_PRICE_CLOSE = "close"
    STR_PRICE_OPEN = "open"
    STR_PRICE_HIGH = "high"
    STR_PRICE_LOW = "low"
    STR_PRICE_VOL = "vol"


class OptionTypes(enum.Enum):
    """
    Default option type
    """

    PUT = "P"
    CALL = "C"


class PlatformsName(enum.Enum):
    """
    OctoBot supported platforms name
    """

    WINDOWS = "nt"
    LINUX = "posix"
    MAC = "mac"


class OctoBotTypes(enum.Enum):
    """
    OctoBot running types
    """

    BINARY = "binary"
    PYTHON = "python"
    DOCKER = "docker"


class MarkdownFormat(enum.Enum):
    """
    Markdown formating
    """

    ITALIC = "_"
    BOLD = "*"
    CODE = "`"
    IGNORE = 1
    NONE = 0


class OctoBotChannelSubjects(enum.Enum):
    """
    OctoBot Channel subjects
    """

    NOTIFICATION = "notification"
    CREATION = "creation"
    UPDATE = "update"
    DELETION = "deletion"
    ERROR = "error"


class UserCommands(enum.Enum):
    """
    Allowed user commands
    """

    MANUAL_TRIGGER = "manual_trigger"
    OPTIMIZE_INITIAL_PORTFOLIO = "optimize_initial_portfolio"
    TRIGGER_HEALTH_CHECK = "trigger_health_check"
    RELOAD_CONFIG = "reload_config"
    RELOAD_SCRIPT = "reload_script"
    CLEAR_PLOTTING_CACHE = "clear_plotting_cache"
    CLEAR_SIMULATED_ORDERS_CACHE = "clear_simulated_orders_cache"
    CLEAR_SIMULATED_TRADES_CACHE = "clear_simulated_trades_cache"
    CLEAR_SIMULATED_TRANSACTIONS_CACHE = "clear_simulated_transactions_cache"


class MultiprocessingLocks(enum.Enum):
    """
    Keys to multiprocessing lock
    """

    DBLock = "db_lock"


class CacheDatabaseTables(enum.Enum):
    """
    Tables in cache databases
    """

    CACHE = "cache"
    METADATA = "metadata"


class CacheDatabaseColumns(enum.Enum):
    """
    Keys/columns in cache databases tables
    """

    TIMESTAMP = "t"
    VALUE = "v"
    TYPE = "ty"
    TRIGGERED_AFTER_CANDLES_CLOSE = "triggered_after_candles_close"


class PlotAttributes(enum.Enum):
    KIND = "kind"
    X = "x"
    Y = "y"
    Z = "z"
    OPEN = "open"
    HIGH = "high"
    LOW = "low"
    CLOSE = "close"
    VOLUME = "volume"
    TITLE = "title"
    TEXT = "text"
    SUB_ELEMENTS = "sub_elements"
    ELEMENTS = "elements"
    NAME = "name"
    DATA = "data"
    X_TYPE = "x_type"
    Y_TYPE = "y_type"
    MODE = "mode"
    LINE_SHAPE = "line_shape"
    OWN_XAXIS = "own_xaxis"
    OWN_YAXIS = "own_yaxis"
    SIDE = "side"
    VALUE = "value"
    CONFIG = "config"
    SCHEMA = "schema"
    TENTACLE = "tentacle"
    TENTACLE_TYPE = "tentacle_type"
    COLUMNS = "columns"
    ROWS = "rows"
    SEARCHES = "searches"
    IS_HIDDEN = "is_hidden"
    TYPE = "type"
    COLOR = "color"
    HTML = "html"
    SIZE = "size"
    SHAPE = "shape"
    SYMBOL = "symbol"


class BacktestingMetadata(enum.Enum):
    ID = "id"
    GAINS = "gains"
    PERCENT_GAINS = "% gains"
    MARKETS_PROFITABILITY = "markets profitability"
    END_PORTFOLIO = "end portfolio"
    START_PORTFOLIO = "start portfolio"
    WIN_RATE = "% win rate"
    DRAW_DOWN = "% draw down"
    COEFFICIENT_OF_DETERMINATION_MAX_BALANCE = "R² max balance"
    COEFFICIENT_OF_DETERMINATION_END_BALANCE = "R² end balance"
    SYMBOLS = "symbols"
    TIME_FRAMES = "time frames"
    START_TIME = "start time"
    END_TIME = "end time"
    DURATION = "duration"
    ENTRIES = "entries"
    WINS = "wins"
    LOSES = "loses"
    TRADES = "trades"
    TIMESTAMP = "timestamp"
    NAME = "name"
    LEVERAGE = "leverage"
    OPTIMIZATION_CAMPAIGN = "optimization campaign"
    USER_INPUTS = "user inputs"
    BACKTESTING_FILES = "backtesting files"
    CHILDREN = "children"
    OPTIMIZER_ID = "optimizer id"
    EXCHANGE = "exchange"


class DBRows(enum.Enum):
    ID = "id"
    REFERENCE_MARKET = "ref_market"
    EXCHANGE = "exchange"
    EXCHANGES = "exchanges"
    FUTURE_CONTRACTS = "future_contracts"
    PAIR = "pair"
    TIME_FRAME = "time_frame"
    VALUE = "value"
    START_TIME = "start_time"
    END_TIME = "end_time"
    TRADING_TYPE = "trading_type"
    TRADING_MODE = "trading_mode"
    SYMBOL = "symbol"
    SYMBOLS = "symbols"
    FEES_AMOUNT = "fees_amount"
    FEES_CURRENCY = "fees_currency"


class PlotCharts(enum.Enum):
    MAIN_CHART = "main-chart"
    SUB_CHART = "sub-chart"


class DisplayedElementTypes(enum.Enum):
    CHART = "chart"
    INPUT = "input"
    TABLE = "table"
    VALUE = "value"
    DICTIONARY = "dictionary"


class DBTables(enum.Enum):
    METADATA = "metadata"
    INPUTS = "inputs"
    PORTFOLIO = "portfolio"
    ORDERS = "all_orders"
    HISTORICAL_ORDERS_UPDATES = "order_updates"
    TRADES = "all_trades"
    TRANSACTIONS = "all_transactions"
    CANDLES = "candles"
    CANDLES_SOURCE = "candles_source"
    CACHE_SOURCE = "cache_source"


class ActivationTopics(enum.Enum):
    """
    Events that can trigger actions
    """

    FULL_CANDLES = "once per bar close"
    IN_CONSTRUCTION_CANDLES = "once per second (Live Price)"
    RECENT_TRADES = "recent trades"
    EVALUATION_CYCLE = "after evaluators"


class TriggerSource(enum.Enum):
    INITIALIZATION = "initialization"
    EVALUATION_MATRIX = "evaluation_matrix"
    EVALUATOR_REFRESH = "evaluator_refresh"
    OHLCV = "ohlcv"
    KLINE = "kline"
    ORDER = "order"
    TRADE = "trade"
    PRICE = "price"
    BALANCE = "balance"
    POSITION = "position"
    CONFIGURATION_UPDATE = "configuration_update"
    MANUAL = "manual"
    UNDEFINED = "undefined"


class DataBaseOrderBy(enum.Enum):
    """
    Database orders
    """

    ASC = "ASC"
    DESC = "DESC"


class DataBaseOperations(enum.Enum):
    """
    Database operators
    """

    SUP = ">"
    INF = "<"
    EQUALS = "="
    INF_EQUALS = f"{INF}{EQUALS}"
    SUP_EQUALS = f"{SUP}{EQUALS}"


class RunDatabases(enum.Enum):
    """
    Database identifiers
    """

    HISTORY = "history"
    LIVE = "live"
    BACKTESTING = "backtesting"
    OPTIMIZER = "optimizer"
    OPTIMIZER_RUNS_SCHEDULE_DB = "runs_schedule"
    RUN_DATA_DB = "run_data"
    PORTFOLIO_VALUE_DB = "portfolio_value"
    HISTORICAL_PORTFOLIO_VALUE = "historical_portfolio_value"
    ORDERS_DB = "orders"
    TRADES_DB = "trades"
    TRANSACTIONS_DB = "transactions"
    EXCHANGES = "exchanges"
    METADATA = "metadata"


class LogicalOperators(enum.Enum):
    """
    Logical operators
    """

    LOWER_THAN = "lower_than"
    HIGHER_THAN = "higher_than"
    LOWER_OR_EQUAL_TO = "lower_or_equal_to"
    HIGHER_OR_EQUAL_TO = "higher_or_equal_to"
    EQUAL_TO = "equal_to"
    DIFFERENT_FROM = "different_from"


class CommunityFeedAttrs(enum.Enum):
    ID = "u"
    STREAM_ID = "i"
    VALUE = "s"
    VERSION = "v"
    TIMESTAMP = "d"
    CHANNEL_TYPE = "t"


class CommunityChannelTypes(enum.Enum):
    CONFIGURATION = "cfg"
    SIGNAL = "t"
    TRADINGVIEW = "tv"
    ALERT = "alert"


class SignalBundlesAttrs(enum.Enum):
    IDENTIFIER = "identifier"
    SIGNALS = "signals"
    VERSION = "version"


class SignalsAttrs(enum.Enum):
    TOPIC = "topic"
    CONTENT = "content"
    DEPENDENCIES = "dependencies"


class SignalDependenciesAttrs(enum.Enum):
    DEPENDENCY = "dependency"


class InitializationEventExchangeTopics(enum.Enum):
    POSITIONS = "positions"
    BALANCE = "balance"
    PROFITABILITY = "profitability"
    ORDERS = "orders"
    TRADES = "trades"
    CONTRACTS = "contracts"
    CANDLES = "candles"
    PRICE = "price"
    ORDER_BOOK = "order_book"
    FUNDING = "funding"
    MARKETS = "markets"


class UserInputTentacleTypes(enum.Enum):
    TRADING_MODE = "trading_mode"
    EVALUATOR = "evaluator"
    EXCHANGE = "exchange"
    BLOCKCHAIN_WALLET = "blockchain_wallet"
    WEB_PLUGIN = "web_plugin"
    AUTOMATION = "automation"
    UNDEFINED = "undefined"


class UserInputTypes(enum.Enum):
    INT = "int"
    FLOAT = "float"
    BOOLEAN = "boolean"
    OPTIONS = "options"
    MULTIPLE_OPTIONS = "multiple-options"
    TEXT = "text"
    OBJECT = "object"
    OBJECT_ARRAY = "object_array"
    STRING_ARRAY = "string_array"


class UserInputEditorOptionsTypes(enum.Enum):
    # source for the available options:
    # https://github.com/json-editor/json-editor#editor-options

    # If set to true, the editor will start collapsed (works for objects and arrays)
    COLLAPSED = "collapsed"
    # If set to true, the "add row" button will be hidden (works for arrays)
    DISABLE_ARRAY_ADD = "disable_array_add"
    # If set to true, all of the "delete" buttons will be hidden (works for arrays)
    DISABLE_ARRAY_DELETE = "disable_array_delete"
    # If set to true, just the "delete all rows"
    #   button will be hidden (works for arrays)
    DISABLE_ARRAY_DELETE_ALL_ROWS = "disable_array_delete_all_rows"
    # If set to true, just the "delete last row"
    #   buttons will be hidden (works for arrays)
    DISABLE_ARRAY_DELETE_LAST_ROW = "disable_array_delete_last_row"
    # If set to true, the "move up/down" buttons will be hidden (works for arrays)
    DISABLE_ARRAY_REORDER = "disable_array_reorder"
    # If set to true, the collapse button will be hidden (works for objects and arrays)
    DISABLE_COLLAPSE = "disable_collapse"
    # If set to true, the Edit JSON button will be hidden (works for objects)
    DISABLE_EDIT_JSON = "disable_edit_json"
    # If set to true, the Edit Properties button will be hidden (works for objects)
    DISABLE_PROPERTIES = "disable_properties"
    # If set to true, array controls (add, delete etc) will be
    #   displayed at top of list (works for arrays)
    ARRAY_CONTROLS_TOP = "array_controls_top"
    # See Enum options (https://github.com/json-editor/json-editor#enum-options)
    ENUM = "enum"
    # An array of display values to use for select box options in the same
    #   order as defined with the enum keyword. Works with schema using enum values.
    ENUM_TITLES = "enum_titles"
    # If set to true, the input will auto expand/contract to fit the content.
    #   Works best with textareas.
    EXPAND_HEIGHT = "expand_height"
    # Explicitly set the number of grid columns (1-12) for the editor
    #   if it's within an object using a grid layout.
    GRID_COLUMNS = "grid_columns"
    # If set to true, the editor will not appear in the UI (works for all types)
    HIDDEN = "hidden"
    # Explicitly set the height of the input element. Should be a valid CSS
    #    width string (e.g. "100px"). Works best with textareas.
    INPUT_HEIGHT = "input_height"
    # Explicitly set the width of the input element. Should be a valid CSS
    #    width string (e.g. "100px"). Works for string, number, and integer data types.
    INPUT_WIDTH = "input_width"
    # If set to true for an object, empty object properties
    #    (i.e. those with falsy values) will not be returned by getValue().
    REMOVE_EMPTY_PROPERTIES = "remove_empty_properties"


class UserInputOtherSchemaValuesTypes(enum.Enum):
    DESCRIPTION = "description"
    DEPENDENCIES = "dependencies"


class ProfileComplexity(enum.Enum):
    EASY = 1
    MEDIUM = 2
    DIFFICULT = 3


class ProfileRisk(enum.Enum):
    LOW = 1
    MODERATE = 2
    HIGH = 3


class ProfileType(enum.Enum):
    LIVE = "live"
    BACKTESTING = "backtesting"


class SignalHistoryTypes(enum.Enum):
    GPT = "gpt"


class StopReason(enum.Enum):
    MISSING_API_KEY_TRADING_RIGHTS = "missing_api_key_trading_rights"
    INVALID_EXCHANGE_CREDENTIALS = "invalid_exchange_credentials"
    STOP_CONDITION_TRIGGERED = "stop_condition_triggered"
    MISSING_MINIMAL_FUNDS = "missing_minimal_funds"
    INVALID_CONFIG = "invalid_config"
    UNKNOWN = "unknown"
