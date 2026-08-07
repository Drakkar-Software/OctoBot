import { describe, it, expect } from 'vitest'
import type { StarfishClient } from '@drakkar.software/starfish-client'
import type { UserActionConfiguration } from '@drakkar.software/octobot-protocol'
import { createAccountsApi } from '../src/client/adapters/accounts.js'
import type { ClientSession } from '../src/client/core/session.js'
import { createSecretEncryptor } from '../src/crypto/secretEncryptor.js'
import { STARFISH_ENCRYPTION_SALT } from '../src/crypto/wireConstants.js'
import { pullPath } from '../src/collections/paths.js'
import { NODE_COLLECTIONS } from '../src/collections/nodeCollections.js'

const ENCRYPTION_SECRET = '0x' + '11'.repeat(32)
const USER_ID = 'user123'
const ORIGINAL_CREATED_AT = '2020-01-01T00:00:00.000Z'

function fakeSession(existingAccountsDoc: Record<string, unknown>): ClientSession {
  const info = NODE_COLLECTIONS.accounts
  const path = pullPath(info.storagePath, { identity: USER_ID })
  const encryptor = createSecretEncryptor(ENCRYPTION_SECRET, STARFISH_ENCRYPTION_SALT, info.encryptionInfo)

  const syncClient = {
    pull: async (p: string) => {
      if (p !== path) throw new Error(`unexpected pull path ${p}`)
      const data = await encryptor.encrypt(existingAccountsDoc)
      return { data, hash: 'h1' }
    },
    push: async () => ({ hash: 'h2' }),
    append: async () => undefined,
  } as unknown as StarfishClient

  return {
    origin: 'http://192.0.2.1:5001',
    node: { host: '192.0.2.1', port: 5001 },
    userId: USER_ID,
    fetch: (() => Promise.reject(new Error('no network in this test'))) as unknown as typeof fetch,
    defaultTimeoutMs: 1000,
    capProvider: {} as ClientSession['capProvider'],
    syncClient,
    collectionEncryptor: async (collection) =>
      createSecretEncryptor(ENCRYPTION_SECRET, STARFISH_ENCRYPTION_SALT, NODE_COLLECTIONS[collection].encryptionInfo),
    close: () => {},
  }
}

describe('accounts.create()', () => {
  it('emits auth+exchange-config creates before the account create', async () => {
    const session = fakeSession({ accounts: [], exchange_configs: [] })
    const emitted: UserActionConfiguration[] = []
    const appendAction = async (configuration: UserActionConfiguration) => {
      emitted.push(configuration)
      return `action_${emitted.length}`
    }

    const api = createAccountsApi(session, appendAction)
    const handle = await api.create({
      name: 'New',
      type: 'exchange',
      exchange: 'binance',
      credentials: { apiKey: 'k', apiSecret: 's' },
    })
    await handle.settled().catch(() => undefined)

    const actionTypes = emitted.map((c) => (c as { action_type: string }).action_type)
    expect(actionTypes).toEqual(['account_auth_create', 'exchange_config_create', 'account_create'])
  })
})

describe('accounts.update()', () => {
  it('emits credential/exchange-config edits before the account edit', async () => {
    const session = fakeSession({
      accounts: [{ id: 'acc1', name: 'Old', is_simulated: false, created_at: ORIGINAL_CREATED_AT, updated_at: ORIGINAL_CREATED_AT, specifics: { account_type: 'exchange', remote_account_id: '', exchange_config_ids: [] } }],
      exchange_configs: [],
    })
    const emitted: UserActionConfiguration[] = []
    const appendAction = async (configuration: UserActionConfiguration) => {
      emitted.push(configuration)
      return `action_${emitted.length}`
    }

    const api = createAccountsApi(session, appendAction)
    const handle = await api.update('acc1', {
      id: 'acc1',
      name: 'Renamed',
      type: 'exchange',
      exchange: 'binance',
      credentials: { apiKey: 'new-key', apiSecret: 'new-secret' },
    })
    await handle.settled().catch(() => undefined) // afterSettle() pulls again; irrelevant to this assertion

    const actionTypes = emitted.map((c) => (c as { action_type: string }).action_type)
    expect(actionTypes).toEqual(['account_auth_edit', 'exchange_config_edit', 'account_edit'])
  })

  it('preserves the existing created_at instead of re-stamping it to now', async () => {
    const session = fakeSession({
      accounts: [{ id: 'acc1', name: 'Old', is_simulated: false, created_at: ORIGINAL_CREATED_AT, updated_at: ORIGINAL_CREATED_AT, specifics: { account_type: 'exchange', remote_account_id: '', exchange_config_ids: [] } }],
      exchange_configs: [],
    })
    const emitted: UserActionConfiguration[] = []
    const appendAction = async (configuration: UserActionConfiguration) => {
      emitted.push(configuration)
      return `action_${emitted.length}`
    }

    const api = createAccountsApi(session, appendAction)
    const handle = await api.update('acc1', {
      id: 'acc1',
      name: 'Renamed',
      type: 'exchange',
      exchange: 'binance',
      credentials: { apiKey: 'new-key', apiSecret: 'new-secret' },
    })
    await handle.settled().catch(() => undefined)

    const accountEdit = emitted.find((c) => (c as { action_type: string }).action_type === 'account_edit') as { configuration: { created_at: string } }
    expect(accountEdit.configuration.created_at).toBe(ORIGINAL_CREATED_AT)
  })

  it('emits only the auth edit before the account edit for a wallet account (no exchange config)', async () => {
    const session = fakeSession({
      accounts: [{ id: 'acc1', name: 'Old', is_simulated: false, created_at: ORIGINAL_CREATED_AT, updated_at: ORIGINAL_CREATED_AT, specifics: { account_type: 'generic' } }],
      exchange_configs: [],
    })
    const emitted: UserActionConfiguration[] = []
    const appendAction = async (configuration: UserActionConfiguration) => {
      emitted.push(configuration)
      return `action_${emitted.length}`
    }

    const api = createAccountsApi(session, appendAction)
    const handle = await api.update('acc1', {
      id: 'acc1',
      name: 'Renamed',
      type: 'wallet',
      address: '0x' + '33'.repeat(20),
    })
    await handle.settled().catch(() => undefined)

    const actionTypes = emitted.map((c) => (c as { action_type: string }).action_type)
    expect(actionTypes).toEqual(['account_auth_edit', 'account_edit'])
  })
})
