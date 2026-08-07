import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import type { NodeEndpoint } from '../src/transport/urls.js'
import { nodeAuthRequest, NodeHttpError } from '../src/transport/rest.js'
import { fetchNodeDslKeywords } from '../src/node-api/dsl.js'
import { createGenericProcessBot } from '../src/node-api/octobots.js'
import { fetchNodeWalletExport } from '../src/node-api/setup.js'

const node: NodeEndpoint = { host: '192.168.1.10', port: 5001, secure: false }
const credentials = { address: '0xabc', password: 'hunter2' }

const originalFetch = globalThis.fetch

function mockFetch(response: { status?: number; body?: unknown }) {
  const fn = vi.fn(async () => ({
    ok: (response.status ?? 200) < 400,
    status: response.status ?? 200,
    json: async () => response.body ?? {},
  }))
  globalThis.fetch = fn as unknown as typeof fetch
  return fn
}

beforeEach(() => { vi.restoreAllMocks() })
afterEach(() => { globalThis.fetch = originalFetch })

describe('nodeAuthRequest', () => {
  it('sends Basic auth for address:password against the node api prefix', async () => {
    const fetchMock = mockFetch({ body: { ok: true } })
    await nodeAuthRequest(node, credentials, '/dsl/keywords')
    const [url, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit]
    expect(url).toBe('http://192.168.1.10:5001/api/v1/dsl/keywords')
    expect(init.method).toBe('GET')
    expect((init.headers as Record<string, string>).Authorization)
      .toBe(`Basic ${btoa('0xabc:hunter2')}`)
  })

  it('sends a JSON body only when one is given', async () => {
    const fetchMock = mockFetch({ body: {} })
    await nodeAuthRequest(node, credentials, '/octobots/generic-process', { method: 'POST', body: { name: 'Bo' } })
    const [, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit]
    expect(init.method).toBe('POST')
    expect(init.body).toBe(JSON.stringify({ name: 'Bo' }))
    expect((init.headers as Record<string, string>)['Content-Type']).toBe('application/json')
  })

  it('throws a NodeHttpError carrying the status on a non-2xx answer', async () => {
    mockFetch({ status: 503 })
    await expect(nodeAuthRequest(node, credentials, '/dsl/keywords'))
      .rejects.toMatchObject({ name: 'NodeHttpError', status: 503 })
  })

  it('aborts when the caller aborts', async () => {
    const controller = new AbortController()
    globalThis.fetch = ((_url: string, init: RequestInit) => new Promise((_resolve, reject) => {
      init.signal?.addEventListener('abort', () => reject(new Error('aborted')))
    })) as unknown as typeof fetch
    const pending = nodeAuthRequest(node, credentials, '/dsl/keywords', { signal: controller.signal })
    controller.abort()
    await expect(pending).rejects.toThrow('aborted')
  })
})

describe('fetchNodeDslKeywords', () => {
  it('reads the versioned keywords state', async () => {
    const state = { version: '1.0.0', keywords: [] }
    const fetchMock = mockFetch({ body: state })
    expect(await fetchNodeDslKeywords(node, credentials)).toEqual(state)
    expect(fetchMock.mock.calls[0][0]).toBe('http://192.168.1.10:5001/api/v1/dsl/keywords')
  })
})

describe('createGenericProcessBot', () => {
  it('posts the name and returns the new automation id', async () => {
    const fetchMock = mockFetch({ body: { automation_id: 'a_1' } })
    expect(await createGenericProcessBot(node, credentials, 'My bot')).toEqual({ automation_id: 'a_1' })
    const [url, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit]
    expect(url).toBe('http://192.168.1.10:5001/api/v1/octobots/generic-process')
    expect(init.body).toBe(JSON.stringify({ name: 'My bot' }))
  })

  it('surfaces the node status so the caller can explain the failure', async () => {
    mockFetch({ status: 504 })
    await expect(createGenericProcessBot(node, credentials, 'My bot'))
      .rejects.toBeInstanceOf(NodeHttpError)
  })
})

describe('fetchNodeWalletExport', () => {
  it('reads the wallet behind the presented credentials', async () => {
    const wallet = { address: '0xabc', private_key: '0xdead', seed: 'legal winner thank' }
    const fetchMock = mockFetch({ body: wallet })
    expect(await fetchNodeWalletExport(node, credentials)).toEqual(wallet)
    const [url, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit]
    expect(url).toBe('http://192.168.1.10:5001/api/v1/setup/wallet/export')
    expect((init.headers as Record<string, string>).Authorization)
      .toBe(`Basic ${btoa('0xabc:hunter2')}`)
  })

  it('keeps a key-only wallet readable (no mnemonic to return)', async () => {
    mockFetch({ body: { address: '0xabc', private_key: '0xdead', seed: null } })
    expect(await fetchNodeWalletExport(node, credentials)).toMatchObject({ seed: null })
  })

  it('surfaces a rejected password as a 401 NodeHttpError', async () => {
    mockFetch({ status: 401 })
    await expect(fetchNodeWalletExport(node, credentials))
      .rejects.toMatchObject({ name: 'NodeHttpError', status: 401 })
  })
})
