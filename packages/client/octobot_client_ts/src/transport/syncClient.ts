import { StarfishClient, type StarfishCapProvider } from '@drakkar.software/starfish-client'
import { SYNC_MOUNT_PATH, SYNC_NAMESPACE, SYNC_FETCH_TIMEOUT_MS } from '../crypto/wireConstants.js'

function buildSyncBaseUrl(origin: string): string {
  return `${origin.replace(/\/$/, '')}/${SYNC_MOUNT_PATH}`
}

/** Bound every sync request with a timeout: without one, a pull to an
 *  offline node hangs for the OS TCP timeout (60s+). */
export function createTimeoutFetch(timeoutMs: number, baseFetch: typeof fetch = globalThis.fetch): typeof fetch {
  return (input, init) => {
    const controller = new AbortController()
    const timer = setTimeout(() => controller.abort(), timeoutMs)
    const callerSignal = (init as RequestInit | undefined)?.signal
    if (callerSignal) callerSignal.addEventListener('abort', () => controller.abort())
    return baseFetch(input, { ...(init as RequestInit), signal: controller.signal }).finally(() =>
      clearTimeout(timer),
    )
  }
}

/** A bare `StarfishClient` factory — no cache, no lifecycle. Callers that
 *  need per-node client caching (e.g. an offline sync engine juggling
 *  several nodes) own that themselves; this just builds one client. */
export function createSyncClient(opts: {
  origin: string
  capProvider: StarfishCapProvider
  fetch?: typeof fetch
  timeoutMs?: number
}): StarfishClient {
  const baseFetch = opts.fetch ?? globalThis.fetch
  return new StarfishClient({
    baseUrl: buildSyncBaseUrl(opts.origin),
    namespace: SYNC_NAMESPACE,
    capProvider: opts.capProvider,
    fetch: createTimeoutFetch(opts.timeoutMs ?? SYNC_FETCH_TIMEOUT_MS, baseFetch),
  })
}
