import type { ClientSession } from '../core/session.js'
import type { CallOptions } from '../core/options.js'
import { pullDocument, pushDocument } from '../../transport/documents.js'
import { rethrowAsOctoBotError } from '../core/errors.js'

/** The node stores this document encrypted and OPAQUE — it never reads a
 *  field, which is why every method here is generic over the caller's own
 *  shape rather than a fixed `UserSettings` type. */
export interface SettingsApi {
  get<T extends object = Record<string, unknown>>(opts?: CallOptions): Promise<T>
  /** Read-modify-write against the pulled `baseHash`. This is last-write-wins
   *  over the WHOLE document, not a field-level or CRDT merge — a concurrent
   *  writer's changes outside `patch` are still preserved (shallow-merged),
   *  but two concurrent patches to the same field race normally. */
  patch<T extends object = Record<string, unknown>>(patch: Partial<T>, opts?: CallOptions): Promise<T>
  replace<T extends object = Record<string, unknown>>(doc: T, opts?: CallOptions): Promise<T>
}

export function createSettingsApi(session: ClientSession): SettingsApi {
  async function pull<T extends object>() {
    const encryptor = await session.collectionEncryptor('settings')
    return pullDocument<T>(session.syncClient, 'settings', { identity: session.userId }, encryptor)
  }

  return {
    async get<T extends object = Record<string, unknown>>() {
      try {
        const { data } = await pull<T>()
        return data
      } catch (err) {
        rethrowAsOctoBotError(err)
      }
    },
    async patch<T extends object = Record<string, unknown>>(patch: Partial<T>) {
      try {
        const { data, hash } = await pull<T>()
        const merged = { ...data, ...patch } as T
        const encryptor = await session.collectionEncryptor('settings')
        await pushDocument(
          session.syncClient, 'settings', { identity: session.userId },
          merged as unknown as Record<string, unknown>, hash, encryptor,
        )
        return merged
      } catch (err) {
        rethrowAsOctoBotError(err)
      }
    },
    async replace<T extends object = Record<string, unknown>>(doc: T) {
      try {
        const { hash } = await pull<T>()
        const encryptor = await session.collectionEncryptor('settings')
        await pushDocument(
          session.syncClient, 'settings', { identity: session.userId },
          doc as unknown as Record<string, unknown>, hash, encryptor,
        )
        return doc
      } catch (err) {
        rethrowAsOctoBotError(err)
      }
    },
  }
}
