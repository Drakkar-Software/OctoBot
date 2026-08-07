import type {
  MarketMakingConfiguration,
  MarketMakingSymbolConfiguration,
  MarketMakingReferencePair,
  MarketMakingHedgingEngine,
  TradingTentaclesConfiguration,
  CopyConfiguration,
  GenericProcessConfiguration,
} from '@drakkar.software/octobot-protocol'

// Per-kind pure builders: local input shape -> protocol configuration. No I/O,
// no local domain types — every function here is a straight function of its
// arguments. This is the part of the old strategyConfig.ts that was never the
// problem; only its neighbors (the discriminated-union facade and the patch
// reader) redeclared things that belonged here once, which is why they now
// live in ./build.ts and ./patch.ts instead of duplicating this file's types.

export type MmRefInput = {
  pair: string
  weight: number
  formula?: string
  timeframe?: string
  /** Venue the reference price is quoted on (protocol allows cross-exchange
   *  references and sentinels). Absent = the bot's own trading venue. */
  exchange?: string
}

export type MmBudgetPairInput = {
  enabled: boolean
  /** 0 = disabled — mirrors the protocol's own "0 means unlimited" semantics. */
  maxBase: string | number
  maxQuote: string | number
  /** 0 = use the node's suggested value. */
  minBase: string | number
  minQuote: string | number
}

export type MmStopsPairInput = {
  enabled: boolean
  minBaseHolding?: string | number
  minQuoteHolding?: string | number
  maxPositivePct?: string | number
  maxNegativePct?: string | number
  avgPriceMinutes?: string | number
}

export type MmVolumePairInput = {
  enabled: boolean
  /** Per-trade notional bounds, quote-denominated. */
  minAmount: string | number
  maxAmount: string | number
  minIntervalSeconds: string | number
  maxIntervalSeconds: string | number
}

export type MmHedgingPairInput = {
  enabled: boolean
  /** Venue to route the hedge trade on — must differ from the bot's own trading exchange. */
  exchange: string
  maxLossThreshold?: string | number
  avgPriceMinutes?: string | number
  maxNegativePct?: string | number
  maxPositivePct?: string | number
}

/** Per-pair order-book/spread configuration — an optional overlay on top of
 *  the bot-wide spreadBp/perSide/shape scalars (which stay the fallback for
 *  budget-disabled pairs and edit-mode recovery). Present = the pair carries
 *  a real per-pair MarketMakingSymbolConfiguration spread/depth setting. */
export type MmOrderBookPairInput = {
  minSpreadBp: string | number
  maxSpreadBp: string | number
  bidsCount: string | number
  asksCount: string | number
  ordersDistribution: 'linear'
  fundsDistribution: 'flat' | 'valley' | 'random'
  /** Order-book depth as % of cumulated volume. */
  cumulatedVolumePercent: string | number
  /** Order-book depth as % of daily trading volume. */
  percentDailyTradingVolume: string | number
}

export type MmInput = {
  exchange: string
  pairs: string[]
  /** Reference price configuration per trading pair. */
  refsByPair: Record<string, MmRefInput[] | undefined>
  /** Spread expressed in basis points (e.g. '50' for 0.5%). */
  spreadBp: string | number
  /** Orders per side. */
  perSide: string | number
  /** Base-asset budget per pair. */
  sizeBase: string | number
  shape: 'flat' | 'linear' | 'expo' | 'random' | 'custom'
  budgetByPair?: Record<string, MmBudgetPairInput | undefined>
  stopsByPair?: Record<string, MmStopsPairInput | undefined>
  volumeByPair?: Record<string, MmVolumePairInput | undefined>
  hedgingByPair?: Record<string, MmHedgingPairInput | undefined>
  orderBookByPair?: Record<string, MmOrderBookPairInput | undefined>
}

export type GridLadderGeometry = {
  spread: number
  increment: number
  buyCount: number
  sellCount: number
}

export type GridInput = {
  pairs: string[]
  /** Lower price bound, quote-denominated. */
  lower?: number | null
  /** Upper price bound, quote-denominated. */
  upper?: number | null
  /** Total initial orders in the ladder (>= 2), split between the buy and sell
   *  sides at the current price. The ladder spans `levels + 1` price lines
   *  across [lower, upper]; the one the price sits on carries no order, which
   *  is why `levels` orders need `levels + 1` lines. */
  levels?: number | null
  /** Market price snapshot when the user configured the grid — drives the buy/sell split. */
  currentPrice?: number | null
  /** Raw ladder params (advanced mode / edit rehydration). When all four are
   *  set they are emitted verbatim and take precedence over the range
   *  derivation — the only way to express flat_spread ≠ flat_increment. */
  flatSpread?: number | null
  flatIncrement?: number | null
  buyOrdersCount?: number | null
  sellOrdersCount?: number | null
  /** Trail the grid upwards when the price escapes it. Default true. */
  enableTrailingUp?: boolean | null
  /** Trail one order at a time instead of the whole grid. Default true. */
  orderByOrderTrailing?: boolean | null
}

export type DcaInput = {
  pairs: string[]
  /** Verbatim protocol amount string: '10%t' (percent of total holdings),
   *  '25q' (quote amount), '0.1' (base amount). */
  buyOrderAmount?: string | null
  /** Interval between buys in time-based trigger mode. */
  minutesBeforeNextBuy?: number | null
  /** Buy with market orders instead of limit orders. */
  useMarketEntry?: boolean | null
  /** Buy with a limit order this % below current price (limit entries only). */
  entryLimitPricePercent?: string | number | null
  /** Create a take-profit sell order when a buy is filled. */
  useTakeProfit?: boolean | null
  /** Sell with a limit order this % above the buying price. */
  exitLimitPricePercent?: string | number | null
}

export type IndexInput = {
  pairs: string[]
  basketWeights?: Record<string, number>
  basketTotal?: number
  /** Drift percentage that triggers a rebalance (wizard ±3/5/10 presets). */
  rebalanceTriggerPct?: number | null
}
export type CopyInput = { sourceId?: string | null }

export type SignalInput = {
  webhookId: string
  webhookSecret: string
  pair: string
  sideMode: 'payload' | 'buy' | 'sell'
  /** JSON field carrying buy/sell when sideMode === 'payload'. */
  sidePayloadField?: string
  orderType: 'market' | 'limit'
  /** Limit offset in bps when orderType === 'limit'. */
  limitOffsetBp?: string | number
  limitOffsetDir?: 'above' | 'below'
  sizeMode: 'fixed' | 'percent'
  sizeValue: string | number
  tpEnabled?: boolean
  tpPct?: string | number
  slEnabled?: boolean
  slPct?: string | number
}

/** Webhook-signal bot settings carried inside generic_process profile_data.
 *  The webhook secret rides along intentionally: the userActions document is
 *  identity-encrypted in transit and the node needs the secret to validate
 *  incoming webhook calls. */
export type SignalProfileData = {
  signal: {
    version: 1
    webhook: { id: string; secret: string }
    pair: string
    side: { mode: 'payload' | 'buy' | 'sell'; payload_field?: string }
    order: { type: 'market' | 'limit'; limit_offset_bp?: number; limit_offset_direction?: 'above' | 'below' }
    size: { mode: 'fixed' | 'percent'; value: number }
    take_profit_percent?: number
    stop_loss_percent?: number
  }
}

/** Constant per-pair-setting fields for GridTradingMode (StaggeredOrders subclass). */
const GRID_PAIR_SETTING_DEFAULTS = {
  sell_funds:               0,
  buy_funds:                0,
  starting_price:           0,
  buy_volume_per_order:     0,
  sell_volume_per_order:    0,
  ignore_exchange_fees:     true,
  reinvest_profits:         true,
  mirror_order_delay:       0,
  use_existing_orders_only: false,
  allow_funds_redispatch:   false,
  funds_redispatch_interval: 24,
  enable_trailing_down:     false,
} as const

type GridTrailingInput = Pick<GridInput, 'enableTrailingUp' | 'orderByOrderTrailing'>

function gridPairSettings(
  pair: string,
  flatSpread: number,
  flatIncrement: number,
  buyOrdersCount: number,
  sellOrdersCount: number,
  trailing?: GridTrailingInput,
) {
  return {
    pair,
    flat_spread:       flatSpread,
    flat_increment:    flatIncrement,
    buy_orders_count:  buyOrdersCount,
    sell_orders_count: sellOrdersCount,
    enable_trailing_up:      trailing?.enableTrailingUp ?? GRID_INPUT_DEFAULTS.enableTrailingUp,
    order_by_order_trailing: trailing?.orderByOrderTrailing ?? GRID_INPUT_DEFAULTS.orderByOrderTrailing,
    ...GRID_PAIR_SETTING_DEFAULTS,
  }
}

/** The wizard's only DCA trigger mode — evaluator-signal triggering needs
 *  evaluator config the wizard has no UI for. */
export const DCA_TRIGGER_MODE_TIME_BASED = 'Time based'

export const DCA_DEFAULTS = {
  buy_order_amount:                 '10%t',
  minutes_before_next_buy:          10080,
  use_market_entry_orders:          false,
  entry_limit_orders_price_percent: 1,
  use_take_profit_exit_orders:      true,
  exit_limit_orders_price_percent:  3,
} as const

/** GridInput-side defaults (spec example values), shared with a caller's own
 *  draft store so both layers agree on what an untouched grid emits. */
export const GRID_INPUT_DEFAULTS = {
  buyOrdersCount:       10,
  sellOrdersCount:      20,
  enableTrailingUp:     true,
  orderByOrderTrailing: true,
} as const

export const INDEX_DEFAULTS = {
  rebalance_trigger_min_percent: 5,
} as const

/** buy_order_amount unit suffixes a caller can express: percent of total
 *  holdings ('%t'), quote amount ('q'), bare base amount (''). */
export type DcaAmountUnit = '%t' | 'q' | 'base'

export function formatDcaAmount(value: string | number, unit: DcaAmountUnit): string {
  return `${String(value).trim()}${unit === 'base' ? '' : unit}`
}

/** Split a protocol buy_order_amount string into value + unit. Unknown
 *  suffixes ('2%', '12a%'…) stay whole in `value` with unit 'base' so a
 *  foreign config re-emits verbatim (formatDcaAmount round-trips it). */
export function parseDcaAmount(amount: string): { value: string; unit: DcaAmountUnit } {
  const trimmed = amount.trim()
  if (trimmed.endsWith('%t')) return { value: trimmed.slice(0, -2), unit: '%t' }
  if (trimmed.endsWith('q') && Number.isFinite(Number.parseFloat(trimmed.slice(0, -1)))) {
    return { value: trimmed.slice(0, -1), unit: 'q' }
  }
  return { value: trimmed, unit: 'base' }
}

/** Float hygiene for derived quote-price deltas. */
function round8(n: number): number {
  return Math.round(n * 1e8) / 1e8
}

function num(v: string | number | null | undefined): number {
  const n = typeof v === 'string' ? Number.parseFloat(v) : v
  return typeof n === 'number' && Number.isFinite(n) ? n : 0
}

/** Amounts/percentages from free-text inputs: the minus sign is typable on
 *  web and Android numeric keyboards, and the protocol's numeric fields are
 *  non-negative domains ('0 means unlimited'). */
function pos(v: string | number | null | undefined): number {
  return Math.max(0, num(v))
}

/** Order counts are whole and non-negative. */
function count(v: string | number | null | undefined): number {
  return Math.max(0, Math.round(num(v)))
}

function refsToProtocol(
  refs: MmRefInput[] | undefined,
  exchange: string,
  tradingPair: string,
): MarketMakingReferencePair[] {
  // No configured references: quote the traded pair on the bot's own venue.
  if (!refs?.length) return [{ exchange, pair: tradingPair, weight: 1 }]
  return refs.map((r) => ({
    // A reference quoted on another venue (or a sentinel like 'local
    // exchange price') keeps it across edits — only venue-less refs (all
    // wizard-created ones) default to the bot's own exchange.
    exchange: r.exchange ?? exchange,
    pair: r.pair,
    weight: r.weight,
    formula: r.formula || undefined,
    time_frame: r.timeframe as MarketMakingReferencePair['time_frame'],
  }))
}

function fundsDistribution(shape: MmInput['shape']): MarketMakingSymbolConfiguration['funds_distribution'] {
  if (shape === 'flat' || shape === 'linear') return 'flat'
  if (shape === 'expo') return 'valley'
  // 'custom' and 'random' both map to the protocol's 'random' distribution.
  return 'random'
}

// The node requires average_price_counted_minutes >= 1 — 0/unset still falls
// back to the 60-minute default, but any typed value below 1 (e.g. '0.5') is
// floored to 1 rather than sent through unclamped.
function avgPriceMinutesOf(v: string | number | undefined): number {
  const raw = pos(v)
  return raw > 0 ? Math.max(1, raw) : 60
}

// Per-pair stop-conditions, real thresholds (no rule-toggle presets). 0
// (or unset) stays "not set", mirroring the protocol's own semantics.
function stopConditionsFor(sc: MmStopsPairInput | undefined): MarketMakingSymbolConfiguration['stop_conditions'] {
  if (!sc?.enabled) return undefined
  const conditions: NonNullable<MarketMakingSymbolConfiguration['stop_conditions']> = {}
  if (pos(sc.minBaseHolding) > 0) conditions.min_base_holding = pos(sc.minBaseHolding)
  if (pos(sc.minQuoteHolding) > 0) conditions.min_quote_holding = pos(sc.minQuoteHolding)
  if (pos(sc.maxPositivePct) > 0) conditions.max_positive_percent_price_change = pos(sc.maxPositivePct)
  if (pos(sc.maxNegativePct) > 0) conditions.max_negative_percent_price_change = pos(sc.maxNegativePct)
  conditions.average_price_counted_minutes = avgPriceMinutesOf(sc.avgPriceMinutes)
  return conditions
}

// hedging_engine_type is intentionally not user-configurable yet — no caller
// exposes anything but 'spot'.
function hedgingEngineFor(h: MmHedgingPairInput): MarketMakingHedgingEngine {
  const engine: MarketMakingHedgingEngine = {
    hedging_engine_type: 'spot',
    hedging_exchange: h.exchange,
    average_price_counted_minutes: avgPriceMinutesOf(h.avgPriceMinutes),
  }
  if (pos(h.maxLossThreshold) > 0) engine.hedging_max_loss_threshold = pos(h.maxLossThreshold)
  if (pos(h.maxNegativePct) > 0) engine.max_negative_percent_price_change = pos(h.maxNegativePct)
  if (pos(h.maxPositivePct) > 0) engine.max_positive_percent_price_change = pos(h.maxPositivePct)
  return engine
}

export function buildMarketMakingConfig(input: MmInput): MarketMakingConfiguration {
  // num()/pos()/count() everywhere so all fields share one parsing behavior —
  // Number() and parseFloat disagree on partially-numeric strings like '1,000',
  // and the protocol's numeric domains exclude negatives and fractional counts.
  const minSpread = pos(input.spreadBp) / 100
  const baseSize = pos(input.sizeBase)
  const pair_settings: MarketMakingSymbolConfiguration[] = input.pairs.map((pair) => {
    const budget = input.budgetByPair?.[pair]
    const volume = input.volumeByPair?.[pair]
    const hedging = input.hedgingByPair?.[pair]
    const orderBook = input.orderBookByPair?.[pair]
    const stop_conditions = stopConditionsFor(input.stopsByPair?.[pair])
    return {
      trading_pair:        pair,
      reference_price:     refsToProtocol(input.refsByPair[pair], input.exchange, pair),
      min_spread:          orderBook ? pos(orderBook.minSpreadBp) / 100 : minSpread,
      max_spread:          orderBook ? pos(orderBook.maxSpreadBp) / 100 : minSpread * 2,
      bids_count:          orderBook ? count(orderBook.bidsCount) : count(input.perSide),
      asks_count:          orderBook ? count(orderBook.asksCount) : count(input.perSide),
      orders_distribution: orderBook?.ordersDistribution ?? 'linear',
      funds_distribution:  orderBook?.fundsDistribution ?? fundsDistribution(input.shape),
      ...(orderBook
        ? {
            order_book_depth: {
              cumulated_volume_percent:     pos(orderBook.cumulatedVolumePercent),
              percent_daily_trading_volume: pos(orderBook.percentDailyTradingVolume),
            },
          }
        : {}),
      exchange:            input.exchange,
      max_base_budget:     budget?.enabled ? pos(budget.maxBase) : baseSize,
      ...(budget?.enabled
        ? {
            max_quote_budget: pos(budget.maxQuote),
            min_base_budget:  pos(budget.minBase),
            min_quote_budget: pos(budget.minQuote),
          }
        : { max_quote_budget: baseSize }),
      ...(volume?.enabled
        ? {
            scheduled_volume: {
              // Free-text bounds: keep min <= max even if typed inverted.
              min_amount:           Math.min(pos(volume.minAmount), pos(volume.maxAmount)),
              max_amount:           Math.max(pos(volume.minAmount), pos(volume.maxAmount)),
              min_interval_seconds: Math.min(pos(volume.minIntervalSeconds), pos(volume.maxIntervalSeconds)),
              max_interval_seconds: Math.max(pos(volume.minIntervalSeconds), pos(volume.maxIntervalSeconds)),
            },
          }
        : {}),
      ...(stop_conditions ? { stop_conditions } : {}),
      ...(hedging?.enabled ? { hedging_engine: hedgingEngineFor(hedging) } : {}),
    }
  })
  return { configuration_type: 'market_making', pair_settings }
}

/** How many of a `levels`-order ladder sit on the buy side, given where the
 *  current price falls in the range (0 = at the lower bound, 100 = at the
 *  upper bound). The sell side takes the remainder, so the two always sum to
 *  `levels` — that is the whole contract.
 *
 *  The index is rounded to 9 decimals before flooring so FP noise in the
 *  caller's division can't shift the split by a whole level (e.g.
 *  (0.3-0.2)/(0.4-0.2) is 0.49999999999999994, not 0.5).
 *
 *  Exported so a caller's own preview UI shows exactly what gets submitted. */
export function gridBuyCount(positionPct: number, levels: number): number {
  const ratio = Math.min(1, Math.max(0, positionPct / 100))
  return Math.min(levels, Math.floor(Math.round(ratio * levels * 1e9) / 1e9))
}

export function buildGridConfig(input: GridInput): TradingTentaclesConfiguration {
  const symbol = input.pairs[0] ?? ''
  const trailing: GridTrailingInput = {
    enableTrailingUp:     input.enableTrailingUp,
    orderByOrderTrailing: input.orderByOrderTrailing,
  }
  // Raw ladder params (advanced mode / edit rehydration) win over the range
  // derivation — the only path that can express flat_spread ≠ flat_increment.
  if (
    input.flatSpread != null && input.flatIncrement != null
    && input.buyOrdersCount != null && input.sellOrdersCount != null
  ) {
    return {
      configuration_type: 'trading_tentacles',
      name: 'GridTradingMode',
      config: {
        pair_settings: [
          gridPairSettings(
            symbol,
            pos(input.flatSpread),
            pos(input.flatIncrement),
            count(input.buyOrdersCount),
            count(input.sellOrdersCount),
            trailing,
          ),
        ],
      },
    }
  }
  const lower = input.lower ?? null
  const upper = input.upper ?? null
  const levels = input.levels ?? null
  // `levels` counts orders, so 1 is a degenerate but representable ladder — an
  // edit rehydrating a 0-buy/1-sell grid must round-trip through here. Only a
  // zero-order ladder is unconfigured.
  if (lower == null || upper == null || levels == null || !(upper > lower) || levels < 1) {
    // Drafts that never visited the strategy step (template path) fall back to
    // a zeroed pair_settings entry rather than inventing a ladder.
    return {
      configuration_type: 'trading_tentacles',
      name: 'GridTradingMode',
      config: { pair_settings: [gridPairSettings(symbol, 0, 0, 0, 0, trailing)] },
    }
  }
  // Ladder step: consecutive same-side orders sit one step apart,
  // quote-denominated. `levels` orders occupy `levels + 1` price lines across
  // the range (the line the current price sits on carries no order), so the
  // range divides into exactly `levels` intervals. A micro-range whose step
  // rounds to zero is unconfigurable — treat as unset.
  const step = round8((upper - lower) / levels)
  if (!(step > 0)) {
    return {
      configuration_type: 'trading_tentacles',
      name: 'GridTradingMode',
      config: { pair_settings: [gridPairSettings(symbol, 0, 0, 0, 0, trailing)] },
    }
  }
  const price = input.currentPrice ?? null
  // Buys below the current price, sells above — the exact split a preview
  // should display. Out-of-range or missing price → symmetric split.
  const positionPct = price != null && price >= lower && price <= upper
    ? ((price - lower) / (upper - lower)) * 100
    : 50
  const buyCount = gridBuyCount(positionPct, levels)
  // Spread defaults to 2x the increment (step) — a bare spread == increment
  // ladder has zero profit margin per round-trip.
  return {
    configuration_type: 'trading_tentacles',
    name: 'GridTradingMode',
    config: {
      pair_settings: [
        gridPairSettings(symbol, round8(step * 2), step, buyCount, levels - buyCount, trailing),
      ],
    },
  }
}

export function buildDCAConfig(input: DcaInput): TradingTentaclesConfiguration {
  const amount = input.buyOrderAmount?.trim()
  return {
    configuration_type: 'trading_tentacles',
    name: 'DCATradingMode',
    config: {
      trigger_mode:                     DCA_TRIGGER_MODE_TIME_BASED,
      minutes_before_next_buy:          Math.max(1, Math.round(num(input.minutesBeforeNextBuy) || DCA_DEFAULTS.minutes_before_next_buy)),
      buy_order_amount:                 amount || DCA_DEFAULTS.buy_order_amount,
      use_market_entry_orders:          input.useMarketEntry ?? DCA_DEFAULTS.use_market_entry_orders,
      entry_limit_orders_price_percent: input.entryLimitPricePercent != null
        ? pos(input.entryLimitPricePercent)
        : DCA_DEFAULTS.entry_limit_orders_price_percent,
      use_take_profit_exit_orders:      input.useTakeProfit ?? DCA_DEFAULTS.use_take_profit_exit_orders,
      exit_limit_orders_price_percent:  input.exitLimitPricePercent != null
        ? pos(input.exitLimitPricePercent)
        : DCA_DEFAULTS.exit_limit_orders_price_percent,
      trading_pairs:                    input.pairs,
    },
  }
}

export function buildIndexConfig(input: IndexInput): TradingTentaclesConfiguration {
  const weights = input.basketWeights ?? {}
  // index_content values are raw relative weights (70/30), not normalised
  // fractions — the node computes each coin's ratio from the sum itself.
  const index_content = input.pairs.map((p) => {
    const symbol = p.includes('/') ? p.split('/')[0] : p
    return { name: symbol, value: weights[symbol] ?? 0 }
  })
  return {
    configuration_type: 'trading_tentacles',
    name: 'IndexTradingMode',
    config: {
      index_content,
      rebalance_trigger_min_percent: input.rebalanceTriggerPct ?? INDEX_DEFAULTS.rebalance_trigger_min_percent,
    },
  }
}

export function buildCopyConfig(input: CopyInput): CopyConfiguration {
  return { configuration_type: 'copy', strategy_id: input.sourceId ?? '' }
}

export function buildSignalConfig(input: SignalInput): GenericProcessConfiguration {
  const signal: SignalProfileData['signal'] = {
    version: 1,
    webhook: { id: input.webhookId, secret: input.webhookSecret },
    pair:    input.pair,
    side: {
      mode: input.sideMode,
      ...(input.sideMode === 'payload' && input.sidePayloadField
        ? { payload_field: input.sidePayloadField }
        : {}),
    },
    order: {
      type: input.orderType,
      ...(input.orderType === 'limit'
        ? {
            limit_offset_bp:        num(input.limitOffsetBp),
            limit_offset_direction: input.limitOffsetDir ?? 'below',
          }
        : {}),
    },
    size: { mode: input.sizeMode, value: num(input.sizeValue) },
    ...(input.tpEnabled ? { take_profit_percent: num(input.tpPct) } : {}),
    ...(input.slEnabled ? { stop_loss_percent: num(input.slPct) } : {}),
  }
  return { configuration_type: 'generic_process', profile_data: { signal } }
}

// Validates every field the inverse reads unguarded — a partial payload from
// a foreign producer or older schema must fall through to 'custom', not throw
// (or worse: round-trip an undefined webhook secret into a re-emitted config).
export function isSignalProfileData(data: unknown): data is SignalProfileData {
  const signal = (data as SignalProfileData | null | undefined)?.signal
  return typeof signal?.webhook?.id === 'string'
    && typeof signal.webhook.secret === 'string'
    && typeof signal.pair === 'string'
    && typeof signal.side?.mode === 'string'
    && typeof signal.order?.type === 'string'
    && typeof signal.size?.mode === 'string'
    && typeof signal.size.value === 'number'
}

export function signalProfileDataToInput(data: SignalProfileData): SignalInput {
  const s = data.signal
  return {
    webhookId:     s.webhook.id,
    webhookSecret: s.webhook.secret,
    pair:          s.pair,
    sideMode:      s.side.mode,
    ...(s.side.payload_field ? { sidePayloadField: s.side.payload_field } : {}),
    orderType:     s.order.type,
    ...(s.order.limit_offset_bp != null ? { limitOffsetBp: s.order.limit_offset_bp } : {}),
    ...(s.order.limit_offset_direction ? { limitOffsetDir: s.order.limit_offset_direction } : {}),
    sizeMode:      s.size.mode,
    sizeValue:     s.size.value,
    ...(s.take_profit_percent != null ? { tpEnabled: true, tpPct: s.take_profit_percent } : {}),
    ...(s.stop_loss_percent != null ? { slEnabled: true, slPct: s.stop_loss_percent } : {}),
  }
}

/** Subset of {@link MmInput} that the inverse adapter (./patch.ts) populates
 *  from a protocol Strategy. */
export type MmInputPatch = {
  /** Venue from the running config — the edit flow's fallback when the bot's
   *  account can no longer be resolved at Apply time. */
  exchange?: string
  spreadBp?: string | number
  perSide?: string | number
  sizeBase?: string | number
  shape?: MmInput['shape']
  budgetByPair?: Record<string, MmBudgetPairInput>
  stopsByPair?: Record<string, MmStopsPairInput>
  volumeByPair?: Record<string, MmVolumePairInput>
  hedgingByPair?: Record<string, MmHedgingPairInput>
  orderBookByPair?: Record<string, MmOrderBookPairInput>
}

export function buildGenericProcessConfig(): GenericProcessConfiguration {
  return { configuration_type: 'generic_process', profile_data: {} as Record<string, never> }
}
