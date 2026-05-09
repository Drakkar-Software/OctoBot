// Drakkar-Software OctoBot-Trading
// LGPL-3.0
//
// Direct TS port of octobot_trading/enums.py — only enums consumed by the in-scope
// REST + WebSocket + adapters surface are reproduced. Values match the Python source
// byte-for-byte so that JSON dumps from the wrapper line up with the Python wrapper.

export enum TradeOrderSide {
  BUY = "buy",
  SELL = "sell",
}

export enum PositionSide {
  LONG = "long",
  SHORT = "short",
  BOTH = "both",
  UNKNOWN = "unknown",
}

export enum TradeOrderType {
  LIMIT = "limit",
  MARKET = "market",
  STOP_LOSS = "stop_loss",
  STOP_LOSS_LIMIT = "stop_loss_limit",
  CONDITIONAL_MARKET = "stop_market",
  CONDITIONAL_LIMIT = "stop_limit",
  TAKE_PROFIT = "take_profit",
  TAKE_PROFIT_LIMIT = "take_profit_limit",
  TRAILING_STOP = "trailing_stop",
  TRAILING_STOP_LIMIT = "trailing_stop_limit",
  LIMIT_MAKER = "limit_maker",
  UNSUPPORTED = "unsupported",
  UNKNOWN = "unknown",
}

export enum TraderOrderType {
  BUY_MARKET = "buy_market",
  BUY_LIMIT = "buy_limit",
  STOP_LOSS = "stop_loss",
  STOP_LOSS_LIMIT = "stop_limit",
  SELL_MARKET = "sell_market",
  SELL_LIMIT = "sell_limit",
  TRAILING_STOP = "trailing_stop",
  TRAILING_STOP_LIMIT = "trailing_stop_limit",
  TAKE_PROFIT = "take_profit",
  TAKE_PROFIT_LIMIT = "take_profit_limit",
  UNSUPPORTED = "unsupported",
  UNKNOWN = "unknown",
}

export enum OrderStatus {
  PENDING_CREATION = "pending_creation",
  OPEN = "open",
  PARTIALLY_FILLED = "partially_filled",
  FILLED = "filled",
  CANCELED = "canceled",
  PENDING_CANCEL = "canceling",
  CLOSED = "closed",
  EXPIRED = "expired",
  REJECTED = "rejected",
  UNKNOWN = "unknown",
}

export enum States {
  PENDING_CREATION = "pending_creation",
  OPENING = "opening",
  OPEN = "open",
  CLOSING = "closing",
  CLOSED = "closed",
  REFRESHING = "refreshing",
  UNKNOWN = "unknown",
}

export enum AccountTypes {
  CASH = "cash",
  MARGIN = "margin",
  FUTURE = "future",
  SWAP = "swap",
  OPTION = "option",
}

export enum ExchangeTypes {
  SPOT = "spot",
  FUTURE = "future",
  MARGIN = "margin",
  OPTION = "option",
  UNKNOWN = "unknown",
}

export enum MarginType {
  CROSS = "cross",
  ISOLATED = "isolated",
}

export enum PositionMode {
  HEDGE = "hedge_mode",
  ONE_WAY = "one_way_mode",
}

export enum ContractTradingTypes {
  LINEAR = "linear",
  INVERSE = "inverse",
}

export enum FutureContractType {
  INVERSE_PERPETUAL = "inverse_perpetual",
  LINEAR_PERPETUAL = "linear_perpetual",
  INVERSE_EXPIRABLE = "inverse_expirable",
  LINEAR_EXPIRABLE = "linear_expirable",
}

export enum OptionContractType {
  INVERSE_EXPIRABLE = "inverse_expirable",
  LINEAR_EXPIRABLE = "linear_expirable",
}

export enum TakeProfitStopLossMode {
  FULL = "Full",
  PARTIAL = "Partial",
}

export enum WebsocketFeeds {
  L1_BOOK = "l1_book",
  L2_BOOK = "l2_book",
  L3_BOOK = "l3_book",
  BOOK_TICKER = "book_ticker",
  BOOK_DELTA = "book_delta",
  TRADES = "trades",
  LIQUIDATIONS = "liquidations",
  MINI_TICKER = "mini_ticker",
  TICKER = "ticker",
  CANDLE = "candle",
  KLINE = "kline",
  FUNDING = "funding",
  MARK_PRICE = "mark_price",
  LAST_PRICE = "last_price",
  ORDERS = "orders",
  MARKETS = "markets",
  LEDGER = "ledger",
  CREATE_ORDER = "create_order",
  CANCEL_ORDER = "cancel_order",
  FUTURES_INDEX = "futures_index",
  OPEN_INTEREST = "open_interest",
  PORTFOLIO = "portfolio",
  POSITION = "position",
  TRADE = "trade",
  TRANSACTIONS = "transactions",
  VOLUME = "volume",
  UNSUPPORTED = "unsupported",
}

export enum MarkPriceSources {
  EXCHANGE_MARK_PRICE = "exchange_mark_price",
  RECENT_TRADE_AVERAGE = "recent_trade_average",
  TICKER_CLOSE_PRICE = "ticker_close_price",
  CANDLE_CLOSE_PRICE = "candle_close_price",
}

export enum FeesCurrencySide {
  CURRENCY = "currency",
  MARKET = "market",
  UNDEFINED = "undefined",
}

export enum ExchangeFeeSides {
  GET = "get",
  GIVE = "give",
  QUOTE = "quote",
}

// CCXT-facing column constants. Keeping the original Python "Columns" enum naming so
// adapter code translated literally still type-checks.

export enum ExchangeConstantsTickersColumns {
  SYMBOL = "symbol",
  TIMESTAMP = "timestamp",
  DATETIME = "datetime",
  HIGH = "high",
  LOW = "low",
  BID = "bid",
  BID_VOLUME = "bidVolume",
  ASK = "ask",
  ASK_VOLUME = "askVolume",
  VWAP = "vwap",
  OPEN = "open",
  CLOSE = "close",
  LAST = "last",
  PREVIOUS_CLOSE = "previousClose",
  CHANGE = "change",
  PERCENTAGE = "percentage",
  AVERAGE = "average",
  BASE_VOLUME = "baseVolume",
  QUOTE_VOLUME = "quoteVolume",
  INFO = "info",
}

export enum ExchangeConstantsMarketStatusColumns {
  SYMBOL = "symbol",
  ID = "id",
  CURRENCY = "base",
  MARKET = "quote",
  ACTIVE = "active",
  PRECISION = "precision",
  PRECISION_PRICE = "price",
  PRECISION_AMOUNT = "amount",
  PRECISION_COST = "cost",
  LIMITS = "limits",
  LIMITS_AMOUNT = "amount",
  LIMITS_AMOUNT_MIN = "min",
  LIMITS_AMOUNT_MAX = "max",
  LIMITS_PRICE = "price",
  LIMITS_PRICE_MIN = "min",
  LIMITS_PRICE_MAX = "max",
  LIMITS_COST = "cost",
  LIMITS_COST_MIN = "min",
  LIMITS_COST_MAX = "max",
  TYPE = "type",
  EXPIRY = "expiry",
  INFO = "info",
}

export enum ExchangeConstantsMarketStatusInfoColumns {
  FILTERS = "filters",
  FILTER_TYPE = "filterType",
  PRICE_FILTER = "PRICE_FILTER",
  LOT_SIZE = "LOT_SIZE",
  MIN_PRICE = "minPrice",
  MAX_PRICE = "maxPrice",
  TICK_SIZE = "tickSize",
  MIN_QTY = "minQty",
  MAX_QTY = "maxQty",
}

export enum ExchangeConstantsOrderColumns {
  INFO = "info",
  ID = "id",
  EXCHANGE_ID = "exchange_id",
  EXCHANGE_TRADE_ID = "exchange_trade_id",
  ORDER_ID = "order_id",
  TIMESTAMP = "timestamp",
  DATETIME = "datetime",
  LAST_TRADE_TIMESTAMP = "lastTradeTimestamp",
  SYMBOL = "symbol",
  MARKET = "market",
  QUANTITY_CURRENCY = "quantity_currency",
  TYPE = "type",
  SIDE = "side",
  PRICE = "price",
  AMOUNT = "amount",
  COST = "cost",
  AVERAGE = "average",
  FILLED = "filled",
  REMAINING = "remaining",
  STATUS = "status",
  FEE = "fee",
  TRADES = "trades",
  MAKER = "maker",
  TAKER = "taker",
  ORDER = "order",
  TAKER_OR_MAKER = "takerOrMaker",
  REDUCE_ONLY = "reduceOnly",
  STOP_PRICE = "stopPrice",
  STOP_LOSS_PRICE = "stopLossPrice",
  TAKE_PROFIT_PRICE = "takeProfitPrice",
  TRIGGER_ABOVE = "triggerAbove",
  TAG = "tag",
  SELF_MANAGED = "self-managed",
  ENTRIES = "entries",
  VOLUME = "volume",
  BROKER_APPLIED = "broker_applied",
  IS_ACTIVE = "is_active",
  EXCHANGE_SPECIFIC_ORDER_VALUES = "esov",
}

export enum ExchangeConstantsOrderBookInfoColumns {
  BIDS = "bids",
  ASKS = "asks",
  TIMESTAMP = "timestamp",
  DATETIME = "datetime",
  NONCE = "nonce",
  ORDER_ID = "order_id",
  PRICE = "price",
  SIZE = "size",
  SIDE = "side",
}

export enum ExchangeConstantsMarkPriceColumns {
  SYMBOL = "symbol",
  TIMESTAMP = "timestamp",
  MARK_PRICE = "mark_price",
}

export enum ExchangeConstantsFundingColumns {
  SYMBOL = "symbol",
  LAST_FUNDING_TIME = "last_funding_time",
  FUNDING_RATE = "funding_rate",
  NEXT_FUNDING_TIME = "next_funding_time",
  PREDICTED_FUNDING_RATE = "predicted_funding_rate",
}

export enum ExchangeConstantsPositionColumns {
  ID = "id",
  LOCAL_ID = "local_id",
  TIMESTAMP = "timestamp",
  SYMBOL = "symbol",
  ENTRY_PRICE = "entry_price",
  MARK_PRICE = "mark_price",
  LIQUIDATION_PRICE = "liquidation_price",
  BANKRUPTCY_PRICE = "bankruptcy_price",
  UNREALIZED_PNL = "unrealised_pnl",
  REALISED_PNL = "realised_pnl",
  CLOSING_FEE = "closing_fee",
  QUANTITY = "quantity",
  SIZE = "size",
  NOTIONAL = "notional",
  INITIAL_MARGIN = "initial_margin",
  AUTO_DEPOSIT_MARGIN = "auto_deposit_margin",
  COLLATERAL = "collateral",
  LEVERAGE = "leverage",
  MARGIN_TYPE = "margin_type",
  CONTRACT_TYPE = "contract_type",
  CONTRACT_SIZE = "contract_size",
  POSITION_MODE = "position_mode",
  MAINTENANCE_MARGIN_RATE = "maintenance_margin_rate",
  STATUS = "status",
  SIDE = "side",
}

export enum FeePropertyColumns {
  TYPE = "type",
  CURRENCY = "currency",
  RATE = "rate",
  COST = "cost",
  IS_FROM_EXCHANGE = "is_from_exchange",
  EXCHANGE_ORIGINAL_COST = "exchange_original_cost",
}

export enum RestExchangePairsRefreshMaxThresholds {
  FAST = 5,
  MEDIUM = 10,
  SLOW = 20,
}

// CCXT-tentacle-local enums (mirrors connectors/ccxt/enums.py).

export enum CCXTOrderSide {
  BUY = "buy",
  SELL = "sell",
}

export enum CCXTOrderType {
  LIMIT = "limit",
  MARKET = "market",
}
