import { describe, it, expect, vi } from 'vitest'
import { generateDeviceKeys } from '@drakkar.software/starfish-identities'
import { startPairingRequest, fetchPairingRequestByCode } from '../src/client/pairing/pairingRequest.js'
import {
  publishPairingGrant,
  clearPairingGrant,
  fetchPairingGrant,
  awaitPairingGrant,
} from '../src/client/pairing/pairingGrantExchange.js'
import { OctoBotConflictError, OctoBotConnectionError } from '../src/client/core/errors.js'
import type { MintedPairingGrant } from '../src/client/pairing/mirrorGrant.js'

// pairingGrantExchange.ts's own concern is the wire protocol (envelope
// shape, phase discrimination, baseHash CAS, polling/timeout) — NOT the
// space-mirror read itself, which is a separate package's concern
// (`readMirrorCollections` thinly wraps `starfish-replica/space`'s
// `readSpaceMirror`). Stubbing it here keeps this suite scoped to what this
// file actually owns, matching how `mirrorReader.ts`/`writer.ts` are tested
// (or rather, not yet tested) elsewhere in this package.
vi.mock('../src/client/pairing/mirrorReader.js', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../src/client/pairing/mirrorReader.js')>()
  return {
    ...actual,
    readMirrorCollections: vi.fn(async () => ({ 'user-accounts': { stub: true } })),
  }
})

const RENDEZVOUS = { baseUrl: 'https://sync.example.test', namespace: 'dk' }
const ORIGIN = 'https://third-party.example'

/** Same in-memory fake StarfishClient wire protocol as
 *  pairingRequestFlow.test.ts's `fakeServer` — GET/POST against
 *  `/pull|push/<path>`, optimistic-concurrency-controlled by a hash
 *  counter. */
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
        return new Response(JSON.stringify({ error: 'conflict', currentHash: entry.hash }), { status: 409 })
      }
      const hash = `hash-${++counter}`
      store.set(key, { data: body.data, hash })
      return new Response(JSON.stringify({ hash, timestamp: Date.now() }), { status: 200 })
    }
    throw new Error(`fakeServer: unhandled method ${method}`)
  }
  return { fetch: fetchImpl, store }
}

function fakeSealer() {
  const device = generateDeviceKeys()
  return { edPrivHex: device.edPriv, edPubHex: device.edPub }
}

function fakeGrant(spaceId = 'space-1'): MintedPairingGrant {
  // The per-node shape `mintPairingGrant` really publishes: one entry per
  // granted collection, each carrying the two caps that reach that ONE node.
  return {
    bundle: JSON.stringify({
      v: 1,
      spaceId,
      nodes: [
        {
          collectionId: 'user-accounts',
          nodeId: 'node-1',
          contentCap: { ops: ['read', 'list'] },
          keyringCap: { ops: ['read'] },
        },
      ],
    }),
    spaceId,
    memberUserId: 'member-1',
    memberKemPub: 'kem-pub-1',
    coveredCollections: ['user-accounts'],
  }
}

describe('pairingGrantExchange: request -> grant round-trip', () => {
  it('full round-trip: publish request, publish grant against its hash, fetchPairingGrant resolves', async () => {
    const server = fakeServer()
    const website = await startPairingRequest({ origin: ORIGIN, rendezvous: RENDEZVOUS, fetch: server.fetch })
    await website.publish()

    const found = await fetchPairingRequestByCode({ code: website.code, rendezvous: RENDEZVOUS, fetch: server.fetch })
    expect(found).not.toBeNull()

    const grant = fakeGrant()
    await publishPairingGrant({
      request: found!.request, sealer: fakeSealer(), grant, rendezvous: RENDEZVOUS, baseHash: found!.hash, fetch: server.fetch,
    })

    const result = await fetchPairingGrant(
      { code: website.code, device: website.device, rendezvous: RENDEZVOUS },
      { fetch: server.fetch },
    )
    expect(result).not.toBeNull()
    expect(result!.spaceId).toBe(grant.spaceId)
    expect(result!.collections).toEqual({ 'user-accounts': { stub: true } })
  })

  it('fetchPairingGrant returns null (does NOT throw) while the slot still holds only the request', async () => {
    const server = fakeServer()
    const website = await startPairingRequest({ origin: ORIGIN, rendezvous: RENDEZVOUS, fetch: server.fetch })
    await website.publish()

    // This is the exact case the joinsessions merge could have broken: the
    // slot is non-empty (a request is published there), but no grant has
    // been published yet — this must be indistinguishable from "keep
    // waiting", not surface as a malformed-document error.
    const result = await fetchPairingGrant(
      { code: website.code, device: website.device, rendezvous: RENDEZVOUS },
      { fetch: server.fetch },
    )
    expect(result).toBeNull()
  })

  it('fetchPairingGrant returns null for a code nobody ever published anything under', async () => {
    const server = fakeServer()
    const someDevice = generateDeviceKeys()
    const result = await fetchPairingGrant(
      { code: 'NOSUCH01', device: someDevice, rendezvous: RENDEZVOUS },
      { fetch: server.fetch },
    )
    expect(result).toBeNull()
  })

  it('publishPairingGrant with baseHash: null against an already-occupied (request) slot 409s as a conflict', async () => {
    const server = fakeServer()
    const website = await startPairingRequest({ origin: ORIGIN, rendezvous: RENDEZVOUS, fetch: server.fetch })
    await website.publish()

    await expect(
      publishPairingGrant({
        request: website.request, sealer: fakeSealer(), grant: fakeGrant(), rendezvous: RENDEZVOUS, baseHash: null, fetch: server.fetch,
      }),
    ).rejects.toThrow(OctoBotConflictError)
  })

  it('publishPairingGrant with a stale/wrong baseHash 409s — does not silently overwrite the request', async () => {
    const server = fakeServer()
    const website = await startPairingRequest({ origin: ORIGIN, rendezvous: RENDEZVOUS, fetch: server.fetch })
    await website.publish()

    await expect(
      publishPairingGrant({
        request: website.request, sealer: fakeSealer(), grant: fakeGrant(), rendezvous: RENDEZVOUS, baseHash: 'totally-wrong-hash', fetch: server.fetch,
      }),
    ).rejects.toThrow(OctoBotConflictError)

    // The request is still there, untouched — the phone's own next
    // `fetchPairingRequestByCode` still sees a normal request, not a
    // half-written grant.
    const stillRequest = await fetchPairingRequestByCode({ code: website.code, rendezvous: RENDEZVOUS, fetch: server.fetch })
    expect(stillRequest).not.toBeNull()
  })

  it('a legitimate re-publish (refresh) using the previous grant publish\'s own returned hash succeeds', async () => {
    const server = fakeServer()
    const website = await startPairingRequest({ origin: ORIGIN, rendezvous: RENDEZVOUS, fetch: server.fetch })
    await website.publish()
    const found = await fetchPairingRequestByCode({ code: website.code, rendezvous: RENDEZVOUS, fetch: server.fetch })

    const first = await publishPairingGrant({
      request: found!.request, sealer: fakeSealer(), grant: fakeGrant(), rendezvous: RENDEZVOUS, baseHash: found!.hash, fetch: server.fetch,
    })
    const second = await publishPairingGrant({
      request: found!.request, sealer: fakeSealer(), grant: fakeGrant('space-2'), rendezvous: RENDEZVOUS, baseHash: first.hash, fetch: server.fetch,
    })
    expect(second.hash).not.toBe(first.hash)

    const result = await fetchPairingGrant(
      { code: website.code, device: website.device, rendezvous: RENDEZVOUS },
      { fetch: server.fetch },
    )
    expect(result!.spaceId).toBe('space-2')
  })

  it('clearPairingGrant wipes the slot entirely — a subsequent lookup sees nothing published', async () => {
    const server = fakeServer()
    const website = await startPairingRequest({ origin: ORIGIN, rendezvous: RENDEZVOUS, fetch: server.fetch })
    await website.publish()
    const found = await fetchPairingRequestByCode({ code: website.code, rendezvous: RENDEZVOUS, fetch: server.fetch })
    await publishPairingGrant({
      request: found!.request, sealer: fakeSealer(), grant: fakeGrant(), rendezvous: RENDEZVOUS, baseHash: found!.hash, fetch: server.fetch,
    })

    await clearPairingGrant({ request: found!.request, rendezvous: RENDEZVOUS, fetch: server.fetch })

    const requestAfterClear = await fetchPairingRequestByCode({ code: website.code, rendezvous: RENDEZVOUS, fetch: server.fetch })
    expect(requestAfterClear).toBeNull()
    const grantAfterClear = await fetchPairingGrant(
      { code: website.code, device: website.device, rendezvous: RENDEZVOUS },
      { fetch: server.fetch },
    )
    expect(grantAfterClear).toBeNull()
  })

  it('awaitPairingGrant resolves immediately when a grant is already published', async () => {
    const server = fakeServer()
    const website = await startPairingRequest({ origin: ORIGIN, rendezvous: RENDEZVOUS, fetch: server.fetch })
    await website.publish()
    const found = await fetchPairingRequestByCode({ code: website.code, rendezvous: RENDEZVOUS, fetch: server.fetch })
    await publishPairingGrant({
      request: found!.request, sealer: fakeSealer(), grant: fakeGrant(), rendezvous: RENDEZVOUS, baseHash: found!.hash, fetch: server.fetch,
    })

    const result = await awaitPairingGrant(
      { code: website.code, device: website.device, rendezvous: RENDEZVOUS },
      { fetch: server.fetch, timeoutMs: 5000 },
    )
    expect(result.spaceId).toBe('space-1')
  })

  // The bug this closes: before the joinsessions merge fixed fetchPairingGrant's
  // phase discrimination, every poll against a still-request-shaped slot
  // THREW "malformed sealed blob" instead of returning null — awaitPairingGrant
  // swallowed that into `lastErr` and rethrew IT on timeout, so a normal
  // "nobody approved in time" outcome surfaced as a confusing internal error
  // instead of a clean timeout.
  it('awaitPairingGrant times out with a clean OctoBotConnectionError — not a stale "malformed blob" error — when nobody ever approves', async () => {
    const server = fakeServer()
    const website = await startPairingRequest({ origin: ORIGIN, rendezvous: RENDEZVOUS, fetch: server.fetch })
    await website.publish() // request published, but no grant ever follows

    let caught: unknown
    try {
      // timeoutMs shorter than the poll loop's own minimum backoff, so the
      // deadline is already passed after the first (null) fetchPairingGrant
      // call — resolves this test in milliseconds, not minutes.
      await awaitPairingGrant(
        { code: website.code, device: website.device, rendezvous: RENDEZVOUS },
        { fetch: server.fetch, timeoutMs: 1 },
      )
      throw new Error('expected awaitPairingGrant to time out')
    } catch (err) {
      caught = err
    }
    expect(caught).toBeInstanceOf(OctoBotConnectionError)
    expect((caught as OctoBotConnectionError).code).toBe('timeout')
    expect((caught as Error).message).toMatch(/timed out waiting for the pairing to be approved/)
    expect((caught as Error).message).not.toMatch(/malformed/)
  })
})
