import {
  MAGIC_DNS_BAD_CHARACTERS,
  MAGIC_DNS_ENTER_NAME,
  MAGIC_DNS_INVALID_SHAPE,
  MAGIC_DNS_REMOVE_SPACES,
  MAGIC_DNS_TRAILING_INVALID,
} from "@/lib/ui-recovery-constants"

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

export function buildSameComputerLoopbackUrl(href: string): string {
  const fromWildcard = getLoopbackUrl(href)
  if (fromWildcard) {
    return fromWildcard
  }
  const url = new URL(href)
  url.hostname = "127.0.0.1"
  return url.toString()
}

export type ParseMagicDnsHostnameResult =
  | { ok: true; hostname: string }
  | { ok: false; message: string }

const MAGIC_DNS_HOSTNAME_PATTERN = /^[a-zA-Z0-9.-]+$/

function stripHttpScheme(value: string): string {
  return value.replace(/^https?:\/\//i, "")
}

function extractHostnameFromPastedValue(value: string): string {
  const withoutScheme = stripHttpScheme(value)
  const urlCandidate =
    withoutScheme.includes("://") || value.includes("://")
      ? value
      : withoutScheme.includes("/") || withoutScheme.includes(":")
        ? `https://${withoutScheme}`
        : withoutScheme

  if (
    urlCandidate.includes("://") ||
    withoutScheme.includes("/") ||
    withoutScheme.includes(":")
  ) {
    try {
      const parsed = new URL(urlCandidate)
      if (parsed.hostname) {
        return parsed.hostname
      }
    } catch {
      // fall through to manual extraction
    }
  }

  let segment = withoutScheme
  if (segment.includes("/")) {
    segment = segment.split("/")[0] ?? ""
  }
  if (segment.includes(":")) {
    segment = segment.split(":")[0] ?? ""
  }
  return segment.trim()
}

export function parseMagicDnsHostnameInput(
  raw: string,
): ParseMagicDnsHostnameResult {
  const trimmed = raw.trim()
  if (trimmed === "") {
    return { ok: false, message: MAGIC_DNS_ENTER_NAME }
  }

  if (/\s/.test(trimmed)) {
    return { ok: false, message: MAGIC_DNS_REMOVE_SPACES }
  }

  const hostname = extractHostnameFromPastedValue(trimmed)
  if (hostname === "") {
    return { ok: false, message: MAGIC_DNS_INVALID_SHAPE }
  }

  if (!MAGIC_DNS_HOSTNAME_PATTERN.test(hostname)) {
    return { ok: false, message: MAGIC_DNS_BAD_CHARACTERS }
  }

  if (!hostname.includes(".")) {
    return { ok: false, message: MAGIC_DNS_INVALID_SHAPE }
  }

  const lastCharacter = hostname[hostname.length - 1]
  if (
    hostname.endsWith(".") ||
    (lastCharacter !== undefined && !/[a-zA-Z0-9]/.test(lastCharacter))
  ) {
    return { ok: false, message: MAGIC_DNS_TRAILING_INVALID }
  }

  return { ok: true, hostname }
}

export function buildHttpsNodeUrlFromHostname(
  hostname: string,
  href: string,
): string {
  const current = new URL(href)
  const url = new URL(current.pathname + current.search + current.hash, `https://${hostname}`)
  return url.toString()
}

export function getNodeUiPortFromHref(href: string): string {
  const port = new URL(href).port
  return port || "8000"
}

export function buildTailscaleServeCommand(href: string): string {
  const port = getNodeUiPortFromHref(href)
  return `tailscale serve --bg http://127.0.0.1:${port}`
}
