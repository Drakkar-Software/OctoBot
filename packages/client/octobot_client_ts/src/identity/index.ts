export {
  deriveBip44PrivateKey,
  isEvmPrivateKey,
  normalizeEvmPrivateKey,
} from './evm.js'
export { deriveEvmAddress } from './address.js'
export {
  entropyToMnemonic,
  generateSeedPhrase,
  validateSeedPhrase,
} from './mnemonic.js'
export {
  classifySecret,
  classifyBareSecret,
  readSecretEnvelope,
  type ClassifiedSecret,
} from './secret.js'
export { WalletCapProvider, deriveRoot, BOOTSTRAP_CHALLENGE, type KeyDerivation } from './capProvider.js'
export { createReadOnlyPairing, parseReadOnlyPairing, type ReadOnlyPairingPayload } from './pairing.js'
export {
  createPairingRequest,
  parsePairingRequest,
  parsePairingCode,
  PAIRING_CODE_ALPHABET,
  PAIRING_CODE_LENGTH,
  type PairingRequestPayload,
} from './pairingRequest.js'
export { createKeyCache, type KeyCache } from './keys.js'
export {
  registerDerivationScheme,
  getDerivationScheme,
  listDerivationSchemeIds,
  DEFAULT_DERIVATION_SCHEME_ID,
  type DerivationScheme,
  type DeriveKeyFn,
} from './derivationSchemes.js'
