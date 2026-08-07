import { API_PREFIX, DEFAULT_NODE_PORT } from './constants.js'

/** The minimal address triple every node-facing call needs. Deliberately
 *  structural (not the caller's own "list of paired nodes" document type) —
 *  any `{ host, port, secure? }` works. */
export type NodeEndpoint = { host: string; port: number; secure?: boolean }

export function nodeBaseUrl(node: NodeEndpoint): string {
  return `${node.secure ? 'https' : 'http'}://${node.host}:${node.port}${API_PREFIX}`
}

export type NodeAddressSpace = 'loopback' | 'local' | 'public'

const IPV4 = /^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$/

/** Parse a user-typed host string into a canonical { host, port, secure } triple.
 *  Accepts: `host`, `host:port`, `http://host:port`, `https://host`, `[::1]:5001`.
 *  A scheme is kept (drives `secure` and the scheme-derived default port below);
 *  no scheme falls back to `defaultPort` (plain HTTP), preserving legacy local-node
 *  behavior. Returns null on empty input or an out-of-range port. */
export function parseHostInput(
  raw: string,
  defaultPort = DEFAULT_NODE_PORT,
): { host: string; port: number; secure: boolean } | null {
  const trimmed = raw.trim()
  if (!trimmed) return null

  // Detect + strip scheme
  const schemeMatch = trimmed.match(/^(https?):\/\//i)
  const secure = schemeMatch ? schemeMatch[1].toLowerCase() === 'https' : false
  const withoutScheme = trimmed.replace(/^https?:\/\//i, '')
  // Strip trailing slashes and path
  const withoutPath = withoutScheme.split('/')[0]
  // Scheme present but no explicit port → the scheme's own default port
  // (80/443); no scheme at all → the caller's local-node default.
  const schemeDefaultPort = schemeMatch ? (secure ? 443 : 80) : defaultPort

  let host: string
  let port: number

  // IPv6 with brackets: [::1] or [::1]:5001
  const ipv6Match = withoutPath.match(/^\[([^\]]+)\](?::(\d+))?$/)
  if (ipv6Match) {
    host = `[${ipv6Match[1]}]`
    port = ipv6Match[2] ? parseInt(ipv6Match[2], 10) : schemeDefaultPort
  } else {
    // host or host:port
    const lastColon = withoutPath.lastIndexOf(':')
    if (lastColon !== -1) {
      const maybePart = withoutPath.slice(lastColon + 1)
      if (/^\d+$/.test(maybePart)) {
        // Explicit port number
        host = withoutPath.slice(0, lastColon)
        port = parseInt(maybePart, 10)
      } else if (maybePart.length > 0) {
        // Non-empty, non-numeric after colon → invalid port spec
        return null
      } else {
        host = withoutPath
        port = schemeDefaultPort
      }
    } else {
      host = withoutPath
      port = schemeDefaultPort
    }
  }

  if (!host || port < 1 || port > 65535 || isNaN(port)) return null

  return { host, port, secure }
}

/** Inverse of {@link parseHostInput}: rebuild the editable host/port strings from a stored
 *  { host, port, secure } triple so that re-parsing them yields the same triple. The scheme
 *  is folded into the host field (there is no separate scheme control) and the port is left
 *  blank when it equals the scheme's implicit default (443 for https, 80 for http). */
export function formatHostInput(node: NodeEndpoint): { host: string; port: string } {
  const secure = !!node.secure
  const schemeDefault = secure ? 443 : 80
  const scheme = secure ? 'https://' : node.port === 80 ? 'http://' : ''
  return {
    host: `${scheme}${node.host}`,
    port: node.port === schemeDefault ? '' : String(node.port),
  }
}

/** Which IP address space a host belongs to, decided from the string alone — no
 *  DNS lookup, because the browsers that care about this decide the same way and
 *  at the same moment (before resolving). `public` therefore means "not knowable
 *  from the hostname", not "definitely on the internet": a DNS name pointing at a
 *  LAN box lands here, exactly as it does in Chrome. */
export function classifyAddressSpace(host: string): NodeAddressSpace {
  // A trailing dot is the DNS root and does not change what the name refers to.
  const trimmed = host.trim().toLowerCase().replace(/\.$/, '')
  if (!trimmed) return 'public'

  // IPv6, bracketed (`[::1]`, the form parseHostInput keeps) or bare.
  if (trimmed.startsWith('[') || trimmed.includes(':')) {
    const v6 = trimmed.replace(/^\[/, '').replace(/\]$/, '').split('%')[0]
    if (v6 === '::1') return 'loopback'
    // IPv4-mapped (`::ffff:127.0.0.1`) inherits the mapped address's own space.
    const mapped = v6.match(/^::ffff:(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})$/)
    if (mapped) return classifyAddressSpace(mapped[1])
    if (/^f[cd][0-9a-f]{2}:/.test(v6)) return 'local' // fc00::/7 unique-local
    if (/^fe[89ab][0-9a-f]:/.test(v6)) return 'local' // fe80::/10 link-local
    return 'public'
  }

  const v4 = trimmed.match(IPV4)
  if (v4) {
    const octets = v4.slice(1, 5).map(Number)
    // Out-of-range octets aren't an address literal at all; a browser would try
    // to resolve the string as a name, so classify it the way a name is.
    if (octets.some((o) => o > 255)) return 'public'
    const [a, b] = octets
    if (a === 127) return 'loopback'
    if (a === 10) return 'local'
    if (a === 192 && b === 168) return 'local'
    if (a === 172 && b >= 16 && b <= 31) return 'local'
    if (a === 100 && b >= 64 && b <= 127) return 'local' // carrier-grade NAT
    if (a === 169 && b === 254) return 'local' // link-local
    return 'public'
  }

  if (trimmed === 'localhost' || trimmed.endsWith('.localhost')) return 'loopback'
  if (trimmed.endsWith('.local')) return 'local' // mDNS
  return 'public'
}
