import { describe, it, expect } from 'vitest'
import {
  startPairingRequest,
  fetchPairingRequestByCode,
} from '../src/client/pairing/pairingRequest.js'
import { OctoBotConnectionError } from '../src/client/core/errors.js'
import { createStarfishWire } from './helpers/fakeNode.js'
import { joinSessionPath } from '../src/transport/rendezvous.js'

const RENDEZVOUS = { baseUrl: 'https://sync.example.test', namespace: 'dk' }
const ORIGIN = 'https://third-party.example'

describe('an expired request throws distinguishably from an unknown code', () => {
  it('an unknown code returns null (nothing published under that slot)', async () => {
    const wire = createStarfishWire()
    const result = await fetchPairingRequestByCode({ code: 'NOSUCH01', rendezvous: RENDEZVOUS, fetch: wire.fetch })
    expect(result).toBeNull()
  })

  it('a real, unexpired request round-trips through lookup normally', async () => {
    const wire = createStarfishWire()
    const session = await startPairingRequest({ origin: ORIGIN, rendezvous: RENDEZVOUS, fetch: wire.fetch })
    await session.publish()
    const found = await fetchPairingRequestByCode({ code: session.code, rendezvous: RENDEZVOUS, fetch: wire.fetch })
    expect(found).not.toBeNull()
    expect(found!.request.code).toBe(session.code)
  })

  it('an expired-but-present request REJECTS (not null), with a message naming the real reason — distinguishable from "wrong code"', async () => {
    const wire = createStarfishWire()
    const session = await startPairingRequest({ origin: ORIGIN, rendezvous: RENDEZVOUS, ttlSec: -1, fetch: wire.fetch })
    await session.publish() // publishes an already-expired request (ttlSec: -1)

    let caught: unknown
    try {
      await fetchPairingRequestByCode({ code: session.code, rendezvous: RENDEZVOUS, fetch: wire.fetch })
      throw new Error('expected fetchPairingRequestByCode to reject')
    } catch (err) {
      caught = err
    }
    expect(caught).toBeInstanceOf(OctoBotConnectionError)
    expect((caught as Error).message).toMatch(/expired/i)
    // DOCUMENTS A CONFIRMED GAP: the .code is 'unreachable', not something
    // that names "expired" specifically — parsePairingRequest throws a bare
    // Error('pairing request: expired'), which the generic toOctoBotError
    // fallback maps to OctoBotConnectionError('unreachable', ...). The
    // message is correct (a caller CAN distinguish via .message), but a
    // caller following this package's own README advice ("switch on .code")
    // cannot tell "expired" apart from "genuinely unreachable" that way.
    expect((caught as OctoBotConnectionError).code).toBe('unreachable')
  })

  // A malformed expiresAt must fail CLOSED (rejected as expired), not open
  // (silently treated as "not expired" forever) — Date.parse of garbage is
  // NaN, and every comparison against NaN is false, so a naive `<=` check
  // would let this through. This also matters because the wire is public
  // and cap-less: anyone can publish a request record with any string here.
  async function publishWithCorruptedExpiresAt(expiresAt: unknown) {
    const wire = createStarfishWire()
    const session = await startPairingRequest({ origin: ORIGIN, rendezvous: RENDEZVOUS, fetch: wire.fetch })
    await session.publish()
    const key = joinSessionPath(session.code)
    const entry = wire.store.get(key)
    expect(entry).toBeDefined()
    wire.store.set(key, { ...entry!, data: { ...entry!.data, expiresAt } })
    return { wire, session }
  }

  it.each([
    ['a non-date garbage string', 'not-a-real-date'],
    ['an empty string', ''],
    ['a numeric-looking non-date string', 'Infinity'],
    ['a whitespace-only string', '   '],
  ])('rejects as expired, not silently accepted, when expiresAt is %s', async (_label, badValue) => {
    const { wire, session } = await publishWithCorruptedExpiresAt(badValue)
    await expect(
      fetchPairingRequestByCode({ code: session.code, rendezvous: RENDEZVOUS, fetch: wire.fetch }),
    ).rejects.toThrow(/expired/i)
  })

  it('a genuinely valid, near-default expiresAt still round-trips normally (not a false positive from the fix)', async () => {
    const nearDefault = new Date(Date.now() + 4 * 60 * 1000).toISOString() // under the 5-min default
    const { wire, session } = await publishWithCorruptedExpiresAt(nearDefault)
    const found = await fetchPairingRequestByCode({ code: session.code, rendezvous: RENDEZVOUS, fetch: wire.fetch })
    expect(found).not.toBeNull()
    expect(found!.request.code).toBe(session.code)
  })

  // Fix E: expiresAt/createdAt are NOT covered by popSig — a party with the
  // code (or a hostile "website") can rewrite the declared window to
  // anything, and website-pairing.md's whole "device code beats a QR"
  // argument rests on that window actually being short. A 1-year expiry
  // used to be silently accepted (this exact test, before the fix, asserted
  // that as the correct/intended behavior) — now it must be rejected
  // regardless of what the requester claims.
  describe('the expiry window is capped independent of the requester\'s claimed ttlSec — fix E', () => {
    it('REJECTS a far-future (1-year) expiresAt — this is a deliberate behavior change from before fix E', async () => {
      const farFuture = new Date(Date.now() + 365 * 24 * 60 * 60 * 1000).toISOString()
      const { wire, session } = await publishWithCorruptedExpiresAt(farFuture)
      await expect(
        fetchPairingRequestByCode({ code: session.code, rendezvous: RENDEZVOUS, fetch: wire.fetch }),
      ).rejects.toThrow(/exceeds the maximum/)
    })

    it('accepts a window just under the 1-hour cap', async () => {
      const justUnder = new Date(Date.now() + (60 * 60 * 1000 - 5000)).toISOString()
      const { wire, session } = await publishWithCorruptedExpiresAt(justUnder)
      const found = await fetchPairingRequestByCode({ code: session.code, rendezvous: RENDEZVOUS, fetch: wire.fetch })
      expect(found).not.toBeNull()
    })

    it('rejects a window just over the 1-hour cap', async () => {
      const justOver = new Date(Date.now() + (60 * 60 * 1000 + 5000)).toISOString()
      const { wire, session } = await publishWithCorruptedExpiresAt(justOver)
      await expect(
        fetchPairingRequestByCode({ code: session.code, rendezvous: RENDEZVOUS, fetch: wire.fetch }),
      ).rejects.toThrow(/exceeds the maximum/)
    })

    it('startPairingRequest clamps an oversized ttlSec instead of creating a request parsePairingRequest would reject', async () => {
      const wire = createStarfishWire()
      const session = await startPairingRequest({
        origin: ORIGIN, rendezvous: RENDEZVOUS, ttlSec: 365 * 24 * 60 * 60, fetch: wire.fetch,
      })
      await session.publish()
      const found = await fetchPairingRequestByCode({ code: session.code, rendezvous: RENDEZVOUS, fetch: wire.fetch })
      expect(found).not.toBeNull()
      const windowMs = Date.parse(found!.request.expiresAt) - Date.parse(found!.request.createdAt)
      expect(windowMs).toBeLessThanOrEqual(60 * 60 * 1000)
    })

    // Regression: the TTL cap used to compare expiresAt against the
    // request's OWN createdAt — both attacker-controlled, neither covered
    // by popSig — which is trivially bypassable: an attacker (or hostile
    // "website") can place BOTH timestamps arbitrarily far in the future
    // while keeping their difference within the cap, making the code
    // "look" freshly issued no matter when it's actually redeemed. Fixed
    // by anchoring the cap to the REAL wall clock at verification time
    // instead — createdAt is now purely informational, never used in any
    // security decision.
    it('REJECTS a request whose createdAt/expiresAt are co-forged far in the future with only a narrow gap between them — the createdAt-relative bypass', async () => {
      const wire = createStarfishWire()
      const session = await startPairingRequest({ origin: ORIGIN, rendezvous: RENDEZVOUS, fetch: wire.fetch })
      await session.publish()
      const key = joinSessionPath(session.code)
      const entry = wire.store.get(key)
      expect(entry).toBeDefined()
      const oneYearOut = Date.now() + 365 * 24 * 60 * 60 * 1000
      wire.store.set(key, {
        ...entry!,
        data: {
          ...entry!.data,
          createdAt: new Date(oneYearOut - 30 * 60 * 1000).toISOString(), // "created" 30min before its own expiry
          expiresAt: new Date(oneYearOut).toISOString(), // ...but that expiry is a year from now
        },
      })
      // A createdAt-relative check would see a 30-minute window (well under
      // the 1-hour cap) and wrongly accept this. The real wall-clock-anchored
      // check must reject it: expiresAt is ~1 year from NOW.
      await expect(
        fetchPairingRequestByCode({ code: session.code, rendezvous: RENDEZVOUS, fetch: wire.fetch }),
      ).rejects.toThrow(/exceeds the maximum/)
    })

    it('createdAt is purely informational now — a malformed/garbage createdAt does NOT affect acceptance (only expiresAt is security-relevant)', async () => {
      const wire = createStarfishWire()
      const session = await startPairingRequest({ origin: ORIGIN, rendezvous: RENDEZVOUS, fetch: wire.fetch })
      await session.publish()
      const key = joinSessionPath(session.code)
      const entry = wire.store.get(key)
      expect(entry).toBeDefined()
      wire.store.set(key, { ...entry!, data: { ...entry!.data, createdAt: 'not-a-real-date' } })
      const found = await fetchPairingRequestByCode({ code: session.code, rendezvous: RENDEZVOUS, fetch: wire.fetch })
      expect(found).not.toBeNull()
      expect(found!.request.code).toBe(session.code)
    })
  })
})
