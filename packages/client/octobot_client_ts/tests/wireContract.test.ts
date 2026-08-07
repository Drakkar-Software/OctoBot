import { describe, it, expect } from 'vitest'
import { BOOTSTRAP_CHALLENGE } from '../src/identity/capProvider.js'
import {
  SYNC_MOUNT_PATH,
  SYNC_NAMESPACE,
  STARFISH_ENCRYPTION_SALT,
} from '../src/crypto/wireConstants.js'
import { NODE_COLLECTIONS } from '../src/collections/nodeCollections.js'
import { pullPath, pushPath } from '../src/collections/paths.js'
import { API_PREFIX, DEFAULT_NODE_PORT, NODE_STATUS_PATH } from '../src/transport/constants.js'
import { deriveAesKeyBytes } from '../src/crypto/hkdf.js'
import { toHex } from '../src/internal/bytes.js'
import { joinSessionPath } from '../src/transport/rendezvous.js'
import { createPairingRequest } from '../src/identity/pairingRequest.js'
import { createReadOnlyPairing } from '../src/identity/pairing.js'
import { publishPairingGrant } from '../src/client/pairing/pairingGrantExchange.js'
import { generateDeviceKeys } from '@drakkar.software/starfish-identities'
import type { MintedPairingGrant } from '../src/client/pairing/mirrorGrant.js'

// Every literal below is shared with the node's Python implementation
// (packages/sync/octobot_sync/*.py in this repo). A mismatch on either side
// breaks sync SILENTLY — this test exists so a change to one of these can
// never land without someone noticing. See
// https://docs.octobot.cloud/client-sdk/wire-contract.

describe('wire contract: identity', () => {
  it('BOOTSTRAP_CHALLENGE matches octobot_sync/constants.py SYNC_BOOTSTRAP_CHALLENGE', () => {
    expect(BOOTSTRAP_CHALLENGE).toBe('octobot:sync-bootstrap')
  })
})

describe('wire contract: sync transport', () => {
  it('SYNC_MOUNT_PATH', () => {
    expect(SYNC_MOUNT_PATH).toBe('sync')
  })
  it('SYNC_NAMESPACE', () => {
    expect(SYNC_NAMESPACE).toBe('octobot')
  })
  it('STARFISH_ENCRYPTION_SALT matches octobot_sync/constants.py HKDF_SALT_STRING', () => {
    expect(STARFISH_ENCRYPTION_SALT).toBe('octobot-starfish-identity-v1')
  })
})

describe('wire contract: node REST', () => {
  it('API_PREFIX', () => {
    expect(API_PREFIX).toBe('/api/v1')
  })
  it('DEFAULT_NODE_PORT', () => {
    expect(DEFAULT_NODE_PORT).toBe(5001)
  })
  it('NODE_STATUS_PATH', () => {
    expect(NODE_STATUS_PATH).toBe('/api/v1/setup/status')
  })
})

// Device-code and QR pairing wire literals. CLAUDE.md names this exact
// class of literal as a silent-failure hazard — before this describe block
// existed, the paths were only pinned incidentally inside rendezvous.test.ts's
// behavior tests, and the payload kinds/versions only inside round-trip
// assertions, neither of which a reviewer changing the Infra draft's
// collection definitions would necessarily look at.
// docs/client-sdk/wire-contract.md's "Pairing wire literals" section
// documents this describe block's assertions — keep both in sync.
describe('wire contract: device-code pairing (rendezvous)', () => {
  it('joinSessionPath matches the joinsessions collection storagePath template (_pairing/session/{code})', () => {
    expect(joinSessionPath('ABCD1234')).toBe('_pairing/session/ABCD1234')
  })

  it('a PairingRequestPayload carries kind "octobot-pairing-request" and v: 1', async () => {
    const { request } = await createPairingRequest({
      origin: 'https://example.test',
      rendezvous: { baseUrl: 'https://sync.example.test', namespace: 'dk' },
    })
    expect(request.kind).toBe('octobot-pairing-request')
    expect(request.v).toBe(1)
  })

  // The grant's kind/version were previously only visible INSIDE the sealed
  // plaintext (invisible on the wire) — the joinsessions merge added an
  // OUTER unsealed envelope specifically so a poller can tell "this slot
  // holds a grant" without attempting unseal(). This pin was called out as
  // missing in wire-contract.md before the merge ("the grant envelope
  // kind/version is not yet pinned by that test") — closing that gap here.
  it('publishPairingGrant writes an UNSEALED {v:1, kind:"octobot-pairing-grant", sealed} wrapper at joinSessionPath(code)', async () => {
    const rendezvous = { baseUrl: 'https://sync.example.test', namespace: 'dk' }
    const { request } = await createPairingRequest({ origin: 'https://example.test', rendezvous })
    const sealerDevice = generateDeviceKeys()
    const sealer = { edPrivHex: sealerDevice.edPriv, edPubHex: sealerDevice.edPub }
    const grant: MintedPairingGrant = {
      bundle: JSON.stringify({ spaceId: 's1', spaceName: 'n1', cap: {} }),
      spaceId: 's1',
      memberUserId: 'u1',
      coveredCollections: [],
    }
    let capturedBody: unknown
    const fetchImpl: typeof fetch = async (input, init) => {
      const path = new URL(typeof input === 'string' ? input : (input as URL).toString()).pathname
      expect(path).toContain(encodeURIComponent(request.code))
      capturedBody = JSON.parse(String(init?.body))
      return new Response(JSON.stringify({ hash: 'h1', timestamp: Date.now() }), { status: 200 })
    }
    await publishPairingGrant({ request, sealer, grant, rendezvous, baseHash: null, fetch: fetchImpl })
    const doc = (capturedBody as { data: Record<string, unknown> }).data
    expect(doc.v).toBe(1)
    expect(doc.kind).toBe('octobot-pairing-grant')
    expect(doc.sealed).toBeTypeOf('object')
  })
})

describe('wire contract: QR read-only pairing', () => {
  it('a ReadOnlyPairingPayload carries kind "octobot-read-only-pairing" and v: 2', async () => {
    const MNEMONIC = 'abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about'
    const { payload } = await createReadOnlyPairing(MNEMONIC, 'bip44', { host: '192.0.2.1', port: 5001 })
    const parsed = JSON.parse(payload) as { kind: string; v: number }
    expect(parsed.kind).toBe('octobot-read-only-pairing')
    expect(parsed.v).toBe(2)
  })
})

describe('wire contract: node collections', () => {
  // Each encryptionInfo MUST equal 'octobot-sync-' + the node's own
  // Collections enum value (octobot_sync/enums.py). The node derives its
  // per-collection key from this exact string.
  const expected: Record<string, { storagePath: string; encryptionInfo: string }> = {
    userData: { storagePath: 'users/{identity}/data', encryptionInfo: 'octobot-sync-user-data' },
    accounts: { storagePath: 'users/{identity}/accounts', encryptionInfo: 'octobot-sync-user-accounts' },
    settings: { storagePath: 'users/{identity}/settings', encryptionInfo: 'octobot-sync-user-settings' },
    strategies: { storagePath: 'users/{identity}/strategies', encryptionInfo: 'octobot-sync-user-strategies' },
    actions: { storagePath: 'users/{identity}/actions', encryptionInfo: 'octobot-sync-user-actions' },
    accountTrading: {
      storagePath: 'users/{identity}/accounts/{accountId}/trading',
      encryptionInfo: 'octobot-sync-user-accounts-trading',
    },
  }

  for (const [key, exp] of Object.entries(expected)) {
    it(`${key}: storagePath + encryptionInfo`, () => {
      const info = NODE_COLLECTIONS[key as keyof typeof NODE_COLLECTIONS]
      expect(info.storagePath).toBe(exp.storagePath)
      expect(info.encryptionInfo).toBe(exp.encryptionInfo)
    })
  }

  it('actions is the only appendOnly collection', () => {
    for (const [key, info] of Object.entries(NODE_COLLECTIONS)) {
      expect(Boolean(info.appendOnly)).toBe(key === 'actions')
    }
  })

  it('pullPath/pushPath resolve every collection template with an identity + accountId', () => {
    for (const info of Object.values(NODE_COLLECTIONS)) {
      const params = { identity: 'abc123', accountId: 'acc1' }
      expect(pullPath(info.storagePath, params)).toMatch(/^\/pull\/users\//)
      expect(pushPath(info.storagePath, params)).toMatch(/^\/push\/users\//)
      // No unresolved {placeholder} left over.
      expect(pullPath(info.storagePath, params)).not.toMatch(/\{[^}]+\}/)
    }
  })
})

describe('wire contract: 0x-prefix stripping before HKDF', () => {
  // octobot_sync's community_wallet.py stores every wallet's private key
  // with `.removeprefix("0x")`, and octobot_sync/crypto.py HKDFs that
  // stripped string directly. HKDF treats its secret as an opaque byte
  // string (not parsed hex), so `"0x1234"` and `"1234"` derive completely
  // different key bytes despite representing the same private key
  // numerically. `createSecretEncryptor`/`deriveCollectionKeys` must both
  // strip the prefix before deriving, or a document encrypted by this
  // package is silently undecryptable by the node (or vice versa).
  it('a "0x"-prefixed secret and its stripped form derive DIFFERENT keys — the prefix is significant to HKDF', async () => {
    const withPrefix = await deriveAesKeyBytesViaWebCrypto('0xdeadbeef', 'salt', 'info')
    const stripped = await deriveAesKeyBytesViaWebCrypto('deadbeef', 'salt', 'info')
    expect(toHex(withPrefix)).not.toBe(toHex(stripped))
  })

  it('deriveAesKeyBytes (local HKDF reimplementation) matches an independent WebCrypto HKDF computation', async () => {
    // Independently computed via the platform's own WebCrypto HKDF (not this
    // package's `secretEncryptor.ts`, which is the thing being cross-checked)
    // to prove `deriveAesKeyBytes` — reimplemented locally because
    // `starfish-protocol` doesn't export it — is byte-identical to what
    // `deriveKey`/`deriveAesKeyBytes` in that package actually compute.
    const secret = 'deadbeef1234'
    const expected = await deriveAesKeyBytesViaWebCrypto(secret, STARFISH_ENCRYPTION_SALT, 'octobot-sync-user-data')
    const actual = deriveAesKeyBytes(secret, STARFISH_ENCRYPTION_SALT, 'octobot-sync-user-data')
    expect(toHex(actual)).toBe(toHex(expected))
    // Known-answer pin: fixed vector so a future accidental change to the
    // HKDF wiring (wrong hash, swapped salt/info order, etc.) fails loudly
    // even if the "independent" WebCrypto comparison above were ever broken
    // the same way.
    expect(toHex(actual)).toBe('0d1ba0fcd7f5f06a8d256bb469f309dc9d22799be8b4db837f489dcf3da512f3')
  })
})

async function deriveAesKeyBytesViaWebCrypto(secret: string, salt: string, info: string): Promise<Uint8Array> {
  const enc = new TextEncoder()
  const km = await globalThis.crypto.subtle.importKey('raw', enc.encode(secret), 'HKDF', false, ['deriveBits'])
  const bits = await globalThis.crypto.subtle.deriveBits(
    { name: 'HKDF', hash: 'SHA-256', salt: enc.encode(salt), info: enc.encode(info) },
    km,
    256,
  )
  return new Uint8Array(bits)
}
