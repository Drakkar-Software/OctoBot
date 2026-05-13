/**
 * Action templates define the parameter schema for each action type.
 * These mirror the `ActionsDAGParserParams` from `actions_dag_parser.py`.
 *
 * Each template has detection patterns (regex on values) and fuzzy aliases
 * (on column headers) used by the column detector to auto-map CSV columns.
 */

export type ParamInputType =
  | "text"
  | "number"
  | "select"
  | "password"
  | "numberOrDate"

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
  isoDate:
    /^\d{4}-\d{2}-\d{2}(T\d{2}:\d{2}(:\d{2})?(\.\d+)?(Z|[+-]\d{2}:?\d{2})?)?$/,
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
  aliasFuzzy?: string[],
): ActionParamDef {
  return {
    key,
    label,
    required,
    type: "text",
    detectPatterns: [PATTERNS.evmAddress, PATTERNS.btcAddress],
    aliasFuzzy: aliasFuzzy || [
      "addr",
      "address",
      "wallet",
      "destination",
      "recipient",
    ],
  }
}

function blockHeightParam(
  key: string,
  label: string,
  required: boolean,
): ActionParamDef {
  return {
    key,
    label,
    required,
    type: "numberOrDate",
    detectPatterns: [PATTERNS.numericAmount, PATTERNS.isoDate],
    aliasFuzzy: ["block_height", "blockheight", "height"],
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

function symbolParam(
  key: string,
  label: string,
  required: boolean,
): ActionParamDef {
  return {
    key,
    label,
    required,
    type: "text",
    detectPatterns: [PATTERNS.tradingPair],
    aliasFuzzy: ["symbol", "pair", "market", "sym", "ticker"],
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

function loopIntervalParam(): ActionParamDef {
  return {
    key: "LOOP_INTERVAL",
    label: "Loop Interval (s)",
    required: true,
    type: "number",
    detectPatterns: [PATTERNS.numericAmount],
    aliasFuzzy: ["loop_interval", "loopinterval", "loop_wait"],
  }
}

function loopTimeoutParam(): ActionParamDef {
  return {
    key: "LOOP_TIMEOUT",
    label: "Loop Timeout (s)",
    required: false,
    type: "number",
    detectPatterns: [PATTERNS.numericAmount],
    aliasFuzzy: ["loop_timeout", "looptimeout", "timeout"],
  }
}

function loopMaxAttemptsParam(): ActionParamDef {
  return {
    key: "LOOP_MAX_ATTEMPTS",
    label: "Loop Max Attempts",
    required: false,
    type: "number",
    detectPatterns: [PATTERNS.numericAmount],
    aliasFuzzy: [
      "loop_max_attempts",
      "loopmaxattempts",
      "max_attempts",
      "attempts",
    ],
  }
}

// ── Template definitions ───────────────────────────────────────────────

export const TRADE_TEMPLATE: ActionTemplate = {
  id: "trade",
  label: "Trade",
  description: "Place a buy or sell order on an exchange",
  actionTypes: ["trade"],
  params: [
    symbolParam("ORDER_SYMBOL", "Order Symbol", true),
    amountParam("ORDER_AMOUNT", "Order Amount", true),
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
      label: "Order Side",
      required: false,
      type: "select",
      options: ["buy", "sell"],
      detectPatterns: [PATTERNS.orderSide],
      aliasFuzzy: ["side", "direction", "buy", "sell"],
    },
    {
      key: "ORDER_PRICE",
      label: "Order Price",
      required: false,
      type: "number",
      detectPatterns: [PATTERNS.numericAmount],
      aliasFuzzy: ["price", "rate", "limit_price"],
    },
    {
      key: "ORDER_STOP_PRICE",
      label: "Order Stop Price",
      required: false,
      type: "number",
      detectPatterns: [PATTERNS.numericAmount],
      aliasFuzzy: ["stop", "stop_price", "stopprice", "trigger"],
    },
    {
      key: "ORDER_TAG",
      label: "Order Tag",
      required: false,
      type: "text",
      aliasFuzzy: ["tag", "label", "note", "comment"],
    },
    {
      key: "ORDER_REDUCE_ONLY",
      label: "Order Reduce Only",
      required: false,
      type: "select",
      options: ["true", "false"],
      aliasFuzzy: ["reduce", "reduce_only", "reduceonly"],
    },
    exchangeParam("EXCHANGE_TO", "Exchange", false),
    {
      key: "ORDER_EXTRA_PARAMS",
      label: "Order Extra Params",
      required: false,
      type: "text",
      aliasFuzzy: ["extra_params", "extra"],
    },
    {
      key: "API_KEY",
      label: "Exchange API Key",
      required: false,
      type: "password",
      sensitive: true,
      aliasFuzzy: ["api_key", "apikey"],
    },
    {
      key: "API_SECRET",
      label: "Exchange API Secret",
      required: false,
      type: "password",
      sensitive: true,
      aliasFuzzy: ["api_secret", "apisecret"],
    },
    {
      key: "SIMULATED_PORTFOLIO",
      label: "Simulated Portfolio",
      required: false,
      type: "text",
      aliasFuzzy: ["simulated_portfolio", "simulatedportfolio"],
    },
  ],
}

export const CANCEL_TEMPLATE: ActionTemplate = {
  id: "cancel",
  label: "Cancel Order",
  description: "Cancel open orders on an exchange",
  actionTypes: ["cancel"],
  params: [
    symbolParam("ORDER_SYMBOL", "Symbol", true),
    {
      key: "ORDER_SIDE",
      label: "Cancel Order Side",
      required: false,
      type: "select",
      options: ["buy", "sell"],
      detectPatterns: [PATTERNS.orderSide],
      aliasFuzzy: ["side", "direction"],
    },
    {
      key: "ORDER_TAG",
      label: "Cancel Order Tag",
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
    assetParam("BLOCKCHAIN_TO_ASSET", "Withdraw Asset", true),
    blockchainParam("BLOCKCHAIN_TO", "Withdraw Network", true),
    addressParam("BLOCKCHAIN_TO_ADDRESS", "Withdraw Address", true),
    amountParam("BLOCKCHAIN_TO_AMOUNT", "Withdraw Amount", false),
    exchangeParam("EXCHANGE_FROM", "Withdraw Src Exchange", false),
  ],
}

export const DEPOSIT_TEMPLATE: ActionTemplate = {
  id: "deposit",
  label: "Deposit",
  description: "Deposit funds from a blockchain wallet to an exchange",
  actionTypes: ["deposit"],
  params: [
    assetParam("BLOCKCHAIN_FROM_ASSET", "Deposit Asset", true),
    amountParam("BLOCKCHAIN_FROM_AMOUNT", "Deposit Amount", true),
    blockchainParam("BLOCKCHAIN_FROM", "Deposit Network", true),
    privateKeyParam("BLOCKCHAIN_FROM_PRIVATE_KEY", "Deposit Src Private Key"),
    mnemonicParam("BLOCKCHAIN_FROM_MNEMONIC_SEED", "Deposit Src Mnemonic"),
    blockHeightParam(
      "BLOCKCHAIN_FROM_BLOCK_HEIGHT",
      "Deposit Src Block Height",
      false,
    ),
    exchangeParam("EXCHANGE_TO", "Deposit Dst Exchange", true),
  ],
}

export const TRANSFER_TEMPLATE: ActionTemplate = {
  id: "transfer",
  label: "Transfer",
  description: "Transfer funds between blockchain wallets",
  actionTypes: ["transfer"],
  params: [
    assetParam("BLOCKCHAIN_FROM_ASSET", "Transfer Asset", true),
    amountParam("BLOCKCHAIN_FROM_AMOUNT", "Transfer Amount", true),
    blockchainParam("BLOCKCHAIN_FROM", "Transfer Network", true),
    addressParam("BLOCKCHAIN_FROM_ADDRESS", "Transfer From Address", false, [
      "from_address",
      "blockchain_from_address",
    ]),
    privateKeyParam("BLOCKCHAIN_FROM_PRIVATE_KEY", "Transfer Src Private Key"),
    mnemonicParam("BLOCKCHAIN_FROM_MNEMONIC_SEED", "Transfer Src Mnemonic"),
    blockHeightParam(
      "BLOCKCHAIN_FROM_BLOCK_HEIGHT",
      "Transfer Src Block Height",
      false,
    ),
    addressParam("BLOCKCHAIN_TO_ADDRESS", "Transfer Dst Address", true, [
      "to_address",
      "blockchain_to_address",
    ]),
    {
      key: "BLOCKCHAIN_FROM_FILENAME",
      label: "Transfer From Filename",
      required: false,
      type: "text",
      aliasFuzzy: [],
    },
    {
      key: "BLOCKCHAIN_FROM_PASSWORD",
      label: "Transfer From Password",
      required: false,
      type: "password",
      aliasFuzzy: [],
    },
    {
      key: "BLOCKCHAIN_FROM_PORT",
      label: "Transfer From Port",
      required: false,
      type: "number",
      aliasFuzzy: [],
    },
  ],
}

export const BLOCKCHAIN_WALLET_INIT_TEMPLATE: ActionTemplate = {
  id: "blockchain_wallet_init",
  label: "Blockchain Wallet Init",
  description: "Initialize a blockchain wallet",
  actionTypes: ["blockchain_wallet_init"],
  params: [
    blockchainParam("BLOCKCHAIN_FROM", "Transfer Network", true),
    privateKeyParam("BLOCKCHAIN_FROM_PRIVATE_KEY", "Transfer Src Private Key"),
    mnemonicParam("BLOCKCHAIN_FROM_MNEMONIC_SEED", "Transfer Src Mnemonic"),
    blockHeightParam(
      "BLOCKCHAIN_FROM_BLOCK_HEIGHT",
      "Transfer Src Block Height",
      false,
    ),
    {
      key: "BLOCKCHAIN_INIT_CLOSE_WALLET_ON_EXIT",
      label: "Close Wallet On Exit",
      required: true,
      type: "select",
      options: ["true", "false"],
      aliasFuzzy: ["close_on_exit"],
    },
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
      label: "Wait Min Delay (s)",
      required: true,
      type: "number",
      detectPatterns: [PATTERNS.numericAmount],
      aliasFuzzy: ["delay", "wait", "timeout", "min_delay", "mindelay"],
    },
    {
      key: "MAX_DELAY",
      label: "Wait Max Delay (s)",
      required: false,
      type: "number",
      detectPatterns: [PATTERNS.numericAmount],
      aliasFuzzy: ["max_delay", "maxdelay", "max_wait"],
    },
  ],
}

export const LOOP_UNTIL_ORDER_CLOSED_TEMPLATE: ActionTemplate = {
  id: "loop_until_order_closed",
  label: "Loop Until Order Closed",
  description: "Loop until an order is closed",
  actionTypes: ["loop_until_order_closed"],
  params: [
    {
      key: "ORDER_EXCHANGE_ID",
      label: "Order Exchange ID",
      required: true,
      type: "text",
      aliasFuzzy: ["order_exchange_id", "order_id", "exchange_order_id"],
    },
    exchangeParam("EXCHANGE_TO", "Exchange", false),
    symbolParam("ORDER_SYMBOL", "Order Symbol", true),
    loopIntervalParam(),
    loopTimeoutParam(),
    loopMaxAttemptsParam(),
  ],
}

export const LOOP_UNTIL_BLOCKCHAIN_BALANCE_TEMPLATE: ActionTemplate = {
  id: "loop_until_blockchain_balance",
  label: "Loop Until Blockchain Balance",
  description: "Loop until a blockchain balance is reached",
  actionTypes: ["loop_until_blockchain_balance"],
  params: [
    assetParam("BLOCKCHAIN_BALANCE_ASSET", "Balance Asset", true),
    blockchainParam("BLOCKCHAIN_BALANCE", "Balance Blockchain", true),
    addressParam("BLOCKCHAIN_BALANCE_ADDRESS", "Balance Address", true),
    amountParam("BLOCKCHAIN_BALANCE_AMOUNT", "Balance Amount", true),
    loopIntervalParam(),
    loopTimeoutParam(),
    loopMaxAttemptsParam(),
  ],
}

export const BASE_ACTION_TEMPLATES: ActionTemplate[] = [
  TRANSFER_TEMPLATE,
  BLOCKCHAIN_WALLET_INIT_TEMPLATE,
  TRADE_TEMPLATE,
  WITHDRAW_TEMPLATE,
  DEPOSIT_TEMPLATE,
  CANCEL_TEMPLATE,
  WAIT_TEMPLATE,
  LOOP_UNTIL_ORDER_CLOSED_TEMPLATE,
  LOOP_UNTIL_BLOCKCHAIN_BALANCE_TEMPLATE,
]

export function getTemplateById(id: string): ActionTemplate | undefined {
  return BASE_ACTION_TEMPLATES.find((t) => t.id === id)
}

export function isParamValueValid(
  param: ActionParamDef,
  rawValue: string | undefined,
): boolean {
  const value = rawValue?.trim() ?? ""
  if (!value) return false
  if (param.type === "number") {
    return Number.isFinite(Number(value))
  }
  if (param.type === "numberOrDate") {
    if (Number.isFinite(Number(value))) return true
    return Number.isFinite(Date.parse(value))
  }
  return true
}
