import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { parseHostInput, formatHostInput, classifyAddressSpace } from '../src/transport/urls.js'
import { detectNode } from '../src/transport/probe.js'

// ---------------------------------------------------------------------------
// parseHostInput
// ---------------------------------------------------------------------------

describe('parseHostInput', () => {
  it('returns null for empty / whitespace', () => {
    expect(parseHostInput('')).toBeNull()
    expect(parseHostInput('   ')).toBeNull()
  })

  it('bare hostname uses default port', () => {
    expect(parseHostInput('octo.example.com')).toEqual({ host: 'octo.example.com', port: 5001, secure: false })
  })

  it('hostname:port', () => {
    expect(parseHostInput('octo.example.com:8080')).toEqual({ host: 'octo.example.com', port: 8080, secure: false })
  })

  it('keeps http:// scheme, explicit port wins', () => {
    expect(parseHostInput('http://octo.example.com:5001')).toEqual({ host: 'octo.example.com', port: 5001, secure: false })
  })

  it('http:// scheme with no port defaults to 80', () => {
    expect(parseHostInput('http://octo.example.com')).toEqual({ host: 'octo.example.com', port: 80, secure: false })
  })

  it('https:// scheme with no port defaults to 443', () => {
    expect(parseHostInput('https://octo.example.com')).toEqual({ host: 'octo.example.com', port: 443, secure: true })
  })

  it('https:// scheme with explicit port keeps that port', () => {
    expect(parseHostInput('https://octo.example.com:8443')).toEqual({ host: 'octo.example.com', port: 8443, secure: true })
  })

  it('strips trailing slash and path', () => {
    expect(parseHostInput('octo.example.com:5001/some/path')).toEqual({ host: 'octo.example.com', port: 5001, secure: false })
  })

  it('IPv4', () => {
    expect(parseHostInput('192.168.1.84:5001')).toEqual({ host: '192.168.1.84', port: 5001, secure: false })
  })

  it('IPv6 in brackets with port', () => {
    expect(parseHostInput('[::1]:5001')).toEqual({ host: '[::1]', port: 5001, secure: false })
  })

  it('IPv6 in brackets without port uses default', () => {
    expect(parseHostInput('[::1]')).toEqual({ host: '[::1]', port: 5001, secure: false })
  })

  it('returns null for non-numeric port', () => {
    expect(parseHostInput('host:abc')).toBeNull()
  })

  it('returns null for out-of-range port', () => {
    expect(parseHostInput('host:99999')).toBeNull()
    expect(parseHostInput('host:0')).toBeNull()
  })

  it('respects custom defaultPort for schemeless input', () => {
    expect(parseHostInput('myhost', 8000)).toEqual({ host: 'myhost', port: 8000, secure: false })
  })
})

// ---------------------------------------------------------------------------
// formatHostInput (inverse of parseHostInput, seeds the edit screen fields)
// ---------------------------------------------------------------------------

describe('formatHostInput', () => {
  it('folds the https scheme in and blanks the implicit 443 port', () => {
    expect(formatHostInput({ host: 'octo.example.com', port: 443, secure: true })).toEqual({
      host: 'https://octo.example.com',
      port: '',
    })
  })

  it('keeps an explicit non-default https port', () => {
    expect(formatHostInput({ host: 'octo.example.com', port: 8443, secure: true })).toEqual({
      host: 'https://octo.example.com',
      port: '8443',
    })
  })

  it('folds the http scheme in and blanks the implicit 80 port', () => {
    expect(formatHostInput({ host: 'octo.example.com', port: 80, secure: false })).toEqual({
      host: 'http://octo.example.com',
      port: '',
    })
  })

  it('leaves a legacy schemeless local node untouched', () => {
    expect(formatHostInput({ host: '192.168.1.84', port: 5001, secure: false })).toEqual({
      host: '192.168.1.84',
      port: '5001',
    })
  })

  // The round-trip property the edit-screen bug violated: for any stored node,
  // re-parsing the reconstructed fields must yield the original triple.
  it('round-trips through parseHostInput for every node shape', () => {
    // Mirrors host.tsx's field join: `host ? (port ? `${host}:${port}` : host) : ''`.
    const join = ({ host, port }: { host: string; port: string }) =>
      host ? (port ? `${host}:${port}` : host) : ''

    const nodes = [
      { host: 'octo.example.com', port: 443, secure: true }, // https, no port
      { host: 'octo.example.com', port: 8443, secure: true }, // https, custom port
      { host: 'octo.example.com', port: 80, secure: false }, // http, no port
      { host: '192.168.1.84', port: 5001, secure: false }, // legacy local
    ]

    for (const node of nodes) {
      expect(parseHostInput(join(formatHostInput(node)))).toEqual(node)
    }
  })
})

// ---------------------------------------------------------------------------
// detectNode
// ---------------------------------------------------------------------------

function makeFetch(impl: (url: string, init?: RequestInit) => Promise<Response>) {
  return vi.spyOn(globalThis, 'fetch').mockImplementation(impl as typeof fetch)
}

function makeResponse(status: number, body: unknown): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  } as unknown as Response
}

function makeSignalAwareFetch(resolve?: unknown) {
  return makeFetch((_url, init) => new Promise<Response>((res, rej) => {
    const signal = init?.signal
    if (signal?.aborted) { rej(new DOMException('Aborted', 'AbortError')); return }
    signal?.addEventListener('abort', () => rej(new DOMException('Aborted', 'AbortError')))
    if (resolve !== undefined) res(makeResponse(200, resolve))
  }))
}

beforeEach(() => { vi.useFakeTimers() })
afterEach(() => { vi.restoreAllMocks(); vi.useRealTimers() })

describe('detectNode', () => {
  it('returns reachable with configured=true', async () => {
    makeFetch(async () => makeResponse(200, { configured: true }))
    const result = await detectNode('localhost', 5001)
    expect(result).toEqual({ status: 'reachable', configured: true })
  })

  it('returns reachable with configured=false', async () => {
    makeFetch(async () => makeResponse(200, { configured: false }))
    const result = await detectNode('localhost', 5001)
    expect(result).toEqual({ status: 'reachable', configured: false })
  })

  it('returns invalid-response when JSON is missing configured field', async () => {
    makeFetch(async () => makeResponse(200, { foo: 'bar' }))
    const result = await detectNode('localhost', 5001)
    expect(result).toEqual({ status: 'unreachable', reason: 'invalid-response' })
  })

  it('returns invalid-response when configured is a string', async () => {
    makeFetch(async () => makeResponse(200, { configured: 'true' }))
    const result = await detectNode('localhost', 5001)
    expect(result).toEqual({ status: 'unreachable', reason: 'invalid-response' })
  })

  it('returns invalid-response when configured is a number', async () => {
    makeFetch(async () => makeResponse(200, { configured: 1 }))
    const result = await detectNode('localhost', 5001)
    expect(result).toEqual({ status: 'unreachable', reason: 'invalid-response' })
  })

  it('ignores extra fields alongside configured', async () => {
    makeFetch(async () => makeResponse(200, { configured: true, name: 'My Bot', version: 'v1' }))
    const result = await detectNode('localhost', 5001)
    expect(result).toEqual({ status: 'reachable', configured: true })
  })

  it('returns invalid-response when response body is not JSON', async () => {
    makeFetch(async () => ({
      ok: true,
      status: 200,
      json: async () => { throw new SyntaxError('Unexpected token') },
    } as unknown as Response))
    const result = await detectNode('localhost', 5001)
    expect(result).toEqual({ status: 'unreachable', reason: 'invalid-response' })
  })

  it('returns http-error on non-2xx status', async () => {
    makeFetch(async () => makeResponse(404, null))
    const result = await detectNode('localhost', 5001)
    expect(result).toEqual({ status: 'unreachable', reason: 'http-error', detail: '404' })
  })

  it('returns refused on network error', async () => {
    makeFetch(async () => { throw new TypeError('Failed to fetch') })
    const result = await detectNode('localhost', 5001)
    expect(result).toEqual({ status: 'unreachable', reason: 'refused', detail: 'Failed to fetch' })
  })

  it('returns timeout when request exceeds timeoutMs', async () => {
    makeSignalAwareFetch() // never resolves without abort
    const probePromise = detectNode('localhost', 5001, false, { timeoutMs: 100 })
    await vi.advanceTimersByTimeAsync(200)
    const result = await probePromise
    expect(result).toEqual({ status: 'unreachable', reason: 'timeout' })
  })

  it('returns idle when caller signal is aborted', async () => {
    makeSignalAwareFetch()
    const controller = new AbortController()
    const probePromise = detectNode('localhost', 5001, false, { signal: controller.signal, timeoutMs: 5000 })
    controller.abort()
    await vi.advanceTimersByTimeAsync(100)
    const result = await probePromise
    expect(result).toEqual({ status: 'idle' })
  })
})

// ---------------------------------------------------------------------------
// classifyAddressSpace
// ---------------------------------------------------------------------------

describe('classifyAddressSpace', () => {
  it('recognises loopback', () => {
    expect(classifyAddressSpace('localhost')).toBe('loopback')
    expect(classifyAddressSpace('LOCALHOST')).toBe('loopback')
    expect(classifyAddressSpace('dev.localhost')).toBe('loopback')
    expect(classifyAddressSpace('127.0.0.1')).toBe('loopback')
    // The whole of 127/8 is loopback, not just .0.0.1.
    expect(classifyAddressSpace('127.42.7.9')).toBe('loopback')
    expect(classifyAddressSpace('[::1]')).toBe('loopback')
    expect(classifyAddressSpace('::1')).toBe('loopback')
  })

  it('recognises the private IPv4 ranges', () => {
    expect(classifyAddressSpace('10.0.0.1')).toBe('local')
    expect(classifyAddressSpace('192.168.1.42')).toBe('local')
    expect(classifyAddressSpace('169.254.1.1')).toBe('local')
    expect(classifyAddressSpace('100.64.0.1')).toBe('local')
  })

  it('gets the 172.16/12 boundaries right', () => {
    // The range is 172.16 through 172.31 — the neighbours on both sides are
    // ordinary public addresses, and a naive `a === 172` test would claim them.
    expect(classifyAddressSpace('172.15.0.1')).toBe('public')
    expect(classifyAddressSpace('172.16.0.1')).toBe('local')
    expect(classifyAddressSpace('172.31.255.254')).toBe('local')
    expect(classifyAddressSpace('172.32.0.1')).toBe('public')
  })

  it('gets the 100.64/10 boundaries right', () => {
    expect(classifyAddressSpace('100.63.0.1')).toBe('public')
    expect(classifyAddressSpace('100.127.255.254')).toBe('local')
    expect(classifyAddressSpace('100.128.0.1')).toBe('public')
  })

  it('recognises IPv6 unique-local and link-local, bracketed or bare', () => {
    expect(classifyAddressSpace('fd00::1')).toBe('local')
    expect(classifyAddressSpace('[fc00::1]')).toBe('local')
    expect(classifyAddressSpace('fe80::1')).toBe('local')
    expect(classifyAddressSpace('[febf::1]')).toBe('local')
    // fe7f and fec0 sit just outside fe80::/10.
    expect(classifyAddressSpace('fe7f::1')).toBe('public')
    expect(classifyAddressSpace('fec0::1')).toBe('public')
    expect(classifyAddressSpace('2001:4860:4860::8888')).toBe('public')
  })

  it('strips an IPv6 zone id before classifying', () => {
    expect(classifyAddressSpace('fe80::1%en0')).toBe('local')
  })

  it('follows an IPv4-mapped IPv6 address to the mapped space', () => {
    expect(classifyAddressSpace('::ffff:127.0.0.1')).toBe('loopback')
    expect(classifyAddressSpace('::ffff:192.168.0.5')).toBe('local')
    expect(classifyAddressSpace('::ffff:8.8.8.8')).toBe('public')
  })

  it('treats .local names as local', () => {
    expect(classifyAddressSpace('octobot.local')).toBe('local')
    expect(classifyAddressSpace('OctoBot.Local')).toBe('local')
    // A trailing root dot does not change what the name means.
    expect(classifyAddressSpace('octobot.local.')).toBe('local')
  })

  it('treats anything it cannot decide from the string as public', () => {
    // This is the point of the function: a DNS name that happens to resolve to
    // a LAN box is still `public` here, because that is what a browser assumes
    // before it resolves anything.
    expect(classifyAddressSpace('node.example.com')).toBe('public')
    expect(classifyAddressSpace('8.8.8.8')).toBe('public')
    expect(classifyAddressSpace('')).toBe('public')
    expect(classifyAddressSpace('   ')).toBe('public')
    // Not a valid literal, so it would be resolved as a name.
    expect(classifyAddressSpace('192.168.1.999')).toBe('public')
    expect(classifyAddressSpace('999.0.0.1')).toBe('public')
  })
})
