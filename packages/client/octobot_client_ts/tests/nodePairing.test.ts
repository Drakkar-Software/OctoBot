import { afterEach, describe, expect, it, vi } from 'vitest'
import { parseNodePairingQr, parsePairingHost, verifyNodeCredentials } from '../src/node-api/pairing.js'

describe('parseNodePairingQr', () => {
  it('reads a current payload, whose password is the wallet itself', () => {
    const data = JSON.stringify({ url: 'https://octo.example.com', address: '0xabc', password: 'hunter2' })
    expect(parseNodePairingQr(data)).toEqual({
      url: 'https://octo.example.com',
      address: '0xabc',
      secret: 'hunter2',
      secretKind: 'wallet',
    })
  })

  it('reads a legacy payload, whose passphrase is only the node password', () => {
    // Nodes keep emitting this until their operator upgrades, so dropping it
    // would break every QR already in the wild.
    const data = JSON.stringify({ url: 'https://octo.example.com', address: '0xabc', passphrase: 'hunter2' })
    expect(parseNodePairingQr(data)).toEqual({
      url: 'https://octo.example.com',
      address: '0xabc',
      secret: 'hunter2',
      secretKind: 'credential',
    })
  })

  it('prefers the wallet when a payload carries both fields', () => {
    const data = JSON.stringify({ url: 'http://x', address: 'a', password: 'w', passphrase: 'p' })
    expect(parseNodePairingQr(data)).toEqual({
      url: 'http://x',
      address: 'a',
      secret: 'w',
      secretKind: 'wallet',
    })
  })

  it('trims surrounding whitespace before parsing', () => {
    const data = `  ${JSON.stringify({ url: 'http://1.2.3.4:5001', address: 'addr', password: 'pw' })}  `
    expect(parseNodePairingQr(data)).toEqual({
      url: 'http://1.2.3.4:5001',
      address: 'addr',
      secret: 'pw',
      secretKind: 'wallet',
    })
  })

  it('returns null for a raw seed phrase', () => {
    expect(parseNodePairingQr('apple banana cherry')).toBeNull()
  })

  it('returns null for a raw EVM private key', () => {
    expect(parseNodePairingQr(`0x${'1'.repeat(64)}`)).toBeNull()
  })

  it('returns null when JSON is missing a required field', () => {
    expect(parseNodePairingQr(JSON.stringify({ url: 'https://octo.example.com', address: '0xabc' }))).toBeNull()
    expect(parseNodePairingQr(JSON.stringify({ address: '0xabc', password: 'pw' }))).toBeNull()
    expect(parseNodePairingQr(JSON.stringify({ url: 'https://octo.example.com', password: 'pw' }))).toBeNull()
  })

  it('returns null when a field has the wrong type', () => {
    expect(parseNodePairingQr(JSON.stringify({ url: 1, address: '0xabc', password: 'pw' }))).toBeNull()
    expect(parseNodePairingQr(JSON.stringify({ url: 'http://x', address: 'a', password: 42 }))).toBeNull()
  })

  it('returns null for malformed JSON', () => {
    expect(parseNodePairingQr('{not json')).toBeNull()
  })

  it('returns null for JSON that is not an object', () => {
    expect(parseNodePairingQr('"just a string"')).toBeNull()
    expect(parseNodePairingQr('42')).toBeNull()
    expect(parseNodePairingQr('null')).toBeNull()
  })
})

describe('parsePairingHost', () => {
  it('derives host/port/secure from a https url', () => {
    expect(parsePairingHost('https://octo.example.com')).toEqual({ host: 'octo.example.com', port: 443, secure: true })
  })

  it('derives host/port/secure from a http url with explicit port', () => {
    expect(parsePairingHost('http://192.168.1.50:5001')).toEqual({ host: '192.168.1.50', port: 5001, secure: false })
  })

  it('returns null for an empty url', () => {
    expect(parsePairingHost('')).toBeNull()
  })
})

describe('verifyNodeCredentials', () => {
  const originalFetch = global.fetch

  afterEach(() => {
    global.fetch = originalFetch
    vi.restoreAllMocks()
  })

  it('returns authorized on a 200 response and sends Basic auth for address:password', async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, status: 200 })
    global.fetch = fetchMock as unknown as typeof fetch

    const result = await verifyNodeCredentials('http://1.2.3.4:5001', 'addr', 'pw')

    expect(result).toEqual({ status: 'authorized' })
    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toBe('http://1.2.3.4:5001/api/v1/login/test')
    expect(init.headers.Authorization).toBe(`Basic ${btoa('addr:pw')}`)
  })

  it('returns unauthorized on a 401 response', async () => {
    global.fetch = vi.fn().mockResolvedValue({ ok: false, status: 401 }) as unknown as typeof fetch
    expect(await verifyNodeCredentials('http://1.2.3.4:5001', 'addr', 'wrong')).toEqual({ status: 'unauthorized' })
  })

  it('returns unauthorized on a 403 response', async () => {
    global.fetch = vi.fn().mockResolvedValue({ ok: false, status: 403 }) as unknown as typeof fetch
    expect(await verifyNodeCredentials('http://1.2.3.4:5001', 'addr', 'wrong')).toEqual({ status: 'unauthorized' })
  })

  it('returns error on other non-ok statuses', async () => {
    global.fetch = vi.fn().mockResolvedValue({ ok: false, status: 500 }) as unknown as typeof fetch
    expect(await verifyNodeCredentials('http://1.2.3.4:5001', 'addr', 'pw')).toEqual({ status: 'error' })
  })

  it('returns error when the network request throws', async () => {
    global.fetch = vi.fn().mockRejectedValue(new Error('network down')) as unknown as typeof fetch
    expect(await verifyNodeCredentials('http://1.2.3.4:5001', 'addr', 'pw')).toEqual({ status: 'error' })
  })
})
