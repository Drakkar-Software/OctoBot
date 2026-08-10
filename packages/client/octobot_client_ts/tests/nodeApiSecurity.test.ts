import { describe, it, expect, vi, afterEach } from 'vitest'
import { createNodeApi } from '../src/client/adapters/nodeApi.js'
import type { ClientSession } from '../src/client/core/session.js'
import { OctoBotConfigError } from '../src/client/core/errors.js'

const NODE = { host: '192.0.2.1', port: 5001 }

function fakeSessionWithoutBasicAuth(fetchSpy: typeof fetch): ClientSession {
  return {
    origin: 'http://192.0.2.1:5001',
    node: NODE,
    userId: 'user123',
    fetch: fetchSpy,
    defaultTimeoutMs: 1000,
    basicAuth: undefined,
    capProvider: {} as ClientSession['capProvider'],
    syncClient: {} as ClientSession['syncClient'],
    collectionEncryptor: async () => {
      throw new Error('not exercised in this test')
    },
    close: () => {},
  }
}

describe('a credential-requiring node.* call throws OctoBotConfigError before any fetch', () => {
  const originalFetch = globalThis.fetch

  afterEach(() => {
    globalThis.fetch = originalFetch
  })

  it('dslKeywords/exportWallet/createGenericProcessBot all reject with OctoBotConfigError and never call fetch, absent basicAuth', async () => {
    const spy = vi.fn(() => Promise.reject(new Error('fetch should never be called')))
    globalThis.fetch = spy as unknown as typeof fetch
    const session = fakeSessionWithoutBasicAuth(spy as unknown as typeof fetch)
    const api = createNodeApi(session)

    await expect(api.dslKeywords()).rejects.toThrow(OctoBotConfigError)
    await expect(api.exportWallet()).rejects.toThrow(OctoBotConfigError)
    await expect(api.createGenericProcessBot('bot')).rejects.toThrow(OctoBotConfigError)
    expect(spy).not.toHaveBeenCalled()
  })

  it('the config-error message names ConnectOptions.basicAuth so a caller knows what to add', async () => {
    const session = fakeSessionWithoutBasicAuth((() => Promise.reject(new Error('unused'))) as unknown as typeof fetch)
    const api = createNodeApi(session)
    await expect(api.dslKeywords()).rejects.toThrow(/basicAuth/)
  })
})

describe('no node.* error ever leaks the basicAuth password', () => {
  const originalFetch = globalThis.fetch
  const SENTINEL = 'SENTINEL_PW_do_not_leak'

  afterEach(() => {
    globalThis.fetch = originalFetch
  })

  function sessionWithBasicAuth(fetchImpl: typeof fetch): ClientSession {
    return {
      origin: 'http://192.0.2.1:5001',
      node: NODE,
      userId: 'user123',
      fetch: fetchImpl,
      defaultTimeoutMs: 1000,
      basicAuth: { address: '0x' + '11'.repeat(20), password: SENTINEL },
      capProvider: {} as ClientSession['capProvider'],
      syncClient: {} as ClientSession['syncClient'],
      collectionEncryptor: async () => {
        throw new Error('not exercised')
      },
      close: () => {},
    }
  }

  const encodedSentinel = btoa(`${'0x' + '11'.repeat(20)}:${SENTINEL}`)

  async function assertNoLeak(work: () => Promise<unknown>) {
    let caught: unknown
    try {
      await work()
      throw new Error('expected the call to reject')
    } catch (err) {
      caught = err
    }
    const asString = JSON.stringify(caught, Object.getOwnPropertyNames(caught as object))
    expect(asString).not.toContain(SENTINEL)
    expect(asString).not.toContain(encodedSentinel)
    let cause = (caught as { cause?: unknown }).cause
    let depth = 0
    while (cause && depth < 5) {
      const causeString = JSON.stringify(cause, Object.getOwnPropertyNames(cause as object))
      expect(causeString).not.toContain(SENTINEL)
      expect(causeString).not.toContain(encodedSentinel)
      cause = (cause as { cause?: unknown }).cause
      depth++
    }
  }

  it('a 401/403/503 response never echoes the password back through the error', async () => {
    globalThis.fetch = (async () => new Response('unauthorized', { status: 401 })) as unknown as typeof fetch
    const api = createNodeApi(sessionWithBasicAuth(globalThis.fetch))
    await assertNoLeak(() => api.exportWallet())
  })

  it('a network TypeError whose own message embeds request context never leaks the password either', async () => {
    globalThis.fetch = (async (input: RequestInfo | URL) => {
      throw new TypeError(`network error fetching ${String(input)}`)
    }) as unknown as typeof fetch
    const api = createNodeApi(sessionWithBasicAuth(globalThis.fetch))
    await assertNoLeak(() => api.dslKeywords())
  })

  it('a non-JSON 200 body never leaks the password', async () => {
    globalThis.fetch = (async () => new Response('<html>not json</html>', { status: 200 })) as unknown as typeof fetch
    const api = createNodeApi(sessionWithBasicAuth(globalThis.fetch))
    await assertNoLeak(() => api.exportWallet())
  })
})

describe('every node.* REST call goes through the injected fetch, not globalThis.fetch', () => {
  const originalFetch = globalThis.fetch

  afterEach(() => {
    globalThis.fetch = originalFetch
  })

  it('REGRESSION: every node.* REST call goes through the injected fetch, not globalThis.fetch — all seven methods', async () => {
    // globalThis.fetch is made to fail outright so any call that fell
    // through to it (the confirmed gap this test used to document) would be
    // unambiguous, not just unobserved.
    globalThis.fetch = (async () => {
      throw new Error('used globalThis.fetch instead of the injected one')
    }) as unknown as typeof fetch

    const injected = vi.fn(async () => new Response(JSON.stringify({ automation_id: 'a_1' }), { status: 200 }))
    const session: ClientSession = {
      origin: 'http://192.0.2.1:5001',
      node: NODE,
      userId: 'user123',
      fetch: injected as unknown as typeof fetch,
      defaultTimeoutMs: 1000,
      basicAuth: { address: '0x' + '11'.repeat(20), password: 'pw' },
      capProvider: {} as ClientSession['capProvider'],
      syncClient: {} as ClientSession['syncClient'],
      collectionEncryptor: async () => {
        throw new Error('not exercised')
      },
      close: () => {},
    }
    const api = createNodeApi(session)

    // README.md sells ConnectOptions.fetch as the hook for proxies, mTLS,
    // and React Native polyfills. Confirmed via source read that six of the
    // seven node.* REST calls used to bypass it entirely (transport/rest.ts's
    // nodeRequest/nodeAuthRequest and node-api/marketMaking.ts called the
    // bare module-global `fetch`). Fixed by threading an optional `fetch`
    // through nodeRequest/nodeAuthRequest and every node-api/*.ts fetcher,
    // the same way transport/probe.ts's detectNode already did, and wiring
    // session.fetch through nodeApi.ts's six remaining methods. Every call
    // below must succeed against ONLY the injected fetch.
    await expect(api.status()).resolves.toBeDefined()
    await expect(api.tradedPairs({ id: 'x', name: 'x', exchange: 'binance' })).resolves.toBeDefined()
    await expect(api.predictedOrderBook({ id: 'x', name: 'x', exchange: 'binance' }, {} as never)).resolves.toBeDefined()
    await expect(api.requiredFunds({ id: 'x', name: 'x', exchange: 'binance' }, {} as never)).resolves.toBeDefined()
    await expect(api.dslKeywords()).resolves.toBeDefined()
    await expect(api.exportWallet()).resolves.toBeDefined()
    await expect(api.createGenericProcessBot('bot')).resolves.toBeDefined()

    expect(injected).toHaveBeenCalledTimes(7)
  })
})
