import type { Strategy as ProtocolStrategy, UserAction } from '@drakkar.software/octobot-protocol'
import type { ClientSession } from '../core/session.js'
import type { CallOptions } from '../core/options.js'
import type { AppendAction } from './accounts.js'
import { automationViewOf, type AutomationView } from '../core/views.js'
import { createActionHandle, type ActionHandle } from './actionHandle.js'
import { pullDocument } from '../../transport/documents.js'
import { parseNodeAutomationStates, parseNodeUserActions } from '../../protocol/state.js'
import { buildEditAutomationConfig, buildEditStrategyConfig, buildStopAutomationConfig, type AutomationBuildInput } from '../../protocol/actions.js'
import { runCreateAutomation, type ActionEmitter, type CreateAutomationProgress } from '../../protocol/orchestration/createAutomation.js'
import { rethrowAsOctoBotError } from '../core/errors.js'

export type { AutomationView, CreateAutomationProgress }

export type CreateAutomationInput = {
  name: string
  description?: string
  strategy: ProtocolStrategy
  accountIds: string[]
}

export interface AutomationsApi {
  list(opts?: CallOptions): Promise<AutomationView[]>
  get(id: string, opts?: CallOptions): Promise<AutomationView | null>
  /** Two-phase under the hood: `strategy_create` is appended and confirmed
   *  BEFORE `automation_create` is appended, avoiding a node-side race where
   *  the automation would resolve its strategy before the node's
   *  StrategyProvider had registered it. See `protocol/orchestration/createAutomation.ts`. */
  create(input: CreateAutomationInput, opts?: { onProgress?: (p: CreateAutomationProgress) => void; timeoutMs?: number; signal?: AbortSignal }): Promise<ActionHandle<AutomationView | null>>
  update(id: string, input: CreateAutomationInput, opts?: CallOptions): Promise<ActionHandle<AutomationView | null>>
  stop(id: string, opts?: CallOptions): Promise<ActionHandle<void>>
}

export function createAutomationsApi(session: ClientSession, appendAction: AppendAction): AutomationsApi {
  async function pullUserData() {
    const encryptor = await session.collectionEncryptor('userData')
    return pullDocument(session.syncClient, 'userData', { identity: session.userId }, encryptor)
  }

  async function listWithActions(): Promise<{ views: AutomationView[]; actions: UserAction[] }> {
    const { data } = await pullUserData()
    const states = parseNodeAutomationStates(data)
    const actions = parseNodeUserActions(data)
    return { views: states.map((s) => automationViewOf(s, actions)), actions }
  }

  async function list(): Promise<AutomationView[]> {
    try {
      return (await listWithActions()).views
    } catch (err) {
      rethrowAsOctoBotError(err)
    }
  }

  async function get(id: string): Promise<AutomationView | null> {
    const all = await list()
    return all.find((a) => a.id === id) ?? null
  }

  const emitter: ActionEmitter = {
    emit: (configuration) => appendAction(configuration),
    poll: async () => {
      const { data } = await pullUserData()
      return parseNodeUserActions(data)
    },
  }

  return {
    list,
    get,
    async create(input, opts) {
      const ids: string[] = []
      const io: ActionEmitter = {
        emit: async (configuration) => {
          const id = await emitter.emit(configuration)
          ids.push(id)
          return id
        },
        poll: emitter.poll,
      }
      const buildInput: AutomationBuildInput = input
      const work = runCreateAutomation(io, buildInput, {
        onProgress: opts?.onProgress,
        timeoutMs: opts?.timeoutMs,
        signal: opts?.signal,
      }).then(({ automationId }) => (automationId ? get(automationId) : null))
      return createActionHandle(session, ids, work)
    },
    async update(id, input) {
      const ids: string[] = []
      const work = (async () => {
        // Same strategy id, bumped version: the node treats strategy items
        // as replace-by-id, so edits flow through strategy_edit.
        ids.push(await appendAction(buildEditStrategyConfig(input.strategy)))
        ids.push(await appendAction(buildEditAutomationConfig({ ...input, automationId: id })))
        return get(id)
      })()
      return createActionHandle(session, ids, work)
    },
    async stop(id) {
      const ids: string[] = []
      const work = (async () => {
        ids.push(await appendAction(buildStopAutomationConfig(id)))
      })()
      return createActionHandle(session, ids, work)
    },
  }
}
