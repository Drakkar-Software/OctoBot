// Mirrors octobot_trading/enums.py exchange constant enums

export const OrderColumns = {
  INFO: "info",
  ID: "id",
  EXCHANGE_ID: "exchange_id",
  EXCHANGE_TRADE_ID: "exchange_trade_id",
  ORDER_ID: "order_id",
  TIMESTAMP: "timestamp",
  DATETIME: "datetime",
  LAST_TRADE_TIMESTAMP: "lastTradeTimestamp",
  SYMBOL: "symbol",
  MARKET: "market",
  QUANTITY_CURRENCY: "quantity_currency",
  TYPE: "type",
  SIDE: "side",
  PRICE: "price",
  AMOUNT: "amount",
  COST: "cost",
  AVERAGE: "average",
  FILLED: "filled",
  REMAINING: "remaining",
  STATUS: "status",
  FEE: "fee",
  TRADES: "trades",
  MAKER: "maker",
  TAKER: "taker",
  ORDER: "order",
  TAKER_OR_MAKER: "takerOrMaker",
  REDUCE_ONLY: "reduceOnly",
  STOP_PRICE: "stopPrice",
  STOP_LOSS_PRICE: "stopLossPrice",
  TAKE_PROFIT_PRICE: "takeProfitPrice",
  TRIGGER_ABOVE: "triggerAbove",
  TAG: "tag",
  SELF_MANAGED: "self-managed",
  ENTRIES: "entries",
  VOLUME: "volume",
  BROKER_APPLIED: "broker_applied",
  IS_ACTIVE: "is_active",
} as const
export type OrderColumn = (typeof OrderColumns)[keyof typeof OrderColumns]

export const MarketStatusColumns = {
  SYMBOL: "symbol",
  ID: "id",
  CURRENCY: "base",
  MARKET: "quote",
  ACTIVE: "active",
  PRECISION: "precision",
  PRECISION_PRICE: "price",
  PRECISION_AMOUNT: "amount",
  PRECISION_COST: "cost",
  LIMITS: "limits",
  LIMITS_AMOUNT: "amount",
  LIMITS_AMOUNT_MIN: "min",
  LIMITS_AMOUNT_MAX: "max",
  LIMITS_PRICE: "price",
  LIMITS_PRICE_MIN: "min",
  LIMITS_PRICE_MAX: "max",
  LIMITS_COST: "cost",
  LIMITS_COST_MIN: "min",
  LIMITS_COST_MAX: "max",
  TYPE: "type",
  EXPIRY: "expiry",
  INFO: "info",
} as const
export type MarketStatusColumn = (typeof MarketStatusColumns)[keyof typeof MarketStatusColumns]

export const TickerColumns = {
  SYMBOL: "symbol",
  TIMESTAMP: "timestamp",
  DATETIME: "datetime",
  HIGH: "high",
  LOW: "low",
  BID: "bid",
  BID_VOLUME: "bidVolume",
  ASK: "ask",
  ASK_VOLUME: "askVolume",
  VWAP: "vwap",
  OPEN: "open",
  CLOSE: "close",
  LAST: "last",
  PREVIOUS_CLOSE: "previousClose",
  CHANGE: "change",
  PERCENTAGE: "percentage",
  AVERAGE: "average",
  BASE_VOLUME: "baseVolume",
  QUOTE_VOLUME: "quoteVolume",
  INFO: "info",
} as const
export type TickerColumn = (typeof TickerColumns)[keyof typeof TickerColumns]

export const OrderBookColumns = {
  BIDS: "bids",
  ASKS: "asks",
  TIMESTAMP: "timestamp",
  DATETIME: "datetime",
  NONCE: "nonce",
} as const

export const FundingColumns = {
  SYMBOL: "symbol",
  LAST_FUNDING_TIME: "last_funding_time",
  FUNDING_RATE: "funding_rate",
  NEXT_FUNDING_TIME: "next_funding_time",
  PREDICTED_FUNDING_RATE: "predicted_funding_rate",
} as const

export const MarkPriceColumns = {
  SYMBOL: "symbol",
  TIMESTAMP: "timestamp",
  MARK_PRICE: "mark_price",
} as const

export const PositionColumns = {
  ID: "id",
  LOCAL_ID: "local_id",
  TIMESTAMP: "timestamp",
  SYMBOL: "symbol",
  ENTRY_PRICE: "entry_price",
  MARK_PRICE: "mark_price",
  LIQUIDATION_PRICE: "liquidation_price",
  BANKRUPTCY_PRICE: "bankruptcy_price",
  UNREALIZED_PNL: "unrealised_pnl",
  REALISED_PNL: "realised_pnl",
  CLOSING_FEE: "closing_fee",
  QUANTITY: "quantity",
  SIZE: "size",
  NOTIONAL: "notional",
  INITIAL_MARGIN: "initial_margin",
  AUTO_DEPOSIT_MARGIN: "auto_deposit_margin",
  COLLATERAL: "collateral",
  LEVERAGE: "leverage",
  MARGIN_TYPE: "margin_type",
  CONTRACT_TYPE: "contract_type",
  CONTRACT_SIZE: "contract_size",
  POSITION_MODE: "position_mode",
  MAINTENANCE_MARGIN_RATE: "maintenance_margin_rate",
  STATUS: "status",
  SIDE: "side",
} as const

export const LeverageTiersColumns = {
  TIER: "tier",
  CURRENCY: "currency",
  MIN_NOTIONAL: "min_notional",
  MAX_NOTIONAL: "max_notional",
  MAINTENANCE_MARGIN_RATE: "maintenance_margin_rate",
  MAX_LEVERAGE: "max_leverage",
  INFO: "info",
} as const

export const FeeColumns = {
  TYPE: "type",
  CURRENCY: "currency",
  RATE: "rate",
  COST: "cost",
  IS_FROM_EXCHANGE: "is_from_exchange",
  EXCHANGE_ORIGINAL_COST: "exchange_original_cost",
} as const

export const TransactionColumns = {
  ID: "id",
  TXID: "txid",
  TIMESTAMP: "timestamp",
  ADDRESS_FROM: "address_from",
  ADDRESS_TO: "address_to",
  TAG: "tag",
  TYPE: "type",
  AMOUNT: "amount",
  CURRENCY: "currency",
  STATUS: "status",
  FEE: "fee",
  NETWORK: "network",
  COMMENT: "comment",
  INTERNAL: "internal",
  INFO: "info",
} as const

export const DepositAddressColumns = {
  CURRENCY: "currency",
  NETWORK: "network",
  ADDRESS: "address",
  TAG: "tag",
  INFO: "info",
} as const

export const MarketPropertyColumns = {
  TAKER: "taker",
  MAKER: "maker",
  FEE: "fee",
  FEE_SIDE: "feeSide",
} as const

// CCXT-specific column names used internally during adaptation
export const CcxtOrderColumns = {
  TAKER_OR_MAKER: "takerOrMaker",
  DATETIME: "datetime",
  TIMESTAMP: "timestamp",
} as const

export const CcxtPositionColumns = {
  SYMBOL: "symbol",
  SIDE: "side",
  CONTRACTS: "contracts",
  CONTRACT_SIZE: "contractSize",
  HEDGED: "hedged",
  LEVERAGE: "leverage",
  COLLATERAL: "collateral",
  NOTIONAL: "notional",
  INITIAL_MARGIN: "initialMargin",
  UNREALISED_PNL: "unrealizedPnl",
  REALISED_PNL: "realizedPnl",
  LIQUIDATION_PRICE: "liquidationPrice",
  MARK_PRICE: "markPrice",
  ENTRY_PRICE: "entryPrice",
  TIMESTAMP: "timestamp",
  MARGIN_TYPE: "marginType",
  MARGIN_MODE: "marginMode",
} as const

export const CcxtFundingColumns = {
  FUNDING_RATE: "fundingRate",
  FUNDING_TIMESTAMP: "fundingTimestamp",
  PREVIOUS_FUNDING_TIMESTAMP: "previousFundingTimestamp",
} as const
