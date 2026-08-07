import type { Strategy as ProtocolStrategy, UserAction } from '@drakkar.software/octobot-protocol'
import type { ClientSession } from '../core/session.js'
import type { CallOptions } from '../core/options.js'
import type { AppendAction } from './accounts.js'
import { createActionHandle, type ActionHandle } from './actionHandle.js'
import { pullDocument } from '../../transport/documents.js'
import { parseNodeUserActions } from '../../protocol/state.js'
import { buildCreateStrategyConfig, buildEditStrategyConfig, buildDeleteStrategyConfig } from '../../protocol/actions.js'
import { rethrowAsOctoBotError } from '../core/errors.js'

export interface StrategiesApi {
  /** Reconstructed from the node's `strategy_create`/`strategy_edit` actions
   *  — the node exposes no strategies collection of its own; a strategy only
   *  exists as the configuration an automation was created or edited with. */
  list(opts?: CallOptions): Promise<ProtocolStrategy[]>
  get(id: string, version?: string, opts?: CallOptions): Promise<ProtocolStrategy | null>
  create(strategy: ProtocolStrategy, opts?: CallOptions): Promise<ActionHandle<ProtocolStrategy>>
  update(strategy: ProtocolStrategy, opts?: CallOptions): Promise<ActionHandle<ProtocolStrategy>>
  delete(id: string, opts?: CallOptions): Promise<ActionHandle<void>>
}

type StrategyActionConfig = {
  action_type?: string
  id?: string
  configuration?: ProtocolStrategy
}

/** Every strategy the action history carries, one entry per (id, version)
 *  the newest action for that pair produced — `strategy_edit` supersedes an
 *  earlier `strategy_create` for the same id. */
function strategiesFromActions(actions: UserAction[]): ProtocolStrategy[] {
  const byKey = new Map<string, { at: string; strategy: ProtocolStrategy }>()
  for (const action of actions) {
    const cfg = action.configuration as StrategyActionConfig | undefined
    if (cfg?.action_type !== 'strategy_create' && cfg?.action_type !== 'strategy_edit') continue
    const strategy = cfg.configuration
    if (!strategy?.id) continue
    const key = `${strategy.id}@${strategy.version ?? ''}`
    const at = action.updated_at ?? action.created_at ?? ''
    const existing = byKey.get(key)
    if (!existing || at >= existing.at) byKey.set(key, { at, strategy })
  }
  return [...byKey.values()].map((v) => v.strategy)
}

export function createStrategiesApi(session: ClientSession, appendAction: AppendAction): StrategiesApi {
  async function pullActions(): Promise<UserAction[]> {
    const encryptor = await session.collectionEncryptor('userData')
    const { data } = await pullDocument(session.syncClient, 'userData', { identity: session.userId }, encryptor)
    return parseNodeUserActions(data)
  }

  async function list(): Promise<ProtocolStrategy[]> {
    try {
      return strategiesFromActions(await pullActions())
    } catch (err) {
      rethrowAsOctoBotError(err)
    }
  }

  async function get(id: string, version?: string): Promise<ProtocolStrategy | null> {
    const all = await list()
    const matches = all.filter((s) => s.id === id)
    if (version) return matches.find((s) => s.version === version) ?? null
    return matches.at(-1) ?? null
  }

  return {
    list,
    get,
    async create(strategy) {
      const ids: string[] = []
      const work = (async () => {
        ids.push(await appendAction(buildCreateStrategyConfig(strategy)))
        return strategy
      })()
      return createActionHandle(session, ids, work)
    },
    async update(strategy) {
      const ids: string[] = []
      const work = (async () => {
        ids.push(await appendAction(buildEditStrategyConfig(strategy)))
        return strategy
      })()
      return createActionHandle(session, ids, work)
    },
    async delete(id) {
      const ids: string[] = []
      const work = (async () => {
        ids.push(await appendAction(buildDeleteStrategyConfig(id)))
      })()
      return createActionHandle(session, ids, work)
    },
  }
}
