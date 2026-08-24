import { describe, it, expect } from 'vitest'
import type { Account as ProtocolAccount, ExchangeConfig } from '@drakkar.software/octobot-protocol'
import { accountViewOf } from '../src/client/core/views.js'

const CONFIGS: ExchangeConfig[] = [{ id: 'cfg_1', name: 'Binance', exchange: 'binance', sandboxed: false }]

function account(specifics: ProtocolAccount['specifics']): ProtocolAccount {
  return { id: 'a1', name: 'A', is_simulated: false, created_at: '2020-01-01T00:00:00.000Z', specifics }
}

describe('accountViewOf — AccountKind over every AccountSpecifics discriminator', () => {
  it('exchange -> exchange, resolving the exchange via exchange_config_ids', () => {
    const view = accountViewOf(
      account({ account_type: 'exchange', remote_account_id: '', exchange_config_ids: ['cfg_1'] }),
      CONFIGS,
    )
    expect(view.type).toBe('exchange')
    expect(view.exchange).toBe('binance')
  })

  it('blockchain -> wallet, resolving the exchange via exchange_config_ids when present', () => {
    const view = accountViewOf(
      account({ account_type: 'blockchain', blockchain: 'ethereum', exchange_config_ids: ['cfg_1'] }),
      CONFIGS,
    )
    expect(view.type).toBe('wallet')
    expect(view.exchange).toBe('binance')
  })

  it('blockchain with no exchange_config_ids -> wallet, no exchange', () => {
    const view = accountViewOf(account({ account_type: 'blockchain', blockchain: 'ethereum' }), CONFIGS)
    expect(view.type).toBe('wallet')
    expect(view.exchange).toBeUndefined()
  })

  it('generic -> generic, no exchange', () => {
    const view = accountViewOf(account({ account_type: 'generic' }), CONFIGS)
    expect(view.type).toBe('generic')
    expect(view.exchange).toBeUndefined()
  })

  it('broker -> generic, resolving the exchange via exchange_config_ids when present', () => {
    const view = accountViewOf(
      account({ account_type: 'broker', provider_id: 'ib', exchange_config_ids: ['cfg_1'] }),
      CONFIGS,
    )
    expect(view.type).toBe('generic')
    expect(view.exchange).toBe('binance')
  })

  it('bank -> generic, no exchange (BankAccount has no exchange_config_ids)', () => {
    const view = accountViewOf(account({ account_type: 'bank', institution: 'Chase' }), CONFIGS)
    expect(view.type).toBe('generic')
    expect(view.exchange).toBeUndefined()
  })

  it('asset -> generic, no exchange (AssetAccount has no exchange_config_ids)', () => {
    const view = accountViewOf(account({ account_type: 'asset', asset_type: 'real-estate' }), CONFIGS)
    expect(view.type).toBe('generic')
    expect(view.exchange).toBeUndefined()
  })

  it('undefined specifics -> generic, no exchange', () => {
    const view = accountViewOf(account(undefined), CONFIGS)
    expect(view.type).toBe('generic')
    expect(view.exchange).toBeUndefined()
  })
})
