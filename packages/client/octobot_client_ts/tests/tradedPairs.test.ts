import { describe, it, expect } from 'vitest'
import { extractPairs } from '../src/node-api/pairs.js'

describe('extractPairs', () => {
  it('reads the symbol → volume map answered by current nodes', () => {
    expect(extractPairs({
      binance: {
        'BTC/USDT': { baseVolume: 12, quoteVolume: 1_200_000 },
        'ETH/USDT': {},
      },
    })).toEqual([
      { symbol: 'BTC/USDT', base: 'BTC', quote: 'USDT', type: 'spot', active: true, baseVolume: 12, quoteVolume: 1_200_000 },
      { symbol: 'ETH/USDT', base: 'ETH', quote: 'USDT', type: 'spot', active: true, baseVolume: undefined, quoteVolume: undefined },
    ])
  })

  it('reads the bare symbol list answered by older nodes', () => {
    expect(extractPairs({ binance: ['BTC/USDT', 'ETH/USDT:USDT'] })).toEqual([
      { symbol: 'BTC/USDT', base: 'BTC', quote: 'USDT', type: 'spot', active: true },
      { symbol: 'ETH/USDT:USDT', base: 'ETH', quote: 'USDT', type: 'swap', active: true },
    ])
  })

  it('merges every exchange in the payload', () => {
    const pairs = extractPairs({
      binance: { 'BTC/USDT': {} },
      kucoin: ['ETH/USDT'],
    })
    expect(pairs.map((p) => p.symbol)).toEqual(['BTC/USDT', 'ETH/USDT'])
  })

  it('lists a symbol once when several exchanges report it, keeping known volumes', () => {
    const pairs = extractPairs({
      binance: { 'BTC/USDT': { quoteVolume: 7 } },
      kucoin: { 'BTC/USDT': { quoteVolume: 3 }, 'ETH/USDT': {} },
    })
    expect(pairs.map((p) => p.symbol)).toEqual(['BTC/USDT', 'ETH/USDT'])
    expect(pairs[0].quoteVolume).toBe(7)
  })

  it('fills a volume a later exchange reported for a symbol the first left empty', () => {
    const [pair] = extractPairs({
      binance: { 'BTC/USDT': {} },
      kucoin: { 'BTC/USDT': { quoteVolume: 3 } },
    })
    expect(pair.quoteVolume).toBe(3)
  })

  it('drops null volumes rather than carrying them into the sort', () => {
    const [pair] = extractPairs({ binance: { 'BTC/USDT': { baseVolume: null, quoteVolume: null } } })
    expect(pair.baseVolume).toBeUndefined()
    expect(pair.quoteVolume).toBeUndefined()
  })

  it('throws on a payload that is not keyed by exchange', () => {
    expect(() => extractPairs(['BTC/USDT'] as never)).toThrow('Unexpected traded-pairs payload from node')
    expect(() => extractPairs(null as never)).toThrow('Unexpected traded-pairs payload from node')
  })

  it('skips an exchange entry that is neither a list nor a map', () => {
    expect(extractPairs({ binance: 'BTC/USDT' as never, kucoin: { 'ETH/USDT': {} } }).map((p) => p.symbol))
      .toEqual(['ETH/USDT'])
  })
})
