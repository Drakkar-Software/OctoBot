import type { Strategy as ProtocolStrategy, UserActionConfiguration } from '@drakkar.software/octobot-protocol'
import { parseReadOnlyPairing } from '../../identity/pairing.js'
import { SYNC_FETCH_TIMEOUT_MS } from '../../crypto/wireConstants.js'
import { createReadOnlySession, type ClientSession, type SessionCapProvider } from '../core/session.js'
import type { CallOptions } from '../core/options.js'
import type { AccountInput } from '../adapters/accounts.js'
import type { CreateAutomationInput } from '../adapters/automations.js'
import type { AccountView, AutomationView } from '../core/views.js'
import { createAccountsApi, toAccountGraph, pullAccountsDocument, type AppendAction } from '../adapters/accounts.js'
import { createAutomationsApi } from '../adapters/automations.js'
import { createStrategiesApi } from '../adapters/strategies.js'
import { createReadOnlyDocumentsApi, type ReadOnlyDocumentsApi } from '../adapters/documents.js'
import { OctoBotConfigError, rethrowAsOctoBotError } from '../core/errors.js'
import {
  accountAuthIdFor,
  exchangeConfigIdFor,
  buildCreateAccountConfig,
  buildEditAccountConfig,
  buildDeleteAccountConfig,
  buildRefreshAccountsConfig,
  buildCreateAccountAuthConfig,
  buildEditAccountAuthConfig,
  buildDeleteAccountAuthConfig,
  buildCreateExchangeConfigConfig,
  buildEditExchangeConfigConfig,
  buildDeleteExchangeConfigConfig,
  buildCreateStrategyConfig,
  buildEditStrategyConfig,
  buildDeleteStrategyConfig,
  buildCreateAutomationConfig,
  buildEditAutomationConfig,
  buildStopAutomationConfig,
} from '../../protocol/actions.js'
import { encodeActionProposal, type ProposedActionEntry } from '../../protocol/proposal.js'

export type { AccountView, AccountKind, AutomationView, Holding } from '../core/views.js'
export type { AccountInput } from '../adapters/accounts.js'
export type { CreateAutomationInput } from '../adapters/automations.js'

/** A write call built its action(s) but never sent them — the session has no
 *  append rights. `payload` is the QR-encodable `ActionProposal`; a
 *  privileged client (real append rights) scans/decodes it and executes it
 *  after a human confirms. See `protocol/proposal.ts`. */
export interface ProposedAction {
  actions: UserActionConfiguration[]
  payload: string
}

/** A session with no append rights (`ops` never includes `'write'`, enforced
 *  by the node) built from `connectReadOnlyDevice()`. Every write method
 *  that would normally return an `ActionHandle` returns a `ProposedAction`
 *  instead — same method names, so a caller migrating between the two client
 *  kinds doesn't rename anything, just changes what it does with the
 *  result. */
export interface ReadOnlyAccountsApi {
  list(opts?: CallOptions): Promise<AccountView[]>
  get(id: string, opts?: CallOptions): Promise<AccountView | null>
  create(input: AccountInput, opts?: CallOptions): Promise<ProposedAction>
  update(id: string, input: AccountInput, opts?: CallOptions): Promise<ProposedAction>
  delete(id: string, opts?: CallOptions): Promise<ProposedAction>
  refresh(ids?: string[], opts?: CallOptions): Promise<ProposedAction>
}

export interface ReadOnlyAutomationsApi {
  list(opts?: CallOptions): Promise<AutomationView[]>
  get(id: string, opts?: CallOptions): Promise<AutomationView | null>
  create(input: CreateAutomationInput, opts?: CallOptions): Promise<ProposedAction>
  update(id: string, input: CreateAutomationInput, opts?: CallOptions): Promise<ProposedAction>
  stop(id: string, opts?: CallOptions): Promise<ProposedAction>
}

export interface ReadOnlyStrategiesApi {
  list(opts?: CallOptions): Promise<ProtocolStrategy[]>
  get(id: string, version?: string, opts?: CallOptions): Promise<ProtocolStrategy | null>
  create(strategy: ProtocolStrategy, opts?: CallOptions): Promise<ProposedAction>
  update(strategy: ProtocolStrategy, opts?: CallOptions): Promise<ProposedAction>
  delete(id: string, opts?: CallOptions): Promise<ProposedAction>
}

export type ReadOnlyOctoBotClient = {
  readonly url: string
  readonly userId: string
  readonly accounts: ReadOnlyAccountsApi
  readonly automations: ReadOnlyAutomationsApi
  readonly strategies: ReadOnlyStrategiesApi
  /** Escape hatch: `pull` only, and only for a granted collection — an
   *  ungranted collection throws `OctoBotScopeError` before any network
   *  request, since this session was never given the key to decrypt it.
   *  No `push`/`append`: this client has no append rights by design (see
   *  the accounts/automations/strategies APIs above, which propose instead
   *  of appending), and `settings`/`node` are not exposed here at all —
   *  `settings` because the default grant never covers that collection, and
   *  `node`'s REST endpoints need `basicAuth`, which a pairing payload never
   *  carries. */
  readonly documents: ReadOnlyDocumentsApi
  close(): void
}

function proposalOf(actions: ProposedActionEntry[], label?: string): ProposedAction {
  return { actions: actions.map((a) => a.configuration), payload: encodeActionProposal(actions, { label }) }
}

const neverAppend: AppendAction = () => {
  throw new Error('read-only client: this session has no append rights, this should never be called')
}

function createReadOnlyAccountsApi(session: ClientSession): ReadOnlyAccountsApi {
  const base = createAccountsApi(session, neverAppend)
  return {
    list: base.list,
    get: base.get,
    async create(input) {
      const { account, auth, exchangeConfig } = toAccountGraph(input)
      const entries: ProposedActionEntry[] = []
      if (auth) entries.push({ configuration: buildCreateAccountAuthConfig(auth) })
      if (exchangeConfig) entries.push({ configuration: buildCreateExchangeConfigConfig(exchangeConfig) })
      entries.push({ configuration: buildCreateAccountConfig(account) })
      return proposalOf(entries, `Create account "${input.name}"`)
    },
    async update(id, input) {
      const { account, auth, exchangeConfig } = toAccountGraph({ ...input, id })
      const existing = await pullAccountsDocument(session)
        .then(({ data }) => (data.accounts ?? []).find((a) => a.id === id))
        .catch(() => undefined)
      if (existing?.created_at) account.created_at = existing.created_at
      const entries: ProposedActionEntry[] = []
      if (auth) entries.push({ configuration: buildEditAccountAuthConfig(auth) })
      if (exchangeConfig) entries.push({ configuration: buildEditExchangeConfigConfig(exchangeConfig) })
      entries.push({ configuration: buildEditAccountConfig(id, account) })
      return proposalOf(entries, `Update account "${input.name}"`)
    },
    async delete(id) {
      return proposalOf([
        { configuration: buildDeleteAccountConfig(id) },
        { configuration: buildDeleteAccountAuthConfig(accountAuthIdFor(id)) },
        { configuration: buildDeleteExchangeConfigConfig(exchangeConfigIdFor(id)) },
      ], `Delete account ${id}`)
    },
    async refresh(accountIds) {
      return proposalOf([{ configuration: buildRefreshAccountsConfig(accountIds) }], 'Refresh account balances')
    },
  }
}

function createReadOnlyAutomationsApi(session: ClientSession): ReadOnlyAutomationsApi {
  const base = createAutomationsApi(session, neverAppend)
  return {
    list: base.list,
    get: base.get,
    async create(input) {
      // Same node-side race `runCreateAutomation` sequences around: the node
      // resolves `automation_create`'s strategy by (id, version) against its
      // StrategyProvider, which only the confirmed `strategy_create` fills.
      // This session can't poll for that confirmation itself (no append
      // rights) — the executing side must, before appending the second entry.
      return proposalOf([
        { configuration: buildCreateStrategyConfig(input.strategy) },
        { configuration: buildCreateAutomationConfig(input), after: 'previous-confirmed' },
      ], `Create automation "${input.name}"`)
    },
    async update(id, input) {
      return proposalOf([
        { configuration: buildEditStrategyConfig(input.strategy) },
        { configuration: buildEditAutomationConfig({ ...input, automationId: id }) },
      ], `Update automation "${input.name}"`)
    },
    async stop(id) {
      return proposalOf([{ configuration: buildStopAutomationConfig(id) }], `Stop automation ${id}`)
    },
  }
}

function createReadOnlyStrategiesApi(session: ClientSession): ReadOnlyStrategiesApi {
  const base = createStrategiesApi(session, neverAppend)
  return {
    list: base.list,
    get: base.get,
    async create(strategy) {
      return proposalOf([{ configuration: buildCreateStrategyConfig(strategy) }], `Create strategy "${strategy.name}"`)
    },
    async update(strategy) {
      return proposalOf([{ configuration: buildEditStrategyConfig(strategy) }], `Update strategy "${strategy.name}"`)
    },
    async delete(id) {
      return proposalOf([{ configuration: buildDeleteStrategyConfig(id) }], `Delete strategy ${id}`)
    },
  }
}

export function createReadOnlyOctoBotClient(session: ClientSession): ReadOnlyOctoBotClient {
  return {
    url: session.origin,
    userId: session.userId,
    accounts: createReadOnlyAccountsApi(session),
    automations: createReadOnlyAutomationsApi(session),
    strategies: createReadOnlyStrategiesApi(session),
    documents: createReadOnlyDocumentsApi(session),
    close: () => session.close(),
  }
}

export type ConnectReadOnlyOptions = {
  /** Injected fetch — proxies, mTLS, React Native polyfills, test stubs.
   *  Default: `globalThis.fetch`. */
  fetch?: typeof fetch
  /** Default per-request timeout, ms. Default 10_000. */
  timeoutMs?: number
}

/**
 * Connect to a self-hosted OctoBot node using a read-only pairing payload —
 * a bearer credential a privileged device minted with `createReadOnlyPairing()`
 * (`@drakkar.software/octobot-client/identity`), NOT a wallet seed. There is
 * no seed anywhere on this path.
 *
 * The returned client's write methods (`accounts.create/update/delete`,
 * `automations.create/update/stop`, `strategies.create/update/delete`) never
 * append anything — this package never calls the node's append endpoint on
 * this session's behalf. (The node does not yet enforce a cap's `ops` scope
 * itself — every collection currently grants `self` role by identity alone,
 * regardless of `ops` — so this is presently a client-side guarantee, not a
 * node-enforced one; see `OctoBotScopeError`.) Instead they build the
 * action(s) and return a `ProposedAction`: the built configuration(s) plus a
 * QR-encodable payload for a privileged device to scan, review, and execute.
 *
 * ```ts
 * const octobot = await connectReadOnlyDevice(pairingPayload)
 * const accounts = await octobot.accounts.list()                    // works
 * const proposed = await octobot.automations.stop(automationId)     // builds, doesn't send
 * console.log(proposed.payload)                                     // render this as a QR
 * ```
 */
export async function connectReadOnlyDevice(
  pairingPayload: string,
  opts: ConnectReadOnlyOptions = {},
): Promise<ReadOnlyOctoBotClient> {
  let parsed
  try {
    parsed = parseReadOnlyPairing(pairingPayload)
  } catch (err) {
    throw new OctoBotConfigError(`invalid read-only pairing payload: ${err instanceof Error ? err.message : String(err)}`)
  }

  const fetchImpl = opts.fetch ?? globalThis.fetch
  const defaultTimeoutMs = opts.timeoutMs ?? SYNC_FETCH_TIMEOUT_MS
  const origin = `${parsed.node.secure ? 'https' : 'http'}://${parsed.node.host}:${parsed.node.port}`

  const capProvider: SessionCapProvider = {
    getCap: async () => ({ cap: parsed.cap, devEdPrivHex: parsed.device.edPriv }),
    getUserId: async () => parsed.userId,
  }

  try {
    const session = createReadOnlySession({
      origin,
      node: parsed.node,
      userId: parsed.userId,
      fetch: fetchImpl,
      defaultTimeoutMs,
      capProvider,
      collectionKeys: parsed.collectionKeys,
    })
    return createReadOnlyOctoBotClient(session)
  } catch (err) {
    rethrowAsOctoBotError(err)
  }
}
