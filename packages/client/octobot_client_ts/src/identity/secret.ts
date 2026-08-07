import { isEvmPrivateKey, normalizeEvmPrivateKey } from './evm.js'
import { validateSeedPhrase } from './mnemonic.js'

/** What a string of key material turned out to be. */
export type ClassifiedSecret =
  | { kind: 'privateKey'; value: string }
  | { kind: 'seed'; value: string }
  | { kind: 'unknown' }

/** Classify key material that arrived somewhere already known to hold it — a
 *  pairing payload's `password`, a standalone `{"password": "…"}` code, or a
 *  phrase typed by hand.
 *
 *  The `0x` prefix picks the branch, and the branch still validates: a value
 *  that is neither a real key nor a real phrase has to be rejected rather than
 *  quietly produce a wallet nobody owns.
 *
 *  Note what this deliberately does **not** decide: which derivation SCHEME
 *  a `seed` needs, if a caller has registered more than the built-in
 *  `'bip44'` (see `derivationSchemes.ts`) — that depends on where the phrase
 *  came from, not on its shape. */
export async function classifySecret(raw: string): Promise<ClassifiedSecret> {
  const trimmed = raw.trim()

  if (trimmed.toLowerCase().startsWith('0x')) {
    const key = normalizeEvmPrivateKey(trimmed)
    return isEvmPrivateKey(key) ? { kind: 'privateKey', value: key } : { kind: 'unknown' }
  }

  const phrase = trimmed.split(/\s+/).map((w) => w.toLowerCase()).filter(Boolean).join(' ')
  if (phrase && (await validateSeedPhrase(phrase))) return { kind: 'seed', value: phrase }
  return { kind: 'unknown' }
}

/** Classify a bare scanned/typed value, where no field name says which shape to
 *  expect, so both are tried. Unlike `classifySecret` an unprefixed 64-hex still
 *  reads as a key here — there is no envelope to say otherwise. */
export async function classifyBareSecret(raw: string): Promise<ClassifiedSecret> {
  const trimmed = raw.trim()

  const key = normalizeEvmPrivateKey(trimmed)
  if (isEvmPrivateKey(key)) return { kind: 'privateKey', value: key }

  const phrase = trimmed.split(/\s+/).map((w) => w.toLowerCase()).filter(Boolean).join(' ')
  if (phrase && (await validateSeedPhrase(phrase))) return { kind: 'seed', value: phrase }
  return { kind: 'unknown' }
}

/** The wallet inside a standalone `{"password": "…"}` code — JSON carrying key
 *  material directly, with no node attached to fetch it from. Null when the
 *  value is not that shape. */
export function readSecretEnvelope(data: string): string | null {
  try {
    const parsed = JSON.parse(data.trim())
    if (parsed && typeof parsed === 'object' && typeof parsed.password === 'string') {
      return parsed.password
    }
  } catch {
    // not JSON — not an envelope
  }
  return null
}
