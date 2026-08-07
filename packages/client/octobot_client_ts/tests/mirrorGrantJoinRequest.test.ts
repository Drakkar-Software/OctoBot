import { describe, expect, it } from 'vitest'
import { defaultUserIdFromEdPub, verifyKemSig } from '@drakkar.software/starfish-spaces'
import { createPairingRequest } from '../src/identity/pairingRequest.js'
import { buildJoinRequestJson } from '../src/client/pairing/mirrorGrant.js'

const ORIGIN = 'https://example.com'
const RENDEZVOUS = { baseUrl: 'https://sync.example', namespace: 'dk' }

// Correctness of the wire-format bridge mirrorGrant.ts builds between
// PairingRequestPayload (this package's own type) and the {edPub, kemPub,
// userId, kemSig} "join request" shape starfish-spaces' own
// parseJoinRequest/inviteToNode expect — verified against starfish-spaces'
// REAL verifyKemSig/defaultUserIdFromEdPub, not just this package's own
// assertions, since a subtly wrong reconstruction here would look correct
// in isolation while failing to interop with the real library.

describe('createPairingRequest — joinRequestKemSig', () => {
  it('produces a joinRequestKemSig starfish-spaces\' own verifyKemSig accepts', async () => {
    const { request } = await createPairingRequest({ origin: ORIGIN, rendezvous: RENDEZVOUS })
    expect(verifyKemSig(request.devEdPub, request.devKemPub, request.joinRequestKemSig)).toBe(true)
  })

  it('is 128 hex characters (a 64-byte Ed25519 signature)', async () => {
    const { request } = await createPairingRequest({ origin: ORIGIN, rendezvous: RENDEZVOUS })
    expect(request.joinRequestKemSig).toMatch(/^[0-9a-f]{128}$/)
  })

  it('rejects verification against a DIFFERENT devKemPub — the signature is bound to the specific key', async () => {
    const { request } = await createPairingRequest({ origin: ORIGIN, rendezvous: RENDEZVOUS })
    const other = await createPairingRequest({ origin: ORIGIN, rendezvous: RENDEZVOUS })
    expect(verifyKemSig(request.devEdPub, other.request.devKemPub, request.joinRequestKemSig)).toBe(false)
  })
})

describe('buildJoinRequestJson', () => {
  it('reconstructs a join request that matches the shape starfish-spaces\' own makeJoinRequest produces', async () => {
    const { request } = await createPairingRequest({ origin: ORIGIN, rendezvous: RENDEZVOUS })
    const joinRequestJson = await buildJoinRequestJson(request)
    const parsed = JSON.parse(joinRequestJson) as {
      edPub: string; kemPub: string; userId: string; kemSig: string
    }
    expect(parsed.edPub).toBe(request.devEdPub)
    expect(parsed.kemPub).toBe(request.devKemPub)
    expect(parsed.userId).toBe(await defaultUserIdFromEdPub(request.devEdPub))
    expect(verifyKemSig(parsed.edPub, parsed.kemPub, parsed.kemSig)).toBe(true)
  })

  it('produces a userId that is genuinely derived from edPub, not a copy of some other field', async () => {
    const { request } = await createPairingRequest({ origin: ORIGIN, rendezvous: RENDEZVOUS })
    const joinRequestJson = await buildJoinRequestJson(request)
    const parsed = JSON.parse(joinRequestJson) as { userId: string }
    expect(parsed.userId).not.toBe(request.code)
    expect(parsed.userId).not.toBe(request.devEdPub)
    expect(parsed.userId).not.toBe(request.devKemPub)
  })
})
