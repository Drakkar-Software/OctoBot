import { parseHostInput } from '../transport/urls.js'

const VERIFY_TIMEOUT_MS = 8000

/** What a node's pairing QR turned out to carry.
 *
 *  `'wallet'` — `secret` is the wallet itself, which the node exports while
 *  building the QR, so importing needs no network at all. A BIP39 phrase when
 *  the node has one, else a 0x private key — see `nodeWalletFromSecret` in
 *  ./wallet.ts, which is what reads it, and why a phrase from here is derived
 *  differently to one an app generated itself.
 *
 *  `'credential'` — a QR from a node that predates that change. `secret` is only
 *  the HTTP Basic password, and the wallet still has to be read off the node. */
export type NodePairingPayload = {
  url: string
  address: string
  secret: string
  secretKind: 'wallet' | 'credential'
}

/** The node's "Pair mobile device" QR (node settings → wallet management, or the
 *  setup wizard) encodes JSON.stringify({ url, address, password }). Older nodes
 *  send `passphrase` instead and mean something different by it — the field name
 *  is what tells the two apart, so both are read here and normalised to one
 *  shape. Returns null when the payload is neither. */
export function parseNodePairingQr(data: string): NodePairingPayload | null {
  try {
    const parsed = JSON.parse(data.trim())
    if (!parsed || typeof parsed !== 'object') return null
    const { url, address } = parsed
    if (typeof url !== 'string' || typeof address !== 'string') return null
    if (typeof parsed.password === 'string') {
      return { url, address, secret: parsed.password, secretKind: 'wallet' }
    }
    if (typeof parsed.passphrase === 'string') {
      return { url, address, secret: parsed.passphrase, secretKind: 'credential' }
    }
  } catch {
    // not JSON — not a node pairing QR
  }
  return null
}

/** Derive { host, port, secure } from a pairing QR's `url` field. */
export function parsePairingHost(url: string) {
  return parseHostInput(url)
}

export type NodeCredentialCheck =
  | { status: 'authorized' }
  | { status: 'unauthorized' }
  | { status: 'error' }

/** Verify address/password against the node's `GET /api/v1/login/test` — the only
 *  endpoint that exercises HTTP Basic auth without side effects. */
export async function verifyNodeCredentials(
  baseUrl: string,
  address: string,
  password: string,
  signal?: AbortSignal,
): Promise<NodeCredentialCheck> {
  const internalController = new AbortController()
  const timer = setTimeout(() => internalController.abort(), VERIFY_TIMEOUT_MS)
  const onCallerAbort = () => internalController.abort()
  if (signal) signal.addEventListener('abort', onCallerAbort)
  try {
    const res = await fetch(`${baseUrl}/api/v1/login/test`, {
      method: 'GET',
      headers: { Authorization: `Basic ${btoa(`${address}:${password}`)}` },
      signal: internalController.signal,
    })
    if (res.status === 401 || res.status === 403) return { status: 'unauthorized' }
    if (!res.ok) return { status: 'error' }
    return { status: 'authorized' }
  } catch {
    return { status: 'error' }
  } finally {
    clearTimeout(timer)
    if (signal) signal.removeEventListener('abort', onCallerAbort)
  }
}
