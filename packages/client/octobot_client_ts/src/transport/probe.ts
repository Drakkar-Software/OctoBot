import { StarfishClient, StarfishHttpError } from '@drakkar.software/starfish-client'
import { WalletCapProvider } from '../identity/capProvider.js'
import { pullPath } from '../collections/paths.js'
import { SYNC_MOUNT_PATH, SYNC_NAMESPACE, DEFAULT_PROBE_TIMEOUT_MS } from '../crypto/wireConstants.js'
import { NODE_STATUS_PATH, PROBE_TIMEOUT_MS } from './constants.js'

export type SyncAuthResult =
  | { status: 'idle' }
  | { status: 'checking' }
  | { status: 'authorized' }
  | { status: 'unauthorized' }
  | { status: 'error'; detail?: string }

function buildSyncBaseUrl(origin: string): string {
  return `${origin.replace(/\/$/, '')}/${SYNC_MOUNT_PATH}`
}

/**
 * Probe whether a wallet seed is authorized on a sync server. Uses the v3
 * cap-cert auth scheme to pull the user-data collection.
 * 200 → wallet is configured; 401/403 → wallet not allowed; other → error.
 */
export async function probeStarfishAuth(
  baseUrl: string,
  seed: string,
  options?: { signal?: AbortSignal; timeoutMs?: number; fetch?: typeof fetch },
): Promise<SyncAuthResult> {
  let capProvider: WalletCapProvider
  try {
    capProvider = new WalletCapProvider(seed)
  } catch {
    return { status: 'error', detail: 'credential-derivation' }
  }

  let userId: string
  try {
    userId = await capProvider.getUserId()
  } catch {
    return { status: 'error', detail: 'credential-derivation' }
  }

  const timeoutMs = options?.timeoutMs ?? DEFAULT_PROBE_TIMEOUT_MS
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), timeoutMs)

  const callerSignal = options?.signal
  let callerListener: (() => void) | undefined
  if (callerSignal) {
    callerListener = () => controller.abort()
    callerSignal.addEventListener('abort', callerListener)
  }

  const baseFetch = options?.fetch ?? globalThis.fetch
  const customFetch: typeof fetch = (url, init) =>
    baseFetch(url as string, { ...(init as RequestInit), signal: controller.signal })

  const client = new StarfishClient({
    baseUrl: buildSyncBaseUrl(baseUrl),
    namespace: SYNC_NAMESPACE,
    capProvider,
    fetch: customFetch,
  })

  try {
    await client.pull(pullPath('users/{identity}/data', { identity: userId }))
    clearTimeout(timer)
    return { status: 'authorized' }
  } catch (err) {
    clearTimeout(timer)
    if (err instanceof StarfishHttpError) {
      if (err.status === 401 || err.status === 403) return { status: 'unauthorized' }
      return { status: 'error', detail: String(err.status) }
    }
    if (controller.signal.aborted) {
      return { status: 'error', detail: callerSignal?.aborted ? 'aborted' : 'timeout' }
    }
    return { status: 'error', detail: err instanceof Error ? err.message : undefined }
  } finally {
    if (callerSignal && callerListener) callerSignal.removeEventListener('abort', callerListener)
  }
}

export type NodeProbeResult =
  | { status: 'idle' }
  | { status: 'probing' }
  | { status: 'reachable'; configured: boolean }
  | { status: 'unreachable'; reason: 'timeout' | 'refused' | 'invalid-response' | 'http-error'; detail?: string }

/** Probe an OctoBot node at the given host:port via GET /api/v1/setup/status.
 *  Returns `{ status: 'reachable', configured }` on success.
 *  Caller-supplied `signal` is combined with the internal timeout so
 *  either can cancel the request (e.g. component unmount or new keystroke). */
export async function detectNode(
  host: string,
  port: number,
  secure?: boolean,
  options?: { signal?: AbortSignal; timeoutMs?: number; fetch?: typeof fetch },
): Promise<NodeProbeResult> {
  const timeoutMs = options?.timeoutMs ?? PROBE_TIMEOUT_MS
  const url = `${secure ? 'https' : 'http'}://${host}:${port}${NODE_STATUS_PATH}`
  const baseFetch = options?.fetch ?? globalThis.fetch

  const internalController = new AbortController()
  const timer = setTimeout(() => internalController.abort(), timeoutMs)

  const callerSignal = options?.signal
  let callerListener: (() => void) | undefined
  if (callerSignal) {
    callerListener = () => internalController.abort()
    callerSignal.addEventListener('abort', callerListener)
  }

  try {
    const res = await baseFetch(url, { signal: internalController.signal })
    clearTimeout(timer)

    if (!res.ok) {
      return { status: 'unreachable', reason: 'http-error', detail: String(res.status) }
    }

    let json: unknown
    try {
      json = await res.json()
    } catch {
      return { status: 'unreachable', reason: 'invalid-response' }
    }

    if (
      typeof json === 'object' &&
      json !== null &&
      typeof (json as Record<string, unknown>).configured === 'boolean'
    ) {
      const { configured } = json as { configured: boolean }
      return { status: 'reachable', configured }
    }

    return { status: 'unreachable', reason: 'invalid-response' }
  } catch (err) {
    clearTimeout(timer)
    if (internalController.signal.aborted) {
      if (callerSignal?.aborted) {
        return { status: 'idle' }
      }
      return { status: 'unreachable', reason: 'timeout' }
    }
    return { status: 'unreachable', reason: 'refused', detail: err instanceof Error ? err.message : undefined }
  } finally {
    if (callerSignal && callerListener) {
      callerSignal.removeEventListener('abort', callerListener)
    }
  }
}
