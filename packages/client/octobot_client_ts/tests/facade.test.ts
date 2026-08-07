import { describe, it, expect } from 'vitest'
import { connectOctoBot } from '../src/client/connect/connect.js'
import { strategy } from '../src/client/strategy.js'
import { getDerivationScheme } from '../src/identity/derivationSchemes.js'

const MNEMONIC = 'abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about'

describe('connectOctoBot', () => {
  it('resolves without network I/O when verify: false', async () => {
    const client = await connectOctoBot({
      url: 'http://192.0.2.1:5001', // TEST-NET-1, guaranteed unreachable
      seed: MNEMONIC,
      verify: false,
    })
    expect(client.url).toBe('http://192.0.2.1:5001')
    expect(client.address).toMatch(/^0x[0-9a-fA-F]{40}$/)
    // userId = sha256(rootEdPub)[:32] hex chars (16 bytes truncated), per
    // identity/capProvider.ts.
    expect(client.userId).toMatch(/^[0-9a-f]{32}$/)
    client.close()
  })

  it('the derivation registry rejects an unregistered scheme id with a clear error', () => {
    expect(() => getDerivationScheme('not-a-real-scheme')).toThrow(/unknown derivation scheme/)
  })

  it('rejects a missing url or seed with OctoBotConfigError', async () => {
    await expect(connectOctoBot({ url: '', seed: MNEMONIC })).rejects.toThrow(/url is required/)
    await expect(connectOctoBot({ url: 'http://192.0.2.1:5001', seed: '' })).rejects.toThrow(/seed is required/)
  })

  it('accepts a bare host:port url', async () => {
    const client = await connectOctoBot({ url: '192.0.2.1:5001', seed: MNEMONIC, verify: false })
    expect(client.url).toBe('http://192.0.2.1:5001')
  })

  it('exposes every namespace', async () => {
    const client = await connectOctoBot({ url: 'http://192.0.2.1:5001', seed: MNEMONIC, verify: false })
    expect(client.accounts).toBeDefined()
    expect(client.automations).toBeDefined()
    expect(client.strategies).toBeDefined()
    expect(client.settings).toBeDefined()
    expect(client.node).toBeDefined()
    expect(client.documents).toBeDefined()
  })
})

describe('strategy builders (pure, zero I/O)', () => {
  it('strategy.dca builds a trading_tentacles/DCATradingMode configuration', () => {
    const s = strategy.dca({ pairs: ['BTC/USDT'], buyOrderAmount: '25' })
    expect(s.configuration.configuration_type).toBe('trading_tentacles')
    expect((s.configuration as { name?: string }).name).toBe('DCATradingMode')
    expect(s.reference_market).toBe('USDT')
    expect(s.id).toMatch(/^s_/)
  })

  it('strategy.toInput round-trips a built strategy back to editable input', () => {
    const built = strategy.dca({ pairs: ['BTC/USDT'], buyOrderAmount: '25' })
    const input = strategy.toInput(built)
    expect(input.kind).toBe('dca')
  })

  it('strategy.bumpVersion increments the patch component', () => {
    expect(strategy.bumpVersion('1.0.0')).toBe('1.0.1')
    expect(strategy.bumpVersion('1.0')).toBe('1.0.1')
  })
})
