// Mirror of connectors/ccxt/enums.py — the column-name constants CCXT itself
// emits, kept separate from the OctoBot-side ExchangeConstants* enums.

export enum ExchangeConstantsCCXTColumns {
  TIMESTAMP = "timestamp",
  DATETIME = "datetime",
  SYMBOL = "symbol",
  SIDE = "side",
  TYPE = "type",
  PRICE = "price",
  AMOUNT = "amount",
  COST = "cost",
  FILLED = "filled",
  REMAINING = "remaining",
  STATUS = "status",
  FEE = "fee",
  AVERAGE = "average",
  TRADES = "trades",
  ID = "id",
  ORDER = "order",
  INFO = "info",
}

export enum ExchangeOrderCCXTColumns {
  TAKER_OR_MAKER = "takerOrMaker",
  TAKER = "taker",
  MAKER = "maker",
}

export enum ExchangePositionCCXTColumns {
  SYMBOL = "symbol",
  TIMESTAMP = "timestamp",
  SIDE = "side",
  CONTRACTS = "contracts",
  CONTRACT_SIZE = "contractSize",
  HEDGED = "hedged",
  LIQUIDATION_PRICE = "liquidationPrice",
  MARK_PRICE = "markPrice",
  ENTRY_PRICE = "entryPrice",
  COLLATERAL = "collateral",
  NOTIONAL = "notional",
  INITIAL_MARGIN = "initialMargin",
  UNREALISED_PNL = "unrealizedPnl",
  REALISED_PNL = "realizedPnl",
  LEVERAGE = "leverage",
  MARGIN_TYPE = "marginType",
  MARGIN_MODE = "marginMode",
}

export enum ExchangeFundingCCXTColumns {
  FUNDING_RATE = "fundingRate",
  FUNDING_TIMESTAMP = "fundingTimestamp",
  PREVIOUS_FUNDING_TIMESTAMP = "previousFundingTimestamp",
}

export enum ExchangeLeverageTiersCCXTColumns {
  TIER = "tier",
  CURRENCY = "currency",
  MIN_NOTIONAL = "minNotional",
  MAX_NOTIONAL = "maxNotional",
  MAINTENANCE_MARGIN_RATE = "maintenanceMarginRate",
  MAX_LEVERAGE = "maxLeverage",
}
