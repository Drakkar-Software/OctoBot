import type { Strategy } from '@drakkar.software/octobot-protocol'
import {
  isSignalProfileData,
  signalProfileDataToInput,
  DCA_DEFAULTS,
  GRID_INPUT_DEFAULTS,
  type MmInputPatch,
  type MmBudgetPairInput,
  type MmStopsPairInput,
  type MmVolumePairInput,
  type MmHedgingPairInput,
  type MmOrderBookPairInput,
  type IndexInput,
  type CopyInput,
  type SignalInput,
  type MmRefInput,
} from './builders.js'

// The inverse of ./build.ts: protocol Strategy -> editable local input, plus
// incremental version bumping. Deliberately a separate module from
// construction — an editor reads through here, a creator writes through
// build.ts, and the two rarely change together.

/** Grid ladder geometry recovered from a protocol config. The absolute price
 *  bounds are not stored in GridConfiguration — an edit UI renders this raw
 *  geometry directly (advanced mode) and derives display bounds from the
 *  live price. */
export type GridGeometryPatch = {
  spread: number
  increment: number
  buyCount: number
  sellCount: number
  levels: number
  enableTrailingUp: boolean
  orderByOrderTrailing: boolean
}

export type DcaPatch = {
  /** Verbatim protocol amount string ('10%t' / '25q' / '0.1'). */
  buyOrderAmount: string
  minutesBeforeNextBuy: number
  useMarketEntry: boolean
  entryLimitPricePercent: number
  useTakeProfit: boolean
  exitLimitPricePercent: number
}

export type StrategyInputPatch = (
  | { kind: 'mm';     mm:     MmInputPatch; pairs: string[]; refsByPair: Record<string, MmRefInput[]> }
  | { kind: 'grid';   pairs: string[]; grid: GridGeometryPatch | null }
  | { kind: 'dca';    pairs: string[]; dca: DcaPatch | null }
  | { kind: 'basket'; pairs: string[]; basket: IndexInput }
  | { kind: 'copy';   copy: CopyInput }
  | { kind: 'signal'; signal: SignalInput }
  | { kind: 'custom' }
)

/** `TradingTentaclesConfiguration.symbols` was dropped from the protocol —
 *  the node resolves traded symbols from the trading mode's own config. New
 *  configs no longer emit it, but strategies written before that still carry
 *  it, so rehydration keeps reading it as a fallback. */
function legacySymbols(cfg: object): string[] {
  const symbols = (cfg as { symbols?: unknown }).symbols
  return Array.isArray(symbols) ? symbols.filter((s): s is string => typeof s === 'string') : []
}

/** Cadence an older builder encoded as a time_frames entry, in minutes. */
const LEGACY_DCA_TIMEFRAME_MINUTES: Record<string, number> = {
  '1d': 1_440,
  '3d': 4_320,
  '1w': 10_080,
}

/** Recover an editable `StrategyInputPatch` from a protocol `Strategy`. The
 *  inverse of `buildStrategy` in ./build.ts, tolerant of configs written by
 *  older or foreign clients (never throws — unrecognized shapes fall to
 *  `{ kind: 'custom' }`). */
export function protocolStrategyToInput(strategy: Strategy): StrategyInputPatch {
  const cfg = strategy.configuration
  switch (cfg.configuration_type) {
    case 'market_making': {
      const first = cfg.pair_settings[0]
      const refsByPair: Record<string, MmRefInput[]> = {}
      const budgetByPair: Record<string, MmBudgetPairInput> = {}
      const stopsByPair: Record<string, MmStopsPairInput> = {}
      const volumeByPair: Record<string, MmVolumePairInput> = {}
      const hedgingByPair: Record<string, MmHedgingPairInput> = {}
      const orderBookByPair: Record<string, MmOrderBookPairInput> = {}
      for (const p of cfg.pair_settings) {
        refsByPair[p.trading_pair] = p.reference_price.map((r) => ({
          pair:      r.pair,
          formula:   r.formula ?? undefined,
          timeframe: (r.time_frame as string | undefined) ?? '1h',
          weight:    r.weight ?? 1,
          // Preserve cross-venue references across the edit round-trip; the
          // bot's own venue stays implicit (re-stamped at build time).
          ...(r.exchange && r.exchange !== p.exchange ? { exchange: r.exchange } : {}),
        }))
        // A pair carries a real budget configuration when a bound beyond the
        // legacy max_base_budget echo is set — an old builder always echoed
        // sizeBase into max_quote_budget, so a bare equal max_quote_budget with
        // no min floor is ambiguous and treated as "no budget" for that pair.
        if (p.max_quote_budget != null
          && (p.max_quote_budget !== p.max_base_budget || p.min_base_budget != null || p.min_quote_budget != null)) {
          budgetByPair[p.trading_pair] = {
            enabled:  true,
            maxBase:  p.max_base_budget ?? 0,
            maxQuote: p.max_quote_budget,
            minBase:  p.min_base_budget ?? 0,
            minQuote: p.min_quote_budget ?? 0,
          }
        }
        if (p.stop_conditions) {
          const sc = p.stop_conditions
          stopsByPair[p.trading_pair] = {
            enabled:         true,
            minBaseHolding:  sc.min_base_holding ?? 0,
            minQuoteHolding: sc.min_quote_holding ?? 0,
            maxPositivePct:  sc.max_positive_percent_price_change ?? 0,
            maxNegativePct:  sc.max_negative_percent_price_change ?? 0,
            avgPriceMinutes: sc.average_price_counted_minutes ?? 60,
          }
        }
        if (p.scheduled_volume) {
          const v = p.scheduled_volume
          volumeByPair[p.trading_pair] = {
            enabled:            true,
            minAmount:          v.min_amount,
            maxAmount:          v.max_amount,
            minIntervalSeconds: v.min_interval_seconds,
            maxIntervalSeconds: v.max_interval_seconds,
          }
        }
        if (p.hedging_engine) {
          const h = p.hedging_engine
          hedgingByPair[p.trading_pair] = {
            enabled:          true,
            exchange:         h.hedging_exchange ?? '',
            maxLossThreshold: h.hedging_max_loss_threshold ?? 0,
            avgPriceMinutes:  h.average_price_counted_minutes ?? 60,
            maxNegativePct:   h.max_negative_percent_price_change ?? 0,
            maxPositivePct:   h.max_positive_percent_price_change ?? 0,
          }
        }
        // Always present on the protocol (not optional like stop_conditions),
        // so populated unconditionally for every pair — round to 6 decimals
        // of a bp same as spreadBp above (min_spread*100 picks up FP noise).
        orderBookByPair[p.trading_pair] = {
          minSpreadBp:               String(Math.round(p.min_spread * 100 * 1e6) / 1e6),
          maxSpreadBp:                String(Math.round(p.max_spread * 100 * 1e6) / 1e6),
          bidsCount:                  String(p.bids_count ?? 0),
          asksCount:                  String(p.asks_count ?? 0),
          ordersDistribution:         p.orders_distribution ?? 'linear',
          fundsDistribution:          p.funds_distribution ?? 'flat',
          cumulatedVolumePercent:     String(p.order_book_depth?.cumulated_volume_percent ?? 1),
          percentDailyTradingVolume:  String(p.order_book_depth?.percent_daily_trading_volume ?? 1),
        }
      }
      // sizeBase is the bot-wide fallback max_base_budget used for pairs with
      // no per-pair budget override — it must be read from one of THOSE
      // pairs, not pairs[0] blindly. pairs[0] may itself carry a per-pair
      // override, in which case its max_base_budget is unrelated to the
      // shared fallback and recovering sizeBase from it would corrupt every
      // other budget-disabled pair on the next build. Every fallback pair
      // shares the same baseSize by construction, so the first one found is
      // authoritative.
      //
      // sizeBase is NOT purely inert when no fallback pair exists (every pair
      // has its own override): an editor may also display/edit it directly
      // as an "size per order" field, and if the user later disables any
      // pair's override in the same edit session, this recovered value
      // becomes that pair's new real budget. Picking an arbitrary pair's own
      // override there risks silently inflating a newly-disabled pair to an
      // unrelated pair's cap — using the smallest override across all pairs
      // instead bounds that risk to under- rather than over-allocating.
      const fallbackBudgetPair = cfg.pair_settings.find((p) => !(p.trading_pair in budgetByPair))
      const smallestOverride = cfg.pair_settings.reduce<number | undefined>((min, p) => {
        const v = p.max_base_budget
        return v != null && (min == null || v < min) ? v : min
      }, undefined)
      return {
        kind: 'mm',
        pairs: cfg.pair_settings.map((p) => p.trading_pair),
        refsByPair,
        mm: {
          // min_spread is spreadBp/100; multiplying back picks up FP noise
          // (0.07 * 100 === 7.000000000000001) — round to 6 decimals of a bp.
          spreadBp: String(Math.round((first?.min_spread ?? 0) * 100 * 1e6) / 1e6),
          perSide:  String(first?.bids_count ?? 0),
          sizeBase: String(fallbackBudgetPair?.max_base_budget ?? smallestOverride ?? first?.max_base_budget ?? 0),
          shape:    first?.funds_distribution === 'valley' ? 'expo'
            : first?.funds_distribution === 'random' ? 'random'
            : 'flat',
          exchange: first?.exchange,
          ...(Object.keys(budgetByPair).length    > 0 ? { budgetByPair }    : {}),
          ...(Object.keys(stopsByPair).length     > 0 ? { stopsByPair }     : {}),
          ...(Object.keys(volumeByPair).length    > 0 ? { volumeByPair }    : {}),
          ...(Object.keys(hedgingByPair).length   > 0 ? { hedgingByPair }   : {}),
          ...(Object.keys(orderBookByPair).length > 0 ? { orderBookByPair } : {}),
        },
      }
    }
    case 'trading_tentacles': {
      // The `name` field identifies the specific trading mode within the
      // generic trading_tentacles configuration_type.
      type IndexConfig = { index_content?: Array<{ name: string; value: number }>; rebalance_trigger_min_percent?: number }
      switch (cfg.name) {
        case 'GridTradingMode': {
          type GridPairSetting = {
            pair?: string
            flat_spread?: number
            flat_increment?: number
            buy_orders_count?: number
            sell_orders_count?: number
            enable_trailing_up?: boolean
            order_by_order_trailing?: boolean
          }
          type GridConfig = { pair_settings?: GridPairSetting[] }
          const c = cfg.config as GridConfig
          const ps: GridPairSetting = c.pair_settings?.[0] ?? {}
          // `levels` counts orders, not price lines — see GridInput.levels.
          const levels = (ps.buy_orders_count ?? 0) + (ps.sell_orders_count ?? 0)
          const configured = (ps.flat_spread ?? 0) > 0 || (ps.flat_increment ?? 0) > 0
          return {
            kind: 'grid',
            pairs: ps.pair ? [ps.pair] : legacySymbols(cfg),
            grid: configured
              ? {
                  spread:    ps.flat_spread ?? 0,
                  increment: ps.flat_increment ?? 0,
                  buyCount:  ps.buy_orders_count ?? 0,
                  sellCount: ps.sell_orders_count ?? 0,
                  levels,
                  // Mirrors gridPairSettings' own emit defaults, so configs
                  // written before these fields existed rehydrate to what
                  // they actually ran with.
                  enableTrailingUp:     ps.enable_trailing_up ?? GRID_INPUT_DEFAULTS.enableTrailingUp,
                  orderByOrderTrailing: ps.order_by_order_trailing ?? GRID_INPUT_DEFAULTS.orderByOrderTrailing,
                }
              : null,
          }
        }
        case 'DCATradingMode': {
          type DcaConfig = {
            trading_pairs?: string[]
            buy_order_amount?: string | number
            minutes_before_next_buy?: number
            use_market_entry_orders?: boolean
            entry_limit_orders_price_percent?: number
            use_take_profit_exit_orders?: boolean
            exit_limit_orders_price_percent?: number
            time_frames?: string[]
          }
          const c = cfg.config as DcaConfig
          // Prefer whichever list actually has pairs, rather than `??`: that
          // only falls through on null/undefined, so a `symbols: []`
          // alongside a populated `config.trading_pairs` would rehydrate the
          // draft with no pairs. Applying that draft re-emits
          // `trading_pairs: []`, and the node — which resolves DCA's traded
          // symbols from `config.trading_pairs` and ignores the top-level
          // `symbols` entirely — then rejects it with "Traded symbols cannot
          // be empty".
          const legacy = legacySymbols(cfg)
          const symbols = legacy.length ? legacy : (c.trading_pairs ?? [])
          const rawAmount = c.buy_order_amount
          const buyOrderAmount = typeof rawAmount === 'number'
            ? `${rawAmount}%t`
            : rawAmount?.trim() || DCA_DEFAULTS.buy_order_amount
          // Legacy configs (pre minutes_before_next_buy) carried cadence in
          // time_frames — map the old '1d'/'3d'/'1w' emission back to minutes.
          const legacyTf = c.time_frames?.[0]
          const legacyMinutes = legacyTf != null ? LEGACY_DCA_TIMEFRAME_MINUTES[legacyTf] ?? null : null
          return {
            kind: 'dca',
            pairs: symbols,
            dca: {
              buyOrderAmount,
              minutesBeforeNextBuy: c.minutes_before_next_buy
                ?? legacyMinutes
                ?? DCA_DEFAULTS.minutes_before_next_buy,
              useMarketEntry:         c.use_market_entry_orders ?? DCA_DEFAULTS.use_market_entry_orders,
              entryLimitPricePercent: c.entry_limit_orders_price_percent ?? DCA_DEFAULTS.entry_limit_orders_price_percent,
              useTakeProfit:          c.use_take_profit_exit_orders ?? DCA_DEFAULTS.use_take_profit_exit_orders,
              exitLimitPricePercent:  c.exit_limit_orders_price_percent ?? DCA_DEFAULTS.exit_limit_orders_price_percent,
            },
          }
        }
        case 'IndexTradingMode': {
          // index_content values are raw relative weights. Configs written by
          // an older builder stored 0–1 fractions instead — a sum at (or
          // below) 1 is unmistakably that legacy shape (a real weight set
          // summing to 1 is scale-invariant anyway), so rescale it to percent.
          const c = cfg.config as IndexConfig
          const coins = c.index_content ?? []
          const rawTotal = coins.reduce((s, coin) => s + coin.value, 0)
          const scale = rawTotal > 0 && rawTotal <= 1.000001 ? 100 : 1
          const basketWeights: Record<string, number> = {}
          for (const coin of coins) basketWeights[coin.name] = Math.round(coin.value * scale * 1e6) / 1e6
          return {
            kind: 'basket',
            pairs: coins.map((coin) => coin.name),
            basket: {
              pairs: coins.map((coin) => coin.name),
              basketWeights,
              basketTotal: Math.round(rawTotal * scale * 1e6) / 1e6,
              rebalanceTriggerPct: c.rebalance_trigger_min_percent,
            },
          }
        }
        default:
          return { kind: 'custom' }
      }
    }
    case 'copy':
      return { kind: 'copy', copy: { sourceId: cfg.strategy_id } }
    case 'generic_process':
      return isSignalProfileData(cfg.profile_data)
        ? { kind: 'signal', signal: signalProfileDataToInput(cfg.profile_data) }
        : { kind: 'custom' }
    default:
      return { kind: 'custom' }
  }
}

/** Bump a semver-ish `MAJOR.MINOR.PATCH` string's patch component by one,
 *  zero-filling any missing component. */
export function bumpStrategyPatchVersion(version: string): string {
  const parts = version.split('.').map((n) => Number.parseInt(n, 10))
  while (parts.length < 3) parts.push(0)
  const patch = Number.isFinite(parts[2]) ? parts[2] + 1 : 1
  return `${parts[0] || 0}.${parts[1] || 0}.${patch}`
}
