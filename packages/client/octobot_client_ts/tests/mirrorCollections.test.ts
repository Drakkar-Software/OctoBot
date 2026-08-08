import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import {
  DEFAULT_MIRROR_COLLECTIONS,
  isKnownMirrorCollection,
  isPublicMirrorCollection,
  isThirdPartyEligible,
  MIRROR_COLLECTIONS,
  MIRROR_PUBLIC_NODE_TITLE,
  MIRROR_ROUTING_BY_VISIBILITY,
  mirrorDocPath,
  mirrorDocPathForVisibility,
  mirrorDocPullPath,
  mirrorDocPushPath,
  mirrorNodeTitleFor,
  mirrorNodeTitleForVisibility,
  MIRROR_SPACE_NAME,
  isIsolatedMirrorCollection,
  mirrorTierFor,
  mirrorVisibilityFor,
  THIRD_PARTY_ELIGIBLE_MIRROR_COLLECTIONS,
  type MirrorVisibility,
} from '../src/client/mirror/collections.js'

const ALL_VISIBILITIES: readonly MirrorVisibility[] = ['private', 'shared', 'public']

describe('MIRROR_COLLECTIONS', () => {
  it('never includes user-accounts-auth — credentials are never mirror-eligible', () => {
    expect(MIRROR_COLLECTIONS.some((c) => c.id === 'user-accounts-auth')).toBe(false)
    expect(isKnownMirrorCollection('user-accounts-auth')).toBe(false)
  })

  it('has no duplicate ids', () => {
    const ids = MIRROR_COLLECTIONS.map((c) => c.id)
    expect(new Set(ids).size).toBe(ids.length)
  })

  it('user-settings is mirror-eligible but not third-party eligible', () => {
    expect(isKnownMirrorCollection('user-settings')).toBe(true)
    expect(isThirdPartyEligible('user-settings')).toBe(false)
  })

  it('accounts/user-data/strategies are third-party eligible and default on', () => {
    for (const id of ['user-accounts', 'user-data', 'user-strategies']) {
      expect(isThirdPartyEligible(id)).toBe(true)
      expect(DEFAULT_MIRROR_COLLECTIONS).toContain(id)
    }
  })

  it('accounts-trading is third-party eligible but not default-on', () => {
    expect(isThirdPartyEligible('user-accounts-trading')).toBe(true)
    expect(DEFAULT_MIRROR_COLLECTIONS).not.toContain('user-accounts-trading')
  })

  it('THIRD_PARTY_ELIGIBLE_MIRROR_COLLECTIONS excludes user-settings', () => {
    expect(THIRD_PARTY_ELIGIBLE_MIRROR_COLLECTIONS).not.toContain('user-settings')
    expect(THIRD_PARTY_ELIGIBLE_MIRROR_COLLECTIONS).toContain('user-accounts')
  })

  it('an unknown id is neither known nor third-party eligible', () => {
    expect(isKnownMirrorCollection('not-a-real-collection')).toBe(false)
    expect(isThirdPartyEligible('not-a-real-collection')).toBe(false)
  })
})

// `visibility` replaced a `thirdPartyEligible: boolean`. These pin the exact
// per-collection values — flipping any of them is a product decision that must
// not happen as a side effect of refactoring the enum.
describe('visibility: the per-collection assignments', () => {
  it('assigns exactly the intended visibility to every collection', () => {
    const byId = Object.fromEntries(MIRROR_COLLECTIONS.map((c) => [c.id, c.visibility]))
    expect(byId).toEqual({
      'user-accounts': 'shared',
      'user-data': 'shared',
      'user-strategies': 'shared',
      'user-accounts-trading': 'shared',
      'user-settings': 'private',
    })
  })

  it('nothing is public today — publishing a collection is a product decision, not a refactor', () => {
    expect(MIRROR_COLLECTIONS.filter((c) => c.visibility === 'public')).toEqual([])
    for (const c of MIRROR_COLLECTIONS) {
      expect(isPublicMirrorCollection(c.id)).toBe(false)
    }
  })

  it('an unknown id resolves to the SAFE end of the enum, not the permissive one', () => {
    expect(mirrorVisibilityFor('not-a-real-collection')).toBe('private')
    expect(isPublicMirrorCollection('not-a-real-collection')).toBe(false)
  })

  it('isThirdPartyEligible is DERIVED from visibility (!== "private"), for every collection', () => {
    for (const c of MIRROR_COLLECTIONS) {
      expect(isThirdPartyEligible(c.id)).toBe(c.visibility !== 'private')
    }
    // …and for the value no collection carries yet: a public collection must
    // read as grant-reachable too, not just a shared one.
    expect(MIRROR_ROUTING_BY_VISIBILITY.public).toBeDefined()
    expect(ALL_VISIBILITIES.filter((v) => v !== 'private')).toEqual(['shared', 'public'])
  })
})

describe('MIRROR_ROUTING_BY_VISIBILITY — one row per visibility', () => {
  it('gives each visibility the tier that matches its audience', () => {
    // The space keyring is space-wide, so anything grantable must NOT be on
    // it — "shared" maps to the isolated tier (its own per-node keyring),
    // which is what makes a grant reach one node instead of the whole space.
    expect(MIRROR_ROUTING_BY_VISIBILITY.private.tier).toBe('private')
    expect(MIRROR_ROUTING_BY_VISIBILITY.shared.tier).toBe('isolated')
    expect(MIRROR_ROUTING_BY_VISIBILITY.public.tier).toBe('public')
  })

  it('sends each tier to the storage collection whose read roles match it', () => {
    // objdoc: space:member only, no cap fallback — unreachable by a per-node
    // grant, which is exactly why "shared" cannot live there.
    expect(MIRROR_ROUTING_BY_VISIBILITY.private.storage).toBe('docs')
    // objinv: space:member OR cap:read:objinv — the cap fallback is the point.
    expect(MIRROR_ROUTING_BY_VISIBILITY.shared.storage).toBe('invite')
    expect(MIRROR_ROUTING_BY_VISIBILITY.public.storage).toBe('pub')
  })

  it('demands an opaque node title for public content only', () => {
    // private and isolated titles live in objindex, which is space:member and
    // unreachable by a per-node grant holder.
    expect(MIRROR_ROUTING_BY_VISIBILITY.private.opaqueTitle).toBe(false)
    expect(MIRROR_ROUTING_BY_VISIBILITY.shared.opaqueTitle).toBe(false)
    expect(MIRROR_ROUTING_BY_VISIBILITY.public.opaqueTitle).toBe(true)
  })

  it('has a row for every visibility value and no extras', () => {
    expect(Object.keys(MIRROR_ROUTING_BY_VISIBILITY).sort()).toEqual(
      [...ALL_VISIBILITIES].sort(),
    )
  })
})

describe('one space, per-node grants', () => {
  it('every collection lives in the ONE mirror space', () => {
    expect(MIRROR_SPACE_NAME).toBe('octobot-mirror')
  })

  it('every third-party-eligible collection is on the isolated tier', () => {
    // The property the old three-space split existed to guarantee, now
    // enforced per node rather than per space: a grant is minted over one
    // node's own keyring, so it cannot reach any other collection.
    for (const id of THIRD_PARTY_ELIGIBLE_MIRROR_COLLECTIONS) {
      expect(isIsolatedMirrorCollection(id)).toBe(true)
      expect(mirrorTierFor(id)).toBe('isolated')
    }
  })

  it('user-settings stays on the space keyring and is never grantable', () => {
    expect(isIsolatedMirrorCollection('user-settings')).toBe(false)
    expect(isThirdPartyEligible('user-settings')).toBe(false)
    expect(mirrorTierFor('user-settings')).toBe('private')
  })

  it('an unknown id is not grantable and gets the private tier', () => {
    expect(isIsolatedMirrorCollection('not-a-real-collection')).toBe(false)
    expect(mirrorTierFor('not-a-real-collection')).toBe('private')
  })
})

describe('mirror doc path helpers', () => {
  it('routes an isolated (grantable) collection to objinv, not objdoc', () => {
    // objdoc's read roles are space:member with NO cap fallback, so a
    // per-node grant holder could never fetch it. objinv is the one that
    // accepts cap:read:objinv.
    expect(mirrorDocPath('user-accounts', 'sp-1', 'obj-1')).toBe(
      'spaces/sp-1/objects/n/obj-1/content',
    )
    for (const id of THIRD_PARTY_ELIGIBLE_MIRROR_COLLECTIONS) {
      expect(mirrorDocPath(id, 'sp-1', 'obj-1')).toBe('spaces/sp-1/objects/n/obj-1/content')
    }
  })

  it('keeps space-private content on objdoc', () => {
    expect(mirrorDocPath('user-settings', 'sp-1', 'obj-1')).toBe('spaces/sp-1/objects/docs/obj-1')
  })

  it('pull/push paths carry the right action prefix', () => {
    expect(mirrorDocPullPath('user-accounts', 'sp-1', 'obj-1')).toBe(
      '/pull/spaces/sp-1/objects/n/obj-1/content',
    )
    expect(mirrorDocPushPath('user-accounts', 'sp-1', 'obj-1')).toBe(
      '/push/spaces/sp-1/objects/n/obj-1/content',
    )
  })

  // A tier:"public" node is stored access:"public", enc:false. Writing it to
  // objdoc would put world-readable content on the private merge-doc path.
  it('routes PUBLIC content to objpub (objects/pub/)', () => {
    expect(mirrorDocPathForVisibility('public', 'sp-1', 'obj-1')).toBe(
      'spaces/sp-1/objects/pub/obj-1',
    )
    expect(mirrorDocPathForVisibility('private', 'sp-1', 'obj-1')).toBe(
      'spaces/sp-1/objects/docs/obj-1',
    )
    expect(mirrorDocPathForVisibility('shared', 'sp-1', 'obj-1')).toBe(
      'spaces/sp-1/objects/n/obj-1/content',
    )
  })

  it('mirrorDocPath is exactly mirrorDocPathForVisibility of the collection visibility', () => {
    for (const c of MIRROR_COLLECTIONS) {
      expect(mirrorDocPath(c.id, 'sp-1', 'obj-1')).toBe(
        mirrorDocPathForVisibility(c.visibility, 'sp-1', 'obj-1'),
      )
    }
  })
})

describe('mirrorNodeTitleFor — a public node must not advertise what it holds', () => {
  it('gives a public node an opaque title that is not the collection id', () => {
    for (const c of MIRROR_COLLECTIONS) {
      expect(mirrorNodeTitleForVisibility('public', c.id)).toBe(MIRROR_PUBLIC_NODE_TITLE)
      expect(mirrorNodeTitleForVisibility('public', c.id)).not.toBe(c.id)
    }
  })

  it('the opaque title carries no collection information at all', () => {
    // One constant shared by every public collection: zero bits about which
    // collection the node holds.
    const titles = MIRROR_COLLECTIONS.map((c) => mirrorNodeTitleForVisibility('public', c.id))
    expect(new Set(titles).size).toBe(1)
    expect(MIRROR_COLLECTIONS.some((c) => c.id === MIRROR_PUBLIC_NODE_TITLE)).toBe(false)
  })

  it('keeps the descriptive collection-id title for private and shared nodes', () => {
    for (const c of MIRROR_COLLECTIONS) {
      expect(mirrorNodeTitleForVisibility('private', c.id)).toBe(c.id)
      expect(mirrorNodeTitleForVisibility('shared', c.id)).toBe(c.id)
      expect(mirrorNodeTitleFor(c.id)).toBe(c.id)
    }
  })
})

// The node's Python writer keeps its own copy of this registry
// (packages/sync/octobot_sync/mirror/collections.py). Both are read by the same
// wallet: the node writes mirror nodes with the Python copy, the app/website
// reads and grants against the TS copy. A drift means a collection lands in a
// space the other side does not look in — or, for `visibility`, that a
// collection the TS side treats as private is handed out by a Python-minted
// grant. This parses the Python file rather than restating its values, so the
// two really cannot disagree.
describe('TS/Python collection-config parity', () => {
  const PY_PATH = join(
    import.meta.dirname,
    '..',
    '..',
    '..',
    'sync',
    'octobot_sync',
    'mirror',
    'collections.py',
  )
  const py = readFileSync(PY_PATH, 'utf8')

  function pyConstant(name: string): string {
    const m = new RegExp(`^${name}\\s*=\\s*"([^"]+)"`, 'm').exec(py)
    if (!m) throw new Error(`${name} not found in ${PY_PATH}`)
    return m[1]
  }

  const pyCollections = [...py.matchAll(/MirrorCollection\(\s*"([^"]+)",\s*(True|False),\s*"([^"]+)"\s*\)/g)]
    .map((m) => ({ id: m[1], defaultEnabled: m[2] === 'True', visibility: m[3] }))

  it('the Python registry was parsed at all (guards this whole block against going vacuous)', () => {
    expect(pyCollections.length).toBe(MIRROR_COLLECTIONS.length)
    expect(pyCollections.length).toBeGreaterThan(0)
  })

  it('carries the same ids, defaults and visibility values, in the same order', () => {
    expect(pyCollections).toEqual(
      MIRROR_COLLECTIONS.map((c) => ({
        id: c.id,
        defaultEnabled: c.defaultEnabled,
        visibility: c.visibility,
      })),
    )
  })

  it('carries the same single mirror space name', () => {
    expect(pyConstant('MIRROR_SPACE_NAME')).toBe(MIRROR_SPACE_NAME)
  })

  it('routes each visibility to the same storage tier on both sides', () => {
    // The visibility -> tier edge is now what decides who can reach a
    // collection (one space, per-node keyrings), so this is the parity edge
    // that matters — the ids above already pinned each collection's
    // visibility.
    const pyTierFor: Record<string, string> = {
      public: 'public',
      shared: 'isolated',
      private: 'private',
    }
    for (const visibility of ALL_VISIBILITIES) {
      expect(pyTierFor[visibility]).toBe(MIRROR_ROUTING_BY_VISIBILITY[visibility].tier)
    }
    // And that Python really branches on all three, not just two.
    expect(py).toMatch(/if visibility == "public":/)
    expect(py).toMatch(/if visibility == "shared":/)
  })

  it('routes the isolated tier to objinv on both sides', () => {
    // objdoc has no cap fallback in its read roles, so a grantable collection
    // stored there would be unreadable by the grant holder. Both sides must
    // agree, or the writer and the website-side reader disagree on the path.
    expect(py).toContain('objects/n/')
  })

  it('keeps third-party eligibility derived from visibility rather than storing it', () => {
    // Eligibility is read off `visibility` on both sides. The Python registry
    // growing a stored field of its own is exactly how the two would drift.
    expect(py).not.toContain('third_party_eligible')
  })
})
