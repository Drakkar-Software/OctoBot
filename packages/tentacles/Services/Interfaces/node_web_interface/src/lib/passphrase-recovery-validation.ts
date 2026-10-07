const EVM_PRIVATE_KEY_PATTERN = /^(0x)?[0-9a-fA-F]{64}$/

export type PassphraseRecoveryProofMode = "seed" | "hex"

export function countSeedWords(seed: string): number {
  return seed.trim().split(/\s+/).filter(Boolean).length
}

export function isValidSeedPhrase(seed: string): boolean {
  return countSeedWords(seed) >= 12
}

export function isValidEvmPrivateKeyHex(privateKey: string): boolean {
  return EVM_PRIVATE_KEY_PATTERN.test(privateKey.trim())
}

export function isPassphraseLongEnough(passphrase: string): boolean {
  return passphrase.length >= 8
}

export function passphrasesMatch(
  passphrase: string,
  confirmPassphrase: string,
): boolean {
  return passphrase === confirmPassphrase
}
