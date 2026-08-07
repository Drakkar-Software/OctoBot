import { describe, it, expect } from 'vitest'
import type { StarfishClient } from '@drakkar.software/starfish-client'
import { createReadOnlyOctoBotClient } from '../src/client/connect/readOnly.js'
import type { ClientSession } from '../src/client/core/session.js'
import { createSecretEncryptor } from '../src/crypto/secretEncryptor.js'
import { STARFISH_ENCRYPTION_SALT } from '../src/crypto/wireConstants.js'
import { pullPath } from '../src/collections/paths.js'
import { NODE_COLLECTIONS, type NodeCollectionKey } from '../src/collections/nodeCollections.js'
import { strategy } from '../src/client/strategy.js'
import { decodeActionProposal } from '../src/protocol/proposal.js'
import { OctoBotScopeError } from '../src/client/core/errors.js'

const ENCRYPTION_SECRET = '0x' + '11'.repeat(32)
const USER_ID = 'user123'
const ORIGINAL_CREATED_AT = '2020-01-01T00:00:00.000Z'
// Mirrors `createReadOnlyPairing`'s default grant — only these two
// collections have a key on a real read-only session.
const GRANTED_COLLECTIONS: readonly NodeCollectionKey[] = ['userData', 'accounts']

function fakeReadOnlySession(docs: { accounts?: Record<string, unknown>; userData?: Record<string, unknown> }): ClientSession {
  const accountsInfo = NODE_COLLECTIONS.accounts
  const userDataInfo = NODE_COLLECTIONS.userData
  const accountsPath = pullPath(accountsInfo.storagePath, { identity: USER_ID })
  const userDataPath = pullPath(userDataInfo.storagePath, { identity: USER_ID })
  const accountsEncryptor = createSecretEncryptor(ENCRYPTION_SECRET, STARFISH_ENCRYPTION_SALT, accountsInfo.encryptionInfo)
  const userDataEncryptor = createSecretEncryptor(ENCRYPTION_SECRET, STARFISH_ENCRYPTION_SALT, userDataInfo.encryptionInfo)

  const syncClient = {
    pull: async (p: string) => {
      if (p === accountsPath) return { data: await accountsEncryptor.encrypt(docs.accounts ?? {}), hash: 'h1' }
      if (p === userDataPath) return { data: await userDataEncryptor.encrypt(docs.userData ?? {}), hash: 'h2' }
      throw new Error(`unexpected pull path ${p}`)
    },
    push: async () => { throw new Error('read-only session: push must never be called') },
    append: async () => { throw new Error('read-only session: append must never be called') },
  } as unknown as StarfishClient

  return {
    origin: 'http://192.0.2.1:5001',
    node: { host: '192.0.2.1', port: 5001 },
    userId: USER_ID,
    fetch: (() => Promise.reject(new Error('no network in this test'))) as unknown as typeof fetch,
    defaultTimeoutMs: 1000,
    capProvider: {
      getCap: async () => { throw new Error('not exercised in this test') },
      getUserId: async () => USER_ID,
    } as ClientSession['capProvider'],
    syncClient,
    // Mirrors the real read-only session's gate: only GRANTED_COLLECTIONS
    // resolve an encryptor, matching OctoBotScopeError's contract.
    async collectionEncryptor(collection) {
      if (!GRANTED_COLLECTIONS.includes(collection)) throw new OctoBotScopeError(collection)
      return createSecretEncryptor(ENCRYPTION_SECRET, STARFISH_ENCRYPTION_SALT, NODE_COLLECTIONS[collection].encryptionInfo)
    },
    close: () => {},
  }
}

describe('createReadOnlyOctoBotClient — accounts', () => {
  it('list()/get() read normally', async () => {
    const session = fakeReadOnlySession({
      accounts: { accounts: [{ id: 'acc1', name: 'Binance', is_simulated: false, created_at: ORIGINAL_CREATED_AT, updated_at: ORIGINAL_CREATED_AT, specifics: { account_type: 'exchange', remote_account_id: '', exchange_config_ids: [] } }], exchange_configs: [] },
    })
    const client = createReadOnlyOctoBotClient(session)
    const all = await client.accounts.list()
    expect(all).toHaveLength(1)
    expect(await client.accounts.get('acc1')).not.toBeNull()
    expect(await client.accounts.get('missing')).toBeNull()
  })

  it('create() builds the action(s) and returns a proposal, never appends', async () => {
    const session = fakeReadOnlySession({ accounts: { accounts: [], exchange_configs: [] } })
    const client = createReadOnlyOctoBotClient(session)
    const proposed = await client.accounts.create({
      name: 'New', type: 'exchange', exchange: 'binance', credentials: { apiKey: 'k', apiSecret: 's' },
    })
    expect(proposed.actions.map((a) => (a as { action_type: string }).action_type)).toEqual([
      'account_auth_create', 'exchange_config_create', 'account_create',
    ])
    const decoded = decodeActionProposal(proposed.payload)
    expect(decoded.actions).toHaveLength(3)
    expect(decoded.label).toContain('New')
  })

  it('update() preserves created_at via a read, still never appends', async () => {
    const session = fakeReadOnlySession({
      accounts: { accounts: [{ id: 'acc1', name: 'Old', is_simulated: false, created_at: ORIGINAL_CREATED_AT, updated_at: ORIGINAL_CREATED_AT, specifics: { account_type: 'exchange', remote_account_id: '', exchange_config_ids: [] } }], exchange_configs: [] },
    })
    const client = createReadOnlyOctoBotClient(session)
    const proposed = await client.accounts.update('acc1', {
      id: 'acc1', name: 'Renamed', type: 'exchange', exchange: 'binance', credentials: { apiKey: 'k2', apiSecret: 's2' },
    })
    const accountEdit = proposed.actions.find((a) => (a as { action_type: string }).action_type === 'account_edit') as { configuration: { created_at: string } }
    expect(accountEdit.configuration.created_at).toBe(ORIGINAL_CREATED_AT)
  })

  it('delete() proposes all three companion deletes', async () => {
    const session = fakeReadOnlySession({ accounts: { accounts: [], exchange_configs: [] } })
    const client = createReadOnlyOctoBotClient(session)
    const proposed = await client.accounts.delete('acc1')
    expect(proposed.actions.map((a) => (a as { action_type: string }).action_type)).toEqual([
      'account_delete', 'account_auth_delete', 'exchange_config_delete',
    ])
  })
})

describe('createReadOnlyOctoBotClient — automations', () => {
  it('create() proposes strategy_create then automation_create, ordered', async () => {
    const session = fakeReadOnlySession({ userData: {} })
    const client = createReadOnlyOctoBotClient(session)
    const dca = strategy.dca({ pairs: ['BTC/USDT'], buyOrderAmount: '25' })
    const proposed = await client.automations.create({ name: 'My DCA', strategy: dca, accountIds: ['acc1'] })
    const decoded = decodeActionProposal(proposed.payload)
    expect(decoded.actions).toHaveLength(2)
    expect((decoded.actions[0].configuration as { action_type: string }).action_type).toBe('strategy_create')
    expect(decoded.actions[0].after).toBeUndefined()
    expect((decoded.actions[1].configuration as { action_type: string }).action_type).toBe('automation_create')
    expect(decoded.actions[1].after).toBe('previous-confirmed')
  })

  it('stop() proposes a single automation_stop', async () => {
    const session = fakeReadOnlySession({ userData: {} })
    const client = createReadOnlyOctoBotClient(session)
    const proposed = await client.automations.stop('auto_1')
    expect(proposed.actions).toHaveLength(1)
    expect((proposed.actions[0] as { action_type: string }).action_type).toBe('automation_stop')
  })
})

describe('createReadOnlyOctoBotClient — strategies', () => {
  it('create()/update()/delete() all propose, never append', async () => {
    const session = fakeReadOnlySession({ userData: {} })
    const client = createReadOnlyOctoBotClient(session)
    const dca = strategy.dca({ pairs: ['BTC/USDT'], buyOrderAmount: '25' })
    const created = await client.strategies.create(dca)
    expect((created.actions[0] as { action_type: string }).action_type).toBe('strategy_create')
    const updated = await client.strategies.update(dca)
    expect((updated.actions[0] as { action_type: string }).action_type).toBe('strategy_edit')
    const deleted = await client.strategies.delete(dca.id)
    expect((deleted.actions[0] as { action_type: string }).action_type).toBe('strategy_delete')
  })
})

describe('createReadOnlyOctoBotClient — documents (the escape hatch)', () => {
  it('pull() works for a granted collection', async () => {
    const session = fakeReadOnlySession({ accounts: { accounts: [], exchange_configs: [] } })
    const client = createReadOnlyOctoBotClient(session)
    const { data } = await client.documents.pull('accounts')
    expect(data).toEqual({ accounts: [], exchange_configs: [] })
  })

  it('pull() throws OctoBotScopeError for a collection outside the default grant', async () => {
    const session = fakeReadOnlySession({})
    const client = createReadOnlyOctoBotClient(session)
    await expect(client.documents.pull('settings')).rejects.toThrow(OctoBotScopeError)
  })

  it('raw.encryptorFor() is gated the same way as pull()', async () => {
    const session = fakeReadOnlySession({})
    const client = createReadOnlyOctoBotClient(session)
    await expect(client.documents.raw.encryptorFor('accounts')).resolves.toBeDefined()
    await expect(client.documents.raw.encryptorFor('strategies')).rejects.toThrow(OctoBotScopeError)
  })

  it('exposes no push, append, sync, or capProvider — no way to bypass the collection gate', () => {
    const session = fakeReadOnlySession({})
    const client = createReadOnlyOctoBotClient(session)
    expect('push' in client.documents).toBe(false)
    expect('append' in client.documents).toBe(false)
    expect('sync' in client.documents.raw).toBe(false)
    expect('capProvider' in client.documents.raw).toBe(false)
    expect('pushPath' in client.documents.raw).toBe(false)
  })

  it('exposes no settings or node namespace at all', () => {
    const session = fakeReadOnlySession({})
    const client = createReadOnlyOctoBotClient(session)
    expect('settings' in client).toBe(false)
    expect('node' in client).toBe(false)
  })

  it('close() never throws, even though there is no derived-key cache to clear', () => {
    const session = fakeReadOnlySession({})
    const client = createReadOnlyOctoBotClient(session)
    expect(() => client.close()).not.toThrow()
  })
})
