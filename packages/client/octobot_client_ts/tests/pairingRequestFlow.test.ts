import { describe, it, expect } from 'vitest'
import {
  startPairingRequest,
  fetchPairingRequestByCode,
} from '../src/client/pairing/pairingRequest.js'
import { joinSessionPath } from '../src/transport/rendezvous.js'
import { OctoBotConflictError } from '../src/client/core/errors.js'

const RENDEZVOUS = { baseUrl: 'https://sync.example.test', namespace: 'dk' }
const ORIGIN = 'https://third-party.example'

/** In-memory fake `fetch` implementing enough of the real StarfishClient
 *  wire protocol (verified against `node_modules/@drakkar.software/
 *  starfish-client/dist/client.js`'s `pull`/`push`) to exercise the
 *  request/lookup flow end to end: GET returns a bare
 *  `{data, hash, timestamp}` JSON body; POST reads `{data, baseHash}`,
 *  applies optimistic-concurrency-control against a simple hash counter,
 *  and returns `{hash, timestamp}` or 409 on a stale baseHash. Shared
 *  across "website" and "phone" test actors, since in production they talk
 *  to the SAME real sync server. */
function fakeServer() {
  const store = new Map<string, { data: Record<string, unknown>; hash: string }>()
  let counter = 0

  function keyFrom(url: string): string {
    const match = /\/(pull|push)\/(.+)$/.exec(new URL(url).pathname)
    if (!match) throw new Error(`fakeServer: could not extract doc key from ${url}`)
    return decodeURIComponent(match[2])
  }

  const fetchImpl: typeof fetch = async (input, init) => {
    const url = typeof input === 'string' ? input : (input as URL).toString()
    const method = init?.method ?? 'GET'
    const key = keyFrom(url)
    if (method === 'GET') {
      const entry = store.get(key) ?? { data: {}, hash: 'empty-hash' }
      return new Response(JSON.stringify({ data: entry.data, hash: entry.hash, timestamp: Date.now() }), { status: 200 })
    }
    if (method === 'POST') {
      const body = JSON.parse(String(init?.body)) as { data: Record<string, unknown>; baseHash: string | null }
      const entry = store.get(key) ?? { data: {}, hash: 'empty-hash' }
      if ((body.baseHash ?? 'empty-hash') !== entry.hash) {
        return new Response(JSON.stringify({ error: 'conflict' }), { status: 409 })
      }
      const hash = `hash-${++counter}`
      store.set(key, { data: body.data, hash })
      return new Response(JSON.stringify({ hash, timestamp: Date.now() }), { status: 200 })
    }
    throw new Error(`fakeServer: unhandled method ${method}`)
  }
  return { fetch: fetchImpl, store }
}

describe('device-code pairing request lookup', () => {
  it('fetchPairingRequestByCode returns null for a code nobody published', async () => {
    const server = fakeServer()
    const result = await fetchPairingRequestByCode({ code: 'NOSUCH12', rendezvous: RENDEZVOUS, fetch: server.fetch })
    expect(result).toBeNull()
  })
})

// Fix 2, end to end through the real public API (not just rendezvous.test.ts's
// unit-level pushRendezvousDoc coverage): a website's session.publish() now
// detects a hostile overwrite of its own slot instead of silently adopting it
// as the new baseline.
describe('own-write CAS detects a hijacked pairing request slot (fix 2)', () => {
  it('session.publish() succeeds on a genuinely fresh code (create-only)', async () => {
    const server = fakeServer()
    const website = await startPairingRequest({ origin: ORIGIN, rendezvous: RENDEZVOUS, fetch: server.fetch })
    await expect(website.publish()).resolves.toBeUndefined()
    const found = await fetchPairingRequestByCode({ code: website.code, rendezvous: RENDEZVOUS, fetch: server.fetch })
    expect(found!.request.code).toBe(website.code)
  })

  it('session.publish() called again (legitimate re-publish/refresh) succeeds using its own remembered hash', async () => {
    const server = fakeServer()
    const website = await startPairingRequest({ origin: ORIGIN, rendezvous: RENDEZVOUS, fetch: server.fetch })
    await website.publish()
    await expect(website.publish()).resolves.toBeUndefined()
  })

  it('session.publish() REJECTS when a third party overwrites the code slot between two publish() calls', async () => {
    const server = fakeServer()
    const website = await startPairingRequest({ origin: ORIGIN, rendezvous: RENDEZVOUS, fetch: server.fetch })
    await website.publish()

    // A third party writes to the SAME code slot directly — not through this
    // SDK, modeling a real attacker who observed the code and overwrote the
    // request record before the website's next publish() call.
    server.store.set(joinSessionPath(website.code), {
      data: { ...website.request, origin: 'https://attacker.example' } as unknown as Record<string, unknown>,
      hash: 'attacker-overwrite',
    })

    await expect(website.publish()).rejects.toThrow(/modified by another party/)
    // The attacker's content is still there — the legitimate publish() was
    // correctly refused rather than stomping over evidence of tampering.
    const stillThere = await fetchPairingRequestByCode({ code: website.code, rendezvous: RENDEZVOUS, fetch: server.fetch })
    expect(stillThere!.request.origin).toBe('https://attacker.example')
  })

  it('a hijacked pairing REQUEST rejection is a real OctoBotConflictError (code: "conflict"), not a generic unreachable error', async () => {
    const server = fakeServer()
    const website = await startPairingRequest({ origin: ORIGIN, rendezvous: RENDEZVOUS, fetch: server.fetch })
    await website.publish()
    server.store.set(joinSessionPath(website.code), {
      data: { ...website.request, origin: 'https://attacker.example' } as unknown as Record<string, unknown>,
      hash: 'attacker-overwrite',
    })

    let caught: unknown
    try {
      await website.publish()
      throw new Error('expected publish() to reject')
    } catch (err) {
      caught = err
    }
    expect(caught).toBeInstanceOf(OctoBotConflictError)
    expect((caught as OctoBotConflictError).code).toBe('conflict')
    expect((caught as Error).message).toMatch(/modified by another party/)
  })

  // Regression: publish()'s closure-scoped lastHash used to be read
  // synchronously by every call before any await, with no serialization —
  // two overlapping calls both read the SAME lastHash, so whichever the
  // server processed second got a real ConflictError caused only by this
  // session's own overlapping write, not third-party tampering, yet (post
  // own-write-CAS) it hit the exact same "treat this code as compromised"
  // error a genuine hijack would. Fixed by serializing publish() calls
  // through an internal queue.
  it('two overlapping publish() calls on the SAME session serialize instead of self-racing into a false conflict', async () => {
    const server = fakeServer()
    const website = await startPairingRequest({ origin: ORIGIN, rendezvous: RENDEZVOUS, fetch: server.fetch })

    // Neither call is awaited before the other starts — both read the
    // session's initial (null) lastHash at call time if there were no
    // serialization.
    const [first, second] = await Promise.all([website.publish(), website.publish()])
    expect(first).toBeUndefined()
    expect(second).toBeUndefined()

    const found = await fetchPairingRequestByCode({ code: website.code, rendezvous: RENDEZVOUS, fetch: server.fetch })
    expect(found!.request.code).toBe(website.code)
  })

  it('three overlapping publish() calls all succeed in sequence, not just two', async () => {
    const server = fakeServer()
    const website = await startPairingRequest({ origin: ORIGIN, rendezvous: RENDEZVOUS, fetch: server.fetch })
    await expect(Promise.all([website.publish(), website.publish(), website.publish()])).resolves.toEqual([
      undefined, undefined, undefined,
    ])
  })
})
