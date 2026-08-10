import { secp256k1 } from '@noble/curves/secp256k1.js'

const HARDENED = 0x80_000_000
// secp256k1 curve order — mathematical constant, used for BIP32 child key modular reduction
const CURVE_N = BigInt('0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141')

// TS 5.x: Uint8Array<ArrayBufferLike> doesn't satisfy BufferSource; slice gives ArrayBuffer
function buf(u: Uint8Array): ArrayBuffer {
  return u.buffer.slice(u.byteOffset, u.byteOffset + u.byteLength) as ArrayBuffer
}

async function hmacSha512(key: Uint8Array, data: Uint8Array): Promise<Uint8Array> {
  const cryptoKey = await globalThis.crypto.subtle.importKey(
    'raw', buf(key), { name: 'HMAC', hash: 'SHA-512' }, false, ['sign'],
  )
  return new Uint8Array(await globalThis.crypto.subtle.sign('HMAC', cryptoKey, buf(data)))
}

function bytesToBigInt(b: Uint8Array): bigint {
  let n = 0n
  for (const byte of b) n = (n << 8n) | BigInt(byte)
  return n
}

function bigIntTo32Bytes(n: bigint): Uint8Array {
  const out = new Uint8Array(32)
  for (let i = 31; i >= 0; i--) { out[i] = Number(n & 0xffn); n >>= 8n }
  return out
}

async function deriveChild(
  key: Uint8Array,
  chain: Uint8Array,
  index: number,
): Promise<{ key: Uint8Array; chain: Uint8Array }> {
  const data = new Uint8Array(37)
  if (index >= HARDENED) {
    data[0] = 0x00
    data.set(key, 1)
  } else {
    data.set(secp256k1.getPublicKey(key, true), 0)
  }
  new DataView(data.buffer).setUint32(33, index, false)
  const I = await hmacSha512(chain, data)
  const childKey = (bytesToBigInt(I.slice(0, 32)) + bytesToBigInt(key)) % CURVE_N
  return { key: bigIntTo32Bytes(childKey), chain: I.slice(32) }
}

const EVM_PRIVATE_KEY_PATTERN = /^(0x)?[0-9a-fA-F]{64}$/

/** True if `s` is a valid secp256k1 EVM private key (0x-prefixed or bare 64-hex, in range [1, n-1]). */
export function isEvmPrivateKey(s: string): boolean {
  if (!EVM_PRIVATE_KEY_PATTERN.test(s)) return false
  const hex = s.startsWith('0x') ? s.slice(2) : s
  const n = BigInt('0x' + hex)
  return n > 0n && n < CURVE_N
}

/** Normalises a private key string to lowercase, 0x-prefixed hex. */
export function normalizeEvmPrivateKey(s: string): string {
  const trimmed = s.trim().toLowerCase()
  return trimmed.startsWith('0x') ? trimmed : '0x' + trimmed
}

// Real m/44'/60'/0'/0/0.
const BIP44_PATH = [44 + HARDENED, 60 + HARDENED, 0 + HARDENED, 0, 0]

async function derivePath(mnemonic: string, path: number[]): Promise<string> {
  const enc = new TextEncoder()
  const keyMaterial = await globalThis.crypto.subtle.importKey(
    'raw', enc.encode(mnemonic), 'PBKDF2', false, ['deriveBits'],
  )
  const seedBits = await globalThis.crypto.subtle.deriveBits(
    { name: 'PBKDF2', hash: 'SHA-512', salt: enc.encode('mnemonic'), iterations: 2048 },
    keyMaterial,
    512,
  )
  const seed = new Uint8Array(seedBits)
  const I = await hmacSha512(enc.encode('Bitcoin seed'), seed)
  let key: Uint8Array = I.slice(0, 32)
  let chain: Uint8Array = I.slice(32)
  for (const idx of path) {
    ;({ key, chain } = await deriveChild(key, chain, idx))
  }
  return '0x' + Array.from(key, (b) => b.toString(16).padStart(2, '0')).join('')
}

/** Derives the standard BIP44 EVM private key (m/44'/60'/0'/0/0) from a BIP39
 *  mnemonic — the derivation web3.py, ethers and MetaMask all agree on. */
export async function deriveBip44PrivateKey(mnemonic: string): Promise<string> {
  if (isEvmPrivateKey(mnemonic)) return normalizeEvmPrivateKey(mnemonic)
  return derivePath(mnemonic, BIP44_PATH)
}
