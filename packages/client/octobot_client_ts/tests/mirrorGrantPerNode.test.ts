import { describe, expect, it, vi } from 'vitest'
import { createPairingRequest } from '../src/identity/pairingRequest.js'
import { parseMirrorGrantBundle } from '../src/client/pairing/mirrorReader.js'

const ORIGIN = 'https://example.com'
const RENDEZVOUS = { baseUrl: 'https://sync.example', namespace: 'dk' }
const SPACE = { id: 'sp-1', name: 'octobot-mirror' }

/** The nodes a synced mirror space would hold: three grantable (visibility
 *  "shared") plus user-settings, which is space-private and must never be
 *  granted. */
const TREE = [
  { id: 'nd-accounts', type: 'user-accounts' },
  { id: 'nd-data', type: 'user-data' },
  { id: 'nd-strategies', type: 'user-strategies' },
  { id: 'nd-settings', type: 'user-settings' },
  { id: 'nd-other', type: 'not-a-mirror-collection' },
]

const inviteToNode = vi.fn(
  async (
    _session: unknown,
    _spaceId: string,
    nodeId: string,
    _requestJson: string,
    node: { enc?: boolean },
    nodeName?: string,
    opts?: { isolated?: boolean; write?: boolean },
  ) =>
    JSON.stringify({
      spaceId: _spaceId,
      nodeId,
      nodeName,
      kind: node.enc && opts?.isolated ? 'node-enc' : 'space-enc',
      nodeCap: { ops: opts?.write === false ? ['read', 'list'] : ['read', 'write', 'list'] },
      keyringCap: { ops: ['read'] },
    }),
)
const removeNodeKeyringRecipient = vi.fn(async () => ({ newEpoch: 2 }))
const inviteToSpace = vi.fn()

vi.mock('@drakkar.software/starfish-spaces', async (importOriginal) => {
  const actual = await importOriginal<Record<string, unknown>>()
  return {
    ...actual,
    inviteToNode: (...args: unknown[]) => inviteToNode(...(args as Parameters<typeof inviteToNode>)),
    inviteToSpace: (...args: unknown[]) => inviteToSpace(...args),
    removeNodeKeyringRecipient: (...args: unknown[]) => removeNodeKeyringRecipient(),
    readObjectTree: async () => TREE,
  }
})

vi.mock('../src/client/mirror/index.js', async (importOriginal) => {
  const actual = await importOriginal<Record<string, unknown>>()
  return { ...actual, findOrCreateMirrorSpace: async () => SPACE }
})

const { mintPairingGrant, revokePairingGrant, NothingToShareError } = await import(
  '../src/client/pairing/mirrorGrant.js'
)

async function mint() {
  const { request } = await createPairingRequest({ origin: ORIGIN, rendezvous: RENDEZVOUS })
  return { request, grant: await mintPairingGrant({} as never, request) }
}

describe('mintPairingGrant — one grant per node, never the space', () => {
  it('grants exactly the third-party-eligible collections that have a node', async () => {
    const { grant } = await mint()
    expect(grant.coveredCollections.sort()).toEqual(
      ['user-accounts', 'user-data', 'user-strategies'],
    )
  })

  it('NEVER grants user-settings — it is space-private, not isolated', async () => {
    const { grant } = await mint()
    expect(grant.coveredCollections).not.toContain('user-settings')
    const granted = inviteToNode.mock.calls.map(([, , nodeId]) => nodeId)
    expect(granted).not.toContain('nd-settings')
  })

  it('ignores nodes that are not known mirror collections', async () => {
    const { grant } = await mint()
    expect(grant.coveredCollections).not.toContain('not-a-mirror-collection')
  })

  it('never joins the space roster — no inviteToSpace, ever', async () => {
    // The property the whole redesign rests on: a grant holder off the roster
    // cannot read objindex, so they cannot enumerate what else exists.
    await mint()
    expect(inviteToSpace).not.toHaveBeenCalled()
  })

  it('mints every invite isolated and read-only', async () => {
    inviteToNode.mockClear()
    await mint()
    expect(inviteToNode.mock.calls.length).toBeGreaterThan(0)
    for (const call of inviteToNode.mock.calls) {
      const [, , , , node, , opts] = call
      expect(node).toEqual({ enc: true })
      expect(opts).toEqual({ isolated: true, write: false })
    }
  })

  it('publishes a bundle the website-side parser accepts', async () => {
    const { grant } = await mint()
    const parsed = parseMirrorGrantBundle(grant.bundle)
    expect(parsed.spaceId).toBe(SPACE.id)
    expect(parsed.nodes.map((n) => n.collectionId).sort()).toEqual(
      ['user-accounts', 'user-data', 'user-strategies'],
    )
    for (const node of parsed.nodes) {
      expect(node.contentCap).toBeTruthy()
      expect(node.keyringCap).toBeTruthy()
      expect(node.nodeId).toMatch(/^nd-/)
    }
  })

  it('carries the KEM pubkey revocation needs', async () => {
    const { request, grant } = await mint()
    expect(grant.memberKemPub).toBe(request.devKemPub)
  })
})

describe('parseMirrorGrantBundle', () => {
  it('rejects an old space-wide grant loudly rather than reading nothing', async () => {
    const legacy = JSON.stringify({ spaceId: 'sp-1', cap: { ops: ['read'] } })
    expect(() => parseMirrorGrantBundle(legacy)).toThrow(/older, incompatible version/)
  })

  it('rejects a node missing either cap', () => {
    const noKeyring = JSON.stringify({
      v: 1,
      spaceId: 'sp-1',
      nodes: [{ collectionId: 'user-accounts', nodeId: 'nd-1', contentCap: {} }],
    })
    expect(() => parseMirrorGrantBundle(noKeyring)).toThrow(/keyring cap/)
  })
})

describe('revokePairingGrant', () => {
  it('rotates every granted node keyring, one call per node', async () => {
    removeNodeKeyringRecipient.mockClear()
    const { grant } = await mint()
    const nodeIds = parseMirrorGrantBundle(grant.bundle).nodes.map((n) => n.nodeId)
    await revokePairingGrant({} as never, grant.spaceId, nodeIds, grant.memberKemPub)
    expect(removeNodeKeyringRecipient).toHaveBeenCalledTimes(nodeIds.length)
  })

  it('revoking one collection leaves the others alone', async () => {
    // Per-node revocation is the capability the space-member grant could not
    // express: it was all-or-nothing over every shared collection.
    removeNodeKeyringRecipient.mockClear()
    const { grant } = await mint()
    await revokePairingGrant({} as never, grant.spaceId, ['nd-accounts'], grant.memberKemPub)
    expect(removeNodeKeyringRecipient).toHaveBeenCalledTimes(1)
  })
})

describe('NothingToShareError', () => {
  it('is thrown when no grantable collection has a node yet', async () => {
    TREE.length = 0
    TREE.push({ id: 'nd-settings', type: 'user-settings' })
    const { request } = await createPairingRequest({ origin: ORIGIN, rendezvous: RENDEZVOUS })
    await expect(mintPairingGrant({} as never, request)).rejects.toBeInstanceOf(NothingToShareError)
  })
})
