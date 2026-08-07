import { describe, it, expect } from 'vitest'
import { BIP39_WORDLIST } from '../src/identity/bip39-wordlist.js'
import { entropyToMnemonic, generateSeedPhrase, validateSeedPhrase } from '../src/identity/mnemonic.js'

// Official BIP-39 test vectors (from https://github.com/trezor/python-mnemonic)
const TV: Array<{ entropy: string; mnemonic: string }> = [
  {
    entropy: '00000000000000000000000000000000',
    mnemonic: 'abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about',
  },
  {
    entropy: '7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f',
    mnemonic: 'legal winner thank year wave sausage worth useful legal winner thank yellow',
  },
  {
    entropy: '80808080808080808080808080808080',
    mnemonic: 'letter advice cage absurd amount doctor acoustic avoid letter advice cage above',
  },
  {
    entropy: 'ffffffffffffffffffffffffffffffff',
    mnemonic: 'zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo wrong',
  },
  // 24-word (256-bit entropy) vectors
  {
    entropy: '0000000000000000000000000000000000000000000000000000000000000000',
    mnemonic:
      'abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon art',
  },
  {
    entropy: 'ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff',
    mnemonic:
      'zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo vote',
  },
]

function hexToBytes(hex: string): Uint8Array {
  const bytes = new Uint8Array(hex.length / 2)
  for (let i = 0; i < bytes.length; i++) {
    bytes[i] = parseInt(hex.slice(i * 2, i * 2 + 2), 16)
  }
  return bytes
}

// ─── Wordlist ─────────────────────────────────────────────────────────────────

describe('BIP39_WORDLIST', () => {
  it('contains exactly 2048 words', () => {
    expect(BIP39_WORDLIST).toHaveLength(2048)
  })

  it('first word is "abandon"', () => {
    expect(BIP39_WORDLIST[0]).toBe('abandon')
  })

  it('last word is "zoo"', () => {
    expect(BIP39_WORDLIST[2047]).toBe('zoo')
  })

  it('all words are non-empty strings', () => {
    for (const w of BIP39_WORDLIST) {
      expect(typeof w).toBe('string')
      expect(w.length).toBeGreaterThan(0)
    }
  })

  it('no duplicate words', () => {
    expect(new Set(BIP39_WORDLIST).size).toBe(2048)
  })
})

// ─── entropyToMnemonic ────────────────────────────────────────────────────────

describe('entropyToMnemonic', () => {
  for (const { entropy, mnemonic } of TV) {
    it(`matches BIP-39 vector for ${entropy.slice(0, 8)}...`, async () => {
      const words = await entropyToMnemonic(hexToBytes(entropy))
      expect(words.join(' ')).toBe(mnemonic)
    })
  }

  it('returns 12 words for 16-byte entropy', async () => {
    const words = await entropyToMnemonic(new Uint8Array(16))
    expect(words).toHaveLength(12)
  })

  it('returns 24 words for 32-byte entropy', async () => {
    const words = await entropyToMnemonic(new Uint8Array(32))
    expect(words).toHaveLength(24)
  })

  it('all returned words are in the BIP-39 wordlist', async () => {
    const words = await entropyToMnemonic(hexToBytes('80808080808080808080808080808080'))
    for (const w of words) {
      expect(BIP39_WORDLIST).toContain(w)
    }
  })

  it('is deterministic for the same entropy', async () => {
    const entropy = new Uint8Array(16).fill(0x42)
    const a = await entropyToMnemonic(entropy)
    const b = await entropyToMnemonic(entropy)
    expect(a).toEqual(b)
  })

  it('produces different output for different entropy', async () => {
    const a = await entropyToMnemonic(new Uint8Array(16).fill(0x01))
    const b = await entropyToMnemonic(new Uint8Array(16).fill(0x02))
    expect(a.join(' ')).not.toBe(b.join(' '))
  })
})

// ─── generateSeedPhrase ───────────────────────────────────────────────────────

describe('generateSeedPhrase', () => {
  it('returns 12 words by default', async () => {
    const words = await generateSeedPhrase()
    expect(words).toHaveLength(12)
  })

  it('returns 15 words when asked', async () => {
    const words = await generateSeedPhrase(15)
    expect(words).toHaveLength(15)
  })

  it('returns 18 words when asked', async () => {
    const words = await generateSeedPhrase(18)
    expect(words).toHaveLength(18)
  })

  it('returns 21 words when asked', async () => {
    const words = await generateSeedPhrase(21)
    expect(words).toHaveLength(21)
  })

  it('returns 24 words when asked', async () => {
    const words = await generateSeedPhrase(24)
    expect(words).toHaveLength(24)
  })

  it('throws for unsupported word count', async () => {
    await expect(generateSeedPhrase(13)).rejects.toThrow('Unsupported word count')
  })

  it('all words are in the BIP-39 wordlist', async () => {
    const words = await generateSeedPhrase()
    for (const w of words) {
      expect(BIP39_WORDLIST).toContain(w)
    }
  })

  it('produces a valid BIP-39 mnemonic (checksum passes)', async () => {
    const words = await generateSeedPhrase()
    expect(await validateSeedPhrase(words.join(' '))).toBe(true)
  })

  it('produces different phrases on successive calls (probabilistic)', async () => {
    const a = await generateSeedPhrase()
    const b = await generateSeedPhrase()
    // Probability of collision ≈ 1/2^128 — astronomically unlikely
    expect(a.join(' ')).not.toBe(b.join(' '))
  })

  it('no word appears "always" — distribution crosses the alphabet', async () => {
    const seen = new Set<string>()
    // 10 calls × 12 words = 120 samples; with a 2048-word space, expect variety
    for (let i = 0; i < 10; i++) {
      const words = await generateSeedPhrase()
      for (const w of words) seen.add(w[0]) // collect first letters
    }
    // should see more than 1 distinct first letter across 120 samples
    expect(seen.size).toBeGreaterThan(1)
  })
})

// ─── validateSeedPhrase ───────────────────────────────────────────────────────

describe('validateSeedPhrase', () => {
  for (const { mnemonic } of TV) {
    it(`accepts BIP-39 test vector: "${mnemonic.slice(0, 30)}..."`, async () => {
      expect(await validateSeedPhrase(mnemonic)).toBe(true)
    })
  }

  it('accepts a freshly generated 12-word phrase', async () => {
    const words = await generateSeedPhrase()
    expect(await validateSeedPhrase(words.join(' '))).toBe(true)
  })

  it('accepts a freshly generated 24-word phrase', async () => {
    const words = await generateSeedPhrase(24)
    expect(await validateSeedPhrase(words.join(' '))).toBe(true)
  })

  it('rejects a phrase with a word not in the wordlist', async () => {
    expect(await validateSeedPhrase('foo bar baz qux quux corge grault garply waldo fred plugh thud')).toBe(false)
  })

  it('rejects wrong word count (11 words)', async () => {
    const words = await generateSeedPhrase()
    expect(await validateSeedPhrase(words.slice(0, 11).join(' '))).toBe(false)
  })

  it('rejects wrong word count (13 words)', async () => {
    const words = await generateSeedPhrase()
    expect(await validateSeedPhrase([...words, 'abandon'].join(' '))).toBe(false)
  })

  it('rejects a phrase with a bad checksum word (last word swapped)', async () => {
    // "abandon" x11 + "about" is valid (TV1); replace last word with a valid but wrong BIP-39 word
    const valid = 'abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about'
    const tampered = valid.replace(/about$/, 'ability')
    expect(await validateSeedPhrase(tampered)).toBe(false)
  })

  it('rejects a phrase with interior word swapped (bad checksum)', async () => {
    // swap word 0 of TV1 from "abandon" to "ability" → checksum word no longer matches
    const tampered =
      'ability abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about'
    expect(await validateSeedPhrase(tampered)).toBe(false)
  })

  it('accepts phrase with extra whitespace (trimmed)', async () => {
    const valid = 'abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about'
    expect(await validateSeedPhrase('  ' + valid + '  ')).toBe(true)
  })

  it('is case-sensitive — rejects uppercase words', async () => {
    const valid = 'abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about'
    expect(await validateSeedPhrase(valid.replace('abandon', 'Abandon'))).toBe(false)
  })
})
