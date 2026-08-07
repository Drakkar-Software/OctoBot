import { describe, it, expect } from 'vitest'
import { createReadOnlyPairing, parseReadOnlyPairing } from '../src/identity/pairing.js'
import { connectReadOnlyDevice } from '../src/client/connect/readOnly.js'
import { OctoBotConfigError, OctoBotConflictError, OctoBotHttpError, OctoBotAuthError } from '../src/client/core/errors.js'

const MNEMONIC = 'abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about'
const NODE = { host: '192.0.2.1', port: 5001 }

describe('a v1 payload, an unbounded cap, a truncated key, and the secure flag all behave predictably', () => {
  it('a v1 payload throws a message distinguishing it from an unrecognized payload — REGRESSION for the "re-pair" UX', () => {
    const v1 = JSON.stringify({ v: 1, kind: 'octobot-read-only-pairing', node: NODE })
    let v1Message = ''
    try {
      parseReadOnlyPairing(v1)
    } catch (err) {
      v1Message = err instanceof Error ? err.message : String(err)
    }
    expect(v1Message).toMatch(/v1|version|re-?pair|outdated/i)

    let wrongKindMessage = ''
    try {
      parseReadOnlyPairing(JSON.stringify({ v: 2, kind: 'something-else' }))
    } catch (err) {
      wrongKindMessage = err instanceof Error ? err.message : String(err)
    }
    // The two failure reasons are now genuinely different messages — a user
    // holding a stale QR is told to re-pair, not that the payload is junk.
    expect(v1Message).not.toBe(wrongKindMessage)
  })

  it('connectReadOnlyDevice surfaces the v1 case as OctoBotConfigError carrying that specific text', async () => {
    const v1 = JSON.stringify({ v: 1, kind: 'octobot-read-only-pairing', node: NODE })
    let caught: unknown
    try {
      await connectReadOnlyDevice(v1)
    } catch (err) {
      caught = err
    }
    expect(caught).toBeInstanceOf(OctoBotConfigError)
    expect((caught as Error).message).toMatch(/v1|re-?pair|outdated/i)
  })

  it('the cap TTL defaults to the mint default (30 days) when unspecified, and honors an explicit ttlSec', async () => {
    const { payload: defaultPayload } = await createReadOnlyPairing(MNEMONIC, 'bip44', NODE)
    const defaultParsed = parseReadOnlyPairing(defaultPayload)
    const THIRTY_DAYS_SEC = 30 * 24 * 3600
    expect(defaultParsed.cap.exp).toBeGreaterThan(defaultParsed.cap.nbf)
    expect(defaultParsed.cap.exp - defaultParsed.cap.nbf).toBe(THIRTY_DAYS_SEC)
    // Expiry is the ONLY revocation this package has for a read-only bearer
    // credential — pin that it is bounded at all, not left open-ended.
    expect(defaultParsed.cap.exp).toBeGreaterThan(Math.floor(Date.now() / 1000))

    const { payload: customPayload } = await createReadOnlyPairing(MNEMONIC, 'bip44', NODE, { ttlSec: 3600 })
    const customParsed = parseReadOnlyPairing(customPayload)
    expect(customParsed.cap.exp - customParsed.cap.nbf).toBe(3600)
  })

  it('a truncated collectionKey is rejected with a clear "32 bytes" error, and the resulting OctoBotError is NOT reported as an auth failure', async () => {
    const { payload } = await createReadOnlyPairing(MNEMONIC, 'bip44', NODE)
    const parsed = JSON.parse(payload) as { collectionKeys: Record<string, string> }
    // 16 raw bytes, base64-encoded — half the required 32.
    parsed.collectionKeys.userData = btoa(String.fromCharCode(...new Uint8Array(16)))
    const corrupted = JSON.stringify(parsed)

    const client = await connectReadOnlyDevice(corrupted)
    let caught: unknown
    try {
      await client.documents.pull('userData')
    } catch (err) {
      caught = err
    }
    expect(caught).toBeInstanceOf(Error)
    expect((caught as Error).message).toMatch(/32 bytes/)
    // Not miscategorized as a credential/auth problem — a corrupt grant is a
    // local data problem, not "the node rejected this wallet".
    expect(caught).not.toBeInstanceOf(OctoBotAuthError)
    expect(caught).not.toBeInstanceOf(OctoBotHttpError)
    expect(caught).not.toBeInstanceOf(OctoBotConflictError)
    client.close()
  })

  it('node.secure: true produces an https origin', async () => {
    const { payload } = await createReadOnlyPairing(MNEMONIC, 'bip44', { ...NODE, secure: true })
    const client = await connectReadOnlyDevice(payload)
    expect(client.url).toBe('https://192.0.2.1:5001')
    client.close()
  })

  it('node.secure: false (or omitted) produces an http origin', async () => {
    const { payload } = await createReadOnlyPairing(MNEMONIC, 'bip44', NODE)
    const client = await connectReadOnlyDevice(payload)
    expect(client.url).toBe('http://192.0.2.1:5001')
    client.close()
  })

  it('DOCUMENTS A CONFIRMED GAP: parseReadOnlyPairing does not validate node.secure\'s type at all — a non-boolean value passes through unchecked and silently decides TLS for every subsequent request', () => {
    const forged = JSON.stringify({
      v: 2, kind: 'octobot-read-only-pairing',
      node: { host: '192.0.2.1', port: 5001, secure: 'not-a-boolean' },
      rootEdPub: 'a'.repeat(64), userId: 'b'.repeat(32),
      device: { edPriv: 'c'.repeat(64), edPub: 'd'.repeat(64), kemPriv: 'e'.repeat(64), kemPub: 'f'.repeat(64) },
      cap: { v: 1, sig: 'sig', nbf: 0, exp: 9999999999 },
      scope: { ops: ['read', 'list'], collections: ['userData'] },
      collectionKeys: {},
    })
    // Currently does NOT throw — parseReadOnlyPairing only checks
    // host:string and port:number, never node.secure's type. Written as an
    // explicit, named, currently-passing-for-the-wrong-reason expectation
    // (not silently skipped) so a future validation add is a deliberate,
    // visible decision, not something this suite forgot to check for.
    expect(() => parseReadOnlyPairing(forged)).not.toThrow()
  })
})
