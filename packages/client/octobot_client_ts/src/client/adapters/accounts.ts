import type {
  Account as ProtocolAccount,
  AccountAuthentication,
  ExchangeConfig,
  DetailedAssetsForTradingType,
  UserActionConfiguration,
} from '@drakkar.software/octobot-protocol'
import type { ClientSession } from '../core/session.js'
import type { CallOptions } from '../core/options.js'
import { accountViewOf, type AccountView, type Holding } from '../core/views.js'
import { createActionHandle, type ActionHandle } from './actionHandle.js'
import { pullDocument } from '../../transport/documents.js'
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
} from '../../protocol/actions.js'
import { rethrowAsOctoBotError } from '../core/errors.js'

export type { AccountView, AccountKind } from '../core/views.js'
export type { AccountTradingDocument } from '../../protocol/documents.js'

export type AccountInput =
  | {
      id?: string
      name: string
      type: 'exchange'
      exchange: string
      credentials: { apiKey: string; apiSecret: string; passphrase?: string }
      simulated?: boolean
      holdings?: Holding[]
    }
  | { id?: string; name: string; type: 'wallet'; address: string; chain?: string; holdings?: Holding[] }
  | { id?: string; name: string; type: 'generic'; description?: string; holdings?: Holding[] }

const SPOT_TRADING_TYPE = 'spot' as const

function holdingsToAssets(holdings: Holding[] | undefined): DetailedAssetsForTradingType[] | undefined {
  if (!holdings?.length) return undefined
  return [{
    trading_type: SPOT_TRADING_TYPE,
    assets: holdings.map((h) => ({ symbol: h.symbol, total: h.total, available: h.free })),
  }]
}

function newAccountId(): string {
  return `acc_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 8)}`
}

/** The three protocol items one `AccountInput` maps to. `auth`/`exchangeConfig`
 *  are null for kinds that don't need them (a wallet/generic account still
 *  gets an `AccountAuthentication` carrying its address; only credentials
 *  proper are exchange-only). Exported for the read-only facade
 *  (`readOnly.ts`), which builds the same protocol items without appending
 *  them. */
export function toAccountGraph(input: AccountInput): {
  account: ProtocolAccount
  auth: AccountAuthentication | null
  exchangeConfig: ExchangeConfig | null
} {
  const id = input.id ?? newAccountId()
  const now = new Date().toISOString()

  if (input.type === 'exchange') {
    return {
      account: {
        id,
        name: input.name,
        is_simulated: Boolean(input.simulated),
        created_at: now,
        updated_at: now,
        authentication_id: accountAuthIdFor(id),
        specifics: { account_type: 'exchange', remote_account_id: '', exchange_config_ids: [exchangeConfigIdFor(id)] },
        ...(holdingsToAssets(input.holdings) ? { assets: holdingsToAssets(input.holdings) } : {}),
      },
      auth: {
        id: accountAuthIdFor(id),
        api_key: input.credentials.apiKey,
        api_secret: input.credentials.apiSecret,
        ...(input.credentials.passphrase ? { api_passphrase: input.credentials.passphrase } : {}),
      },
      exchangeConfig: {
        id: exchangeConfigIdFor(id),
        name: input.name,
        exchange: input.exchange,
        sandboxed: Boolean(input.simulated),
      },
    }
  }

  if (input.type === 'wallet') {
    return {
      account: {
        id,
        name: input.name,
        is_simulated: false,
        created_at: now,
        updated_at: now,
        authentication_id: accountAuthIdFor(id),
        specifics: { account_type: 'generic' },
        ...(input.chain ? { description: input.chain } : {}),
        ...(holdingsToAssets(input.holdings) ? { assets: holdingsToAssets(input.holdings) } : {}),
      },
      auth: { id: accountAuthIdFor(id), public_key: input.address },
      exchangeConfig: null,
    }
  }

  // 'generic' — no credentials, node has nothing to authenticate.
  return {
    account: {
      id,
      name: input.name,
      is_simulated: false,
      created_at: now,
      updated_at: now,
      specifics: { account_type: 'generic' },
      ...(input.description ? { description: input.description } : {}),
      ...(holdingsToAssets(input.holdings) ? { assets: holdingsToAssets(input.holdings) } : {}),
    },
    auth: null,
    exchangeConfig: null,
  }
}

export interface AccountsApi {
  list(opts?: CallOptions): Promise<AccountView[]>
  get(id: string, opts?: CallOptions): Promise<AccountView | null>
  create(input: AccountInput, opts?: CallOptions): Promise<ActionHandle<AccountView | null>>
  update(id: string, input: AccountInput, opts?: CallOptions): Promise<ActionHandle<AccountView | null>>
  /** The node does NOT cascade deletes — this emits `account_delete` plus
   *  the two companion deletes (auth, exchange config) itself. */
  delete(id: string, opts?: CallOptions): Promise<ActionHandle<void>>
  refresh(ids?: string[], opts?: CallOptions): Promise<ActionHandle<AccountView[]>>
  trading(id: string, opts?: CallOptions): ReturnType<DocumentsApiTrading>
}

type DocumentsApiTrading = (id: string, opts?: CallOptions) => Promise<import('../../protocol/documents.js').AccountTradingDocument | null>

export type AppendAction = (configuration: UserActionConfiguration) => Promise<string>

/** Pull the raw `accounts` collection document. Exported for the read-only
 *  facade (`readOnly.ts`), which needs an existing account's `created_at`
 *  when proposing an edit, same as `update()` below does. */
export async function pullAccountsDocument(session: ClientSession) {
  const encryptor = await session.collectionEncryptor('accounts')
  return pullDocument<{ accounts?: ProtocolAccount[]; exchange_configs?: ExchangeConfig[] }>(
    session.syncClient, 'accounts', { identity: session.userId }, encryptor,
  )
}

export function createAccountsApi(session: ClientSession, appendAction: AppendAction): AccountsApi {
  const pullAccounts = () => pullAccountsDocument(session)

  async function list(): Promise<AccountView[]> {
    try {
      const { data } = await pullAccounts()
      const configs = data.exchange_configs ?? []
      return (data.accounts ?? []).map((a) => accountViewOf(a, configs))
    } catch (err) {
      rethrowAsOctoBotError(err)
    }
  }

  async function get(id: string): Promise<AccountView | null> {
    const all = await list()
    return all.find((a) => a.id === id) ?? null
  }

  async function afterSettle(id: string): Promise<AccountView | null> {
    return get(id)
  }

  return {
    list,
    get,
    async create(input) {
      const { account, auth, exchangeConfig } = toAccountGraph(input)
      const ids: string[] = []
      const work = (async () => {
        if (auth) ids.push(await appendAction(buildCreateAccountAuthConfig(auth)))
        if (exchangeConfig) ids.push(await appendAction(buildCreateExchangeConfigConfig(exchangeConfig)))
        ids.push(await appendAction(buildCreateAccountConfig(account)))
        return afterSettle(account.id)
      })()
      // ids[] is populated synchronously as `work` progresses; the handle
      // reflects whatever has been appended by the time it's inspected.
      return createActionHandle(session, ids, work)
    },
    async update(id, input) {
      const ids: string[] = []
      const work = (async () => {
        const { account, auth, exchangeConfig } = toAccountGraph({ ...input, id })
        const existing = await pullAccounts()
          .then(({ data }) => (data.accounts ?? []).find((a) => a.id === id))
          .catch(() => undefined)
        if (existing?.created_at) account.created_at = existing.created_at
        // Credentials/exchange config are rotated BEFORE the account edit so
        // the node's account re-validation reads the new keys, not the old ones.
        if (auth) ids.push(await appendAction(buildEditAccountAuthConfig(auth)))
        if (exchangeConfig) ids.push(await appendAction(buildEditExchangeConfigConfig(exchangeConfig)))
        ids.push(await appendAction(buildEditAccountConfig(id, account)))
        return afterSettle(id)
      })()
      return createActionHandle(session, ids, work)
    },
    async delete(id) {
      const ids: string[] = []
      const work = (async () => {
        // Which companion deletes actually apply depends on account kind —
        // a 'generic' account has no AccountAuthentication at all
        // (toAccountGraph: auth: null), and an ExchangeConfig only exists
        // when `specifics.exchange_config_ids` is actually populated (every
        // AccountSpecifics variant, including 'blockchain', CAN carry it —
        // this is not exclusive to 'exchange'). Emitting a delete for a
        // companion that was never created queues a guaranteed non-retriable
        // failed action on the node (it deletes-by-id; the id never
        // existed). Pulling first to check is the same pattern update()
        // already uses for created_at.
        //
        // If the pull itself fails (network blip, decrypt error — NOT "the
        // account doesn't exist"), `existing` is undefined and we can't tell
        // which companions exist. Defaulting to "delete nothing but the
        // account" would silently orphan real credentials on the node with
        // no error surfaced anywhere — worse than the bug being fixed here.
        // Fall back to the old unconditional-three behavior instead: a
        // delete for a companion that never existed is a harmless failed
        // action, not a data leak.
        let existing: ProtocolAccount | undefined
        let pullFailed = false
        try {
          const { data } = await pullAccounts()
          existing = (data.accounts ?? []).find((a) => a.id === id)
        } catch {
          pullFailed = true
        }
        const specifics = existing?.specifics
        const hasAuth = pullFailed || Boolean(existing?.authentication_id)
        const hasExchangeConfig =
          pullFailed || (specifics !== undefined && 'exchange_config_ids' in specifics && (specifics.exchange_config_ids?.length ?? 0) > 0)
        ids.push(await appendAction(buildDeleteAccountConfig(id)))
        if (hasAuth) {
          ids.push(await appendAction(buildDeleteAccountAuthConfig(accountAuthIdFor(id))))
        }
        if (hasExchangeConfig) {
          ids.push(await appendAction(buildDeleteExchangeConfigConfig(exchangeConfigIdFor(id))))
        }
      })()
      return createActionHandle(session, ids, work)
    },
    async refresh(accountIds) {
      const ids: string[] = []
      const work = (async () => {
        ids.push(await appendAction(buildRefreshAccountsConfig(accountIds)))
        return list()
      })()
      return createActionHandle(session, ids, work)
    },
    async trading(id) {
      try {
        const encryptor = await session.collectionEncryptor('accountTrading')
        const { data } = await pullDocument(
          session.syncClient, 'accountTrading', { identity: session.userId, accountId: id }, encryptor,
        )
        return data as unknown as import('../../protocol/documents.js').AccountTradingDocument
      } catch (err) {
        rethrowAsOctoBotError(err)
      }
    },
  }
}
