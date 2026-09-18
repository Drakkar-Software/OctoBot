/** UTF-8-safe Basic Authorization header value (no "Basic " prefix). */
export function encodeBasicCredentials(username: string, password: string): string {
  const raw = `${username}:${password}`
  try {
    return btoa(raw)
  } catch {
    const bytes = new TextEncoder().encode(raw)
    let binary = ""
    for (const byte of bytes) {
      binary += String.fromCharCode(byte)
    }
    return btoa(binary)
  }
}

export function buildBasicAuthorizationHeader(
  username: string,
  password: string,
): string {
  return `Basic ${encodeBasicCredentials(username, password)}`
}
