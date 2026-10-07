/** True when passphrase has leading or trailing whitespace (incl. newlines). */
export function passphraseHasEdgeWhitespace(passphrase: string): boolean {
  if (passphrase.length === 0) {
    return false
  }
  return /^\s/.test(passphrase) || /\s$/.test(passphrase)
}
