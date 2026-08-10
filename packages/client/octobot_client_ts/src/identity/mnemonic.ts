import { BIP39_WORDLIST } from './bip39-wordlist.js'

const STRENGTH_BY_COUNT: Record<number, number> = {
  12: 128,
  15: 160,
  18: 192,
  21: 224,
  24: 256,
}

function getCrypto() {
  const c = globalThis.crypto
  if (!c?.getRandomValues || !c?.subtle?.digest) {
    throw new Error('Crypto polyfill not ready: cannot generate a secure seed phrase')
  }
  return c
}

export async function entropyToMnemonic(entropy: Uint8Array): Promise<string[]> {
  const c = getCrypto()
  // TS 5.7+ makes Uint8Array generic over ArrayBufferLike; WebCrypto wants the
  // concrete ArrayBuffer variant (not SharedArrayBuffer).
  const hashBuf = await c.subtle.digest('SHA-256', entropy as Uint8Array<ArrayBuffer>)
  const hash = new Uint8Array(hashBuf)
  const checksumBits = (entropy.length * 8) / 32
  const wordCount = (entropy.length * 8 + checksumBits) / 11
  // combined = entropy bytes + one byte holding the checksum (only top checksumBits are read)
  const combined = new Uint8Array(entropy.length + 1)
  combined.set(entropy)
  combined[entropy.length] = hash[0]
  const words: string[] = []
  for (let wi = 0; wi < wordCount; wi++) {
    let index = 0
    const startBit = wi * 11
    for (let b = 0; b < 11; b++) {
      const bit = startBit + b
      const byteIdx = bit >> 3
      const bitInByte = 7 - (bit & 7)
      index = (index << 1) | ((combined[byteIdx] >> bitInByte) & 1)
    }
    words.push(BIP39_WORDLIST[index])
  }
  return words
}

export async function generateSeedPhrase(count = 12): Promise<string[]> {
  const strength = STRENGTH_BY_COUNT[count]
  if (strength === undefined) throw new Error(`Unsupported word count: ${count}. Use 12, 15, 18, 21, or 24.`)
  const c = getCrypto()
  const entropy = new Uint8Array(strength / 8)
  c.getRandomValues(entropy)
  return entropyToMnemonic(entropy)
}

export async function validateSeedPhrase(phrase: string): Promise<boolean> {
  const words = phrase.trim().split(/\s+/)
  const strength = STRENGTH_BY_COUNT[words.length]
  if (strength === undefined) return false

  const indices = words.map((w) => BIP39_WORDLIST.indexOf(w))
  if (indices.some((i) => i === -1)) return false

  const entropyBits = strength
  const checksumBits = strength / 32
  const totalBits = words.length * 11

  // Rebuild the full bit array from word indices
  const bits = new Uint8Array(totalBits)
  for (let i = 0; i < words.length; i++) {
    const idx = indices[i]
    for (let b = 0; b < 11; b++) {
      bits[i * 11 + b] = (idx >> (10 - b)) & 1
    }
  }

  // Extract entropy bytes
  const entropy = new Uint8Array(entropyBits / 8)
  for (let byte = 0; byte < entropy.length; byte++) {
    let v = 0
    for (let bit = 0; bit < 8; bit++) {
      v = (v << 1) | bits[byte * 8 + bit]
    }
    entropy[byte] = v
  }

  // Compare given checksum bits vs recomputed SHA-256 checksum
  const c = globalThis.crypto
  if (!c?.subtle?.digest) return false
  const hashBuf = await c.subtle.digest('SHA-256', entropy as Uint8Array<ArrayBuffer>)
  const hash = new Uint8Array(hashBuf)
  for (let i = 0; i < checksumBits; i++) {
    const given = bits[entropyBits + i]
    const expected = (hash[0] >> (7 - i)) & 1
    if (given !== expected) return false
  }
  return true
}
