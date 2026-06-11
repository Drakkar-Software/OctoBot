export function isWebCryptoAvailable(): boolean {
  return (
    typeof window !== "undefined" &&
    window.isSecureContext === true &&
    !!window.crypto?.subtle
  )
}

export function getLoopbackUrl(href: string): string | null {
  const url = new URL(href)
  const map: Record<string, string> = {
    "0.0.0.0": "127.0.0.1",
    "[::]": "[::1]",
    "::": "[::1]",
  }
  const target = map[url.hostname]
  if (!target) return null
  url.hostname = target
  return url.toString()
}
