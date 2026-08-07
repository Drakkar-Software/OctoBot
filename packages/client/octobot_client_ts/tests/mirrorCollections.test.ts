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
  MIRROR_SPACE_PRIVATE_NAME,
  MIRROR_SPACE_PUBLIC_NAME,
  MIRROR_SPACE_SHARED_NAME,
  mirrorSpaceNameFor,
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
  it('routes each visibility to its own dedicated space', () => {
    expect(MIRROR_ROUTING_BY_VISIBILITY.private.spaceName).toBe(MIRROR_SPACE_PRIVATE_NAME)
    expect(MIRROR_ROUTING_BY_VISIBILITY.shared.spaceName).toBe(MIRROR_SPACE_SHARED_NAME)
    expect(MIRROR_ROUTING_BY_VISIBILITY.public.spaceName).toBe(MIRROR_SPACE_PUBLIC_NAME)
  })

  it('gives each visibility the right storage tier — only public is stored world-readable', () => {
    expect(MIRROR_ROUTING_BY_VISIBILITY.private.tier).toBe('private')
    // "shared" is deliberately NOT its own tier: still E2EE + member-gated,
    // it just lives in a space a read-only grant can be minted against.
    expect(MIRROR_ROUTING_BY_VISIBILITY.shared.tier).toBe('private')
    expect(MIRROR_ROUTING_BY_VISIBILITY.public.tier).toBe('public')
  })

  it('sends only public content to the plaintext objpub storage collection', () => {
    expect(MIRROR_ROUTING_BY_VISIBILITY.private.storage).toBe('docs')
    expect(MIRROR_ROUTING_BY_VISIBILITY.shared.storage).toBe('docs')
    expect(MIRROR_ROUTING_BY_VISIBILITY.public.storage).toBe('pub')
  })

  it('demands an opaque node title for public content only', () => {
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

describe('mirrorSpaceNameFor — the private/shared/public split', () => {
  it('routes every third-party-eligible collection to the SHARED space', () => {
    for (const id of THIRD_PARTY_ELIGIBLE_MIRROR_COLLECTIONS) {
      expect(mirrorSpaceNameFor(id)).toBe(MIRROR_SPACE_SHARED_NAME)
    }
  })

  it('routes user-settings (never third-party eligible) to the PRIVATE space', () => {
    expect(mirrorSpaceNameFor('user-settings')).toBe(MIRROR_SPACE_PRIVATE_NAME)
  })

  // `_project_objindex_public` keys the world-readable object projection BY
  // SPACE ID, so a public node parked in the shared space would hand every
  // anonymous reader the id of the space a read-only grant is minted against.
  it('routes public content to a THIRD space, never the shared or private one', () => {
    expect(MIRROR_ROUTING_BY_VISIBILITY.public.spaceName).toBe(MIRROR_SPACE_PUBLIC_NAME)
    expect(MIRROR_SPACE_PUBLIC_NAME).not.toBe(MIRROR_SPACE_SHARED_NAME)
    expect(MIRROR_SPACE_PUBLIC_NAME).not.toBe(MIRROR_SPACE_PRIVATE_NAME)
  })

  it('the three space names are pairwise distinct', () => {
    const names = [MIRROR_SPACE_SHARED_NAME, MIRROR_SPACE_PRIVATE_NAME, MIRROR_SPACE_PUBLIC_NAME]
    expect(new Set(names).size).toBe(names.length)
  })

  it('a read-only grant scoped to the shared space can never structurally reach user-settings', () => {
    // This is the property the space split exists to guarantee: since a
    // space-member cap's scope covers spaces/{spaceId}/** for exactly ONE
    // space, no collection routed to the private space can ever share a
    // space (and therefore a keyring, and therefore a grant) with any
    // third-party-eligible collection.
    const sharedSpaceCollections = MIRROR_COLLECTIONS.filter(
      (c) => mirrorSpaceNameFor(c.id) === MIRROR_SPACE_SHARED_NAME,
    )
    expect(sharedSpaceCollections.some((c) => c.id === 'user-settings')).toBe(false)
  })
})

describe('mirrorTierFor — what the writer hands createSpaceMirrorChannel', () => {
  it('creates every collection that exists today at the private (E2EE, space-gated) tier', () => {
    for (const c of MIRROR_COLLECTIONS) {
      expect(mirrorTierFor(c.id)).toBe('private')
    }
  })

  it('an unknown id gets the private tier, never the world-readable one', () => {
    expect(mirrorTierFor('not-a-real-collection')).toBe('private')
  })
})

describe('mirror doc path helpers', () => {
  // Mirror content lives in `objdoc`, the canonical content location for a node
  // created access:"space", enc:true. It used to have its own `mirrordoc`
  // collection purely for a bigger body limit; objdoc is now 10 MiB and that
  // clone is gone. This assertion is the guard against it drifting back.
  it('resolves to objdoc, the canonical node-content collection', () => {
    expect(mirrorDocPath('user-accounts', 'sp-1', 'obj-1')).toBe('spaces/sp-1/objects/docs/obj-1')
    expect(mirrorDocPath('user-accounts', 'sp-1', 'obj-1')).not.toContain('objects/mirror/')
  })

  it('pull/push paths carry the right action prefix', () => {
    expect(mirrorDocPullPath('user-accounts', 'sp-1', 'obj-1')).toBe(
      '/pull/spaces/sp-1/objects/docs/obj-1',
    )
    expect(mirrorDocPushPath('user-accounts', 'sp-1', 'obj-1')).toBe(
      '/push/spaces/sp-1/objects/docs/obj-1',
    )
  })

  it('keeps every private/shared collection on the objdoc path', () => {
    for (const c of MIRROR_COLLECTIONS) {
      expect(mirrorDocPath(c.id, 'sp-1', 'obj-1')).toBe('spaces/sp-1/objects/docs/obj-1')
    }
  })

  // A `tier:"public"` node is stored access:"public", enc:false. Writing it to
  // objdoc would put world-readable content on the private merge-doc path,
  // where the server does not expect plaintext.
  it('routes PUBLIC content to objpub (objects/pub/), not objdoc', () => {
    expect(mirrorDocPathForVisibility('public', 'sp-1', 'obj-1')).toBe(
      'spaces/sp-1/objects/pub/obj-1',
    )
    expect(mirrorDocPathForVisibility('private', 'sp-1', 'obj-1')).toBe(
      'spaces/sp-1/objects/docs/obj-1',
    )
    expect(mirrorDocPathForVisibility('shared', 'sp-1', 'obj-1')).toBe(
      'spaces/sp-1/objects/docs/obj-1',
    )
  })

  it('mirrorDocPath is exactly mirrorDocPathForVisibility of the collection visibility', () => {
    for (const c of MIRROR_COLLECTIONS) {
      expect(mirrorDocPath(c.id, 'sp-1', 'obj-1')).toBe(
        mirrorDocPathForVisibility(c.visibility, 'sp-1', 'obj-1'),
      )
    }
  })

  // The mirror gets its own spaces, so sharing objdoc with ordinary user
  // documents cannot collide: different space entirely, and node ids are minted
  // by createNode rather than derived from a collection id.
  it('keeps mirror content in dedicated spaces, not a user content space', () => {
    expect(MIRROR_SPACE_SHARED_NAME).toBe('octobot-mirror')
    expect(MIRROR_SPACE_PRIVATE_NAME).toBe('octobot-mirror-private')
    expect(MIRROR_SPACE_PUBLIC_NAME).toBe('octobot-mirror-public')
  })
})

// Infra's `_project_objindex_public` republishes a public node's title into the
// world-readable `_index/objects/public` projection. A descriptive title there
// tells any anonymous reader exactly which collections a given wallet mirrors.
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

  it('carries the same three mirror space names', () => {
    expect(pyConstant('MIRROR_SPACE_SHARED_NAME')).toBe(MIRROR_SPACE_SHARED_NAME)
    expect(pyConstant('MIRROR_SPACE_PRIVATE_NAME')).toBe(MIRROR_SPACE_PRIVATE_NAME)
    expect(pyConstant('MIRROR_SPACE_PUBLIC_NAME')).toBe(MIRROR_SPACE_PUBLIC_NAME)
  })

  it('routes each visibility to the same space name on both sides', () => {
    // Python's `mirror_space_name_for`, restated as the mapping it implements —
    // the ids above already proved which visibility each collection carries, so
    // this pins the visibility -> space edge itself.
    const pySpaceFor: Record<string, string> = {
      public: pyConstant('MIRROR_SPACE_PUBLIC_NAME'),
      shared: pyConstant('MIRROR_SPACE_SHARED_NAME'),
      private: pyConstant('MIRROR_SPACE_PRIVATE_NAME'),
    }
    for (const visibility of ALL_VISIBILITIES) {
      expect(pySpaceFor[visibility]).toBe(MIRROR_ROUTING_BY_VISIBILITY[visibility].spaceName)
    }
    // And that Python really branches on all three, not just two.
    expect(py).toMatch(/if visibility == "public":/)
    expect(py).toMatch(/if visibility == "shared":/)
  })

  it('derives is_third_party_eligible from visibility rather than storing it', () => {
    expect(py).not.toContain('third_party_eligible: bool')
    expect(py).toMatch(/mirror_visibility_for\(collection_id\) != "private"/)
  })
})
