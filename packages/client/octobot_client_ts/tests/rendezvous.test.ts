import { describe, it, expect, vi } from 'vitest'
import type { StarfishClient } from '@drakkar.software/starfish-client'
import { ConflictError } from '@drakkar.software/starfish-client'
import {
  pullRendezvousDoc,
  pushRendezvousDoc,
  clearRendezvousDoc,
  joinSessionPath,
} from '../src/transport/rendezvous.js'

/** In-memory fake matching real StarfishClient pull/push semantics: an
 *  unwritten path pulls as `{data: {}, hash: <some hash>}` (never a thrown
 *  404), and `push` requires the caller's `baseHash` to match the store's
 *  current hash or throws `ConflictError` — verified against the real
 *  package's client.d.ts and behavior notes in this package's own docs. */
function fakeStore() {
  const store = new Map<string, { data: Record<string, unknown>; hash: string }>()
  let hashCounter = 0
  function currentEntry(path: string) {
    return store.get(path) ?? { data: {}, hash: 'empty-hash' }
  }
  async function realPush(path: string, data: Record<string, unknown>, baseHash: string | null) {
    const key = path.replace(/^\/push\//, '')
    const entry = currentEntry(key)
    if ((baseHash ?? 'empty-hash') !== entry.hash) throw new ConflictError(entry.hash)
    const hash = `hash-${++hashCounter}`
    store.set(key, { data, hash })
    return { hash, timestamp: Date.now() }
  }
  const client = {
    pull: vi.fn(async (path: string) => {
      const key = path.replace(/^\/pull\//, '')
      const entry = currentEntry(key)
      return { data: entry.data, hash: entry.hash, timestamp: Date.now() }
    }),
    push: vi.fn(realPush),
  } as unknown as StarfishClient
  return { client, store, realPush }
}

describe('pullRendezvousDoc', () => {
  it('returns null for a never-written slot', async () => {
    const { client } = fakeStore()
    expect(await pullRendezvousDoc(client, '_pairing/session/ABCD1234')).toBeNull()
  })

  it('returns the document once something has been pushed', async () => {
    const { client } = fakeStore()
    await pushRendezvousDoc(client, '_pairing/session/ABCD1234', { a: 1 }, null)
    const doc = await pullRendezvousDoc(client, '_pairing/session/ABCD1234')
    expect(doc).toEqual({ data: { a: 1 }, hash: 'hash-1' })
  })
})

// Fix 2: pushRendezvousDoc now takes an EXPLICIT baseHash from the caller
// instead of internally re-pulling and adopting whatever's currently at the
// path — that old behavior is exactly what let a hostile overwrite of a
// slot go undetected forever, including by the original publisher's own
// next write. It no longer retries on conflict either: a ConflictError here
// means the document changed since THIS CALLER last wrote it, which is the
// caller's cue to treat the slot as possibly tampered with, not a transient
// blip to paper over.
describe('pushRendezvousDoc — explicit own-write CAS, no blind retry (fix 2)', () => {
  it('writes to a genuinely fresh slot with baseHash: null (create-only)', async () => {
    const { client, store } = fakeStore()
    await pushRendezvousDoc(client, 'p', { hello: 'world' }, null)
    expect(store.get('p')?.data).toEqual({ hello: 'world' })
  })

  it('returns the resulting hash from a successful push', async () => {
    const { client } = fakeStore()
    const result = await pushRendezvousDoc(client, 'p', { v: 1 }, null)
    expect(result.hash).toBe('hash-1')
    expect((await pullRendezvousDoc(client, 'p'))?.hash).toBe('hash-1')
  })

  it('REJECTS baseHash: null against an already-occupied slot — no silent squat-adoption', async () => {
    const { client } = fakeStore()
    await pushRendezvousDoc(client, 'p', { v: 'legitimate-first-writer' }, null)
    // A second baseHash:null push (as if a caller believed this was still a
    // fresh slot) must NOT silently succeed and overwrite — that's exactly
    // the pre-fix behavior that let a hostile publish go undetected.
    await expect(pushRendezvousDoc(client, 'p', { v: 'squatter' }, null)).rejects.toThrow(ConflictError)
    // The legitimate first write is untouched — the rejected push never
    // landed.
    expect((await pullRendezvousDoc(client, 'p'))?.data).toEqual({ v: 'legitimate-first-writer' })
  })

  it('a caller passing its OWN previously-returned hash can legitimately update the document (own-write CAS)', async () => {
    const { client } = fakeStore()
    const first = await pushRendezvousDoc(client, 'p', { v: 1 }, null)
    const second = await pushRendezvousDoc(client, 'p', { v: 2 }, first.hash)
    expect((await pullRendezvousDoc(client, 'p'))?.data).toEqual({ v: 2 })
    expect(second.hash).not.toBe(first.hash)
  })

  it('REJECTS a stale remembered hash — the document changed since the caller last wrote it (tamper detection)', async () => {
    const { client, store } = fakeStore()
    const first = await pushRendezvousDoc(client, 'p', { v: 'legitimate' }, null)
    // A third party overwrites the slot DIRECTLY (bypassing pushRendezvousDoc
    // entirely) — modeling a real attacker who just writes to the wire, not
    // through this function's own CAS discipline.
    store.set('p', { data: { v: 'attacker-overwrite' }, hash: 'attacker-hash' })
    // The legitimate caller's next write, using the hash from ITS OWN last
    // successful publish (not "whatever is currently there"), must reject —
    // this is the actual fix: the old pushRendezvousDoc would have re-pulled
    // 'attacker-hash', silently treated it as the new legitimate baseline,
    // and pushed right over it with no error at all.
    await expect(pushRendezvousDoc(client, 'p', { v: 'legitimate-update' }, first.hash)).rejects.toThrow(ConflictError)
    // The attacker's content is still there — the legitimate caller's write
    // was correctly refused, not silently allowed to stomp over evidence of
    // tampering.
    expect((await pullRendezvousDoc(client, 'p'))?.data).toEqual({ v: 'attacker-overwrite' })
  })

  it('propagates a non-conflict error immediately, with a single push() call — no retry loop', async () => {
    const { client } = fakeStore()
    ;(client.push as unknown as { mockImplementation: (fn: unknown) => void }).mockImplementation(async () => {
      throw new Error('payload too large')
    })
    await expect(pushRendezvousDoc(client, 'p', { v: 1 }, null)).rejects.toThrow('payload too large')
    expect(client.push).toHaveBeenCalledTimes(1)
  })

  it('does NOT retry even on a ConflictError — a single push() call, error propagates as-is', async () => {
    const { client } = fakeStore()
    ;(client.push as unknown as { mockImplementation: (fn: unknown) => void }).mockImplementation(async () => {
      throw new ConflictError('some-other-hash')
    })
    await expect(pushRendezvousDoc(client, 'p', { v: 1 }, null)).rejects.toThrow(ConflictError)
    expect(client.push).toHaveBeenCalledTimes(1)
  })
})

// clearRendezvousDoc is the one place blind-overwrite-and-retry semantics
// are still correct — unpair/cleanup must succeed even without a
// remembered hash (e.g. in-memory state lost across a reload), so it keeps
// the re-pull-and-retry behavior pushRendezvousDoc used to have. Fix C: it
// used to derive its retry baseHash through pullRendezvousDoc, which
// collapses an existing-but-empty doc (exactly what THIS function itself
// writes) down to null — discarding the real hash and turning every
// double-clear into a guaranteed conflict on all 3 retries. Now pulls the
// raw hash directly and returns it, mirroring pushRendezvousDoc.
describe('clearRendezvousDoc — blind overwrite, retried on conflict', () => {
  it('overwrites the slot with an empty document', async () => {
    const { client } = fakeStore()
    await pushRendezvousDoc(client, 'p', { secret: 'stuff' }, null)
    await clearRendezvousDoc(client, 'p')
    expect(await pullRendezvousDoc(client, 'p')).toBeNull()
  })

  it('returns the resulting hash, like pushRendezvousDoc does', async () => {
    const { client } = fakeStore()
    await pushRendezvousDoc(client, 'p', { v: 1 }, null)
    const result = await clearRendezvousDoc(client, 'p')
    expect(result).toHaveProperty('hash')
    expect(typeof result.hash).toBe('string')
  })

  // Regression: clearing an already-cleared slot (a benign double-unpair, or
  // the documented "unpair then re-approve" recovery path) used to always
  // throw "too many baseHash conflicts" — the slot's real hash after the
  // first clear was discarded by pullRendezvousDoc's null-collapsing, so
  // every retry pushed baseHash: null against a slot that DID have a hash.
  it('clearing an ALREADY-CLEARED slot succeeds too — not a guaranteed conflict', async () => {
    const { client } = fakeStore()
    await pushRendezvousDoc(client, 'p', { v: 1 }, null)
    await clearRendezvousDoc(client, 'p') // first clear
    await expect(clearRendezvousDoc(client, 'p')).resolves.toHaveProperty('hash') // second clear
    expect(await pullRendezvousDoc(client, 'p')).toBeNull()
  })

  it('clearing a genuinely never-written slot also succeeds (not just previously-occupied ones)', async () => {
    const { client } = fakeStore()
    await expect(clearRendezvousDoc(client, 'never-written-path')).resolves.toHaveProperty('hash')
  })

  it('succeeds even without the caller ever having tracked a hash (blind-overwrite semantics preserved)', async () => {
    const { client, store } = fakeStore()
    // Simulate "in-memory state was lost" — something is at the path, but
    // this call has no idea what hash it's at (unlike pushRendezvousDoc,
    // which would now require the caller's own hash).
    store.set('p', { data: { stale: true }, hash: 'whatever-is-there' })
    await clearRendezvousDoc(client, 'p')
    expect(await pullRendezvousDoc(client, 'p')).toBeNull()
  })

  it('retries on a CAS conflict caused by a concurrent writer, using the fresh hash', async () => {
    const { client, store, realPush } = fakeStore()
    await pushRendezvousDoc(client, 'p', { v: 1 }, null)
    // Simulate a concurrent writer landing between our pull and push: the
    // first push() call lands a concurrent write and reports a conflict
    // against the stale baseHash our caller pulled; the retry re-pulls (sees
    // the concurrent write) and its push then goes through for real.
    let calls = 0
    ;(client.push as unknown as { mockImplementation: (fn: unknown) => void }).mockImplementation(
      async (path: string, data: Record<string, unknown>, baseHash: string | null) => {
        calls++
        if (calls === 1) {
          store.set('p', { data: { v: 'concurrent' }, hash: 'hash-concurrent' })
          throw new ConflictError('hash-concurrent')
        }
        return realPush(path, data, baseHash)
      },
    )
    await clearRendezvousDoc(client, 'p')
    expect(await pullRendezvousDoc(client, 'p')).toBeNull()
    expect(calls).toBeGreaterThanOrEqual(2)
  })

  it('gives up and throws after too many conflicts', async () => {
    const { client } = fakeStore()
    ;(client.push as unknown as { mockImplementation: (fn: unknown) => void }).mockImplementation(async () => {
      throw new ConflictError('always-conflicting')
    })
    await expect(clearRendezvousDoc(client, 'p')).rejects.toThrow(/too many baseHash conflicts/)
  })

  it('propagates a non-conflict error immediately, without retrying', async () => {
    const { client } = fakeStore()
    ;(client.push as unknown as { mockImplementation: (fn: unknown) => void }).mockImplementation(async () => {
      throw new Error('payload too large')
    })
    await expect(clearRendezvousDoc(client, 'p')).rejects.toThrow('payload too large')
    expect(client.push).toHaveBeenCalledTimes(1)
  })
})

describe('path builders', () => {
  it('joinSessionPath produces the path the Infra collections.py registers', () => {
    expect(joinSessionPath('ABCD1234')).toBe('_pairing/session/ABCD1234')
  })

  it('URL-encode a slot key with unsafe characters', () => {
    expect(joinSessionPath('a/b')).toBe('_pairing/session/a%2Fb')
  })
})
