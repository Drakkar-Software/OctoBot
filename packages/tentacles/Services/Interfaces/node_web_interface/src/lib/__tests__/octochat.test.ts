import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

// ── Stable mock function references ─────────────────────────────────────────
const mockPull = vi.fn()
const mockAppend = vi.fn()
const mockBuildNodeAccess = vi.fn()
const mockGetRequesterTicketForSpace = vi.fn()
const mockRemoveNodeAccessEntry = vi.fn()
const mockClaimGrantedNodes = vi.fn()
const mockGetNodeKeyringAccessEntry = vi.fn()
const mockScanResourceRejects = vi.fn()
const mockKvGet = vi.fn()
const mockKvSet = vi.fn()
const mockKvRemove = vi.fn()
const mockSubmitTicketRequest = vi.fn()
const mockLocalSpaceAccessEntries = vi.fn()

vi.mock("@drakkar.software/octochat-sdk", () => ({
  buildSession: vi.fn(async () => ({
    userId: "u-session",
    accountClient: {},
    spacesRegistryClient: {},
  })),
  ensureProfileKeys: vi.fn(async () => undefined),
  readSpaces: vi.fn(async () => ({ caps: {}, pubAccess: {} })),
  recoverSpaceAccess: vi.fn(async () => undefined),
  claimGrantedNodes: mockClaimGrantedNodes,
  getRequesterTicketForSpace: mockGetRequesterTicketForSpace,
  buildNodeAccess: mockBuildNodeAccess,
  getNodeKeyringAccessEntry: mockGetNodeKeyringAccessEntry,
  isTicketRoomId: vi.fn((id: string) => id.startsWith("ticket-")),
  localSpaceAccessEntries: mockLocalSpaceAccessEntries,
  scanResourceRejects: mockScanResourceRejects,
  getNodeStreamClient: vi.fn(() => ({ pull: mockPull, append: mockAppend })),
  objInvLogPull: vi.fn(
    (sp: string, n: string) => `/spaces/${sp}/objects/n/${n}/log`,
  ),
  objInvLogPush: vi.fn(
    (sp: string, n: string) => `/spaces/${sp}/objects/n/${n}/log`,
  ),
  decodeRequestLink: vi.fn(() => ({ spaceId: "sp-desk" })),
  configureOctoChat: vi.fn(),
  configureKv: vi.fn(),
  loadAttachment: vi.fn(),
  uploadAttachment: vi.fn(),
  removeNodeAccessEntry: mockRemoveNodeAccessEntry,
  submitTicketRequest: mockSubmitTicketRequest,
}))

vi.mock("@drakkar.software/octochat-sdk/platform", () => ({
  kvGet: mockKvGet,
  kvSet: mockKvSet,
  kvRemove: mockKvRemove,
}))

vi.mock("@/lib/device-key", () => ({
  loadPassword: vi.fn(async () => "pw"),
}))

vi.mock("@/lib/octochat-identity", () => ({
  getWalletBoundIdentity: vi.fn(async () => ({
    userId: "u-identity",
    keys: {},
  })),
}))

// ── Shared globals & config fetch ────────────────────────────────────────────
const fetchMock = vi.fn()

const CONFIG_RESPONSE = {
  ok: true,
  json: async () => ({
    syncBase: "https://sync.dev",
    syncNamespace: "octospaces",
    supportDeskRequestLink: "https://desk.dev/request?s=sp-desk",
    webBase: null,
  }),
}

beforeEach(() => {
  vi.resetModules()
  mockPull.mockReset().mockResolvedValue([])
  mockAppend.mockReset()
  mockBuildNodeAccess.mockReset()
  mockGetRequesterTicketForSpace.mockReset().mockResolvedValue(null)
  mockRemoveNodeAccessEntry.mockReset()
  mockClaimGrantedNodes.mockReset().mockResolvedValue([])
  mockGetNodeKeyringAccessEntry.mockReset().mockReturnValue(true)
  mockLocalSpaceAccessEntries.mockReset().mockReturnValue({})
  mockScanResourceRejects.mockReset().mockResolvedValue([])
  mockKvGet.mockReset().mockResolvedValue(null)
  mockKvSet.mockReset().mockResolvedValue(undefined)
  mockKvRemove.mockReset().mockResolvedValue(undefined)
  mockSubmitTicketRequest.mockReset().mockResolvedValue({ reqId: "new-req-id", spaceId: "sp-desk" })
  fetchMock.mockReset().mockResolvedValue(CONFIG_RESPONSE)
  vi.stubGlobal("fetch", fetchMock)
  vi.stubGlobal("localStorage", { getItem: vi.fn(() => "0xwallet") })
})

afterEach(() => {
  vi.unstubAllGlobals()
})

// ── Stateful access-store helper ─────────────────────────────────────────────
// Mirrors the SDK _cache so purgeDismissed / getRequesterTicketForSpace interact
// correctly in tests: removeNodeAccessEntry deletes the content/:stream/:keyring keys;
// localSpaceAccessEntries and getRequesterTicketForSpace both read the same object.
function makeAccessStore(initial: Record<string, object> = {}) {
  const store: Record<string, object> = { ...initial }
  return {
    entries: () => store,
    remove: (spaceId: string, nodeId: string) => {
      delete store[`${spaceId}:${nodeId}`]
      delete store[`${spaceId}:${nodeId}:stream`]
      delete store[`${spaceId}:${nodeId}:keyring`]
    },
    getTicket: async (
      _session: unknown,
      spaceId: string,
    ): Promise<{ nodeId: string; title: string } | null> => {
      const prefix = `${spaceId}:`
      const ids = Object.keys(store)
        .filter((k) => k.startsWith(prefix))
        .map((k) => k.slice(prefix.length))
        .filter((id) => !id.includes(":") && id.startsWith("ticket-"))
        .sort()
      return ids.length ? { nodeId: ids[0], title: "" } : null
    },
  }
}

// ─────────────────────────────────────────────────────────────────────────────

describe("getThread", () => {
  it("passes { appendField: 'items', full: true } to client.pull (400 regression guard)", async () => {
    mockBuildNodeAccess.mockResolvedValue({ encryptor: null })
    const msg = {
      t: "msg",
      e: { id: "m1", authorId: "u-other", ts: 1000, text: "Hello" },
    }
    mockPull.mockResolvedValue([{ ts: 1000, data: msg }])

    const { getThread } = await import("@/lib/octochat")
    const messages = await getThread("ticket-1")

    expect(mockPull).toHaveBeenCalledWith(
      expect.any(String),
      { appendField: "items", full: true },
    )
    expect(messages).toHaveLength(1)
    expect(messages[0].text).toBe("Hello")
    expect(messages[0].id).toBe("m1")
  })

  it("decrypts item.data (not item) when encryptor is present", async () => {
    const env = { t: "msg", e: { id: "m1", authorId: "u-other", ts: 1000, text: "Hi" } }
    const mockDecrypt = vi.fn(async () => env)
    // Default keyring true + buildNodeAccess returning an encryptor ⇒ E2EE path
    mockBuildNodeAccess.mockResolvedValue({
      encryptor: { decrypt: mockDecrypt, encrypt: vi.fn() },
    })
    mockPull.mockResolvedValue([{ ts: 1000, data: { ct: "cipher" } }])

    const { getThread } = await import("@/lib/octochat")
    const messages = await getThread("ticket-1")

    expect(mockDecrypt).toHaveBeenCalledWith({ ct: "cipher" })
    expect(messages).toHaveLength(1)
    expect(messages[0].text).toBe("Hi")
  })

  it("returns [] when the pull fails", async () => {
    mockBuildNodeAccess.mockResolvedValue({ encryptor: null })
    mockPull.mockRejectedValue(new Error("network"))

    const { getThread } = await import("@/lib/octochat")
    const messages = await getThread("ticket-1")

    expect(messages).toEqual([])
  })

  it("returns [] when buildNodeAccess rejects (keyring 403) — channel not ready, never archived", async () => {
    // E2EE ticket: keyring cap 403s (structural cap-scope bug or propagation delay).
    // enc becomes null; thread is empty but ticket is NOT archived.
    mockBuildNodeAccess.mockRejectedValue(new Error("403 Forbidden"))
    mockPull.mockResolvedValue([])

    const { getThread } = await import("@/lib/octochat")
    const messages = await getThread("ticket-1")

    expect(messages).toEqual([])
    // No archived-tickets KV must be written
    expect(mockKvSet).not.toHaveBeenCalledWith(
      expect.stringContaining("archived-tickets"),
      expect.any(String),
    )
  })

  it("returns [] on a log-pull error without writing archived KV", async () => {
    mockBuildNodeAccess.mockResolvedValue({ encryptor: null })
    mockPull.mockRejectedValue(new Error("503 Service Unavailable"))

    const { getThread } = await import("@/lib/octochat")
    const messages = await getThread("ticket-1")

    expect(messages).toEqual([])
    expect(mockKvSet).not.toHaveBeenCalledWith(
      expect.stringContaining("archived-tickets"),
      expect.any(String),
    )
  })
})

// ─────────────────────────────────────────────────────────────────────────────

describe("sendMessage", () => {
  it("sends plaintext envelope when ticket has no keyring cap (regression: message not sent)", async () => {
    mockGetNodeKeyringAccessEntry.mockReturnValue(false)
    mockAppend.mockResolvedValue(undefined)

    const { sendMessage } = await import("@/lib/octochat")
    await sendMessage("ticket-1", "hi")

    expect(mockBuildNodeAccess).not.toHaveBeenCalled()
    expect(mockAppend).toHaveBeenCalledTimes(1)
    const appended = mockAppend.mock.calls[0][1] as { t: string; e: { text: string } }
    expect(appended.t).toBe("msg")
    expect(appended.e.text).toBe("hi")
  })

  it("throws SECURE_CHANNEL_NOT_READY for an E2EE ticket with no encryptor (never leak)", async () => {
    // Default keyring true + buildNodeAccess returns null ⇒ enc = null, plaintext = false
    mockBuildNodeAccess.mockResolvedValue(null)

    const { sendMessage } = await import("@/lib/octochat")
    await expect(sendMessage("ticket-1", "hi")).rejects.toThrow(
      "Support chat isn't ready yet",
    )
    expect(mockAppend).not.toHaveBeenCalled()
  })

  it("throws SECURE_CHANNEL_NOT_READY when buildNodeAccess rejects (keyring 403)", async () => {
    // E2EE ticket whose keyring still 403s → enc = null, plaintext = false → "not ready"
    mockBuildNodeAccess.mockRejectedValue(new Error("403 Forbidden"))

    const { sendMessage } = await import("@/lib/octochat")
    await expect(sendMessage("ticket-1", "hi")).rejects.toThrow(
      "Support chat isn't ready yet",
    )
    expect(mockAppend).not.toHaveBeenCalled()
  })

  it("encrypts and appends when E2EE ticket has an encryptor", async () => {
    const encrypted = { ct: "sealed" }
    const mockEncrypt = vi.fn(async () => encrypted)
    // Default keyring true + encryptor present ⇒ E2EE path
    mockBuildNodeAccess.mockResolvedValue({
      encryptor: { encrypt: mockEncrypt, decrypt: vi.fn() },
    })
    mockAppend.mockResolvedValue(undefined)

    const { sendMessage } = await import("@/lib/octochat")
    await sendMessage("ticket-1", "secret")

    expect(mockEncrypt).toHaveBeenCalledTimes(1)
    expect(mockAppend).toHaveBeenCalledWith(expect.any(String), encrypted)
  })
})

// ─────────────────────────────────────────────────────────────────────────────

describe("closeTicket", () => {
  it("removes local access entry and clears the pending key", async () => {
    mockGetNodeKeyringAccessEntry.mockReturnValue(null) // plaintext mode
    mockAppend.mockResolvedValue(undefined)

    const { closeTicket } = await import("@/lib/octochat")
    await closeTicket("ticket-1")

    expect(mockRemoveNodeAccessEntry).toHaveBeenCalledWith("sp-desk", "ticket-1")
    expect(mockRemoveNodeAccessEntry).not.toHaveBeenCalledWith("sp-desk", "ticket-2")
    expect(mockKvRemove).toHaveBeenCalledWith(expect.stringContaining("pending"))
  })

  it("does not call claimGrantedNodes (no re-claim on close)", async () => {
    // Use default keyring=true so the nodeContext keyring-restore branch is skipped.
    // buildNodeAccess returns undefined → enc=null, plaintext=false → appendMessage throws
    // SECURE_CHANNEL_NOT_READY → caught silently by closeTicket. claimGrantedNodes never runs.
    const { closeTicket } = await import("@/lib/octochat")
    await closeTicket("ticket-1")

    expect(mockClaimGrantedNodes).not.toHaveBeenCalled()
  })

  it("posts a visible close note to the thread before removing local access", async () => {
    // Use plaintext mode (no keyring) so appendMessage reaches client.append
    mockGetNodeKeyringAccessEntry.mockReturnValue(null)
    mockAppend.mockResolvedValue(undefined)

    const { closeTicket } = await import("@/lib/octochat")
    await closeTicket("ticket-1")

    // Note must be posted before the local access entry is removed
    const appendOrder = mockAppend.mock.invocationCallOrder[0]
    const removeOrder = mockRemoveNodeAccessEntry.mock.invocationCallOrder[0]
    expect(appendOrder).toBeLessThan(removeOrder)

    expect(mockAppend).toHaveBeenCalledWith(
      expect.any(String),
      expect.objectContaining({ e: expect.objectContaining({ text: "Closed by the requester from OctoBot." }) }),
    )
  })

  it("records the dismissed nodeId to KV before clearing local access (durable on reload)", async () => {
    mockGetNodeKeyringAccessEntry.mockReturnValue(null) // plaintext → appendMessage reaches append
    mockAppend.mockResolvedValue(undefined)

    const { closeTicket } = await import("@/lib/octochat")
    await closeTicket("ticket-1")

    expect(mockKvSet).toHaveBeenCalledWith(
      expect.stringContaining("dismissed:"),
      expect.stringContaining("ticket-1"),
    )
    const dismissedCall = mockKvSet.mock.calls.find((args: string[]) =>
      args[0].includes("dismissed"),
    )
    const dismissedOrder = mockKvSet.mock.invocationCallOrder[
      mockKvSet.mock.calls.indexOf(dismissedCall ?? [])
    ]
    const removeOrder = mockRemoveNodeAccessEntry.mock.invocationCallOrder[0]
    expect(dismissedOrder).toBeLessThan(removeOrder)
  })

  it("merges the new nodeId into any existing dismissed set (additive, no overwrite)", async () => {
    mockGetNodeKeyringAccessEntry.mockReturnValue(null)
    mockAppend.mockResolvedValue(undefined)
    mockKvGet.mockImplementation((key: string) => {
      if (key.includes("dismissed")) return Promise.resolve(JSON.stringify(["ticket-1"]))
      return Promise.resolve(null)
    })

    const { closeTicket } = await import("@/lib/octochat")
    await closeTicket("ticket-2")

    const dismissedCall = mockKvSet.mock.calls.find((args: string[]) =>
      args[0].includes("dismissed"),
    )
    expect(dismissedCall?.[1]).toContain("ticket-1")
    expect(dismissedCall?.[1]).toContain("ticket-2")
  })
})

// ─────────────────────────────────────────────────────────────────────────────

describe("getSupportTicket", () => {
  it("returns 'open' when ticket exists locally (desk-side status unreadable, always open)", async () => {
    mockGetRequesterTicketForSpace.mockResolvedValue({
      nodeId: "n-ticket",
      title: "My issue",
    })
    mockLocalSpaceAccessEntries.mockReturnValue({ "sp-desk:n-ticket": {} })

    const { getSupportTicket } = await import("@/lib/octochat")
    const state = await getSupportTicket()

    expect(state.status).toBe("open")
    expect(mockRemoveNodeAccessEntry).not.toHaveBeenCalled()
    expect(mockKvRemove).toHaveBeenCalledWith(
      expect.stringContaining("pending"),
    )
  })

  it("returns 'open' even when the desk has closed the ticket (status not observable by requester)", async () => {
    mockGetRequesterTicketForSpace.mockResolvedValue({
      nodeId: "n-ticket",
      title: "My issue",
    })
    mockLocalSpaceAccessEntries.mockReturnValue({ "sp-desk:n-ticket": {} })

    const { getSupportTicket } = await import("@/lib/octochat")
    const state = await getSupportTicket()

    expect(state.status).toBe("open")
    expect(mockRemoveNodeAccessEntry).not.toHaveBeenCalled()
  })

  it("returns 'open' when ticket exists but encryptor is not available (status independent of encryptor)", async () => {
    mockGetRequesterTicketForSpace.mockResolvedValue({
      nodeId: "n-ticket",
      title: "",
    })
    mockLocalSpaceAccessEntries.mockReturnValue({ "sp-desk:n-ticket": {} })
    mockBuildNodeAccess.mockResolvedValue(null)

    const { getSupportTicket } = await import("@/lib/octochat")
    const state = await getSupportTicket()

    expect(state.status).toBe("open")
    expect(mockRemoveNodeAccessEntry).not.toHaveBeenCalled()
  })

  it("returns allTickets from the local node-access store (no separate open-tickets list)", async () => {
    mockGetRequesterTicketForSpace.mockResolvedValue({
      nodeId: "ticket-1",
      title: "First issue",
    })
    // localTicketNodeIds reads localSpaceAccessEntries — this is the source of truth
    mockLocalSpaceAccessEntries.mockReturnValue({
      "sp-desk:ticket-1": {},
      "sp-desk:ticket-2": {},
    })
    mockKvGet.mockImplementation((key: string) => {
      if (key.includes("title") && key.includes("ticket-2"))
        return Promise.resolve("Second issue")
      return Promise.resolve(null)
    })

    const { getSupportTicket } = await import("@/lib/octochat")
    const state = await getSupportTicket()

    expect(state.status).toBe("open")
    if (state.status === "open") {
      expect(state.allTickets).toHaveLength(2)
      expect(state.allTickets[0]).toEqual({ nodeId: "ticket-1", title: "First issue" })
      expect(state.allTickets[1]).toEqual({ nodeId: "ticket-2", title: "Second issue" })
    }
  })

  it("does not call claimGrantedNodes when a ticket already exists locally", async () => {
    mockGetRequesterTicketForSpace.mockResolvedValue({
      nodeId: "n-ticket",
      title: "My issue",
    })
    mockLocalSpaceAccessEntries.mockReturnValue({ "sp-desk:n-ticket": {} })

    const { getSupportTicket } = await import("@/lib/octochat")
    await getSupportTicket()

    expect(mockClaimGrantedNodes).not.toHaveBeenCalled()
  })

  it("calls claimGrantedNodes when no ticket exists locally (newly accepted grant)", async () => {
    mockGetRequesterTicketForSpace
      .mockResolvedValueOnce(null)
      .mockResolvedValueOnce({ nodeId: "n-new", title: "New" })
    mockLocalSpaceAccessEntries.mockReturnValue({ "sp-desk:n-new": {} })

    const { getSupportTicket } = await import("@/lib/octochat")
    const state = await getSupportTicket()

    expect(mockClaimGrantedNodes).toHaveBeenCalledTimes(1)
    expect(state.status).toBe("open")
  })

  it("persists a claimed grant's reqId to the seen-grants ledger", async () => {
    mockGetRequesterTicketForSpace
      .mockResolvedValueOnce(null)
      .mockResolvedValueOnce({ nodeId: "ticket-1", title: "Issue" })
    mockClaimGrantedNodes.mockResolvedValue([
      { v: 1, kind: "grant", reqId: "req-123", spaceId: "sp-desk", nodeId: "ticket-1", bundle: "" },
    ])
    mockLocalSpaceAccessEntries.mockReturnValue({ "sp-desk:ticket-1": {} })

    const { getSupportTicket } = await import("@/lib/octochat")
    await getSupportTicket()

    expect(mockKvSet).toHaveBeenCalledWith(
      expect.stringContaining("seen-grants:"),
      expect.stringContaining("req-123"),
    )
  })

  it("clears pendingKey and returns 'none' when the desk declines the ticket", async () => {
    mockGetRequesterTicketForSpace.mockResolvedValue(null)
    mockKvGet.mockImplementation((key: string) => {
      if (key.includes("pending")) return Promise.resolve("r-1")
      return Promise.resolve(null)
    })
    mockScanResourceRejects.mockResolvedValue([{ v: 1, kind: "reject", reqId: "r-1" }])

    const { getSupportTicket } = await import("@/lib/octochat")
    const state = await getSupportTicket()

    expect(state.status).toBe("none")
    expect(mockKvRemove).toHaveBeenCalledWith(expect.stringContaining("pending"))
  })

  it("stays 'pending' when a pending key exists but no matching reject is found", async () => {
    mockGetRequesterTicketForSpace.mockResolvedValue(null)
    mockKvGet.mockImplementation((key: string) => {
      if (key.includes("pending")) return Promise.resolve("r-1")
      return Promise.resolve(null)
    })
    mockScanResourceRejects.mockResolvedValue([])

    const { getSupportTicket } = await import("@/lib/octochat")
    const state = await getSupportTicket()

    expect(state.status).toBe("pending")
    expect(mockKvRemove).not.toHaveBeenCalledWith(expect.stringContaining("pending"))
  })

  // ── Dismissed-set / hydrate-resurrection tests ──────────────────────────────

  it("suppresses a ticket re-hydrated by recoverSpaceAccess when it is in the dismissed set", async () => {
    // Simulate recoverSpaceAccess re-adding a previously closed ticket to the local store
    const store = makeAccessStore({ "sp-desk:ticket-1": {} })
    mockLocalSpaceAccessEntries.mockImplementation(() => store.entries())
    mockRemoveNodeAccessEntry.mockImplementation((sp: string, id: string) => store.remove(sp, id))
    mockGetRequesterTicketForSpace.mockImplementation((_: unknown, sp: string) =>
      store.getTicket(_, sp),
    )
    mockKvGet.mockImplementation((key: string) => {
      if (key.includes("dismissed")) return Promise.resolve(JSON.stringify(["ticket-1"]))
      return Promise.resolve(null)
    })

    const { getSupportTicket } = await import("@/lib/octochat")
    const state = await getSupportTicket()

    expect(mockRemoveNodeAccessEntry).toHaveBeenCalledWith("sp-desk", "ticket-1")
    expect(store.entries()["sp-desk:ticket-1"]).toBeUndefined()
    expect(state.status).toBe("none")
  })

  it("suppresses a dismissed ticket re-added by claimGrantedNodes (second purgeDismissed)", async () => {
    // Store starts empty; dismissed = ticket-1; claimGrantedNodes "accepts" the grant and
    // re-adds the entry to the store (simulating acceptNodeInvite). The second purgeDismissed
    // must remove it again before getRequesterTicketForSpace is called the second time.
    const store = makeAccessStore({})
    mockLocalSpaceAccessEntries.mockImplementation(() => store.entries())
    mockRemoveNodeAccessEntry.mockImplementation((sp: string, id: string) => store.remove(sp, id))
    mockGetRequesterTicketForSpace.mockImplementation((_: unknown, sp: string) =>
      store.getTicket(_, sp),
    )
    mockKvGet.mockImplementation((key: string) => {
      if (key.includes("dismissed")) return Promise.resolve(JSON.stringify(["ticket-1"]))
      return Promise.resolve(null)
    })
    mockClaimGrantedNodes.mockImplementation(async () => {
      store.entries()["sp-desk:ticket-1"] = {} // simulate acceptNodeInvite side effect
      return [{ v: 1, kind: "grant", reqId: "req-1", spaceId: "sp-desk", nodeId: "ticket-1", bundle: "" }]
    })

    const { getSupportTicket } = await import("@/lib/octochat")
    const state = await getSupportTicket()

    expect(mockRemoveNodeAccessEntry).toHaveBeenCalledWith("sp-desk", "ticket-1")
    expect(store.entries()["sp-desk:ticket-1"]).toBeUndefined()
    expect(state.status).toBe("none")
  })

  it("shows only non-dismissed tickets when the local store has both dismissed and active", async () => {
    // Both ticket-1 (dismissed) and ticket-2 (active) are re-hydrated into the local store
    const store = makeAccessStore({ "sp-desk:ticket-1": {}, "sp-desk:ticket-2": {} })
    mockLocalSpaceAccessEntries.mockImplementation(() => store.entries())
    mockRemoveNodeAccessEntry.mockImplementation((sp: string, id: string) => store.remove(sp, id))
    mockGetRequesterTicketForSpace.mockImplementation((_: unknown, sp: string) =>
      store.getTicket(_, sp),
    )
    mockKvGet.mockImplementation((key: string) => {
      if (key.includes("dismissed")) return Promise.resolve(JSON.stringify(["ticket-1"]))
      return Promise.resolve(null)
    })

    const { getSupportTicket } = await import("@/lib/octochat")
    const state = await getSupportTicket()

    expect(mockRemoveNodeAccessEntry).toHaveBeenCalledWith("sp-desk", "ticket-1")
    expect(store.entries()["sp-desk:ticket-1"]).toBeUndefined()
    expect(state.status).toBe("open")
    if (state.status === "open") {
      expect(state.nodeId).toBe("ticket-2")
      expect(state.allTickets).toHaveLength(1)
      expect(state.allTickets[0].nodeId).toBe("ticket-2")
    }
  })
})

// ─────────────────────────────────────────────────────────────────────────────

describe("createSupportTicket", () => {
  it("submits a ticket request and stores the pending reqId (happy path)", async () => {
    // No existing ticket, no pending key
    mockGetRequesterTicketForSpace.mockResolvedValue(null)
    mockKvGet.mockResolvedValue(null)

    const { createSupportTicket } = await import("@/lib/octochat")
    await createSupportTicket({ title: "New issue", message: "Help needed" })

    expect(mockSubmitTicketRequest).toHaveBeenCalledTimes(1)
    expect(mockKvSet).toHaveBeenCalledWith(
      expect.stringContaining("pending"),
      "new-req-id",
    )
  })
})
