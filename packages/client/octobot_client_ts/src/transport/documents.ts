import type { StarfishClient } from '@drakkar.software/starfish-client'
import type { Encryptor } from '@drakkar.software/starfish-protocol'
import { pullPath, pushPath } from '../collections/paths.js'
import { NODE_COLLECTIONS, type NodeCollectionInfo, type NodeCollectionKey } from '../collections/nodeCollections.js'

export type PulledDocument<T> = { data: T; hash: string | null }

/** One collection's `{identity}`-scoped params. `accountId` is only needed for
 *  `accountTrading` — every other node collection is identity-only. */
export type DocumentParams = { identity: string; accountId?: string }

/** Pull + decrypt one node-owned document. `encryptor` must be the one built
 *  for `collection` — see `ClientSession.collectionEncryptor()`, which is
 *  the enforcement point deciding whether the caller even gets one. */
export async function pullDocument<T = Record<string, unknown>>(
  client: StarfishClient,
  collection: NodeCollectionKey,
  params: DocumentParams,
  encryptor: Encryptor,
): Promise<PulledDocument<T>> {
  const info = NODE_COLLECTIONS[collection]
  const result = await client.pull(pullPath(info.storagePath, params))
  // No document has ever been pushed for this identity/collection — the node
  // answers 200 with `data: null`-shaped content rather than 404 (`hash` is
  // the existence signal, same as pushDocument's `baseHash`). `encryptor`
  // resolves that to `{}`, which every caller downstream already treats as
  // "no data" (accounts.list()'s `data.accounts ?? []`, parseNodeUserActions).
  const decrypted = await encryptor.decrypt(result.data as Record<string, unknown>)
  return { data: decrypted as T, hash: result.hash }
}

/** Encrypt + push one node-owned document. Throws `ConflictError` (from
 *  `@drakkar.software/starfish-client`) on a stale `baseHash`. */
export async function pushDocument(
  client: StarfishClient,
  collection: NodeCollectionKey,
  params: DocumentParams,
  data: Record<string, unknown>,
  baseHash: string | null,
  encryptor: Encryptor,
): Promise<{ hash: string }> {
  const info = NODE_COLLECTIONS[collection]
  const encrypted = await encryptor.encrypt(data)
  return client.push(pushPath(info.storagePath, params), encrypted, baseHash)
}

/** Append one wire element to an append-only collection (only `actions`
 *  today). Each append publishes ONE queue element the node consumes and
 *  executes — re-sending an element is re-executing it. */
export async function appendElement(
  client: StarfishClient,
  collection: NodeCollectionKey,
  params: DocumentParams,
  element: Record<string, unknown>,
  encryptor: Encryptor,
): Promise<void> {
  const info: NodeCollectionInfo = NODE_COLLECTIONS[collection]
  if (!info.appendOnly) throw new Error(`${collection} is not an append-only collection`)
  const encrypted = await encryptor.encrypt(element)
  await client.append(pushPath(info.storagePath, params), encrypted)
}
