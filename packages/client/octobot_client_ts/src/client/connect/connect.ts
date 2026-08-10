import { StarfishHttpError } from '@drakkar.software/starfish-client'
import { parseHostInput, type NodeEndpoint } from '../../transport/urls.js'
import { isEvmPrivateKey } from '../../identity/evm.js'
import { listDerivationSchemeIds, DEFAULT_DERIVATION_SCHEME_ID } from '../../identity/derivationSchemes.js'
import { pullPath } from '../../collections/paths.js'
import { SYNC_FETCH_TIMEOUT_MS } from '../../crypto/wireConstants.js'
import { createSession, type WalletClientSession } from '../core/session.js'
import { type ConnectOptions, type SeedDerivation, type CallOptions } from '../core/options.js'
import { OctoBotConfigError, OctoBotAuthError, rethrowAsOctoBotError } from '../core/errors.js'
import { createAccountsApi, type AccountsApi } from '../adapters/accounts.js'
import { createAutomationsApi, type AutomationsApi } from '../adapters/automations.js'
import { createStrategiesApi, type StrategiesApi } from '../adapters/strategies.js'
import { createSettingsApi, type SettingsApi } from '../adapters/settings.js'
import { createNodeApi, type NodeApi } from '../adapters/nodeApi.js'
import { createDocumentsApi, type DocumentsApi } from '../adapters/documents.js'
import { appendElement } from '../../transport/documents.js'
import type { UserActionConfiguration } from '@drakkar.software/octobot-protocol'

export type { ConnectOptions, SeedDerivation, CallOptions }

export type OctoBotClient = {
  /** The node's origin, normalized, e.g. `'http://192.168.1.10:5001'`. */
  readonly url: string
  /** EIP-55 checksummed EVM address the seed derives to. */
  readonly address: string
  /** Starfish identity — `sha256(rootEdPub)[:32]`; the `{identity}` URL segment. */
  readonly userId: string
  readonly accounts: AccountsApi
  readonly automations: AutomationsApi
  readonly strategies: StrategiesApi
  readonly settings: SettingsApi
  readonly node: NodeApi
  /** Escape hatch: raw pull/push/append and the underlying `StarfishClient`. */
  readonly documents: DocumentsApi
  /** Drops the derived-key cache. Does not abort in-flight `ActionHandle`
   *  work already started — those complete or time out on their own. */
  close(): void
}

async function probeIdentity(session: WalletClientSession): Promise<{ ok: boolean; err?: unknown }> {
  try {
    await session.syncClient.pull(pullPath('users/{identity}/data', { identity: session.userId }))
    return { ok: true }
  } catch (err) {
    if (err instanceof StarfishHttpError && (err.status === 401 || err.status === 403)) {
      return { ok: false, err }
    }
    throw err
  }
}

/**
 * Connect to a self-hosted OctoBot node.
 *
 * ```ts
 * const octobot = await connectOctoBot({ url: 'http://192.168.1.10:5001', seed })
 * const accounts = await octobot.accounts.list()
 * ```
 *
 * No document is ever cached — every read is a fresh pull. The only state
 * kept across calls is the derived key material (a pure function of `seed`),
 * dropped by `close()`.
 */
export async function connectOctoBot(options: ConnectOptions): Promise<OctoBotClient> {
  if (!options?.url?.trim()) throw new OctoBotConfigError('ConnectOptions.url is required')
  if (!options?.seed?.trim()) throw new OctoBotConfigError('ConnectOptions.seed is required')

  const parsedHost = parseHostInput(options.url)
  if (!parsedHost) throw new OctoBotConfigError(`could not parse ConnectOptions.url: ${JSON.stringify(options.url)}`)
  const node: NodeEndpoint = { host: parsedHost.host, port: parsedHost.port, secure: parsedHost.secure }

  const fetchImpl = options.fetch ?? globalThis.fetch
  const defaultTimeoutMs = options.timeoutMs ?? SYNC_FETCH_TIMEOUT_MS
  const origin = `${node.secure ? 'https' : 'http'}://${node.host}:${node.port}`
  const verify = options.verify ?? true
  const requested: SeedDerivation = options.seedDerivation ?? DEFAULT_DERIVATION_SCHEME_ID
  const isRawKey = isEvmPrivateKey(options.seed.trim())

  function buildSession(derivation: string): WalletClientSession {
    return createSession({
      origin,
      node,
      // address/userId filled in below via the cap provider itself; placeholder
      // values here are never observed because they're overwritten before return.
      address: '',
      userId: '',
      derivation,
      seed: options.seed,
      fetch: fetchImpl,
      defaultTimeoutMs,
      basicAuth: options.basicAuth,
    })
  }

  async function finalize(session: WalletClientSession): Promise<WalletClientSession> {
    const address = await session.walletAddress()
    const userId = await session.capProvider.getUserId()
    return { ...session, address, userId }
  }

  let session: WalletClientSession
  try {
    if (requested === 'auto') {
      // A raw key passes through every scheme identically, so trying more than
      // one is pointless — only a mnemonic's derivation is actually ambiguous.
      const candidates = isRawKey ? [DEFAULT_DERIVATION_SCHEME_ID] : listDerivationSchemeIds()
      let lastFailed: WalletClientSession | undefined
      let authorized: WalletClientSession | undefined
      for (const d of candidates) {
        const candidate = await finalize(buildSession(d))
        if (!verify) { authorized = candidate; break }
        const probe = await probeIdentity(candidate)
        if (probe.ok) { authorized = candidate; break }
        lastFailed = candidate
      }
      if (!authorized) {
        const failed = lastFailed!
        throw new OctoBotAuthError(failed.address, failed.userId, failed.derivation)
      }
      session = authorized
    } else {
      session = await finalize(buildSession(requested))
      if (verify) {
        const probe = await probeIdentity(session)
        if (!probe.ok) throw new OctoBotAuthError(session.address, session.userId, session.derivation)
      }
    }
  } catch (err) {
    rethrowAsOctoBotError(err)
  }

  async function appendAction(configuration: UserActionConfiguration): Promise<string> {
    const id = `ua_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 8)}`
    const encryptor = await session.collectionEncryptor('actions')
    await appendElement(
      session.syncClient, 'actions', { identity: session.userId },
      { id, status: 'pending', created_at: new Date().toISOString(), configuration }, encryptor,
    )
    return id
  }

  return {
    url: origin,
    address: session.address,
    userId: session.userId,
    accounts: createAccountsApi(session, appendAction),
    automations: createAutomationsApi(session, appendAction),
    strategies: createStrategiesApi(session, appendAction),
    settings: createSettingsApi(session),
    node: createNodeApi(session),
    documents: createDocumentsApi(session),
    close: () => session.close(),
  }
}
