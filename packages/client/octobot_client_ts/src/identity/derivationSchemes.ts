import { isEvmPrivateKey, normalizeEvmPrivateKey, deriveBip44PrivateKey } from './evm.js'

/** Turns a mnemonic into a private key hex string. Every scheme must pass a
 *  raw private key through unchanged (via `isEvmPrivateKey`/
 *  `normalizeEvmPrivateKey`) — a raw key has no derivation, it IS the key. */
export type DeriveKeyFn = (mnemonicOrKey: string) => Promise<string>

export type DerivationScheme = {
  /** Stable identifier persisted alongside a wallet — e.g. in `Wallet.derivation`
   *  on the consumer side. Never reuse an id for a different derivation once
   *  anything may have been minted under it. */
  id: string
  derive: DeriveKeyFn
}

function bip44Derive(mnemonicOrKey: string): Promise<string> {
  if (isEvmPrivateKey(mnemonicOrKey)) return Promise.resolve(normalizeEvmPrivateKey(mnemonicOrKey))
  return deriveBip44PrivateKey(mnemonicOrKey)
}

const schemes = new Map<string, DerivationScheme>([
  ['bip44', { id: 'bip44', derive: bip44Derive }],
])

/** The scheme used when a caller doesn't pass one explicitly. */
export const DEFAULT_DERIVATION_SCHEME_ID = 'bip44'

/** Registers a new derivation scheme (e.g. for a future wallet type this
 *  package doesn't ship natively) so `deriveRoot`/`WalletCapProvider`/
 *  `createKeyCache()` can address it by id. Throws if `id` is already
 *  registered — schemes are identity-bearing, so silently replacing one
 *  would re-derive every wallet that used it under a different key. */
export function registerDerivationScheme(scheme: DerivationScheme): void {
  if (schemes.has(scheme.id)) throw new Error(`derivation scheme "${scheme.id}" is already registered`)
  schemes.set(scheme.id, scheme)
}

/** Throws for an unknown id — there is no silent fallback, since deriving
 *  under the wrong scheme silently produces a DIFFERENT identity rather than
 *  an error a caller could catch. */
export function getDerivationScheme(id: string): DerivationScheme {
  const scheme = schemes.get(id)
  if (!scheme) throw new Error(`unknown derivation scheme: "${id}"`)
  return scheme
}

export function listDerivationSchemeIds(): string[] {
  return [...schemes.keys()]
}
