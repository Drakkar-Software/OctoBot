import { describe, it, expect } from 'vitest'
import {
  buildMarketMakingConfig,
  buildGridConfig,
  gridBuyCount,
  buildDCAConfig,
  buildIndexConfig,
  buildCopyConfig,
  buildSignalConfig,
  buildGenericProcessConfig,
  isSignalProfileData,
  signalProfileDataToInput,
  buildStrategy as buildProtocolStrategy,
  protocolStrategyToInput,
  bumpStrategyPatchVersion,
  buildAutomationConfiguration,
  buildCreateAutomationConfig,
  buildEditAutomationConfig,
  buildStopAutomationConfig,
  newUserActionId,
  type MmInput,
  type SignalInput,
} from '../src/protocol/index.js'

describe('strategyConfig builders', () => {
  describe('buildMarketMakingConfig', () => {
    const baseInput: MmInput = {
      exchange:  'binance',
      pairs:     ['BTC/USDT'],
      refsByPair: {},
      spreadBp:  '50',
      perSide:   '3',
      sizeBase:  '100',
      shape:     'flat',
    }

    it('emits configuration_type market_making', () => {
      const cfg = buildMarketMakingConfig(baseInput)
      expect(cfg.configuration_type).toBe('market_making')
    })

    it('converts basis-point spread to fractional spread', () => {
      // 50bp → 0.5% → 0.5 in protocol units (spreadBp/100)
      const cfg = buildMarketMakingConfig(baseInput)
      expect(cfg.pair_settings[0].min_spread).toBe(0.5)
      expect(cfg.pair_settings[0].max_spread).toBe(1)
    })

    it('falls back to quoting the traded pair on its own venue when no refs supplied', () => {
      const cfg = buildMarketMakingConfig(baseInput)
      expect(cfg.pair_settings[0].reference_price).toEqual([
        { exchange: 'binance', pair: 'BTC/USDT', weight: 1 },
      ])
    })

    it('maps shape=flat to funds_distribution=flat', () => {
      const cfg = buildMarketMakingConfig({ ...baseInput, shape: 'flat' })
      expect(cfg.pair_settings[0].funds_distribution).toBe('flat')
    })

    it('maps shape=expo to funds_distribution=valley', () => {
      const cfg = buildMarketMakingConfig({ ...baseInput, shape: 'expo' })
      expect(cfg.pair_settings[0].funds_distribution).toBe('valley')
    })

    it('maps shape=custom to funds_distribution=random', () => {
      const cfg = buildMarketMakingConfig({ ...baseInput, shape: 'custom' })
      expect(cfg.pair_settings[0].funds_distribution).toBe('random')
    })

    it('forwards user-supplied refs preserving weight/formula/timeframe', () => {
      const cfg = buildMarketMakingConfig({
        ...baseInput,
        refsByPair: {
          'BTC/USDT': [
            { pair: 'BTC/USD', weight: 0.7, formula: 'mid', timeframe: '1m' },
            { pair: 'ETH/USDT', weight: 0.3 },
          ],
        },
      })
      expect(cfg.pair_settings[0].reference_price).toEqual([
        { exchange: 'binance', pair: 'BTC/USD',  weight: 0.7, formula: 'mid',     time_frame: '1m' },
        { exchange: 'binance', pair: 'ETH/USDT', weight: 0.3, formula: undefined, time_frame: undefined },
      ])
    })

    it('emits zero min_spread when spreadBp parses to NaN', () => {
      const cfg = buildMarketMakingConfig({ ...baseInput, spreadBp: 'not-a-number' })
      expect(cfg.pair_settings[0].min_spread).toBe(0)
      expect(cfg.pair_settings[0].max_spread).toBe(0)
    })
  })

  describe('buildGridConfig / buildDCAConfig / buildCopyConfig', () => {
    it('grid takes the first pair as symbol in pair_settings[0].pair', () => {
      const cfg = buildGridConfig({ pairs: ['BTC/USDT', 'ETH/USDT'] })
      expect(cfg.configuration_type).toBe('trading_tentacles')
      expect(cfg.name).toBe('GridTradingMode')
      expect((cfg.config as { pair_settings: Array<{ pair: string }> }).pair_settings[0].pair).toBe('BTC/USDT')
    })

    it('grid emits empty pair when no pairs supplied', () => {
      const cfg = buildGridConfig({ pairs: [] })
      expect((cfg.config as { pair_settings: Array<{ pair: string }> }).pair_settings[0].pair).toBe('')
    })

    it('dca forwards all pairs as the trading mode\'s own traded pairs', () => {
      // The protocol dropped the top-level `symbols`; the node resolves DCA's
      // traded symbols from `config.trading_pairs`.
      const cfg = buildDCAConfig({ pairs: ['BTC/USDT', 'ETH/USDT'] })
      expect((cfg.config as { trading_pairs?: string[] }).trading_pairs).toEqual(['BTC/USDT', 'ETH/USDT'])
    })

    it('copy forwards sourceId; defaults to empty string when null', () => {
      expect(buildCopyConfig({ sourceId: 's_42' }).strategy_id).toBe('s_42')
      expect(buildCopyConfig({ sourceId: null }).strategy_id).toBe('')
      expect(buildCopyConfig({}).strategy_id).toBe('')
    })
  })

  describe('buildIndexConfig', () => {
    it('emits raw relative weights in index_content', () => {
      const cfg = buildIndexConfig({
        pairs: ['BTC/USDT', 'ETH/USDT'],
        basketWeights: { BTC: 60, ETH: 40 },
        basketTotal: 100,
      })
      const content = (cfg.config as { index_content: Array<{ name: string; value: number }> }).index_content
      expect(content).toEqual([
        { name: 'BTC', value: 60 },
        { name: 'ETH', value: 40 },
      ])
    })

    it('defaults rebalance_trigger_min_percent to 5 and passes explicit values through', () => {
      const dflt = buildIndexConfig({ pairs: ['BTC'], basketWeights: { BTC: 100 } })
      expect((dflt.config as { rebalance_trigger_min_percent: number }).rebalance_trigger_min_percent).toBe(5)
      const explicit = buildIndexConfig({ pairs: ['BTC'], basketWeights: { BTC: 100 }, rebalanceTriggerPct: 4 })
      expect((explicit.config as { rebalance_trigger_min_percent: number }).rebalance_trigger_min_percent).toBe(4)
    })

    it('strips base symbol from "BASE/QUOTE" pair when extracting coin name', () => {
      const cfg = buildIndexConfig({ pairs: ['BTC/USDT'], basketWeights: { BTC: 100 }, basketTotal: 100 })
      const content = (cfg.config as { index_content: Array<{ name: string }> }).index_content
      expect(content[0].name).toBe('BTC')
    })
  })

  describe('buildGenericProcessConfig', () => {
    it('emits empty profile_data record', () => {
      expect(buildGenericProcessConfig().configuration_type).toBe('generic_process')
    })
  })
})

describe('buildProtocolStrategy + protocolStrategyToInput round-trip', () => {
  it('grid round-trip preserves the symbol', () => {
    const strat = buildProtocolStrategy({ kind: 'grid', grid: { pairs: ['BTC/USDT'] } })
    const back = protocolStrategyToInput(strat)
    expect(back.kind).toBe('grid')
    if (back.kind === 'grid') expect(back.pairs).toEqual(['BTC/USDT'])
  })

  it('dca round-trip preserves all symbols', () => {
    const strat = buildProtocolStrategy({ kind: 'dca', dca: { pairs: ['BTC/USDT', 'ETH/USDT'] } })
    const back = protocolStrategyToInput(strat)
    expect(back.kind).toBe('dca')
    if (back.kind === 'dca') expect(back.pairs).toEqual(['BTC/USDT', 'ETH/USDT'])
  })

  it('basket round-trip restores weights on the wizard percent scale', () => {
    const strat = buildProtocolStrategy({
      kind: 'basket',
      basket: { pairs: ['BTC', 'ETH'], basketWeights: { BTC: 70, ETH: 30 }, basketTotal: 100 },
    })
    const back = protocolStrategyToInput(strat)
    expect(back.kind).toBe('basket')
    if (back.kind === 'basket') {
      expect(back.basket.basketWeights).toEqual({ BTC: 70, ETH: 30 })
      expect(back.basket.basketTotal).toBe(100)
    }
  })

  it('mm round-trip preserves spreadBp scale (basis points)', () => {
    const strat = buildProtocolStrategy({
      kind: 'mm',
      mm: {
        exchange: 'binance', pairs: ['BTC/USDT'], refsByPair: {},
        spreadBp: '100', perSide: '5', sizeBase: '50', shape: 'flat',
      },
    })
    const back = protocolStrategyToInput(strat)
    expect(back.kind).toBe('mm')
    if (back.kind === 'mm') expect(back.mm.spreadBp).toBe('100')
  })

  it('default id contains a random suffix', () => {
    const a = buildProtocolStrategy({ kind: 'custom' })
    const b = buildProtocolStrategy({ kind: 'custom' })
    expect(a.id).not.toBe(b.id)
  })

  it('honors caller-supplied id, version, name, description', () => {
    const strat = buildProtocolStrategy({ kind: 'custom' }, {
      id: 's_fixed', version: '2.5.0', name: 'My Strategy', description: 'desc',
    })
    expect(strat.id).toBe('s_fixed')
    expect(strat.version).toBe('2.5.0')
    expect(strat.name).toBe('My Strategy')
    expect(strat.description).toBe('desc')
  })
})

describe('referenceMarketOf (Strategy.reference_market is required in 0.4.0)', () => {
  it('derives the quote currency from the traded pair', () => {
    expect(buildProtocolStrategy({ kind: 'grid', grid: { pairs: ['ETH/USDC'] } }).reference_market).toBe('USDC')
    expect(buildProtocolStrategy({
      kind: 'signal',
      signal: { webhookId: 'w', webhookSecret: 's', pair: 'BTC/EUR', sideMode: 'buy', orderType: 'market', sizeMode: 'fixed', sizeValue: 1 },
    }).reference_market).toBe('EUR')
  })

  it('falls back to USDT for pairless kinds and honors the explicit override', () => {
    expect(buildProtocolStrategy({ kind: 'copy', copy: { sourceId: 's' } }).reference_market).toBe('USDT')
    expect(buildProtocolStrategy({ kind: 'grid', grid: { pairs: [] } }).reference_market).toBe('USDT')
    expect(buildProtocolStrategy({ kind: 'custom' }, { referenceMarket: 'BTC' }).reference_market).toBe('BTC')
  })
})

describe('bumpStrategyPatchVersion', () => {
  it('increments only the patch component', () => {
    expect(bumpStrategyPatchVersion('1.2.3')).toBe('1.2.4')
  })
  it('treats missing segments as 0', () => {
    expect(bumpStrategyPatchVersion('1')).toBe('1.0.1')
    expect(bumpStrategyPatchVersion('1.2')).toBe('1.2.1')
  })
  it('coerces non-numeric tail to 1', () => {
    expect(bumpStrategyPatchVersion('1.2.foo')).toBe('1.2.1')
  })
})

describe('userAction builders', () => {
  const strategy = { id: 's_1', version: '1.0.0', configuration: { configuration_type: 'generic_process', profile_data: {} } } as any

  it('newUserActionId returns a unique ua_-prefixed id each call', () => {
    const a = newUserActionId()
    const b = newUserActionId()
    expect(a.startsWith('ua_')).toBe(true)
    expect(a).not.toBe(b)
  })

  it('buildAutomationConfiguration wires name, description, strategy ref, accounts', () => {
    const cfg = buildAutomationConfiguration({
      name: 'Auto-A', description: 'desc', strategy, accountIds: ['acc_1', 'acc_2'],
    })
    expect(cfg.name).toBe('Auto-A')
    expect(cfg.description).toBe('desc')
    expect(cfg.strategy).toEqual({ id: 's_1', version: '1.0.0', emit_signals: false })
    expect(cfg.accounts).toEqual([{ id: 'acc_1' }, { id: 'acc_2' }])
  })

  it('buildCreateAutomationConfig tags action_type=automation_create', () => {
    const c = buildCreateAutomationConfig({ name: 'A', strategy, accountIds: [] })
    expect(c.action_type).toBe('automation_create')
  })

  it('buildEditAutomationConfig carries the target automation id', () => {
    const c = buildEditAutomationConfig({ name: 'A', strategy, accountIds: [], automationId: 'auto_1' })
    expect(c.action_type).toBe('automation_edit')
    expect(c.id).toBe('auto_1')
  })

  it('buildStopAutomationConfig is id-only payload', () => {
    const c = buildStopAutomationConfig('auto_1')
    expect(c).toEqual({ id: 'auto_1', action_type: 'automation_stop' })
  })
})

type GridPairSetting = { pair?: string; flat_spread: number; flat_increment: number; buy_orders_count: number; sell_orders_count: number }
type GridCfg = { pair_settings?: GridPairSetting[] }
const ZERO_PS: GridPairSetting = { flat_spread: 0, flat_increment: 0, buy_orders_count: 0, sell_orders_count: 0 }
const gc = (cfg: ReturnType<typeof buildGridConfig>): GridPairSetting =>
  ((cfg.config as GridCfg).pair_settings?.[0] ?? ZERO_PS)

describe('buildGridConfig ladder math', () => {
  const bounds = { pairs: ['ETH/USDT'], lower: 90, upper: 110, levels: 20 }

  it('derives a quote-denominated step for flat_increment, spread at 2x that step', () => {
    const cfg = buildGridConfig({ ...bounds, currentPrice: 100 })
    expect(gc(cfg).flat_spread).toBe(2)
    expect(gc(cfg).flat_increment).toBe(1)
  })

  it('splits buys/sells at the current price position', () => {
    const cfg = buildGridConfig({ ...bounds, currentPrice: 100 })
    expect(gc(cfg).buy_orders_count).toBe(10)
    expect(gc(cfg).sell_orders_count).toBe(10)
    const low = buildGridConfig({ ...bounds, currentPrice: 95 })
    expect(gc(low).buy_orders_count).toBe(5)
    expect(gc(low).sell_orders_count).toBe(15)
  })

  it('falls back to a symmetric split when price is out of range or missing', () => {
    const out = buildGridConfig({ ...bounds, currentPrice: 200 })
    expect(gc(out).buy_orders_count).toBe(10)
    expect(gc(out).sell_orders_count).toBe(10)
    const none = buildGridConfig(bounds)
    expect(gc(none).buy_orders_count).toBe(10)
  })

  it('total order count is exactly levels', () => {
    const cfg = buildGridConfig({ ...bounds, currentPrice: 93.7 })
    expect(gc(cfg).buy_orders_count + gc(cfg).sell_orders_count).toBe(20)
  })

  it('keeps zeroed pair_settings when bounds are missing or invalid', () => {
    expect(gc(buildGridConfig({ pairs: ['ETH/USDT'] })).flat_spread).toBe(0)
    expect(gc(buildGridConfig({ ...bounds, upper: 80 })).flat_spread).toBe(0)
    expect(gc(buildGridConfig({ ...bounds, levels: 0 })).flat_spread).toBe(0)
  })

  it('is immune to FP noise in the position division (exact mid-price)', () => {
    // (0.3-0.2)/(0.4-0.2) is 0.49999999999999994 in floats — without rounding
    // before floor, the split shifts a whole level to 9/11.
    const cfg = buildGridConfig({ pairs: ['X'], lower: 0.2, upper: 0.4, levels: 20, currentPrice: 0.3 })
    expect(gc(cfg).buy_orders_count).toBe(10)
    expect(gc(cfg).sell_orders_count).toBe(10)
  })

  it('emits one-sided ladders when the price sits on a bound', () => {
    const atUpper = buildGridConfig({ ...bounds, currentPrice: 110 })
    expect(gc(atUpper).buy_orders_count).toBe(20)
    expect(gc(atUpper).sell_orders_count).toBe(0)
    expect(gc(atUpper).flat_spread).toBe(2)
    const atLower = buildGridConfig({ ...bounds, currentPrice: 90 })
    expect(gc(atLower).buy_orders_count).toBe(0)
    expect(gc(atLower).sell_orders_count).toBe(20)
  })

  it('treats a micro-range whose step rounds to zero as unconfigured', () => {
    const cfg = buildGridConfig({ pairs: ['X'], lower: 1, upper: 1 + 1e-9, levels: 20, currentPrice: 1 })
    expect(gc(cfg).flat_spread).toBe(0)
    expect(gc(cfg).buy_orders_count).toBe(0)
    expect(gc(cfg).sell_orders_count).toBe(0)
  })

  it('emits raw ladder params verbatim, spread independent from increment', () => {
    const cfg = buildGridConfig({
      pairs: ['ETH/USDT'],
      flatSpread: 2000, flatIncrement: 500, buyOrdersCount: 10, sellOrdersCount: 20,
    })
    expect(gc(cfg).flat_spread).toBe(2000)
    expect(gc(cfg).flat_increment).toBe(500)
    expect(gc(cfg).buy_orders_count).toBe(10)
    expect(gc(cfg).sell_orders_count).toBe(20)
  })

  it('raw params take precedence over range bounds', () => {
    const cfg = buildGridConfig({
      ...bounds, currentPrice: 100,
      flatSpread: 4, flatIncrement: 2, buyOrdersCount: 3, sellOrdersCount: 7,
    })
    expect(gc(cfg).flat_spread).toBe(4)
    expect(gc(cfg).flat_increment).toBe(2)
    expect(gc(cfg).buy_orders_count).toBe(3)
  })

  it('threads trailing toggles into pair_settings, defaulting both to true', () => {
    type TrailingPs = { enable_trailing_up: boolean; order_by_order_trailing: boolean }
    const ps = (cfg: ReturnType<typeof buildGridConfig>) =>
      (cfg.config as { pair_settings: TrailingPs[] }).pair_settings[0]
    const dflt = buildGridConfig({ ...bounds, currentPrice: 100 })
    expect(ps(dflt).enable_trailing_up).toBe(true)
    expect(ps(dflt).order_by_order_trailing).toBe(true)
    const off = buildGridConfig({
      pairs: ['ETH/USDT'],
      flatSpread: 4, flatIncrement: 2, buyOrdersCount: 3, sellOrdersCount: 7,
      enableTrailingUp: false, orderByOrderTrailing: false,
    })
    expect(ps(off).enable_trailing_up).toBe(false)
    expect(ps(off).order_by_order_trailing).toBe(false)
  })
})

describe('gridBuyCount', () => {
  it('splits a ladder at the price position', () => {
    expect(gridBuyCount(50, 20)).toBe(10)
    expect(gridBuyCount(0, 20)).toBe(0)
    expect(gridBuyCount(100, 20)).toBe(20)
    expect(gridBuyCount(25, 20)).toBe(5)
    expect(gridBuyCount(75, 20)).toBe(15)
  })

  it('gives the odd order to the sell side', () => {
    expect(gridBuyCount(50, 21)).toBe(10)
    expect(gridBuyCount(50, 3)).toBe(1)
  })

  it('is immune to FP noise in the caller position division', () => {
    // (0.3-0.2)/(0.4-0.2)*100 is 49.99999999999999, not 50 — without the
    // pre-round this floors a whole level early.
    const noisy = ((0.3 - 0.2) / (0.4 - 0.2)) * 100
    expect(noisy).not.toBe(50)
    expect(gridBuyCount(noisy, 20)).toBe(10)
  })

  it('clamps a position outside 0..100', () => {
    expect(gridBuyCount(-5, 20)).toBe(0)
    expect(gridBuyCount(120, 20)).toBe(20)
  })
})

describe('grid level count regression', () => {
  // Reported: "grid level 20 gives 9 buy / 10 sell, should be 10 and 10".
  it('levels 20 with a centred price is an even 10 / 10 split', () => {
    const cfg = buildGridConfig({
      pairs: ['ETH/USDT'], lower: 90, upper: 110, levels: 20, currentPrice: 100,
    })
    expect(gc(cfg).buy_orders_count).toBe(10)
    expect(gc(cfg).sell_orders_count).toBe(10)
  })

  it('every wizard preset splits evenly at a centred price', () => {
    for (const levels of [10, 20, 30, 50]) {
      const cfg = buildGridConfig({
        pairs: ['ETH/USDT'], lower: 90, upper: 110, levels, currentPrice: 100,
      })
      expect(gc(cfg).buy_orders_count).toBe(levels / 2)
      expect(gc(cfg).sell_orders_count).toBe(levels / 2)
    }
  })

  it('pins the tie-break for an odd level count (extra order sells)', () => {
    const cfg = buildGridConfig({
      pairs: ['ETH/USDT'], lower: 90, upper: 110, levels: 21, currentPrice: 100,
    })
    expect(gc(cfg).buy_orders_count).toBe(10)
    expect(gc(cfg).sell_orders_count).toBe(11)
  })
})

describe('grid ladder invariants', () => {
  const LOWER = 90
  const UPPER = 110
  const POSITIONS = [0, 12.5, 25, 33.33, 50, 66.67, 75, 100]
  const priceAt = (pct: number) => LOWER + ((UPPER - LOWER) * pct) / 100
  const build = (levels: number, currentPrice: number | undefined) =>
    gc(buildGridConfig({ pairs: ['ETH/USDT'], lower: LOWER, upper: UPPER, levels, currentPrice }))

  it('buy + sell always equals levels', () => {
    for (let levels = 2; levels <= 60; levels++) {
      for (const pct of POSITIONS) {
        const ps = build(levels, priceAt(pct))
        expect(`${levels}@${pct}: ${ps.buy_orders_count + ps.sell_orders_count}`)
          .toBe(`${levels}@${pct}: ${levels}`)
      }
    }
  })

  it('the range divides into exactly `levels` increments', () => {
    for (let levels = 2; levels <= 60; levels++) {
      const ps = build(levels, 100)
      expect(ps.flat_increment * levels).toBeCloseTo(UPPER - LOWER, 6)
      expect(ps.flat_spread).toBeCloseTo(ps.flat_increment * 2, 8)
    }
  })

  it('buy count rises monotonically as the price rises through the range', () => {
    let previous = -1
    for (const pct of POSITIONS) {
      const ps = build(20, priceAt(pct))
      expect(ps.buy_orders_count).toBeGreaterThanOrEqual(previous)
      previous = ps.buy_orders_count
    }
  })

  it('goes fully one-sided when the price sits on a bound', () => {
    for (let levels = 2; levels <= 60; levels++) {
      const atUpper = build(levels, UPPER)
      expect(atUpper.buy_orders_count).toBe(levels)
      expect(atUpper.sell_orders_count).toBe(0)
      const atLower = build(levels, LOWER)
      expect(atLower.buy_orders_count).toBe(0)
      expect(atLower.sell_orders_count).toBe(levels)
    }
  })

  it('out-of-range and missing prices both fall back to the same symmetric split', () => {
    for (const levels of [10, 20, 21, 30]) {
      const below = build(levels, LOWER - 50)
      const above = build(levels, UPPER + 50)
      const missing = build(levels, undefined)
      expect(below).toEqual(missing)
      expect(above).toEqual(missing)
      expect(missing.buy_orders_count + missing.sell_orders_count).toBe(levels)
      expect(missing.buy_orders_count).toBe(Math.floor(levels / 2))
    }
  })
})

type DcaCfg = {
  trading_pairs?: string[]
  buy_order_amount: string
  minutes_before_next_buy: number
  trigger_mode: string
  use_market_entry_orders: boolean
  entry_limit_orders_price_percent: number
  use_take_profit_exit_orders: boolean
  exit_limit_orders_price_percent: number
}
const dc = (cfg: ReturnType<typeof buildDCAConfig>) => cfg.config as DcaCfg

describe('buildDCAConfig params', () => {
  it('always emits the time-based trigger mode', () => {
    expect(dc(buildDCAConfig({ pairs: [] })).trigger_mode).toBe('Time based')
  })

  it('emits the amount string verbatim', () => {
    expect(dc(buildDCAConfig({ pairs: [], buyOrderAmount: '10%t' })).buy_order_amount).toBe('10%t')
    expect(dc(buildDCAConfig({ pairs: [], buyOrderAmount: '25q' })).buy_order_amount).toBe('25q')
    expect(dc(buildDCAConfig({ pairs: [], buyOrderAmount: '0.1' })).buy_order_amount).toBe('0.1')
  })

  it('defaults amount to 10%t and cadence to weekly (10080 min)', () => {
    const cfg = dc(buildDCAConfig({ pairs: [] }))
    expect(cfg.buy_order_amount).toBe('10%t')
    expect(cfg.minutes_before_next_buy).toBe(10080)
  })

  it('emits the buy interval in minutes, floored at 1 whole minute', () => {
    expect(dc(buildDCAConfig({ pairs: [], minutesBeforeNextBuy: 1440 })).minutes_before_next_buy).toBe(1440)
    expect(dc(buildDCAConfig({ pairs: [], minutesBeforeNextBuy: 0.4 })).minutes_before_next_buy).toBe(1)
    expect(dc(buildDCAConfig({ pairs: [], minutesBeforeNextBuy: 1440.6 })).minutes_before_next_buy).toBe(1441)
  })

  it('emits entry order type and limit percent', () => {
    const market = dc(buildDCAConfig({ pairs: [], useMarketEntry: true }))
    expect(market.use_market_entry_orders).toBe(true)
    const limit = dc(buildDCAConfig({ pairs: [], useMarketEntry: false, entryLimitPricePercent: 1.5 }))
    expect(limit.use_market_entry_orders).toBe(false)
    expect(limit.entry_limit_orders_price_percent).toBe(1.5)
    expect(dc(buildDCAConfig({ pairs: [] })).entry_limit_orders_price_percent).toBe(1)
  })

  it('emits take-profit exit toggle and percent', () => {
    const on = dc(buildDCAConfig({ pairs: [], useTakeProfit: true, exitLimitPricePercent: '4.5' }))
    expect(on.use_take_profit_exit_orders).toBe(true)
    expect(on.exit_limit_orders_price_percent).toBe(4.5)
    const off = dc(buildDCAConfig({ pairs: [], useTakeProfit: false }))
    expect(off.use_take_profit_exit_orders).toBe(false)
    expect(dc(buildDCAConfig({ pairs: [] })).use_take_profit_exit_orders).toBe(true)
    expect(dc(buildDCAConfig({ pairs: [] })).exit_limit_orders_price_percent).toBe(3)
  })
})

describe('buildSignalConfig', () => {
  const input: SignalInput = {
    webhookId: 'wh_1', webhookSecret: 'sec_1', pair: 'BTC/USDT',
    sideMode: 'payload', sidePayloadField: 'action',
    orderType: 'limit', limitOffsetBp: '5', limitOffsetDir: 'below',
    sizeMode: 'fixed', sizeValue: '100',
    tpEnabled: true, tpPct: '5', slEnabled: false, slPct: '5',
  }

  it('serializes the full signal settings into profile_data', () => {
    const cfg = buildSignalConfig(input)
    expect(cfg.configuration_type).toBe('generic_process')
    expect(cfg.profile_data).toEqual({
      signal: {
        version: 1,
        webhook: { id: 'wh_1', secret: 'sec_1' },
        pair: 'BTC/USDT',
        side: { mode: 'payload', payload_field: 'action' },
        order: { type: 'limit', limit_offset_bp: 5, limit_offset_direction: 'below' },
        size: { mode: 'fixed', value: 100 },
        take_profit_percent: 5,
      },
    })
  })

  it('omits limit fields for market orders and payload_field for fixed sides', () => {
    const cfg = buildSignalConfig({ ...input, orderType: 'market', sideMode: 'buy' })
    const signal = (cfg.profile_data as { signal: Record<string, unknown> }).signal
    expect(signal.order).toEqual({ type: 'market' })
    expect(signal.side).toEqual({ mode: 'buy' })
  })

  it('emits stop_loss_percent only when enabled', () => {
    const off = buildSignalConfig(input)
    expect((off.profile_data as { signal: Record<string, unknown> }).signal.stop_loss_percent).toBeUndefined()
    const on = buildSignalConfig({ ...input, slEnabled: true })
    expect((on.profile_data as { signal: Record<string, unknown> }).signal.stop_loss_percent).toBe(5)
  })

  it('isSignalProfileData accepts built configs and rejects foreign profiles', () => {
    expect(isSignalProfileData(buildSignalConfig(input).profile_data)).toBe(true)
    expect(isSignalProfileData({})).toBe(false)
    expect(isSignalProfileData(undefined)).toBe(false)
    expect(isSignalProfileData({ signal: {} })).toBe(false)
  })

  it('signalProfileDataToInput inverts the serialization', () => {
    const cfg = buildSignalConfig(input)
    const back = signalProfileDataToInput(cfg.profile_data as Parameters<typeof signalProfileDataToInput>[0])
    expect(back).toEqual({
      webhookId: 'wh_1', webhookSecret: 'sec_1', pair: 'BTC/USDT',
      sideMode: 'payload', sidePayloadField: 'action',
      orderType: 'limit', limitOffsetBp: 5, limitOffsetDir: 'below',
      sizeMode: 'fixed', sizeValue: 100,
      tpEnabled: true, tpPct: 5,
    })
  })
})

describe('buildMarketMakingConfig volume / stops / budget / hedging (per pair)', () => {
  const baseInput: MmInput = {
    exchange: 'binance', pairs: ['BTC/USDT'], refsByPair: {},
    spreadBp: '50', perSide: '3', sizeBase: '100', shape: 'flat',
  }

  it('emits scheduled_volume with the given bounds when volume is enabled for the pair', () => {
    const cfg = buildMarketMakingConfig({
      ...baseInput,
      volumeByPair: { 'BTC/USDT': { enabled: true, minAmount: '140', maxAmount: '260', minIntervalSeconds: '240', maxIntervalSeconds: '240' } },
    })
    expect(cfg.pair_settings[0].scheduled_volume).toEqual({
      min_amount: 140, max_amount: 260, min_interval_seconds: 240, max_interval_seconds: 240,
    })
    const off = buildMarketMakingConfig({
      ...baseInput,
      volumeByPair: { 'BTC/USDT': { enabled: false, minAmount: '140', maxAmount: '260', minIntervalSeconds: '240', maxIntervalSeconds: '240' } },
    })
    expect(off.pair_settings[0].scheduled_volume).toBeUndefined()
  })

  it('emits real stop-condition thresholds for the pair', () => {
    const cfg = buildMarketMakingConfig({
      ...baseInput,
      stopsByPair: {
        'BTC/USDT': {
          enabled: true,
          minQuoteHolding: '400',
          maxPositivePct: '0.5',
          maxNegativePct: '0.5',
          avgPriceMinutes: '5',
        },
      },
    })
    expect(cfg.pair_settings[0].stop_conditions).toEqual({
      min_quote_holding: 400,
      max_positive_percent_price_change: 0.5,
      max_negative_percent_price_change: 0.5,
      average_price_counted_minutes: 5,
    })
  })

  it('omits stop_conditions when stops are disabled for the pair', () => {
    const cfg = buildMarketMakingConfig({
      ...baseInput,
      stopsByPair: { 'BTC/USDT': { enabled: false, minQuoteHolding: '400' } },
    })
    expect(cfg.pair_settings[0].stop_conditions).toBeUndefined()
  })

  it('floors average_price_counted_minutes to 1 instead of sending a sub-1 value', () => {
    // The node (and legacy's own Zod schema) rejects values below 1.
    const cfg = buildMarketMakingConfig({
      ...baseInput,
      stopsByPair: { 'BTC/USDT': { enabled: true, minQuoteHolding: '400', avgPriceMinutes: '0.5' } },
      hedgingByPair: { 'BTC/USDT': { enabled: true, exchange: 'bybit', avgPriceMinutes: '0.2' } },
    })
    expect(cfg.pair_settings[0].stop_conditions?.average_price_counted_minutes).toBe(1)
    expect(cfg.pair_settings[0].hedging_engine?.average_price_counted_minutes).toBe(1)
  })

  it('falls back to the 60-minute default when average_price_counted_minutes is unset', () => {
    const cfg = buildMarketMakingConfig({
      ...baseInput,
      stopsByPair: { 'BTC/USDT': { enabled: true, minQuoteHolding: '400', avgPriceMinutes: '0' } },
    })
    expect(cfg.pair_settings[0].stop_conditions?.average_price_counted_minutes).toBe(60)
  })

  it('caps base/quote budgets from the per-pair budget fields', () => {
    const cfg = buildMarketMakingConfig({
      ...baseInput,
      budgetByPair: { 'BTC/USDT': { enabled: true, maxBase: '50', maxQuote: '2000', minBase: '5', minQuote: '500' } },
    })
    expect(cfg.pair_settings[0].max_base_budget).toBe(50)
    expect(cfg.pair_settings[0].max_quote_budget).toBe(2000)
    expect(cfg.pair_settings[0].min_base_budget).toBe(5)
    expect(cfg.pair_settings[0].min_quote_budget).toBe(500)
    const off = buildMarketMakingConfig(baseInput)
    expect(off.pair_settings[0].max_quote_budget).toBe(100)
    expect(off.pair_settings[0].min_quote_budget).toBeUndefined()
  })

  it('emits a spot hedging engine with the given venue and thresholds when hedging is enabled', () => {
    const on = buildMarketMakingConfig({
      ...baseInput,
      hedgingByPair: { 'BTC/USDT': { enabled: true, exchange: 'bybit', maxLossThreshold: '2' } },
    })
    expect(on.pair_settings[0].hedging_engine).toEqual({
      hedging_engine_type: 'spot', hedging_exchange: 'bybit',
      average_price_counted_minutes: 60, hedging_max_loss_threshold: 2,
    })
    expect(buildMarketMakingConfig(baseInput).pair_settings[0].hedging_engine).toBeUndefined()
  })

  it('drops the hedging engine when disabled for the pair, even with a configured venue', () => {
    const off = buildMarketMakingConfig({
      ...baseInput,
      hedgingByPair: { 'BTC/USDT': { enabled: false, exchange: 'bybit' } },
    })
    expect(off.pair_settings[0].hedging_engine).toBeUndefined()
  })

  it('falls back to quoting the traded pair on its own venue when a pair has no references', () => {
    const cfg = buildMarketMakingConfig({ ...baseInput, pairs: ['ETH/USDT'] })
    // The required `pair` field must hold a pair symbol — never the exchange value.
    expect(cfg.pair_settings[0].reference_price).toEqual([
      { exchange: 'binance', pair: 'ETH/USDT', weight: 1 },
    ])
  })

  it('parses every numeric field with the same rules', () => {
    // Number('1,000') is NaN but parseFloat('1,000') is 1 — mixed parsing made
    // a thousands-separator typo zero the base budget while setting capital to 1.
    const cfg = buildMarketMakingConfig({
      ...baseInput,
      sizeBase: '1,000',
      budgetByPair: { 'BTC/USDT': { enabled: true, maxBase: '1,000', maxQuote: '1,000', minBase: '0', minQuote: '0' } },
    })
    expect(cfg.pair_settings[0].max_base_budget).toBe(1)
    expect(cfg.pair_settings[0].max_quote_budget).toBe(1)
  })

  it('uses per-pair order-book overrides instead of the bot-wide spread/perSide scalars', () => {
    const cfg = buildMarketMakingConfig({
      ...baseInput,
      orderBookByPair: {
        'BTC/USDT': {
          minSpreadBp: '30', maxSpreadBp: '200',
          bidsCount: '3', asksCount: '4',
          ordersDistribution: 'linear', fundsDistribution: 'valley',
          cumulatedVolumePercent: '2', percentDailyTradingVolume: '1.5',
        },
      },
    })
    const p = cfg.pair_settings[0]
    expect(p.min_spread).toBe(0.3)
    expect(p.max_spread).toBe(2)
    expect(p.bids_count).toBe(3)
    expect(p.asks_count).toBe(4)
    expect(p.funds_distribution).toBe('valley')
    expect(p.order_book_depth).toEqual({ cumulated_volume_percent: 2, percent_daily_trading_volume: 1.5 })
  })

  it('falls back to the bot-wide scalars when a pair has no order-book override', () => {
    const cfg = buildMarketMakingConfig(baseInput)
    const p = cfg.pair_settings[0]
    expect(p.min_spread).toBe(0.5)
    expect(p.max_spread).toBe(1)
    expect(p.bids_count).toBe(3)
    expect(p.asks_count).toBe(3)
    expect(p.order_book_depth).toBeUndefined()
  })
})

describe('protocolStrategyToInput fidelity round-trips', () => {
  it('grid restores ladder geometry, levels and trailing toggles', () => {
    const strat = buildProtocolStrategy({
      kind: 'grid',
      grid: { pairs: ['ETH/USDT'], lower: 90, upper: 110, levels: 20, currentPrice: 95 },
    })
    const back = protocolStrategyToInput(strat)
    expect(back.kind).toBe('grid')
    if (back.kind === 'grid') {
      expect(back.grid).toEqual({
        spread: 2, increment: 1, buyCount: 5, sellCount: 15, levels: 20,
        enableTrailingUp: true, orderByOrderTrailing: true,
      })
    }
  })

  it('grid recovers the original level count for any ladder size', () => {
    for (let levels = 2; levels <= 60; levels++) {
      const strat = buildProtocolStrategy({
        kind: 'grid',
        grid: { pairs: ['ETH/USDT'], lower: 90, upper: 110, levels, currentPrice: 97.5 },
      })
      const back = protocolStrategyToInput(strat)
      if (back.kind !== 'grid') throw new Error('expected a grid patch')
      expect(`levels ${levels} → ${back.grid?.levels}`).toBe(`levels ${levels} → ${levels}`)
    }
  })

  it('grid raw params round-trip verbatim (spread ≠ increment)', () => {
    const strat = buildProtocolStrategy({
      kind: 'grid',
      grid: {
        pairs: ['BTC/USDC'],
        flatSpread: 2000, flatIncrement: 500, buyOrdersCount: 10, sellOrdersCount: 20,
        enableTrailingUp: true, orderByOrderTrailing: false,
      },
    })
    const back = protocolStrategyToInput(strat)
    expect(back.kind).toBe('grid')
    if (back.kind === 'grid') {
      expect(back.grid).toEqual({
        spread: 2000, increment: 500, buyCount: 10, sellCount: 20, levels: 30,
        enableTrailingUp: true, orderByOrderTrailing: false,
      })
    }
  })

  it('grid maps the legacy all-zero config to a null patch', () => {
    const strat = buildProtocolStrategy({ kind: 'grid', grid: { pairs: ['ETH/USDT'] } })
    const back = protocolStrategyToInput(strat)
    if (back.kind === 'grid') expect(back.grid).toBeNull()
  })

  it('dca restores every param verbatim', () => {
    const strat = buildProtocolStrategy({
      kind: 'dca',
      dca: {
        pairs: ['BTC/USDT'],
        buyOrderAmount: '25q', minutesBeforeNextBuy: 1440,
        useMarketEntry: true, entryLimitPricePercent: 2,
        useTakeProfit: false, exitLimitPricePercent: 6,
      },
    })
    const back = protocolStrategyToInput(strat)
    expect(back.kind).toBe('dca')
    if (back.kind === 'dca') {
      expect(back.dca).toEqual({
        buyOrderAmount: '25q', minutesBeforeNextBuy: 1440,
        useMarketEntry: true, entryLimitPricePercent: 2,
        useTakeProfit: false, exitLimitPricePercent: 6,
      })
    }
  })

  it('dca recovers legacy time_frames cadence when minutes_before_next_buy is absent', () => {
    const strat = buildProtocolStrategy({ kind: 'dca', dca: { pairs: ['BTC/USDT'] } })
    const cfg = strat.configuration as { config: Record<string, unknown> }
    delete cfg.config.minutes_before_next_buy
    cfg.config.time_frames = ['1w']
    const back = protocolStrategyToInput(strat)
    if (back.kind === 'dca') expect(back.dca?.minutesBeforeNextBuy).toBe(10080)
  })

  it('basket rescales legacy fraction weights (sum ≤ 1) to percent', () => {
    const strat = buildProtocolStrategy({
      kind: 'basket',
      basket: { pairs: ['BTC', 'ETH'], basketWeights: { BTC: 0.6, ETH: 0.4 } },
    })
    const back = protocolStrategyToInput(strat)
    expect(back.kind).toBe('basket')
    if (back.kind === 'basket') {
      expect(back.basket.basketWeights).toEqual({ BTC: 60, ETH: 40 })
      expect(back.basket.basketTotal).toBe(100)
    }
  })

  it('signal-tagged generic_process restores the signal input; plain ones stay custom', () => {
    const input: SignalInput = {
      webhookId: 'wh_1', webhookSecret: 'sec_1', pair: 'BTC/USDT',
      sideMode: 'buy', orderType: 'market', sizeMode: 'percent', sizeValue: 25,
    }
    const back = protocolStrategyToInput(buildProtocolStrategy({ kind: 'signal', signal: input }))
    expect(back.kind).toBe('signal')
    if (back.kind === 'signal') expect(back.signal).toMatchObject(input)
    expect(protocolStrategyToInput(buildProtocolStrategy({ kind: 'custom' })).kind).toBe('custom')
  })

  it('mm restores spreadBp without FP noise (0.07 * 100 !== 7 in floats)', () => {
    const strat = buildProtocolStrategy({
      kind: 'mm',
      mm: { exchange: 'binance', pairs: ['BTC/USDT'], refsByPair: {}, spreadBp: '7', perSide: '3', sizeBase: '100', shape: 'flat' },
    })
    const back = protocolStrategyToInput(strat)
    if (back.kind === 'mm') expect(back.mm.spreadBp).toBe('7')
  })

  it('mm restores per-pair order-book settings (build -> patch -> rebuild is stable)', () => {
    const strat = buildProtocolStrategy({
      kind: 'mm',
      mm: {
        exchange: 'binance', pairs: ['BTC/USDT'], refsByPair: {},
        spreadBp: '50', perSide: '3', sizeBase: '100', shape: 'flat',
        orderBookByPair: {
          'BTC/USDT': {
            minSpreadBp: '30', maxSpreadBp: '200',
            bidsCount: '3', asksCount: '4',
            ordersDistribution: 'linear', fundsDistribution: 'valley',
            cumulatedVolumePercent: '2', percentDailyTradingVolume: '1.5',
          },
        },
      },
    })
    const back = protocolStrategyToInput(strat)
    expect(back.kind).toBe('mm')
    if (back.kind !== 'mm') return
    expect(back.mm.orderBookByPair?.['BTC/USDT']).toEqual({
      minSpreadBp: '30', maxSpreadBp: '200',
      bidsCount: '3', asksCount: '4',
      ordersDistribution: 'linear', fundsDistribution: 'valley',
      cumulatedVolumePercent: '2', percentDailyTradingVolume: '1.5',
    })
    // Rebuild from the recovered patch and confirm the protocol config is stable.
    const rebuilt = buildMarketMakingConfig({
      exchange: 'binance', pairs: ['BTC/USDT'], refsByPair: {},
      spreadBp: back.mm.spreadBp ?? '50', perSide: back.mm.perSide ?? '3',
      sizeBase: back.mm.sizeBase ?? '100', shape: back.mm.shape ?? 'flat',
      orderBookByPair: back.mm.orderBookByPair,
    })
    expect(rebuilt.pair_settings[0].min_spread).toBe(0.3)
    expect(rebuilt.pair_settings[0].max_spread).toBe(2)
    expect(rebuilt.pair_settings[0].asks_count).toBe(4)
    expect(rebuilt.pair_settings[0].funds_distribution).toBe('valley')
  })

  it('mm restores order-book settings for every pair unconditionally (always-present protocol fields)', () => {
    const strat = buildProtocolStrategy({
      kind: 'mm',
      mm: {
        exchange: 'binance', pairs: ['BTC/USDT', 'ETH/USDT'], refsByPair: {},
        spreadBp: '50', perSide: '3', sizeBase: '100', shape: 'flat',
      },
    })
    const back = protocolStrategyToInput(strat)
    if (back.kind !== 'mm') return
    expect(back.mm.orderBookByPair?.['BTC/USDT']).toBeDefined()
    expect(back.mm.orderBookByPair?.['ETH/USDT']).toBeDefined()
  })

  it('mm restores the budget for a pair even when max_quote_budget equals max_base_budget (ambiguity signal)', () => {
    // Without the min_base_budget/min_quote_budget clause the inverse reads
    // "no budget" and a re-save silently drops the node's inventory floor.
    const strat = buildProtocolStrategy({
      kind: 'mm',
      mm: {
        exchange: 'binance', pairs: ['BTC/USDT'], refsByPair: {},
        spreadBp: '50', perSide: '3', sizeBase: '100', shape: 'flat',
        budgetByPair: { 'BTC/USDT': { enabled: true, maxBase: '100', maxQuote: '100', minBase: '0', minQuote: '20' } },
      },
    })
    const back = protocolStrategyToInput(strat)
    if (back.kind === 'mm') {
      expect(back.mm.budgetByPair?.['BTC/USDT']).toEqual({ enabled: true, maxBase: 100, maxQuote: 100, minBase: 0, minQuote: 20 })
    }
  })

  it('mm round-trips funds_distribution random instead of degrading it to flat', () => {
    const strat = buildProtocolStrategy({
      kind: 'mm',
      mm: { exchange: 'binance', pairs: ['BTC/USDT'], refsByPair: {}, spreadBp: '50', perSide: '3', sizeBase: '100', shape: 'random' },
    })
    const back = protocolStrategyToInput(strat)
    if (back.kind === 'mm') expect(back.mm.shape).toBe('random')
  })

  it('mm multi-pair round-trip keys refs and stops to the right pair', () => {
    const strat = buildProtocolStrategy({
      kind: 'mm',
      mm: {
        exchange: 'binance',
        pairs: ['BTC/USDT', 'ETH/USDT'],
        refsByPair: {
          'BTC/USDT': [{ pair: 'BTC/USD', weight: 1 }],
          'ETH/USDT': [{ pair: 'ETH/USD', weight: 0.5 }],
        },
        spreadBp: '50', perSide: '3', sizeBase: '100', shape: 'flat',
        stopsByPair: { 'ETH/USDT': { enabled: true, minQuoteHolding: '400' } },
      },
    })
    const back = protocolStrategyToInput(strat)
    expect(back.kind).toBe('mm')
    if (back.kind === 'mm') {
      expect(back.pairs).toEqual(['BTC/USDT', 'ETH/USDT'])
      expect(back.refsByPair['BTC/USDT'][0].pair).toBe('BTC/USD')
      expect(back.refsByPair['ETH/USDT'][0].pair).toBe('ETH/USD')
      expect(Object.keys(back.mm.stopsByPair ?? {})).toEqual(['ETH/USDT'])
    }
  })

  it('mm multi-pair budget round-trip is a fixed point when only one pair has an override (regression: sizeBase must not leak from the overridden pair)', () => {
    // BTC has its own per-pair budget; ETH has none and falls back to the
    // bot-wide sizeBase. Recovering sizeBase from an arbitrary pair (rather
    // than one actually using the fallback) would read BTC's override and
    // silently rewrite ETH's budget on the next build.
    const strat = buildProtocolStrategy({
      kind: 'mm',
      mm: {
        exchange: 'binance',
        pairs: ['BTC/USDT', 'ETH/USDT'],
        refsByPair: {},
        spreadBp: '50', perSide: '3', sizeBase: '5', shape: 'flat',
        budgetByPair: { 'BTC/USDT': { enabled: true, maxBase: '10', maxQuote: '20000', minBase: '1', minQuote: '1000' } },
      },
    })
    const ethBefore = (strat.configuration as MarketMakingConfiguration).pair_settings.find((p) => p.trading_pair === 'ETH/USDT')
    expect(ethBefore?.max_base_budget).toBe(5)
    expect(ethBefore?.max_quote_budget).toBe(5)

    const patch = protocolStrategyToInput(strat)
    if (patch.kind !== 'mm') throw new Error('expected mm')
    expect(patch.mm.sizeBase).toBe('5')

    const reEmitted = buildProtocolStrategy({
      kind: 'mm',
      mm: {
        exchange:    patch.mm.exchange ?? 'binance',
        pairs:       patch.pairs,
        refsByPair:  patch.refsByPair,
        spreadBp:    patch.mm.spreadBp ?? '0',
        perSide:     patch.mm.perSide ?? '0',
        sizeBase:    patch.mm.sizeBase ?? '0',
        shape:       patch.mm.shape ?? 'flat',
        budgetByPair: patch.mm.budgetByPair,
      },
    })
    const ethAfter = (reEmitted.configuration as MarketMakingConfiguration).pair_settings.find((p) => p.trading_pair === 'ETH/USDT')
    // An untouched edit+Apply must not change ETH's budget.
    expect(ethAfter?.max_base_budget).toBe(5)
    expect(ethAfter?.max_quote_budget).toBe(5)
  })

  it('recovers sizeBase as the smallest override when every pair has its own budget (regression: must not pick an arbitrary pair and silently inflate a later-disabled pair)', () => {
    // No pair uses the shared fallback here, so there is no "true" bot-wide
    // sizeBase to recover — but the recovered value still surfaces (it's
    // shown/edited on the OrderBook step, and becomes a pair's real budget
    // if the user disables that pair's override in the same edit session).
    // Picking the smallest override bounds that risk to under- rather than
    // over-allocating a pair the user didn't intend to touch.
    const strat = buildProtocolStrategy({
      kind: 'mm',
      mm: {
        exchange: 'binance',
        pairs: ['BTC/USDT', 'ETH/USDT'],
        refsByPair: {},
        spreadBp: '50', perSide: '3', sizeBase: '5', shape: 'flat',
        budgetByPair: {
          'BTC/USDT': { enabled: true, maxBase: '50', maxQuote: '20000', minBase: '1', minQuote: '1000' },
          'ETH/USDT': { enabled: true, maxBase: '8',  maxQuote: '9000',  minBase: '1', minQuote: '500' },
        },
      },
    })
    const patch = protocolStrategyToInput(strat)
    if (patch.kind !== 'mm') throw new Error('expected mm')
    // Smallest override (ETH's 8), not pairs[0]'s BTC override (50).
    expect(patch.mm.sizeBase).toBe('8')

    // If the user now disables ETH's override without touching sizeBase,
    // ETH must fall back to the conservative recovered value (8), not an
    // unrelated pair's much larger cap (50).
    const reEmitted = buildProtocolStrategy({
      kind: 'mm',
      mm: {
        exchange:    patch.mm.exchange ?? 'binance',
        pairs:       patch.pairs,
        refsByPair:  patch.refsByPair,
        spreadBp:    patch.mm.spreadBp ?? '0',
        perSide:     patch.mm.perSide ?? '0',
        sizeBase:    patch.mm.sizeBase ?? '0',
        shape:       patch.mm.shape ?? 'flat',
        budgetByPair: { 'BTC/USDT': patch.mm.budgetByPair?.['BTC/USDT'] },
      },
    })
    const ethAfter = (reEmitted.configuration as MarketMakingConfiguration).pair_settings.find((p) => p.trading_pair === 'ETH/USDT')
    expect(ethAfter?.max_base_budget).toBe(8)
  })

  it('rejects partial signal payloads instead of throwing (foreign producers)', () => {
    const strat = buildProtocolStrategy({ kind: 'custom' })
    const partial = {
      ...strat,
      configuration: {
        configuration_type: 'generic_process' as const,
        profile_data: { signal: { webhook: { id: 'a', secret: '' }, pair: 'BTC/USDT' } },
      },
    }
    expect(isSignalProfileData(partial.configuration.profile_data)).toBe(false)
    expect(protocolStrategyToInput(partial).kind).toBe('custom')
  })

  it('mm restores volume, budget, stop conditions and hedging per pair', () => {
    const strat = buildProtocolStrategy({
      kind: 'mm',
      mm: {
        exchange: 'binance', pairs: ['BTC/USDT'], refsByPair: {},
        spreadBp: '50', perSide: '3', sizeBase: '100', shape: 'flat',
        volumeByPair: { 'BTC/USDT': { enabled: true, minAmount: '140', maxAmount: '260', minIntervalSeconds: '240', maxIntervalSeconds: '240' } },
        budgetByPair: { 'BTC/USDT': { enabled: true, maxBase: '50', maxQuote: '2000', minBase: '5', minQuote: '500' } },
        stopsByPair: { 'BTC/USDT': { enabled: true, minQuoteHolding: '400' } },
        hedgingByPair: { 'BTC/USDT': { enabled: true, exchange: 'bybit' } },
      },
    })
    const back = protocolStrategyToInput(strat)
    expect(back.kind).toBe('mm')
    if (back.kind === 'mm') {
      expect(back.mm.volumeByPair?.['BTC/USDT']).toEqual({ enabled: true, minAmount: 140, maxAmount: 260, minIntervalSeconds: 240, maxIntervalSeconds: 240 })
      expect(back.mm.budgetByPair?.['BTC/USDT']).toEqual({ enabled: true, maxBase: 50, maxQuote: 2000, minBase: 5, minQuote: 500 })
      expect(back.mm.hedgingByPair?.['BTC/USDT']).toMatchObject({ enabled: true, exchange: 'bybit' })
      expect(back.mm.stopsByPair?.['BTC/USDT']).toEqual({
        enabled: true, minBaseHolding: 0, minQuoteHolding: 400, maxPositivePct: 0, maxNegativePct: 0, avgPriceMinutes: 60,
      })
    }
  })
})

describe('cross-venue references and basket fidelity (round-trip)', () => {
  it('preserves a reference quoted on another venue across the edit round-trip', () => {
    const strat = buildProtocolStrategy({
      kind: 'mm',
      mm: {
        exchange: 'binance', pairs: ['BTC/USDT'],
        refsByPair: {
          'BTC/USDT': [
            { pair: 'BTC/USD', weight: 0.7, exchange: 'coinbase' },
            { pair: 'BTC/USDT', weight: 0.3 },
          ],
        },
        spreadBp: '50', perSide: '3', sizeBase: '100', shape: 'flat',
      },
    })
    const patch = protocolStrategyToInput(strat)
    if (patch.kind !== 'mm') throw new Error('expected mm')
    // Cross-venue ref keeps its exchange; same-venue ref stays implicit.
    expect(patch.refsByPair['BTC/USDT'][0].exchange).toBe('coinbase')
    expect(patch.refsByPair['BTC/USDT'][1].exchange).toBeUndefined()
    const reEmitted = buildMarketMakingConfig({
      exchange: 'binance', pairs: ['BTC/USDT'], refsByPair: patch.refsByPair,
      spreadBp: patch.mm.spreadBp ?? '0', perSide: patch.mm.perSide ?? '0',
      sizeBase: patch.mm.sizeBase ?? '0', shape: patch.mm.shape ?? 'flat',
    })
    expect(reEmitted.pair_settings[0].reference_price.map((r) => r.exchange)).toEqual([
      'coinbase', 'binance',
    ])
  })

  it('restores basket weights on the wizard percent scale and keeps the drift threshold', () => {
    const strat = buildProtocolStrategy({
      kind: 'basket',
      basket: {
        pairs: ['BTC/USDT', 'ETH/USDT'],
        basketWeights: { BTC: 60, ETH: 40 },
        basketTotal: 100,
        rebalanceTriggerPct: 10,
      },
    })
    const cfg = strat.configuration
    if (cfg.configuration_type !== 'trading_tentacles' || cfg.name !== 'IndexTradingMode') throw new Error('expected IndexTradingMode')
    const indexCfg = cfg.config as { index_content: Array<{ name: string; value: number }>; rebalance_trigger_min_percent: number }
    expect(indexCfg.rebalance_trigger_min_percent).toBe(10)
    expect(indexCfg.index_content).toEqual([
      { name: 'BTC', value: 60 },
      { name: 'ETH', value: 40 },
    ])
    const patch = protocolStrategyToInput(strat)
    if (patch.kind !== 'basket') throw new Error('expected basket')
    expect(patch.basket.basketWeights).toEqual({ BTC: 60, ETH: 40 })
    expect(patch.basket.basketTotal).toBe(100)
    expect(patch.basket.rebalanceTriggerPct).toBe(10)
  })
})

describe('free-text numeric sanitization (MM) and verbatim DCA override', () => {
  const base: MmInput = {
    exchange: 'binance', pairs: ['BTC/USDT'], refsByPair: {},
    spreadBp: '50', perSide: '3', sizeBase: '100', shape: 'flat',
  }

  it('clamps negative spread/size and rounds fractional order counts', () => {
    // The minus sign is typable on web/Android numeric keyboards.
    const cfg = buildMarketMakingConfig({ ...base, spreadBp: '-50', perSide: '2.5', sizeBase: '-100' })
    const pair = cfg.pair_settings[0]
    expect(pair.min_spread).toBe(0)
    expect(pair.max_spread).toBe(0)
    expect(pair.bids_count).toBe(3)
    expect(Number.isInteger(pair.bids_count)).toBe(true)
    expect(pair.max_base_budget).toBe(0)
    expect(pair.max_quote_budget).toBe(0)
  })

  it('keeps scheduled volume bounds ordered and non-negative', () => {
    const cfg = buildMarketMakingConfig({
      ...base,
      volumeByPair: { 'BTC/USDT': { enabled: true, minAmount: '500', maxAmount: '-100', minIntervalSeconds: '240', maxIntervalSeconds: '240' } },
    })
    expect(cfg.pair_settings[0].scheduled_volume).toEqual({
      min_amount: 0, max_amount: 500, min_interval_seconds: 240, max_interval_seconds: 240,
    })
  })

  it('clamps a negative budget field to zero', () => {
    const cfg = buildMarketMakingConfig({
      ...base,
      budgetByPair: { 'BTC/USDT': { enabled: true, maxBase: '100', maxQuote: '-2000', minBase: '0', minQuote: '0' } },
    })
    // pos() floors at 0 — a negative max quote budget can't go through as-is.
    expect(cfg.pair_settings[0].max_quote_budget).toBe(0)
  })

  it('re-emits a fractional percent amount string VERBATIM (no rounding to 2 decimals)', () => {
    const cfg = buildDCAConfig({ pairs: ['BTC/USDT'], buyOrderAmount: '0.125%t' })
    expect((cfg.config as { buy_order_amount: string }).buy_order_amount).toBe('0.125%t')
  })
})

describe('MM inverse captures hedging independently per pair', () => {
  const pairSetting = (overrides: object) => ({
    trading_pair: 'X/USDT',
    reference_price: [{ exchange: 'binance', pair: 'X/USDT', weight: 1 }],
    min_spread: 0.5, max_spread: 1, bids_count: 3, asks_count: 3,
    orders_distribution: 'linear' as const, funds_distribution: 'flat' as const,
    exchange: 'binance', max_base_budget: 100, max_quote_budget: 100,
    ...overrides,
  })

  it('keeps a hedging engine configured on one pair from leaking onto another', () => {
    const strat = {
      id: 's', version: '1.0.0', reference_market: 'USDT',
      configuration: {
        configuration_type: 'market_making' as const,
        pair_settings: [
          pairSetting({ trading_pair: 'BTC/USDT' }),
          pairSetting({ trading_pair: 'ETH/USDT', hedging_engine: { hedging_engine_type: 'spot' as const, hedging_exchange: 'bybit' } }),
        ],
      },
    }
    const patch = protocolStrategyToInput(strat)
    if (patch.kind !== 'mm') throw new Error('expected mm')
    expect(patch.mm.hedgingByPair?.['ETH/USDT']).toMatchObject({ enabled: true, exchange: 'bybit' })
    expect(patch.mm.hedgingByPair?.['BTC/USDT']).toBeUndefined()
    // The running venue still rides the patch for the account-deleted Apply fallback.
    expect(patch.mm.exchange).toBe('binance')
  })

  it('rejects a signal profile lacking the webhook secret (would round-trip undefined)', () => {
    expect(isSignalProfileData({
      signal: {
        webhook: { id: 'wh_1' }, pair: 'BTC/USDT',
        side: { mode: 'buy' }, order: { type: 'market' }, size: { mode: 'fixed', value: 100 },
      },
    })).toBe(false)
  })
})
