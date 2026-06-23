/**
 * OctoChat support-ticket integration for the node web interface.
 *
 * This is the ONLY module that imports the OctoChat SDK. It lets the browser open and hold a
 * single support ticket with the OctoBot team and exchange messages + attachments — replacing
 * the old "share logs to the cloud" flow.
 *
 * Model (see the approved plan): ONE ticket per configured desk space. The ticket is created
 * via the requester resource-request flow (`submitTicketRequest`) and only becomes writable
 * once the desk accepts it (`claimGrantedNodes` turns the sealed grant into per-node access).
 * The ticket's existence is derived from the local space-access store
 * (`getRequesterTicketForSpace`), not a local list — so it survives reloads on this browser.
 *
 * Identity is PERSISTENT (stored encrypted at rest via `device-key`), so the same requester can
 * later list/reply across sessions. Conversation read/write mirrors `desk/ticket-info` +
 * `desk/intake`: the ticket's messages live in its per-node invite-log stream (`objInvLog*`).
 * The requester is NOT a space member, so the desk object index (_index) is 403 by design.
 * Enc mode is detected from the LOCAL per-node keyring cap: present ⇒ E2EE (build the encryptor
 * only then, avoiding any 403); absent ⇒ plaintext (the default for a non-member requester).
 * Reads tolerate both. Desk-side ticket status is not observable from the requester's caps.
 */
import {
  type AttachmentRef,
  type ByteSealer,
  buildNodeAccess,
  buildSession,
  claimGrantedNodes,
  configureKv,
  configureOctoChat,
  type DeviceKeys,
  decodeRequestLink,
  ensureProfileKeys,
  getNodeStreamClient,
  getRequesterTicketForSpace,
  isTicketRoomId,
  loadAttachment,
  localSpaceAccessEntries,
  objInvLogPull,
  objInvLogPush,
  readSpaces,
  getNodeKeyringAccessEntry,
  removeNodeAccessEntry,
  recoverSpaceAccess,
  type ResourceGrant,
  type ResourceReject,
  scanResourceRejects,
  type Session,
  submitTicketRequest,
  uploadAttachment,
} from "@drakkar.software/octochat-sdk"
import { kvGet, kvRemove, kvSet } from "@drakkar.software/octochat-sdk/platform"

import { loadPassword } from "@/lib/device-key"
import { getWalletBoundIdentity } from "@/lib/octochat-identity"

export interface OctoChatConfig {
  syncBase: string | null
  syncNamespace: string
  supportDeskRequestLink: string | null
  webBase: string | null
}

export type SupportTicketState =
  | { status: "disabled" }
  | { status: "none" }
  | { status: "pending" }
  | { status: "open"; nodeId: string; title: string; allTickets: Array<{ nodeId: string; title: string }> }
  | { status: "resolved"; nodeId: string; title: string }

export interface TicketMessage {
  id: string
  authorId: string
  ts: number
  text: string
  attachment?: AttachmentRef
  /** True when this message was authored by the current requester (vs the support team). */
  fromMe: boolean
}

/** A minimal per-node encryptor shape (seal/unseal an envelope). null for plaintext tickets. */
type NodeEncryptor = {
  encrypt: (d: Record<string, unknown>) => Promise<Record<string, unknown>>
  decrypt: (d: Record<string, unknown>) => Promise<Record<string, unknown>>
} | null

const DISPLAY_NAME = "OctoBot user"
const SECURE_CHANNEL_NOT_READY =
  "Support chat isn't ready yet — the encrypted channel is still being set up. Try again in a moment."
const CLOSED_BY_REQUESTER_NOTE = "Closed by the requester from OctoBot."

/** Shared React Query key for the single support ticket, so every view polls the same cache. */
export const SUPPORT_TICKET_QUERY_KEY = ["support-ticket"] as const

let configPromise: Promise<OctoChatConfig> | null = null
let configured = false
let sessionPromise: Promise<Session> | null = null
const keyringRestoreAttempted = new Set<string>()

function pendingKey(spaceId: string): string {
  return `octochat:pending:${spaceId}`
}

function seenGrantsKey(spaceId: string): string {
  return `octochat:seen-grants:${spaceId}`
}

function ticketTitleKey(spaceId: string, nodeId: string): string {
  return `octochat:title:${spaceId}:${nodeId}`
}

function dismissedKey(spaceId: string): string {
  return `octochat:dismissed:${spaceId}`
}

async function loadStringSet(key: string): Promise<Set<string>> {
  const raw = await kvGet(key).catch(() => null)
  if (!raw) return new Set()
  try {
    const arr = JSON.parse(raw) as unknown
    return Array.isArray(arr)
      ? new Set(arr.filter((x): x is string => typeof x === "string"))
      : new Set()
  } catch {
    return new Set()
  }
}

async function saveStringSet(key: string, set: Set<string>): Promise<void> {
  await kvSet(key, JSON.stringify([...set])).catch(() => undefined)
}

const loadSeenReqIds = (spaceId: string): Promise<Set<string>> => loadStringSet(seenGrantsKey(spaceId))
const saveSeenReqIds = (spaceId: string, set: Set<string>): Promise<void> => saveStringSet(seenGrantsKey(spaceId), set)
const loadDismissed  = (spaceId: string): Promise<Set<string>> => loadStringSet(dismissedKey(spaceId))
const saveDismissed  = (spaceId: string, set: Set<string>): Promise<void> => saveStringSet(dismissedKey(spaceId), set)

// Record successfully-claimed grants so they're never re-claimed from the inbox.
// Reloads fresh from KV (not the in-memory set claimGrantedNodes mutates) so
// transiently-failed accepts aren't persisted and still get retried on next claim.
async function recordClaimedReqIds(spaceId: string, claimed: ResourceGrant[]): Promise<void> {
  if (!claimed.length) return
  const seen = await loadSeenReqIds(spaceId)
  for (const g of claimed) seen.add(g.reqId)
  await saveSeenReqIds(spaceId, seen)
}

function localTicketNodeIds(spaceId: string): string[] {
  const prefix = `${spaceId}:`
  return Object.keys(localSpaceAccessEntries())
    .filter((k) => k.startsWith(prefix))
    .map((k) => k.slice(prefix.length))
    .filter((id) => !id.includes(":") && isTicketRoomId(id))
}

// The SDK re-hydrates every claimed ticket's cap into the local access store on each load
// (recoverSpaceAccess), even ones the requester closed — the cap lives in the requester's own
// _spaces doc and there is no SDK path to drop it. A requester "close" is therefore a durable
// local dismissal: re-forget dismissed tickets from the local store whenever a refresh restores them.
function purgeDismissed(spaceId: string, dismissed: Set<string>): void {
  if (!dismissed.size) return
  for (const id of localTicketNodeIds(spaceId)) {
    if (dismissed.has(id)) removeNodeAccessEntry(spaceId, id)
  }
}

/** Cancel a pending ticket request, resetting the state to 'none'. */
export async function cancelPendingTicket(): Promise<void> {
  if (!(await isSupportConfigured())) return
  const spaceId = await deskSpaceId()
  await kvRemove(pendingKey(spaceId)).catch(() => undefined)
}


async function buildAuthHeader(): Promise<string> {
  const username = localStorage.getItem("auth_username") || "node"
  const password = (await loadPassword()) ?? ""
  return `Basic ${btoa(`${username}:${password}`)}`
}

/** Fetch (and cache) the OctoChat config served by the node API from packages/node settings. */
export async function getOctoChatConfig(): Promise<OctoChatConfig> {
  if (!configPromise) {
    configPromise = (async () => {
      const res = await fetch("/api/v1/config/octochat", {
        headers: { Authorization: await buildAuthHeader() },
      })
      if (!res.ok)
        throw new Error(`Failed to load OctoChat config (${res.status})`)
      return (await res.json()) as OctoChatConfig
    })().catch((err) => {
      configPromise = null // allow retry on transient failure
      throw err
    })
  }
  return configPromise
}

/** True when the support desk is configured (a request link is present). */
export async function isSupportConfigured(): Promise<boolean> {
  try {
    const cfg = await getOctoChatConfig()
    return Boolean(cfg.syncBase && cfg.supportDeskRequestLink)
  } catch {
    return false
  }
}

async function ensureConfigured(): Promise<OctoChatConfig> {
  const cfg = await getOctoChatConfig()
  if (!cfg.syncBase || !cfg.supportDeskRequestLink) {
    throw new Error("OctoChat support desk is not configured")
  }
  if (!configured) {
    configureOctoChat({
      syncBase: cfg.syncBase,
      syncNamespace: cfg.syncNamespace || "",
      ...(cfg.webBase ? { webBase: cfg.webBase } : {}),
    })
    configureKv({ get: kvGet, set: kvSet, remove: kvRemove })
    configured = true
  }
  return cfg
}

/** The configured desk space id, decoded from the request link. */
async function deskSpaceId(): Promise<string> {
  const cfg = await ensureConfigured()
  const { spaceId } = decodeRequestLink(cfg.supportDeskRequestLink as string)
  if (!spaceId)
    throw new Error("Support desk request link is missing its space id (?s=…)")
  return spaceId
}

/** Get-or-create the PERSISTENT requester identity, build a session, and hydrate access. */
async function getSession(): Promise<Session> {
  if (!sessionPromise) {
    sessionPromise = (async () => {
      await ensureConfigured()
      // Identity is derived deterministically from the OctoBot wallet, so the same account
      // resolves to the same OctoChat identity (and thus the same ticket) on every device.
      const { userId, keys } = await getWalletBoundIdentity(buildAuthHeader)
      const deviceKeys = keys as DeviceKeys
      const session = await buildSession(
        { userId, keys: deviceKeys },
        DISPLAY_NAME,
      )
      // Publish profile keys so the desk can seal grants/messages to us.
      await ensureProfileKeys(session.accountClient, userId, deviceKeys).catch(
        () => undefined,
      )
      // Load the local space-access store (+ reconcile with server) so previously accepted
      // grants resolve to a ticket after a reload.
      await hydrate(session)
      return session
    })().catch((err) => {
      sessionPromise = null
      throw err
    })
  }
  return sessionPromise
}

async function hydrate(session: Session): Promise<void> {
  try {
    const { caps, pubAccess } = await readSpaces(
      session.spacesRegistryClient,
      session,
    )
    await recoverSpaceAccess(session, {
      caps,
      pubAccess: pubAccess as Parameters<
        typeof recoverSpaceAccess
      >[1]["pubAccess"],
    })
  } catch {
    // Best-effort: a failed hydrate leaves the local cache intact (offline-friendly).
  }
}

/** Resolve the current support ticket state for the configured desk space. */
export async function getSupportTicket(): Promise<SupportTicketState> {
  if (!(await isSupportConfigured())) return { status: "disabled" }
  const session = await getSession()
  const spaceId = await deskSpaceId()
  // Purge any dismissed tickets the SDK re-hydrated via recoverSpaceAccess. The requester's
  // own _spaces.caps doc persists per-node caps after the first claim; every load re-adds them
  // to the local store. Re-forget them before reading so closed tickets stay closed.
  const dismissed = await loadDismissed(spaceId)
  purgeDismissed(spaceId, dismissed)
  let ticket = await getRequesterTicketForSpace(session, spaceId)
  if (!ticket) {
    // No locally-known ticket — claim any freshly-accepted grant. seenReqIds gates the scan so
    // dismissed grants aren't re-accepted. purgeDismissed runs again because acceptNodeInvite
    // (inside claimGrantedNodes) can re-add a dismissed ticket to the local store.
    const seen = await loadSeenReqIds(spaceId)
    const claimed = await claimGrantedNodes(session, { seenReqIds: seen }).catch(
      (): ResourceGrant[] => [],
    )
    await recordClaimedReqIds(spaceId, claimed)
    purgeDismissed(spaceId, dismissed)
    ticket = await getRequesterTicketForSpace(session, spaceId)
  }
  if (ticket) {
    await kvRemove(pendingKey(spaceId)).catch(() => undefined)
    await kvSet(ticketTitleKey(spaceId, ticket.nodeId), ticket.title).catch(() => undefined)
    // The local node-access store is the source of truth for open tickets; no separate list.
    const otherIds = localTicketNodeIds(spaceId).filter((id) => id !== ticket.nodeId)
    const allTickets: Array<{ nodeId: string; title: string }> = [
      { nodeId: ticket.nodeId, title: ticket.title },
      ...(await Promise.all(
        otherIds.map(async (id) => ({
          nodeId: id,
          title: (await kvGet(ticketTitleKey(spaceId, id)).catch(() => null)) ?? "Support ticket",
        })),
      )),
    ]
    return { status: "open", nodeId: ticket.nodeId, title: ticket.title, allTickets }
  }
  const pending = await kvGet(pendingKey(spaceId))
  if (!pending) return { status: "none" }
  const rejects = await scanResourceRejects(session).catch(
    (): ResourceReject[] => [],
  )
  if (rejects.some((r) => r.reqId === pending)) {
    await kvRemove(pendingKey(spaceId)).catch(() => undefined)
    return { status: "none" }
  }
  return { status: "pending" }
}

/** Open a NEW support ticket. Refuses if one already exists (one ticket per space). */
export async function createSupportTicket(opts: {
  title: string
  message: string
}): Promise<void> {
  const current = await getSupportTicket()
  if (current.status === "open" || current.status === "pending") {
    throw new Error("A support ticket already exists for this OctoBot")
  }
  const cfg = await ensureConfigured()
  const session = await getSession()
  const { reqId, spaceId } = await submitTicketRequest(
    session,
    cfg.supportDeskRequestLink as string,
    { requester: DISPLAY_NAME, title: opts.title, message: opts.message },
  )
  await kvSet(pendingKey(spaceId), reqId)
}

/** Poll for desk acceptance of a pending ticket; returns the resolved state. */
export async function ensureJoined(): Promise<SupportTicketState> {
  return getSupportTicket()
}

// ── Conversation ─────────────────────────────────────────────────────────────────
// The requester is NOT a space member, so the desk object index (_index) is 403 by design.
// Enc mode is detected from the LOCAL per-node keyring cap (no server read, no 403): present
// ⇒ E2EE (build the encryptor only then); absent ⇒ plaintext (non-member requester default).

async function nodeContext(nodeId: string): Promise<{
  session: Session
  spaceId: string
  enc: NodeEncryptor
  client: ReturnType<typeof getNodeStreamClient>
  plaintext: boolean
}> {
  const session = await getSession()
  const spaceId = await deskSpaceId()
  // The desk _index is 403 for a non-member requester, so node.enc is unreadable. Detect the mode
  // from the LOCAL per-node keyring cap: present ⇒ E2EE, absent ⇒ plaintext (non-member default).
  // One-time keyring restore in case an E2EE grant is still pending in the inbox.
  if (!getNodeKeyringAccessEntry(spaceId, nodeId) && !keyringRestoreAttempted.has(nodeId)) {
    keyringRestoreAttempted.add(nodeId)
    const seen = await loadSeenReqIds(spaceId)
    const claimed = await claimGrantedNodes(session, { seenReqIds: seen }).catch((): ResourceGrant[] => [])
    await recordClaimedReqIds(spaceId, claimed)
  }
  const keyring = getNodeKeyringAccessEntry(spaceId, nodeId)
  let enc: NodeEncryptor = null
  if (keyring) {
    // E2EE ticket: attempt to build the encryptor from the server keyring.
    // A 403 here is structural (cap-scope mismatch) or the channel isn't ready yet — not a
    // reliable "ticket closed" signal. Degrade gracefully: enc = null keeps sends blocked
    // (SECURE_CHANNEL_NOT_READY) without permanently bricking the ticket.
    const access = await buildNodeAccess(session, spaceId, nodeId, { access: "invite", enc: true })
      .catch(() => null)
    enc = (access?.encryptor ?? null) as NodeEncryptor
  }
  const client = getNodeStreamClient(spaceId, nodeId, session)
  const plaintext = !keyring   // no keyring ⇒ legitimately plaintext; never leak on a keyring node
  return { session, spaceId, enc, client, plaintext }
}

/** Read the full ticket message history (decrypting E2EE entries; skipping the sealed header). */
export async function getThread(nodeId: string): Promise<TicketMessage[]> {
  const { session, spaceId, enc, client } = await nodeContext(nodeId)
  const res = await client
    .pull(objInvLogPull(spaceId, nodeId), { appendField: "items", full: true })
    .catch(() => null)
  if (!Array.isArray(res)) return []
  const items = res
  const out: TicketMessage[] = []
  for (const raw of items) {
    const payload = (raw as { data?: Record<string, unknown> }).data
    if (!payload) continue
    let env: Record<string, unknown> | null = null
    if (enc) {
      env = await enc.decrypt(payload).catch(() => null)
    } else {
      env = payload
    }
    if (!env || env.t !== "msg") continue // skip ticket-info headers and undecryptable entries
    const e = env.e as
      | {
          id?: string
          authorId?: string
          ts?: number
          text?: string
          attachment?: AttachmentRef
        }
      | undefined
    if (!e?.id || typeof e.authorId !== "string") continue
    out.push({
      id: e.id,
      authorId: e.authorId,
      ts: typeof e.ts === "number" ? e.ts : 0,
      text: typeof e.text === "string" ? e.text : "",
      attachment: e.attachment,
      fromMe: e.authorId === session.userId,
    })
  }
  out.sort((a, b) => a.ts - b.ts)
  return out
}

async function appendMessage(
  nodeId: string,
  body: { text: string; attachment?: AttachmentRef },
): Promise<void> {
  const { session, spaceId, enc, client, plaintext } = await nodeContext(nodeId)
  if (!enc && !plaintext) throw new Error(SECURE_CHANNEL_NOT_READY)
  const envelope = {
    t: "msg",
    e: {
      id: crypto.randomUUID(),
      authorId: session.userId,
      ts: Date.now(),
      text: body.text,
      ...(body.attachment ? { attachment: body.attachment } : {}),
    },
  }
  const out = enc
    ? await enc.encrypt(envelope as unknown as Record<string, unknown>)
    : (envelope as unknown as Record<string, unknown>)
  await client.append(objInvLogPush(spaceId, nodeId), out)
}

/** Post a text reply to the ticket. */
export async function sendMessage(nodeId: string, text: string): Promise<void> {
  await appendMessage(nodeId, { text })
}

/** Upload a file (or generated artifact) and post it as a message attachment. */
export async function sendAttachment(
  nodeId: string,
  file: { bytes: Uint8Array; name: string; mime: string },
  text = "",
): Promise<void> {
  const { spaceId, enc, client, plaintext } = await nodeContext(nodeId)
  if (!enc && !plaintext) throw new Error(SECURE_CHANNEL_NOT_READY)
  const ref = await uploadAttachment(
    client,
    enc ? (enc as unknown as ByteSealer) : null,
    spaceId,
    file.bytes,
    file.name,
    file.mime,
    nodeId,
  )
  await appendMessage(nodeId, { text, attachment: ref })
}

/** Download an attachment's bytes (decrypting for E2EE tickets). */
export async function fetchAttachment(
  nodeId: string,
  ref: AttachmentRef,
): Promise<Uint8Array> {
  const { spaceId, enc, client } = await nodeContext(nodeId)
  return loadAttachment(
    client,
    enc ? (enc as unknown as ByteSealer) : null,
    spaceId,
    ref,
    nodeId,
  )
}

/** Forget a single ticket node locally. The requester can't flip desk-side status, so this is
 * a local clear; a visible note is posted first (best-effort, E2EE-aware) so a support agent
 * can close it desk-side. The dismissal is durable (KV-backed): the SDK re-hydrates the cap
 * on every load from the requester's own _spaces doc, and getSupportTicket re-purges it. */
export async function closeTicket(nodeId: string): Promise<void> {
  if (!(await isSupportConfigured())) return
  const spaceId = await deskSpaceId()
  await appendMessage(nodeId, { text: CLOSED_BY_REQUESTER_NOTE }).catch(() => undefined)
  const dismissed = await loadDismissed(spaceId)
  dismissed.add(nodeId)
  await saveDismissed(spaceId, dismissed)
  removeNodeAccessEntry(spaceId, nodeId)
  await kvRemove(pendingKey(spaceId)).catch(() => undefined)
}
