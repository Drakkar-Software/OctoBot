import enum


class TimeFrames(enum.Enum):
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
    IND_PRICE_TIME = 0
    IND_PRICE_OPEN = 1
    IND_PRICE_HIGH = 2
    IND_PRICE_LOW = 3
    IND_PRICE_CLOSE = 4
    IND_PRICE_VOL = 5


class PriceStrings(enum.Enum):
    STR_PRICE_TIME = "time"
    STR_PRICE_CLOSE = "close"
    STR_PRICE_OPEN = "open"
    STR_PRICE_HIGH = "high"
    STR_PRICE_LOW = "low"
    STR_PRICE_VOL = "vol"


class OptionTypes(enum.Enum):
    PUT = "P"
    CALL = "C"


class PlatformsName(enum.Enum):
    WINDOWS = "nt"
    LINUX = "posix"
    MAC = "mac"


class OctoBotTypes(enum.Enum):
    BINARY = "binary"
    PYTHON = "python"
    DOCKER = "docker"


class MarkdownFormat(enum.Enum):
    ITALIC = "_"
    BOLD = "*"
    CODE = "`"
    IGNORE = 1
    NONE = 0


class OctoBotChannelSubjects(enum.Enum):
    NOTIFICATION = "notification"
    CREATION = "creation"
    UPDATE = "update"
    DELETION = "deletion"
    ERROR = "error"


class UserCommands(enum.Enum):
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
    DBLock = "db_lock"


class CacheDatabaseTables(enum.Enum):
    CACHE = "cache"
    METADATA = "metadata"


class CacheDatabaseColumns(enum.Enum):
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
    COEFFICIENT_OF_DETERMINATION_MAX_BALANCE = "R\u00b2 max balance"
    COEFFICIENT_OF_DETERMINATION_END_BALANCE = "R\u00b2 end balance"
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
    ASC = "ASC"
    DESC = "DESC"


class DataBaseOperations(enum.Enum):
    SUP = ">"
    INF = "<"
    EQUALS = "="
    INF_EQUALS = "<="
    SUP_EQUALS = ">="


class RunDatabases(enum.Enum):
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
    COLLAPSED = "collapsed"
    DISABLE_ARRAY_ADD = "disable_array_add"
    DISABLE_ARRAY_DELETE = "disable_array_delete"
    DISABLE_ARRAY_DELETE_ALL_ROWS = "disable_array_delete_all_rows"
    DISABLE_ARRAY_DELETE_LAST_ROW = "disable_array_delete_last_row"
    DISABLE_ARRAY_REORDER = "disable_array_reorder"
    DISABLE_COLLAPSE = "disable_collapse"
    DISABLE_EDIT_JSON = "disable_edit_json"
    DISABLE_PROPERTIES = "disable_properties"
    ARRAY_CONTROLS_TOP = "array_controls_top"
    ENUM = "enum"
    ENUM_TITLES = "enum_titles"
    EXPAND_HEIGHT = "expand_height"
    GRID_COLUMNS = "grid_columns"
    HIDDEN = "hidden"
    INPUT_HEIGHT = "input_height"
    INPUT_WIDTH = "input_width"
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


# --- Channel name enums ---


class OctoBotChannelsName(enum.Enum):
    OCTOBOT_CHANNEL = "OctoBot"


class OctoBotUserChannelsName(enum.Enum):
    USER_COMMANDS_CHANNEL = "UserCommands"


class OctoBotEvaluatorsChannelsName(enum.Enum):
    MATRIX_CHANNEL = "Matrix"
    EVALUATORS_CHANNEL = "Evaluators"


class OctoBotBacktestingChannelsName(enum.Enum):
    TIME_CHANNEL = "Time"


class OctoBotCommunityChannelsName(enum.Enum):
    REMOTE_TRADING_SIGNALS_CHANNEL = "RemoteTradingSignals"


class OctoBotTradingChannelsName(enum.Enum):
    OHLCV_CHANNEL = "OHLCV"
    TICKER_CHANNEL = "Ticker"
    MINI_TICKER_CHANNEL = "MiniTicker"
    RECENT_TRADES_CHANNEL = "RecentTrade"
    ORDER_BOOK_CHANNEL = "OrderBook"
    ORDER_BOOK_TICKER_CHANNEL = "OrderBookTicker"
    KLINE_CHANNEL = "Kline"
    TRADES_CHANNEL = "Trades"
    LIQUIDATIONS_CHANNEL = "Liquidations"
    ORDERS_CHANNEL = "Orders"
    BALANCE_CHANNEL = "Balance"
    BALANCE_PROFITABILITY_CHANNEL = "BalanceProfitability"
    POSITIONS_CHANNEL = "Positions"
    MODE_CHANNEL = "Mode"
    MARK_PRICE_CHANNEL = "MarkPrice"
    FUNDING_CHANNEL = "Funding"
    MARKETS_CHANNEL = "Markets"
