import { describe, it, expect } from 'vitest'
import { createPairingRequest, parsePairingRequest } from '../src/identity/pairingRequest.js'

const RENDEZVOUS = { baseUrl: 'https://sync.example.test/sync', namespace: 'dk' }
const ORIGIN = 'https://third-party.example'

describe('createPairingRequest / parsePairingRequest', () => {
  it('round-trips through JSON, and parse validates the shape', async () => {
    const { request } = await createPairingRequest({ origin: ORIGIN, rendezvous: RENDEZVOUS })
    const parsed = parsePairingRequest(JSON.stringify(request), request.code)
    expect(parsed.v).toBe(1)
    expect(parsed.kind).toBe('octobot-pairing-request')
    expect(parsed.code).toBe(request.code)
    expect(parsed.origin).toBe(ORIGIN)
    expect(parsed.rendezvous).toEqual(RENDEZVOUS)
    expect(parsed.devEdPub).toMatch(/^[0-9a-f]+$/)
    expect(parsed.devKemPub).toMatch(/^[0-9a-f]+$/)
    expect(parsed.popSig).toMatch(/^[0-9a-f]+$/)
  })

  it('generates a code of the expected shape and length', async () => {
    const { code } = await createPairingRequest({ origin: ORIGIN, rendezvous: RENDEZVOUS })
    expect(code).toHaveLength(8)
    expect(code).toMatch(/^[ABCDEFGHJKMNPQRSTUVWXYZ23456789]+$/)
    // No ambiguous characters.
    expect(code).not.toMatch(/[0O1IL]/)
  })

  // Fix J: `randomCode()` used to do `byte % 31` over uniform 0-255 bytes —
  // since 256 isn't a multiple of 31, that over-represented the alphabet's
  // first 8 symbols (A-H) by 12.5% in every character position. Fixed with
  // rejection sampling. This doesn't assert a hard statistical bound (that
  // would make the test flaky by design) — it asserts the SHAPE of the fix:
  // over a large sample, no symbol's frequency should be dramatically
  // skewed relative to the others, which the old modulo bias would produce
  // reliably (A-H at ~12.5% higher share than I-Z2-9).
  it('every alphabet symbol appears with roughly equal frequency over a large sample (no modulo bias)', async () => {
    const ALPHABET = 'ABCDEFGHJKMNPQRSTUVWXYZ23456789'
    const counts = new Map<string, number>()
    for (const ch of ALPHABET) counts.set(ch, 0)

    const SAMPLES = 4000 // 4000 codes * 8 chars = 32000 draws, ~1000 per symbol expected
    for (let i = 0; i < SAMPLES; i++) {
      const { code } = await createPairingRequest({ origin: ORIGIN, rendezvous: RENDEZVOUS })
      for (const ch of code) counts.set(ch, (counts.get(ch) ?? 0) + 1)
    }

    const total = SAMPLES * 8
    const expected = total / ALPHABET.length
    // A biased-by-12.5% symbol would sit ~1.125x expected; a generous 40%
    // tolerance band comfortably separates "uniform, just noisy" from "the
    // old bias is back" without making this test flaky under normal
    // sampling variance.
    for (const [ch, count] of counts) {
      expect(count, `symbol "${ch}" frequency ${count}, expected ~${expected}`).toBeGreaterThan(expected * 0.6)
      expect(count, `symbol "${ch}" frequency ${count}, expected ~${expected}`).toBeLessThan(expected * 1.4)
    }
  })

  it('two requests never share a code (astronomically unlikely, not a hard guarantee)', async () => {
    const a = await createPairingRequest({ origin: ORIGIN, rendezvous: RENDEZVOUS })
    const b = await createPairingRequest({ origin: ORIGIN, rendezvous: RENDEZVOUS })
    expect(a.code).not.toBe(b.code)
    expect(a.request.devEdPub).not.toBe(b.request.devEdPub)
  })

  it('carries an optional label and requestedCollections when supplied', async () => {
    const { request } = await createPairingRequest({
      origin: ORIGIN, rendezvous: RENDEZVOUS, label: 'My Dashboard', requestedCollections: ['accounts'],
    })
    expect(request.label).toBe('My Dashboard')
    expect(request.requestedCollections).toEqual(['accounts'])
  })

  it('omits label/requestedCollections entirely when not supplied, rather than null/undefined fields', async () => {
    const { request } = await createPairingRequest({ origin: ORIGIN, rendezvous: RENDEZVOUS })
    expect(request).not.toHaveProperty('label')
    expect(request).not.toHaveProperty('requestedCollections')
  })

  it('respects a custom ttlSec', async () => {
    const { request } = await createPairingRequest({ origin: ORIGIN, rendezvous: RENDEZVOUS, ttlSec: 30 })
    const ttlMs = Date.parse(request.expiresAt) - Date.parse(request.createdAt)
    expect(ttlMs).toBeCloseTo(30_000, -2)
  })

  it('parsePairingRequest rejects garbage and mismatched kinds', async () => {
    expect(() => parsePairingRequest('not json', 'ANYCODE1')).toThrow()
    expect(() => parsePairingRequest(JSON.stringify({ v: 1, kind: 'something-else' }), 'ANYCODE1')).toThrow()
  })

  it('parsePairingRequest rejects a tampered devEdPub (popSig no longer verifies)', async () => {
    const { request } = await createPairingRequest({ origin: ORIGIN, rendezvous: RENDEZVOUS })
    const tampered = { ...request, devEdPub: 'a'.repeat(64) }
    expect(() => parsePairingRequest(JSON.stringify(tampered), request.code)).toThrow(/proof-of-possession/)
  })

  it('parsePairingRequest rejects a tampered code (popSig binds it too)', async () => {
    const { request } = await createPairingRequest({ origin: ORIGIN, rendezvous: RENDEZVOUS })
    // Also pass the tampered code as `expectedCode` so the address-mismatch
    // check doesn't short-circuit before popSig verification even runs —
    // this test is specifically about popSig binding `code`, not about the
    // separate mismatch check.
    const tampered = { ...request, code: 'SWAPPED1' }
    expect(() => parsePairingRequest(JSON.stringify(tampered), 'SWAPPED1')).toThrow(/proof-of-possession/)
  })

  it('parsePairingRequest rejects a request whose code does not match the address it was fetched from', async () => {
    const { request } = await createPairingRequest({ origin: ORIGIN, rendezvous: RENDEZVOUS })
    expect(() => parsePairingRequest(JSON.stringify(request), 'DIFFERENT-CODE')).toThrow(/code does not match/)
  })

  it('parsePairingRequest rejects an expired request', async () => {
    const { request } = await createPairingRequest({ origin: ORIGIN, rendezvous: RENDEZVOUS, ttlSec: 1 })
    const expired = { ...request, expiresAt: new Date(Date.now() - 1000).toISOString() }
    // popSig doesn't cover expiresAt, so this is still a "signature valid,
    // structurally expired" case, not a tamper-detection case — both must
    // independently reject it.
    expect(() => parsePairingRequest(JSON.stringify(expired), request.code)).toThrow(/expired/)
  })

  it('parsePairingRequest rejects a request missing the rendezvous field', () => {
    const bad = {
      v: 1, kind: 'octobot-pairing-request', code: 'x', requesterKind: 'website', devEdPub: 'a'.repeat(64),
      devKemPub: 'b'.repeat(64), popSig: 'c'.repeat(128), joinRequestKemSig: 'd'.repeat(128), origin: ORIGIN,
      createdAt: new Date().toISOString(), expiresAt: new Date(Date.now() + 60_000).toISOString(),
    }
    expect(() => parsePairingRequest(JSON.stringify(bad), 'x')).toThrow(/rendezvous/)
  })

  describe('requesterKind — website vs. device', () => {
    it('defaults to "website" when not passed', async () => {
      const { request } = await createPairingRequest({ origin: ORIGIN, rendezvous: RENDEZVOUS })
      expect(request.requesterKind).toBe('website')
    })

    it('round-trips "device" through create/parse', async () => {
      const { request } = await createPairingRequest({ origin: ORIGIN, rendezvous: RENDEZVOUS, requesterKind: 'device' })
      expect(request.requesterKind).toBe('device')
      const parsed = parsePairingRequest(JSON.stringify(request), request.code)
      expect(parsed.requesterKind).toBe('device')
    })

    it('rejects a payload missing requesterKind entirely', async () => {
      const { request } = await createPairingRequest({ origin: ORIGIN, rendezvous: RENDEZVOUS })
      const { requesterKind: _drop, ...withoutRequesterKind } = request
      expect(() => parsePairingRequest(JSON.stringify(withoutRequesterKind), request.code)).toThrow(/requesterKind/)
    })

    it('rejects an unrecognized requesterKind value', async () => {
      const { request } = await createPairingRequest({ origin: ORIGIN, rendezvous: RENDEZVOUS })
      const tampered = { ...request, requesterKind: 'admin' }
      expect(() => parsePairingRequest(JSON.stringify(tampered), request.code)).toThrow(/requesterKind/)
    })
  })

  // Regression: every other field on the payload (code/devEdPub/devKemPub/
  // popSig/origin/createdAt/expiresAt/rendezvous.*) is validated as a string
  // before the final `p as unknown as PairingRequestPayload` cast — `label`
  // (unlike the documented-advisory `requestedCollections`) got no check at
  // all and rode through the cast unchecked, so a malformed record could set
  // `request.label` to an array/object/number while the type system asserts
  // `string | undefined`.
  it('parsePairingRequest rejects a non-string label instead of letting it ride through the cast unchecked', async () => {
    const { request } = await createPairingRequest({ origin: ORIGIN, rendezvous: RENDEZVOUS })
    const tamperedNumber = { ...request, label: 12345 }
    expect(() => parsePairingRequest(JSON.stringify(tamperedNumber), request.code)).toThrow(/label/)
    const tamperedObject = { ...request, label: { injected: 'not-a-string' } }
    expect(() => parsePairingRequest(JSON.stringify(tamperedObject), request.code)).toThrow(/label/)
  })

  it('parsePairingRequest still accepts a request with no label at all (label is genuinely optional)', async () => {
    const { request } = await createPairingRequest({ origin: ORIGIN, rendezvous: RENDEZVOUS })
    expect(request).not.toHaveProperty('label')
    expect(() => parsePairingRequest(JSON.stringify(request), request.code)).not.toThrow()
  })

  // Fix D: origin/label are the two fields the approving human actually
  // reads and relies on (popSig only proves key possession, not intent) —
  // previously validated as `typeof === 'string'` only, with no length cap
  // and no rejection of control/bidi characters that render unsafely.
  describe('origin/label are bounded and sanitized against control/bidi injection — fix D', () => {
    it('rejects an origin carrying an embedded newline (fake extra "chrome" lines when rendered)', async () => {
      const { request } = await createPairingRequest({ origin: ORIGIN, rendezvous: RENDEZVOUS })
      const tampered = { ...request, origin: `${ORIGIN}\n\nVerified by OctoBot` }
      expect(() => parsePairingRequest(JSON.stringify(tampered), request.code)).toThrow(/control or bidi-override/)
    })

    it('rejects a label carrying an embedded newline', async () => {
      const { request } = await createPairingRequest({ origin: ORIGIN, rendezvous: RENDEZVOUS, label: 'ok' })
      const tampered = { ...request, label: '\n\nVerified by OctoBot. Safe to approve.' }
      expect(() => parsePairingRequest(JSON.stringify(tampered), request.code)).toThrow(/control or bidi-override/)
    })

    it('rejects a label carrying a bidi override character', async () => {
      const { request } = await createPairingRequest({ origin: ORIGIN, rendezvous: RENDEZVOUS, label: 'ok' })
      const tampered = { ...request, label: `evil\u202Emalicious` }
      expect(() => parsePairingRequest(JSON.stringify(tampered), request.code)).toThrow(/control or bidi-override/)
    })

    it('rejects an origin carrying a bidi isolate character', async () => {
      const { request } = await createPairingRequest({ origin: ORIGIN, rendezvous: RENDEZVOUS })
      const tampered = { ...request, origin: `https://\u2066octobot.cloud\u2069.evil.example` }
      expect(() => parsePairingRequest(JSON.stringify(tampered), request.code)).toThrow(/control or bidi-override/)
    })

    it('rejects an over-length origin', async () => {
      const { request } = await createPairingRequest({ origin: ORIGIN, rendezvous: RENDEZVOUS })
      const tampered = { ...request, origin: `https://example.com/${'a'.repeat(3000)}` }
      expect(() => parsePairingRequest(JSON.stringify(tampered), request.code)).toThrow(/exceeds max length/)
    })

    it('rejects an over-length label', async () => {
      const { request } = await createPairingRequest({ origin: ORIGIN, rendezvous: RENDEZVOUS, label: 'ok' })
      const tampered = { ...request, label: 'a'.repeat(500) }
      expect(() => parsePairingRequest(JSON.stringify(tampered), request.code)).toThrow(/exceeds max length/)
    })

    it('rejects an origin that does not parse as a URL', async () => {
      const { request } = await createPairingRequest({ origin: ORIGIN, rendezvous: RENDEZVOUS })
      const tampered = { ...request, origin: 'not a url at all' }
      expect(() => parsePairingRequest(JSON.stringify(tampered), request.code)).toThrow(/not a valid URL/)
    })

    it('a genuinely normal origin/label still round-trips (not a false positive from the fix)', async () => {
      const { request } = await createPairingRequest({
        origin: 'https://my-trading-app.example', rendezvous: RENDEZVOUS, label: 'My Trading Dashboard',
      })
      expect(() => parsePairingRequest(JSON.stringify(request), request.code)).not.toThrow()
    })
  })

  describe('hex-encoded fields are length-checked before hexToBytes/verify runs — fix D', () => {
    it('rejects an oversized popSig fast, before signature verification even runs', async () => {
      const { request } = await createPairingRequest({ origin: ORIGIN, rendezvous: RENDEZVOUS })
      const tampered = { ...request, popSig: 'c'.repeat(500_000) }
      expect(() => parsePairingRequest(JSON.stringify(tampered), request.code)).toThrow(/popSig is not a valid 128-character hex string/)
    })

    it('rejects a too-short popSig', async () => {
      const { request } = await createPairingRequest({ origin: ORIGIN, rendezvous: RENDEZVOUS })
      const tampered = { ...request, popSig: 'c'.repeat(10) }
      expect(() => parsePairingRequest(JSON.stringify(tampered), request.code)).toThrow(/popSig is not a valid 128-character hex string/)
    })

    it('rejects a non-hex popSig of the right length', async () => {
      const { request } = await createPairingRequest({ origin: ORIGIN, rendezvous: RENDEZVOUS })
      const tampered = { ...request, popSig: 'z'.repeat(128) }
      expect(() => parsePairingRequest(JSON.stringify(tampered), request.code)).toThrow(/popSig is not a valid 128-character hex string/)
    })

    it('rejects an oversized devEdPub / devKemPub', async () => {
      const { request } = await createPairingRequest({ origin: ORIGIN, rendezvous: RENDEZVOUS })
      expect(() => parsePairingRequest(JSON.stringify({ ...request, devEdPub: 'a'.repeat(1000) }), request.code))
        .toThrow(/devEdPub is not a valid 64-character hex string/)
      expect(() => parsePairingRequest(JSON.stringify({ ...request, devKemPub: 'b'.repeat(1000) }), request.code))
        .toThrow(/devKemPub is not a valid 64-character hex string/)
    })
  })
})
