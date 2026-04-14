/**
 * Action templates define the parameter schema for each action type.
 * These mirror the `ActionsDAGParserParams` from `actions_dag_parser.py`.
 *
 * Each template has detection patterns (regex on values) and fuzzy aliases
 * (on column headers) used by the column detector to auto-map CSV columns.
 */

export type ParamInputType = "text" | "number" | "select" | "password"

export interface ActionParamDef {
  key: string
  label: string
  required: boolean
  type: ParamInputType
  options?: string[]
  sensitive?: boolean
  /** Pre-filled value when this template is selected */
  defaultValue?: string
  /** Regex patterns to detect this param type from cell values */
  detectPatterns?: RegExp[]
  /** Fuzzy aliases to match column header names (case-insensitive) */
  aliasFuzzy?: string[]
  /** If true, this param is hidden from the UI (still included in task content) */
  hidden?: boolean
}

export interface ActionTemplate {
  id: string
  label: string
  description: string
  actionTypes: string[]
  params: ActionParamDef[]
}

// ── Common detection patterns ──────────────────────────────────────────

const PATTERNS = {
  evmAddress: /^0x[0-9a-fA-F]{40}$/,
  btcAddress: /^(bc1|[13])[a-zA-HJ-NP-Z0-9]{25,62}$/,
  privateKeyHex: /^(0x)?[0-9a-fA-F]{64}$/,
  mnemonicSeed: /^(?:\S+\s+){11,23}\S+$/,
  tradingPair: /^[A-Z]{2,10}\/[A-Z]{2,10}$/i,
  numericAmount: /^-?\d+(\.\d+)?$/,
  exchangeName:
    /^(binance|coinbase|kraken|kucoin|bybit|okx|gate\.?io|huobi|htx|bitfinex|bitstamp|gemini|mexc|bitget|ascendex|hollaex)$/i,
  orderSide: /^(buy|sell|long|short)$/i,
  orderType: /^(market|limit|stop|stop.?limit|trailing.?stop)$/i,
} as const

// ── Shared param building helpers ──────────────────────────────────────

function addressParam(
  key: string,
  label: string,
  required: boolean,
): ActionParamDef {
  return {
    key,
    label,
    required,
    type: "text",
    detectPatterns: [PATTERNS.evmAddress, PATTERNS.btcAddress],
    aliasFuzzy: ["addr", "address", "wallet", "destination", "recipient"],
  }
}

function privateKeyParam(key: string, label: string): ActionParamDef {
  return {
    key,
    label,
    required: false,
    type: "password",
    sensitive: true,
    detectPatterns: [PATTERNS.privateKeyHex],
    aliasFuzzy: ["key", "private", "secret", "pk", "private_key", "privatekey"],
  }
}

function mnemonicParam(key: string, label: string): ActionParamDef {
  return {
    key,
    label,
    required: false,
    type: "password",
    sensitive: true,
    detectPatterns: [PATTERNS.mnemonicSeed],
    aliasFuzzy: ["seed", "mnemonic", "recovery", "phrase"],
  }
}

function amountParam(
  key: string,
  label: string,
  required: boolean,
): ActionParamDef {
  return {
    key,
    label,
    required,
    type: "number",
    detectPatterns: [PATTERNS.numericAmount],
    aliasFuzzy: ["amount", "qty", "quantity", "vol", "volume", "size"],
  }
}

function assetParam(
  key: string,
  label: string,
  required: boolean,
): ActionParamDef {
  return {
    key,
    label,
    required,
    type: "text",
    aliasFuzzy: ["asset", "coin", "token", "currency", "crypto"],
  }
}

function blockchainParam(
  key: string,
  label: string,
  required: boolean,
): ActionParamDef {
  return {
    key,
    label,
    required,
    type: "text",
    aliasFuzzy: ["network", "chain", "blockchain", "net"],
  }
}

function exchangeParam(
  key: string,
  label: string,
  required: boolean,
): ActionParamDef {
  return {
    key,
    label,
    required,
    type: "text",
    detectPatterns: [PATTERNS.exchangeName],
    aliasFuzzy: ["exchange", "exch", "platform", "cex"],
  }
}

// ── Template definitions ───────────────────────────────────────────────

export const TRADE_TEMPLATE: ActionTemplate = {
  id: "trade",
  label: "Trade",
  description: "Place a buy or sell order on an exchange",
  actionTypes: ["trade"],
  params: [
    {
      key: "ORDER_SYMBOL",
      label: "Symbol",
      required: true,
      type: "text",
      detectPatterns: [PATTERNS.tradingPair],
      aliasFuzzy: ["symbol", "pair", "market", "sym", "ticker"],
    },
    amountParam("ORDER_AMOUNT", "Amount", true),
    {
      key: "ORDER_TYPE",
      label: "Order Type",
      required: true,
      type: "select",
      options: ["market", "limit", "stop", "stop_limit", "trailing_stop"],
      detectPatterns: [PATTERNS.orderType],
      aliasFuzzy: ["type", "order_type", "ordertype"],
    },
    {
      key: "ORDER_SIDE",
      label: "Side",
      required: false,
      type: "select",
      options: ["buy", "sell"],
      detectPatterns: [PATTERNS.orderSide],
      aliasFuzzy: ["side", "direction", "buy", "sell"],
    },
    {
      key: "ORDER_PRICE",
      label: "Price",
      required: false,
      type: "number",
      detectPatterns: [PATTERNS.numericAmount],
      aliasFuzzy: ["price", "rate", "limit_price"],
    },
    {
      key: "ORDER_STOP_PRICE",
      label: "Stop Price",
      required: false,
      type: "number",
      detectPatterns: [PATTERNS.numericAmount],
      aliasFuzzy: ["stop", "stop_price", "stopprice", "trigger"],
    },
    {
      key: "ORDER_TAG",
      label: "Tag",
      required: false,
      type: "text",
      aliasFuzzy: ["tag", "label", "note", "comment"],
    },
    {
      key: "ORDER_REDUCE_ONLY",
      label: "Reduce Only",
      required: false,
      type: "select",
      options: ["true", "false"],
      aliasFuzzy: ["reduce", "reduce_only", "reduceonly"],
    },
    exchangeParam("EXCHANGE_TO", "Exchange", false),
    {
      key: "API_KEY",
      label: "API Key",
      required: false,
      type: "password",
      sensitive: true,
      aliasFuzzy: ["api_key", "apikey"],
    },
    {
      key: "API_SECRET",
      label: "API Secret",
      required: false,
      type: "password",
      sensitive: true,
      aliasFuzzy: ["api_secret", "apisecret"],
    },
  ],
}

export const CANCEL_TEMPLATE: ActionTemplate = {
  id: "cancel",
  label: "Cancel Order",
  description: "Cancel open orders on an exchange",
  actionTypes: ["cancel"],
  params: [
    {
      key: "ORDER_SYMBOL",
      label: "Symbol",
      required: true,
      type: "text",
      detectPatterns: [PATTERNS.tradingPair],
      aliasFuzzy: ["symbol", "pair", "market", "sym", "ticker"],
    },
    {
      key: "ORDER_SIDE",
      label: "Side",
      required: false,
      type: "select",
      options: ["buy", "sell"],
      detectPatterns: [PATTERNS.orderSide],
      aliasFuzzy: ["side", "direction"],
    },
    {
      key: "ORDER_TAG",
      label: "Tag",
      required: false,
      type: "text",
      aliasFuzzy: ["tag", "label", "note"],
    },
  ],
}

export const WITHDRAW_TEMPLATE: ActionTemplate = {
  id: "withdraw",
  label: "Withdraw",
  description: "Withdraw funds from an exchange to a blockchain address",
  actionTypes: ["withdraw"],
  params: [
    assetParam("BLOCKCHAIN_TO_ASSET", "Asset", true),
    blockchainParam("BLOCKCHAIN_TO", "Network", true),
    addressParam("BLOCKCHAIN_TO_ADDRESS", "Destination Address", true),
    amountParam("BLOCKCHAIN_TO_AMOUNT", "Amount", false),
    exchangeParam("EXCHANGE_FROM", "Source Exchange", false),
  ],
}

export const DEPOSIT_TEMPLATE: ActionTemplate = {
  id: "deposit",
  label: "Deposit",
  description: "Deposit funds from a blockchain wallet to an exchange",
  actionTypes: ["deposit"],
  params: [
    assetParam("BLOCKCHAIN_FROM_ASSET", "Asset", true),
    amountParam("BLOCKCHAIN_FROM_AMOUNT", "Amount", true),
    blockchainParam("BLOCKCHAIN_FROM", "Source Network", true),
    addressParam("BLOCKCHAIN_FROM_ADDRESS", "Source Address", false),
    privateKeyParam("BLOCKCHAIN_FROM_PRIVATE_KEY", "Source Private Key"),
    mnemonicParam("BLOCKCHAIN_FROM_MNEMONIC_SEED", "Source Mnemonic"),
    exchangeParam("EXCHANGE_TO", "Destination Exchange", true),
  ],
}

export const TRANSFER_TEMPLATE: ActionTemplate = {
  id: "transfer",
  label: "Transfer",
  description: "Transfer funds between blockchain wallets",
  actionTypes: ["transfer"],
  params: [
    assetParam("BLOCKCHAIN_FROM_ASSET", "Asset", true),
    amountParam("BLOCKCHAIN_FROM_AMOUNT", "Amount", true),
    blockchainParam("BLOCKCHAIN_FROM", "Network", true),
    addressParam("BLOCKCHAIN_FROM_ADDRESS", "Source Address", false),
    privateKeyParam("BLOCKCHAIN_FROM_PRIVATE_KEY", "Source Private Key"),
    mnemonicParam("BLOCKCHAIN_FROM_MNEMONIC_SEED", "Source Mnemonic"),
    addressParam("BLOCKCHAIN_TO_ADDRESS", "Destination Address", true),
  ],
}

export const WAIT_TEMPLATE: ActionTemplate = {
  id: "wait",
  label: "Wait",
  description: "Wait for a specified delay before continuing",
  actionTypes: ["wait"],
  params: [
    {
      key: "MIN_DELAY",
      label: "Min Delay (s)",
      required: true,
      type: "number",
      detectPatterns: [PATTERNS.numericAmount],
      aliasFuzzy: ["delay", "wait", "timeout", "min_delay", "mindelay"],
    },
    {
      key: "MAX_DELAY",
      label: "Max Delay (s)",
      required: false,
      type: "number",
      detectPatterns: [PATTERNS.numericAmount],
      aliasFuzzy: ["max_delay", "maxdelay", "max_wait"],
    },
  ],
}

export const BASE_ACTION_TEMPLATES: ActionTemplate[] = [
  TRANSFER_TEMPLATE,
  TRADE_TEMPLATE,
  WITHDRAW_TEMPLATE,
  DEPOSIT_TEMPLATE,
  CANCEL_TEMPLATE,
  WAIT_TEMPLATE,
]

export function getTemplateById(id: string): ActionTemplate | undefined {
  return BASE_ACTION_TEMPLATES.find((t) => t.id === id)
}
