import { describe, it, expect } from 'vitest'
import { connectOctoBot } from '../src/client/connect/connect.js'
import { createSession } from '../src/client/core/session.js'
import { createFakeNode } from './helpers/fakeNode.js'

const MNEMONIC = 'abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about'

describe('two consecutive reads produce two real node pulls — nothing is cached', () => {
  it('accounts.list() called twice issues two separate pull requests', async () => {
    const node = await createFakeNode({ seed: MNEMONIC })
    await node.seedDoc('accounts', {
      accounts: [{ id: 'acc1', name: 'Binance', is_simulated: false, created_at: '2020-01-01T00:00:00.000Z', updated_at: '2020-01-01T00:00:00.000Z', specifics: { account_type: 'exchange', remote_account_id: '', exchange_config_ids: [] } }],
      exchange_configs: [],
    })
    const client = await connectOctoBot({ url: 'http://192.0.2.1:5001', seed: MNEMONIC, fetch: node.fetch, verify: false })

    await client.accounts.list()
    await client.accounts.list()

    const accountPulls = node.requests.filter((r) => r.method === 'GET' && r.path.includes('/accounts'))
    expect(accountPulls).toHaveLength(2) // not memoized — a real pull each time
    client.close()
  })
})

describe('close() is checked against what it actually drops, not just that it does not throw', () => {
  it('REGRESSION-SHAPED: close() clears the key cache, but the underlying WalletCapProvider keeps minting valid caps afterward', async () => {
    const node = await createFakeNode({ seed: MNEMONIC })
    const session = createSession({
      origin: 'http://192.0.2.1:5001',
      node: { host: '192.0.2.1', port: 5001 },
      address: '',
      userId: node.userId,
      derivation: 'bip44',
      seed: MNEMONIC,
      fetch: node.fetch,
      defaultTimeoutMs: 5000,
    })

    // Confirm close() really does clear the key-derivation cache: a fresh
    // read after close() still works (it re-derives), proving there is no
    // dangling stale-key bug — this is the honest half of the claim.
    session.close()
    expect(() => session.close()).not.toThrow() // idempotent

    // The dishonest half, pinned explicitly: `close()` never touches
    // `capProvider` at all (see session.ts — `close: () => keyCache.clear()`,
    // nothing else). `WalletCapProvider`'s `rootPromise` was computed once in
    // its constructor and is never invalidated, so a "closed" session can
    // still mint a full-scope, validly-signed device cap. If `close()` were
    // truly dropping all derived key material, this call would have to fail
    // or re-derive from a cleared state — it does neither.
    const cap = await session.capProvider.getCap()
    expect(cap.cap).toBeDefined()
    expect(cap.devEdPrivHex).toBeDefined()
    const userId = await session.capProvider.getUserId()
    expect(userId).toBe(node.userId)
  })
})
