import { describe, it, expect } from 'vitest'
import {
  DEX_PAIR_EXAMPLE,
  isValidDexNameSegment,
  isValidDexPair,
  isValidDexPairSegment,
  parseDexPair,
  splitDexPairSegments,
} from '../src/node-api/dexPair.js'

describe('parseDexPair', () => {
  it('parses a full identifier', () => {
    expect(parseDexPair('WETH/USDT@BASE!PANCAKESWAP')).toEqual({
      base: 'WETH',
      quote: 'USDT',
      network: 'BASE',
      dex: 'PANCAKESWAP',
    })
  })

  it('parses an identifier without a dex suffix', () => {
    expect(parseDexPair('WETH/USDT@BASE')).toEqual({
      base: 'WETH',
      quote: 'USDT',
      network: 'BASE',
      dex: undefined,
    })
  })

  it('parses contract addresses', () => {
    expect(parseDexPair('0xabc/0xdef@BEP20!UNISWAP')).toEqual({
      base: '0xabc',
      quote: '0xdef',
      network: 'BEP20',
      dex: 'UNISWAP',
    })
  })

  it('trims surrounding whitespace', () => {
    expect(parseDexPair('  WETH/USDT@BASE!PANCAKESWAP  ')).toEqual({
      base: 'WETH',
      quote: 'USDT',
      network: 'BASE',
      dex: 'PANCAKESWAP',
    })
  })

  it('parses the documented example', () => {
    expect(parseDexPair(DEX_PAIR_EXAMPLE)).toBeDefined()
  })
})

describe('isValidDexPair', () => {
  it.each([
    'WETH/USDT@BASE!PANCAKESWAP',
    '0xabc/0xdef@BEP20!UNISWAP',
    '  WETH/USDT@BASE!PANCAKESWAP  ',
    'WETH/USDT@BASE', // dex suffix is optional
  ])('accepts %s', (value) => {
    expect(isValidDexPair(value)).toBe(true)
  })

  it.each([
    '',
    'WETH',
    'WETH/USDT', // network is required
    'A/B@NET!', // empty dex when '!' is present
    'A/B!DEX', // dex without network
    'A B/C@N!D', // whitespace
    'A/B/C@N!D', // double slash
    '@BASE!PANCAKESWAP', // missing pair
    'A/B@N!D!E', // double bang
  ])('rejects %s', (value) => {
    expect(isValidDexPair(value)).toBe(false)
  })
})

describe('splitDexPairSegments', () => {
  it('splits a full identifier', () => {
    expect(splitDexPairSegments('WETH/USDT@BASE!PANCAKESWAP')).toEqual({
      pair: 'WETH/USDT',
      network: 'BASE',
      dex: 'PANCAKESWAP',
    })
  })

  it('splits a partial identifier while typing', () => {
    expect(splitDexPairSegments('WETH/USDT@BA')).toEqual({
      pair: 'WETH/USDT',
      network: 'BA',
      dex: '',
    })
    expect(splitDexPairSegments('WETH')).toEqual({
      pair: 'WETH',
      network: '',
      dex: '',
    })
  })
})

describe('segment validators', () => {
  it('validates pair segments', () => {
    expect(isValidDexPairSegment('WETH/USDT')).toBe(true)
    expect(isValidDexPairSegment('WETH')).toBe(false)
    expect(isValidDexPairSegment('A/B/C')).toBe(false)
  })

  it('validates name segments', () => {
    expect(isValidDexNameSegment('BASE')).toBe(true)
    expect(isValidDexNameSegment('')).toBe(false)
    expect(isValidDexNameSegment('BA SE')).toBe(false)
  })
})
