import type { StarfishClient, StarfishCapProvider } from '@drakkar.software/starfish-client'
import type { Encryptor } from '@drakkar.software/starfish-protocol'
import type { ClientSession } from '../core/session.js'
import type { CallOptions } from '../core/options.js'
import { pullDocument, pushDocument, appendElement, type DocumentParams } from '../../transport/documents.js'
import { pullPath, pushPath } from '../../collections/paths.js'
import { NODE_COLLECTIONS, type NodeCollectionKey } from '../../collections/nodeCollections.js'
import { rethrowAsOctoBotError } from '../core/errors.js'

/** Escape hatch: raw access to the node collections and the underlying
 *  Starfish client, for anything the typed `accounts`/`automations`/`strategies`
 *  namespaces don't cover. Full-wallet client only — see `ReadOnlyDocumentsApi`
 *  for the read-only client's deliberately narrower equivalent. */
export interface DocumentsApi {
  pull<T = Record<string, unknown>>(
    collection: NodeCollectionKey,
    opts?: CallOptions & { accountId?: string },
  ): Promise<{ data: T; hash: string | null }>
  push(
    collection: NodeCollectionKey,
    data: Record<string, unknown>,
    opts: CallOptions & { baseHash: string | null; accountId?: string },
  ): Promise<{ hash: string }>
  append(
    collection: NodeCollectionKey,
    element: Record<string, unknown>,
    opts?: CallOptions,
  ): Promise<void>
  readonly raw: {
    readonly sync: StarfishClient
    readonly capProvider: StarfishCapProvider
    encryptorFor(collection: NodeCollectionKey): Promise<Encryptor>
    pullPath(collection: NodeCollectionKey, accountId?: string): string
    pushPath(collection: NodeCollectionKey, accountId?: string): string
  }
}

/** The read-only client's `documents` escape hatch — deliberately smaller
 *  than `DocumentsApi`. No `push`/`append` (this client has no append rights
 *  by design — see `ReadOnlyOctoBotClient`'s doc comment), and `raw` drops
 *  `sync`/`capProvider`/`pushPath`: those hand a caller an unconstrained
 *  `StarfishClient` that can pull or push ANY path, bypassing
 *  `collectionEncryptor`'s per-collection gate entirely. What remains
 *  (`pull`, `raw.encryptorFor`, `raw.pullPath`) all still route through the
 *  session's gate, so a collection outside the grant still throws
 *  `OctoBotScopeError` rather than silently working. */
export interface ReadOnlyDocumentsApi {
  pull<T = Record<string, unknown>>(
    collection: NodeCollectionKey,
    opts?: CallOptions & { accountId?: string },
  ): Promise<{ data: T; hash: string | null }>
  readonly raw: {
    encryptorFor(collection: NodeCollectionKey): Promise<Encryptor>
    pullPath(collection: NodeCollectionKey, accountId?: string): string
  }
}

function documentPath(userId: string, accountId?: string): DocumentParams {
  return accountId ? { identity: userId, accountId } : { identity: userId }
}

export function createDocumentsApi(session: ClientSession): DocumentsApi {
  function params(accountId?: string): DocumentParams {
    return documentPath(session.userId, accountId)
  }

  return {
    async pull(collection, opts) {
      try {
        const encryptor = await session.collectionEncryptor(collection)
        return await pullDocument(session.syncClient, collection, params(opts?.accountId), encryptor)
      } catch (err) {
        rethrowAsOctoBotError(err)
      }
    },
    async push(collection, data, opts) {
      try {
        const encryptor = await session.collectionEncryptor(collection)
        return await pushDocument(session.syncClient, collection, params(opts?.accountId), data, opts.baseHash, encryptor)
      } catch (err) {
        rethrowAsOctoBotError(err)
      }
    },
    async append(collection, element) {
      try {
        const encryptor = await session.collectionEncryptor(collection)
        await appendElement(session.syncClient, collection, params(), element, encryptor)
      } catch (err) {
        rethrowAsOctoBotError(err)
      }
    },
    raw: {
      sync: session.syncClient,
      capProvider: session.capProvider,
      encryptorFor: (collection) => session.collectionEncryptor(collection),
      pullPath: (collection, accountId) => pullPath(
        NODE_COLLECTIONS[collection].storagePath,
        accountId ? { identity: session.userId, accountId } : { identity: session.userId },
      ),
      pushPath: (collection, accountId) => pushPath(
        NODE_COLLECTIONS[collection].storagePath,
        accountId ? { identity: session.userId, accountId } : { identity: session.userId },
      ),
    },
  }
}

export function createReadOnlyDocumentsApi(session: ClientSession): ReadOnlyDocumentsApi {
  return {
    async pull(collection, opts) {
      try {
        const encryptor = await session.collectionEncryptor(collection)
        return await pullDocument(
          session.syncClient, collection,
          documentPath(session.userId, opts?.accountId), encryptor,
        )
      } catch (err) {
        rethrowAsOctoBotError(err)
      }
    },
    raw: {
      encryptorFor: (collection) => session.collectionEncryptor(collection),
      pullPath: (collection, accountId) => pullPath(
        NODE_COLLECTIONS[collection].storagePath,
        accountId ? { identity: session.userId, accountId } : { identity: session.userId },
      ),
    },
  }
}
