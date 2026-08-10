import { describe, it, expect } from 'vitest'
import {
  deriveBip44PrivateKey,
  isEvmPrivateKey,
  normalizeEvmPrivateKey,
} from '../src/identity/evm.js'
import { createKeyCache } from '../src/identity/keys.js'

// Fixed mnemonic for deterministic key derivation across runs.
const MNEMONIC = 'abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about'
// Hardhat's default mnemonic — its account #0 key/address are widely published,
// which makes it a good check that a derivation really is the standard one.
const HARDHAT = 'test test test test test test test test test test test junk'
// secp256k1 curve order, for boundary tests.
const CURVE_N = BigInt('0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141')

describe('isEvmPrivateKey', () => {
  it('accepts a 0x-prefixed 64-hex key', () => {
    expect(isEvmPrivateKey('0x' + '1'.repeat(64))).toBe(true)
  })

  it('accepts a bare 64-hex key (no 0x prefix)', () => {
    expect(isEvmPrivateKey('1'.repeat(64))).toBe(true)
  })

  it('rejects zero', () => {
    expect(isEvmPrivateKey('0x' + '0'.repeat(64))).toBe(false)
  })

  it('rejects a value >= curve order n', () => {
    expect(isEvmPrivateKey('0x' + CURVE_N.toString(16))).toBe(false)
  })

  it('rejects 63-hex (too short)', () => {
    expect(isEvmPrivateKey('0x' + '1'.repeat(63))).toBe(false)
  })

  it('rejects 65-hex (too long)', () => {
    expect(isEvmPrivateKey('0x' + '1'.repeat(65))).toBe(false)
  })

  it('rejects a 12-word mnemonic', () => {
    expect(isEvmPrivateKey(MNEMONIC)).toBe(false)
  })
})

describe('normalizeEvmPrivateKey', () => {
  it('lowercases and trims', () => {
    expect(normalizeEvmPrivateKey('  0X' + 'A'.repeat(64) + '  ')).toBe('0x' + 'a'.repeat(64))
  })

  it('adds a 0x prefix when missing', () => {
    expect(normalizeEvmPrivateKey('B'.repeat(64))).toBe('0x' + 'b'.repeat(64))
  })
})

describe('deriveBip44PrivateKey: standard m/44\'/60\'/0\'/0/0', () => {
  it('returns a raw private key unchanged (normalized)', async () => {
    const raw = '0x' + '1'.repeat(64)
    expect(await deriveBip44PrivateKey(raw)).toBe(raw)
  })

  it('normalizes a bare (no 0x) raw private key', async () => {
    expect(await deriveBip44PrivateKey('2'.repeat(64))).toBe('0x' + '2'.repeat(64))
  })

  it('matches the canonical key for a known mnemonic', async () => {
    // Hardhat account #0 — the same value web3.py, ethers and MetaMask produce.
    expect(await deriveBip44PrivateKey(HARDHAT))
      .toBe('0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80')
  })

  it('matches the canonical address for a known mnemonic', async () => {
    const address = await createKeyCache().getWalletAddress(await deriveBip44PrivateKey(MNEMONIC), 'bip44')
    expect(address).toBe('0x9858EfFD232B4033E47d90003D41EC34EcaEda94')
  })

  it('a raw key and its mnemonic-derived counterpart resolve to the same address', async () => {
    const derivedKey = await deriveBip44PrivateKey(MNEMONIC)
    const addrFromMnemonic = await createKeyCache().getWalletAddress(MNEMONIC, 'bip44')
    const addrFromKey = await createKeyCache().getWalletAddress(derivedKey, 'bip44')
    expect(addrFromKey).toBe(addrFromMnemonic)
  })
})
