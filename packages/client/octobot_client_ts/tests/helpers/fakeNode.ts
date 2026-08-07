import type { UserAction, UserActionConfiguration, AutomationState } from '@drakkar.software/octobot-protocol'
import { createSecretEncryptor } from '../../src/crypto/secretEncryptor.js'
import { STARFISH_ENCRYPTION_SALT } from '../../src/crypto/wireConstants.js'
import { NODE_COLLECTIONS, type NodeCollectionKey } from '../../src/collections/nodeCollections.js'
import { createKeyCache } from '../../src/identity/keys.js'
import { deriveRoot } from '../../src/identity/capProvider.js'

/** One recorded HTTP call the fake wire actually saw — the lever every
 *  "issues zero writes" / "never touches this endpoint" / "goes through the
 *  injected fetch" assertion in this suite is built on. */
export type RecordedRequest = {
  method: string
  url: string
  path: string
  headers: Record<string, string>
  body: string | undefined
}

export type StarfishWireOptions = {
  /** `undefined`/`null` = every identity is authorized. A `Set` restricts
   *  which `users/{identity}/...` paths answer 200 instead of a real 403 —
   *  real, because it's constructed from an actual non-2xx `Response`, so
   *  `StarfishClient` raises a genuine `StarfishHttpError` from it, the same
   *  way `connect.ts`'s `probeIdentity` distinguishes "unauthorized" from
   *  "unreachable". */
  authorizedIdentities?: Set<string> | null
  /** Inject an HTTP failure for a specific request. Return a status to force
   *  it; return `undefined` to let the request proceed normally. */
  statusFor?: (req: RecordedRequest) => number | undefined
}

/**
 * The base fake: an in-memory `fetch` implementing enough of the real
 * `StarfishClient` wire protocol (verified against
 * `node_modules/@drakkar.software/starfish-client/dist/client.js`'s
 * `pull`/`push`/`append`) to drive the SDK's real public entry points
 * (`connectOctoBot`, `connectReadOnlyDevice`) end to end, not a hand-rolled
 * `ClientSession`.
 *
 * Wire shape, confirmed by reading the client source directly:
 * - `pull(path)` is a GET; an unwritten slot answers with `data` as the
 *   STRING `"null"` (the same opaque-JSON-string convention a real {iv,data}
 *   blob is wrapped in, just carrying the JSON `null` literal instead) —
 *   never a 404, and never a raw `data: null` either. `hash` may still be a
 *   real, non-null value even for this never-written case (a node can
 *   bootstrap a CAS-trackable slot without ever writing real content into
 *   it) — `hash` is NOT a reliable "does this exist" signal on its own; the
 *   parsed `data` is. The response body IS the `{data, hash, timestamp}`
 *   triple the client expects verbatim, no field extraction. This is real,
 *   observed node behavior (a fresh identity's first `accounts.list()`
 *   before anything was ever pushed for it) — the encryptor's `decrypt()`
 *   must treat a parsed-null blob as "no data yet", not assume every
 *   document is bootstrapped with real content by pairing time.
 * - `push(path, data, baseHash)` is a POST whose body ALWAYS carries a
 *   `baseHash` key (even when `null`, on a first push) — a stale hash
 *   answers a real `409`, which the client turns into a `ConflictError`.
 * - `append(path, data)` POSTs to the SAME `/push/...` path push() uses,
 *   but its body carries NO `baseHash` key at all (only `data` and,
 *   optionally, `authorPubkey`/`authorSignature`). The presence/absence of
 *   the `baseHash` key is the only wire-level signal distinguishing an
 *   append from a CAS push — there is no separate endpoint.
 *
 * This fake doesn't verify cap-cert signatures (it isn't a security
 * boundary; the SDK's own client-side gates are what these tests exercise)
 * — it only needs to route pull/push/append correctly and optionally deny
 * an identity, which is enough to exercise every real code path that reads
 * a `StarfishHttpError`.
 */
export function createStarfishWire(opts: StarfishWireOptions = {}) {
  const store = new Map<string, { data: Record<string, unknown>; hash: string }>()
  const appends = new Map<string, Record<string, unknown>[]>()
  const requests: RecordedRequest[] = []
  let hashCounter = 0

  function keyFrom(pathname: string): { action: 'pull' | 'push'; key: string } {
    const match = /\/(pull|push)\/(.+)$/.exec(pathname)
    if (!match) throw new Error(`fakeNode: could not extract a doc key from ${pathname}`)
    return { action: match[1] as 'pull' | 'push', key: decodeURIComponent(match[2]) }
  }

  function identityFromKey(key: string): string | null {
    const m = /^users\/([^/]+)\//.exec(key)
    return m ? m[1] : null
  }

  const fetchImpl: typeof fetch = async (input, init) => {
    const urlStr = typeof input === 'string' ? input : input instanceof URL ? input.toString() : (input as Request).url
    const url = new URL(urlStr)
    const method = init?.method ?? 'GET'
    const headers: Record<string, string> = {}
    const rawHeaders = init?.headers
    if (rawHeaders) {
      const h = rawHeaders instanceof Headers ? rawHeaders : new Headers(rawHeaders as HeadersInit)
      h.forEach((v, k) => {
        headers[k] = v
      })
    }
    const bodyStr = init?.body !== undefined ? String(init.body) : undefined
    const record: RecordedRequest = { method, url: urlStr, path: url.pathname, headers, body: bodyStr }
    requests.push(record)

    const injected = opts.statusFor?.(record)
    if (injected !== undefined) {
      return new Response(JSON.stringify({ error: 'injected' }), { status: injected })
    }

    const { action, key } = keyFrom(url.pathname)
    const identity = identityFromKey(key)
    if (identity && opts.authorizedIdentities && !opts.authorizedIdentities.has(identity)) {
      return new Response(JSON.stringify({ error: 'forbidden' }), { status: 403 })
    }

    if (action === 'pull') {
      const entry = store.get(key)
      if (!entry) {
        // Matches an actual node's observed response for a slot nothing has
        // ever been pushed to: `data` is the STRING "null", and `hash` can
        // still be a real, non-null value (bootstrapped for CAS tracking
        // without any real content ever having been written).
        return new Response(
          JSON.stringify({ data: 'null', hash: `unwritten-${key}`, timestamp: Date.now() }),
          { status: 200 },
        )
      }
      return new Response(JSON.stringify({ data: entry.data, hash: entry.hash, timestamp: Date.now() }), { status: 200 })
    }

    // POST — push (CAS) or append, distinguished by the `baseHash` key.
    const body = JSON.parse(bodyStr ?? '{}') as {
      data: Record<string, unknown>
      baseHash?: string | null
      authorPubkey?: string
      authorSignature?: string
    }
    const isAppend = !('baseHash' in body)
    if (isAppend) {
      const list = appends.get(key) ?? []
      list.push(body.data)
      appends.set(key, list)
      return new Response(JSON.stringify({ hash: `append-${list.length}`, timestamp: Date.now() }), { status: 200 })
    }
    const entry = store.get(key) ?? { data: {}, hash: 'empty-hash' }
    if ((body.baseHash ?? 'empty-hash') !== entry.hash) {
      return new Response(JSON.stringify({ error: 'conflict' }), { status: 409 })
    }
    const hash = `hash-${++hashCounter}`
    store.set(key, { data: body.data, hash })
    return new Response(JSON.stringify({ hash, timestamp: Date.now() }), { status: 200 })
  }

  return { fetch: fetchImpl, store, appends, requests }
}

export type StarfishWire = ReturnType<typeof createStarfishWire>

/**
 * OctoBot semantics on top of the base wire: real per-collection encryptors
 * keyed by the SAME secret `connectOctoBot({seed})` derives (crypto stays
 * real end to end, matching every other fake in this suite — nothing at the
 * crypto layer is ever stubbed), plus a scriptable `execute()` that mirrors
 * an appended action's outcome into `userData`, the way a real node would,
 * so `ActionHandle.settled()`/`.status()` have something real to observe.
 */
export async function createFakeNode(opts: { seed: string; derivation?: string; wireOptions?: StarfishWireOptions } = { seed: '' }) {
  const derivation = opts.derivation ?? 'bip44'
  const root = await deriveRoot(opts.seed, derivation)
  const userId = root.userId
  const secret = await createKeyCache().getEncryptionKey(opts.seed, derivation)

  const encryptors = Object.fromEntries(
    (Object.keys(NODE_COLLECTIONS) as NodeCollectionKey[]).map((k) => [
      k,
      createSecretEncryptor(secret, STARFISH_ENCRYPTION_SALT, NODE_COLLECTIONS[k].encryptionInfo),
    ]),
  ) as Record<NodeCollectionKey, ReturnType<typeof createSecretEncryptor>>

  const wire = createStarfishWire(opts.wireOptions)

  function pathFor(collection: NodeCollectionKey, params: Record<string, string> = {}): string {
    let path = NODE_COLLECTIONS[collection].storagePath
    for (const [k, v] of Object.entries({ identity: userId, ...params })) path = path.replaceAll(`{${k}}`, v)
    return path
  }

  /** Pre-populate a collection's document directly (bypassing the wire) —
   *  for setting up "existing state" before a test connects a client. */
  async function seedDoc(collection: NodeCollectionKey, data: Record<string, unknown>, params?: Record<string, string>): Promise<void> {
    const encrypted = await encryptors[collection].encrypt(data)
    wire.store.set(pathFor(collection, params), { data: encrypted, hash: `seed-${collection}` })
  }

  // Pre-seeded so most tests in this suite don't have to think about the
  // never-written case — `pullDocument` itself now handles a genuinely
  // unwritten slot (`data: null` over the wire) by treating it as `{}`, see
  // `transport/documents.ts`. A never-written document is real, observed
  // production behavior (a fresh identity's first read, before anything was
  // ever pushed for it) — it's not something a real node avoids by
  // bootstrapping documents at pairing time, which is what this suite
  // originally assumed. `fakeNode.smoke.test.ts` has a dedicated test that
  // deletes a pre-seeded doc to exercise the genuinely-unwritten path
  // directly. `actions` stays untouched — the queue itself always pulls
  // empty by design (docs/user-actions.md) and is never read via
  // `pullDocument`, only appended/append-logged.
  await seedDoc('userData', { user_actions: [], automations: [] })
  await seedDoc('accounts', { accounts: [], exchange_configs: [] })
  await seedDoc('settings', {})
  await seedDoc('strategies', {})

  /** The current `userData` document, decrypted (empty shape if never
   *  written). Kept as the live source of truth `execute()` mutates. */
  async function userData(): Promise<{ user_actions: UserAction[]; automations: AutomationState[] } & Record<string, unknown>> {
    const entry = wire.store.get(pathFor('userData'))
    if (!entry) return { user_actions: [], automations: [] }
    const decrypted = (await encryptors.userData.decrypt(entry.data)) as {
      user_actions?: UserAction[]
      automations?: AutomationState[]
    }
    return { user_actions: decrypted.user_actions ?? [], automations: decrypted.automations ?? [] }
  }

  async function writeUserData(next: { user_actions: UserAction[]; automations: AutomationState[] }): Promise<void> {
    await seedDoc('userData', next)
  }

  /** Every action appended to the queue so far, decrypted, in append order.
   *  The queue itself always pulls empty on a real node (and does here,
   *  since nothing ever writes to `wire.store` for it) — this reads the
   *  `appends` log directly, the same way a test double stands in for what
   *  only the node's own execution loop would otherwise report back. */
  async function decryptedActions(): Promise<{ id: string; status: string; created_at: string; configuration: UserActionConfiguration }[]> {
    const raw = wire.appends.get(pathFor('actions')) ?? []
    return Promise.all(
      raw.map(
        (envelope) =>
          encryptors.actions.decrypt(envelope) as Promise<{
            id: string
            status: string
            created_at: string
            configuration: UserActionConfiguration
          }>,
      ),
    )
  }

  /** Simulate the node executing one queued action: upserts its `UserAction`
   *  into `userData.user_actions` with the given status/result. For a
   *  completed `automation_create`, also upserts a matching
   *  `AutomationState` when `automation` is supplied. */
  async function execute(
    actionId: string,
    outcome: { status: 'completed' | 'failed' | 'running'; result?: Record<string, unknown> | null },
    automation?: AutomationState,
  ): Promise<void> {
    const actions = await decryptedActions()
    const appended = actions.find((a) => a.id === actionId)
    if (!appended) throw new Error(`fakeNode.execute: no appended action with id ${actionId}`)

    const current = await userData()
    const nextAction: UserAction = {
      id: actionId,
      status: outcome.status,
      configuration: appended.configuration,
      ...(outcome.result !== undefined ? { result: outcome.result } : {}),
    } as UserAction
    const nextActions = [...current.user_actions.filter((a) => a.id !== actionId), nextAction]
    const nextAutomations = automation
      ? [...current.automations.filter((a) => a.id !== automation.id), automation]
      : current.automations
    await writeUserData({ user_actions: nextActions, automations: nextAutomations })
  }

  return {
    ...wire,
    userId,
    seed: opts.seed,
    derivation,
    encryptors,
    pathFor,
    seedDoc,
    userData,
    writeUserData,
    decryptedActions,
    execute,
  }
}

export type FakeNode = Awaited<ReturnType<typeof createFakeNode>>
