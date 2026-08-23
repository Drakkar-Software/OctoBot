import { describe, it, expect } from 'vitest'
import {
  parsePairingCode,
  createPairingRequest,
  PAIRING_CODE_ALPHABET,
  PAIRING_CODE_LENGTH,
} from '../src/identity/pairingRequest.js'

describe('parsePairingCode', () => {
  it('accepts a canonical code and returns it unchanged', () => {
    expect(parsePairingCode('ABCD2345')).toBe('ABCD2345')
  })

  it('normalizes case and surrounding whitespace', () => {
    // A user typing the code they read off a website will not match the
    // rendered casing, and a paste picks up stray whitespace.
    expect(parsePairingCode('abcd2345')).toBe('ABCD2345')
    expect(parsePairingCode('  AbCd2345 \n')).toBe('ABCD2345')
  })

  it('rejects the visually-ambiguous characters the alphabet deliberately excludes', () => {
    // These are the whole reason the alphabet is not plain base32: a code
    // containing them would be unreadable off a screen, so accepting one
    // would mean accepting something this package can never mint.
    for (const ch of ['I', 'O', '0', '1', 'L']) {
      expect(PAIRING_CODE_ALPHABET).not.toContain(ch)
      expect(parsePairingCode(`${ch}BCD2345`)).toBeNull()
    }
  })

  it('rejects wrong lengths, including the empty string', () => {
    expect(parsePairingCode('')).toBeNull()
    expect(parsePairingCode('ABCD234')).toBeNull()
    expect(parsePairingCode('ABCD23456')).toBeNull()
  })

  it('rejects a JSON payload, which is what a scanner hands it alongside real codes', () => {
    expect(parsePairingCode('{"v":1,"kind":"octobot-action-proposal"}')).toBeNull()
  })

  it('rejects punctuation and whitespace inside the code, not just around it', () => {
    expect(parsePairingCode('ABCD-234')).toBeNull()
    expect(parsePairingCode('ABCD 234')).toBeNull()
  })

  it('round-trips a code actually minted by createPairingRequest', async () => {
    for (let i = 0; i < 20; i++) {
      const { code } = await createPairingRequest({
        origin: 'https://example.test',
        rendezvous: { baseUrl: 'https://sync.example.test', namespace: 'dk' },
      })
      expect(code).toHaveLength(PAIRING_CODE_LENGTH)
      expect(parsePairingCode(code)).toBe(code)
      expect(parsePairingCode(code.toLowerCase())).toBe(code)
    }
  })
})
