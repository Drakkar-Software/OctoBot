import { nodeBaseUrl, type NodeEndpoint } from './urls.js'
import { EXCHANGES_TIMEOUT_MS } from './constants.js'

/** A node answered, but with a non-2xx status. Carries the status so callers
 *  can branch on it (e.g. 501 = the node can't fetch volumes for this
 *  exchange) instead of parsing the message. */
export class NodeHttpError extends Error {
  readonly status: number
  constructor(status: number) {
    super(`Node request failed: HTTP ${status}`)
    this.name = 'NodeHttpError'
    this.status = status
  }
}

/** HTTP Basic credentials for a node's REST API: the EVM address is the
 *  username (see the node's `CurrentUser` dependency). Only a node paired by an
 *  older QR has these — a current pairing code carries the wallet instead of a
 *  password, so nothing authenticates on its behalf. */
export type NodeCredentials = { address: string; password: string }

function basicAuthHeader({ address, password }: NodeCredentials): string {
  return `Basic ${btoa(`${address}:${password}`)}`
}

/** Shared timeout/abort plumbing for `nodeRequest`/`nodeAuthRequest`: combines
 *  an internal timeout with an optional caller `AbortSignal` into one signal,
 *  fetches, and throws `NodeHttpError` on a non-2xx answer. */
async function fetchNodeJson<T>(
  node: NodeEndpoint,
  path: string,
  init: RequestInit,
  options: { signal?: AbortSignal; timeoutMs?: number; fetch?: typeof fetch },
): Promise<T> {
  const fetchImpl = options.fetch ?? globalThis.fetch
  const internalController = new AbortController()
  const timer = setTimeout(() => internalController.abort(), options.timeoutMs ?? EXCHANGES_TIMEOUT_MS)
  const onCallerAbort = () => internalController.abort()
  if (options.signal) options.signal.addEventListener('abort', onCallerAbort)
  try {
    const res = await fetchImpl(`${nodeBaseUrl(node)}${path}`, { ...init, signal: internalController.signal })
    if (!res.ok) throw new NodeHttpError(res.status)
    return (await res.json()) as T
  } finally {
    clearTimeout(timer)
    if (options.signal) options.signal.removeEventListener('abort', onCallerAbort)
  }
}

/** Unauthenticated `GET` against a node endpoint, combining an internal
 *  timeout with an optional caller `AbortSignal`. Throws `NodeHttpError` on a
 *  non-2xx answer. */
export async function nodeRequest<T>(
  node: NodeEndpoint,
  path: string,
  options: { signal?: AbortSignal; timeoutMs?: number; fetch?: typeof fetch } = {},
): Promise<T> {
  return fetchNodeJson<T>(node, path, { method: 'GET' }, options)
}

/** Authenticated call against a node endpoint (`path` is relative to
 *  `/api/v1`). Same internal timeout + caller-abort plumbing as `nodeRequest`,
 *  and the same `NodeHttpError` on a non-2xx answer. */
export async function nodeAuthRequest<T>(
  node: NodeEndpoint,
  credentials: NodeCredentials,
  path: string,
  options: { method?: string; body?: unknown; signal?: AbortSignal; timeoutMs?: number; fetch?: typeof fetch } = {},
): Promise<T> {
  return fetchNodeJson<T>(
    node,
    path,
    {
      method: options.method ?? 'GET',
      headers: {
        Authorization: basicAuthHeader(credentials),
        ...(options.body === undefined ? {} : { 'Content-Type': 'application/json' }),
      },
      body: options.body === undefined ? undefined : JSON.stringify(options.body),
    },
    options,
  )
}
