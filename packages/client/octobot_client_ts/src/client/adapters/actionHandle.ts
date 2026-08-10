import type { UserAction } from '@drakkar.software/octobot-protocol'
import type { ClientSession } from '../core/session.js'
import type { CallOptions } from '../core/options.js'
import { pullDocument } from '../../transport/documents.js'
import { parseNodeUserActions } from '../../protocol/state.js'
import { rethrowAsOctoBotError } from '../core/errors.js'

export interface ActionHandle<T = void> {
  /** Action ids appended so far. For a multi-phase operation (e.g.
   *  `automations.create`, which emits a strategy action before the
   *  automation action) this grows as each phase starts. */
  readonly ids: readonly string[]
  /** Resolves once the node reports every phase completed. Memoized — safe
   *  to await twice, from different call sites, without double-polling.
   *  The underlying work started the moment the method that returned this
   *  handle returned (tuning like `timeoutMs`/`onProgress` belongs on THAT
   *  call, not here) — a caller who never awaits `settled()` still leaves
   *  nothing half-done, it just won't know the outcome.
   *  Rejects with `OctoBotActionError` (the node rejected an action) or
   *  `OctoBotTimeoutError` (the node never confirmed in time). */
  settled(): Promise<T>
  /** One-shot, non-blocking read of the node's current verdict for `ids` —
   *  does not wait, does not affect the in-flight `settled()` work. */
  status(opts?: CallOptions): Promise<{ settled: boolean; actions: UserAction[] }>
}

/** Wrap an already-started promise (and the action ids it's driving) as a
 *  public `ActionHandle`. `work` must already be running — see the
 *  `settled()` doc comment on why eager-start matters. */
export function createActionHandle<T>(
  session: ClientSession,
  ids: readonly string[],
  work: Promise<T>,
): ActionHandle<T> {
  // Attach a no-op rejection handler so an unawaited handle never surfaces
  // an unhandled promise rejection — settled() still gets the real outcome.
  work.catch(() => undefined)

  return {
    ids,
    settled: () => work.catch((err) => rethrowAsOctoBotError(err)),
    async status(_opts?: CallOptions) {
      try {
        const encryptor = await session.collectionEncryptor('userData')
        const { data } = await pullDocument(
          session.syncClient,
          'userData',
          { identity: session.userId },
          encryptor,
        )
        const nodeActions = parseNodeUserActions(data)
        const actions = nodeActions.filter((a) => ids.includes(a.id))
        // `ids.length > 0` matters: before any phase has appended,
        // `ids` is still `[]`, making `actions.length === ids.length` true
        // (0 === 0) and `[].every(...)` vacuously true — without this guard
        // a caller polling status() immediately after getting a handle back
        // would see `settled: true` before a single action exists.
        const settledAll = ids.length > 0 && actions.length === ids.length && actions.every(
          (a) => a.status === 'completed' || a.status === 'failed',
        )
        return { settled: settledAll, actions }
      } catch (err) {
        rethrowAsOctoBotError(err)
      }
    },
  }
}
