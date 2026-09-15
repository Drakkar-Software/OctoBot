import { describe, it, expect } from 'vitest'
import * as qrFrames from '../src/protocol/qrFrames.js'
import * as proposal from '../src/protocol/proposal.js'
import * as proposalSummary from '../src/protocol/proposalSummary.js'
import * as protocolBarrel from '../src/protocol/index.js'
import * as identityBarrel from '../src/identity/index.js'
import * as root from '../src/index.js'

// Nothing else in this suite imports `../src/index.js`, so until this file
// existed the root entry point — the one `import { x } from
// '@drakkar.software/octobot-client'` resolves to — had zero coverage, and a
// symbol could be added to a submodule barrel and silently omitted from it.
// That is not hypothetical: QR_FRAME_HEADER_LENGTH, QR_FRAME_MAX_BYTES and
// QR_FRAME_BODY_MAX_BYTES were all exported from ./protocol and missing from
// the root while the docs listed them as the consumer-facing sizing contract.
describe('barrel parity: the root entry point re-exports what the submodules do', () => {
  it('re-exports every runtime symbol of protocol/qrFrames, by identity', () => {
    const names = Object.keys(qrFrames)
    expect(names.length).toBeGreaterThan(0)
    for (const name of names) {
      expect(root, `root barrel is missing ${name}`).toHaveProperty(name)
      // Identity, not just presence: a re-export that resolved to a different
      // binding would break `instanceof` for QrPayloadTooLargeError.
      expect((root as Record<string, unknown>)[name]).toBe((qrFrames as Record<string, unknown>)[name])
    }
  })

  it('the ./protocol subpath also re-exports every one of them', () => {
    for (const name of Object.keys(qrFrames)) {
      expect(protocolBarrel, `./protocol is missing ${name}`).toHaveProperty(name)
      expect((protocolBarrel as Record<string, unknown>)[name]).toBe((qrFrames as Record<string, unknown>)[name])
    }
  })

  it('QrPayloadTooLargeError is one class across every entry point, so instanceof holds', () => {
    // A consumer that catches from one import path and tests against another
    // (share-action.tsx in mobile2 does exactly this) depends on this.
    expect(root.QrPayloadTooLargeError).toBe(qrFrames.QrPayloadTooLargeError)
    expect(protocolBarrel.QrPayloadTooLargeError).toBe(qrFrames.QrPayloadTooLargeError)
    try {
      qrFrames.encodeQrFrames('q'.repeat((qrFrames.QR_MAX_FRAMES + 5) * qrFrames.QR_FRAME_BODY_MAX_BYTES))
      throw new Error('expected a throw')
    } catch (e) {
      expect(e).toBeInstanceOf(root.QrPayloadTooLargeError)
      expect(e).toBeInstanceOf(protocolBarrel.QrPayloadTooLargeError)
    }
  })

  it('re-exports every runtime symbol of protocol/proposal, by identity, from both the root and ./protocol', () => {
    // UnsupportedActionProposalVersionError is exactly the kind of symbol
    // that went missing before — a caller needs the same class instance
    // whichever entry point they imported it from for instanceof to hold.
    for (const name of Object.keys(proposal)) {
      expect(root, `root barrel is missing ${name}`).toHaveProperty(name)
      expect(protocolBarrel, `./protocol is missing ${name}`).toHaveProperty(name)
      expect((root as Record<string, unknown>)[name]).toBe((proposal as Record<string, unknown>)[name])
      expect((protocolBarrel as Record<string, unknown>)[name]).toBe((proposal as Record<string, unknown>)[name])
    }
  })

  it('re-exports every runtime symbol of protocol/proposalSummary, by identity, from both the root and ./protocol', () => {
    for (const name of Object.keys(proposalSummary)) {
      expect(root, `root barrel is missing ${name}`).toHaveProperty(name)
      expect(protocolBarrel, `./protocol is missing ${name}`).toHaveProperty(name)
      expect((root as Record<string, unknown>)[name]).toBe((proposalSummary as Record<string, unknown>)[name])
      expect((protocolBarrel as Record<string, unknown>)[name]).toBe((proposalSummary as Record<string, unknown>)[name])
    }
  })

  it('exposes the pairing-code surface from both the root and ./identity', () => {
    for (const name of ['parsePairingCode', 'PAIRING_CODE_ALPHABET', 'PAIRING_CODE_LENGTH'] as const) {
      expect(root, `root barrel is missing ${name}`).toHaveProperty(name)
      expect(identityBarrel, `./identity is missing ${name}`).toHaveProperty(name)
      expect((root as Record<string, unknown>)[name]).toBe((identityBarrel as Record<string, unknown>)[name])
    }
  })
})
