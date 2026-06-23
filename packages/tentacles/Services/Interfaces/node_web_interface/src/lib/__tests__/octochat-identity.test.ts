import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

vi.mock("@drakkar.software/octochat-sdk", () => ({
  clearSpaceAccessStore: vi.fn(),
}))
vi.mock("@drakkar.software/octochat-sdk/platform", () => ({
  kvRemove: vi.fn(async () => undefined),
}))
vi.mock("@drakkar.software/starfish-identities", () => ({
  deriveRootIdentityFromEvmSignature: vi.fn(),
}))
vi.mock("@/lib/device-key", () => ({
  loadOctoChatKeys: vi.fn(),
  saveOctoChatKeys: vi.fn(),
}))

import { clearSpaceAccessStore } from "@drakkar.software/octochat-sdk"
import { kvRemove } from "@drakkar.software/octochat-sdk/platform"
import { deriveRootIdentityFromEvmSignature } from "@drakkar.software/starfish-identities"
import { loadOctoChatKeys, saveOctoChatKeys } from "@/lib/device-key"
import {
  getWalletBoundIdentity,
  hexToBytes,
  OCTOCHAT_IDENTITY_CHALLENGE,
} from "@/lib/octochat-identity"

const mockedClearSpaceAccessStore = vi.mocked(clearSpaceAccessStore)
const mockedKvRemove = vi.mocked(kvRemove)

const mockedDerive = vi.mocked(deriveRootIdentityFromEvmSignature)
const mockedLoad = vi.mocked(loadOctoChatKeys)
const mockedSave = vi.mocked(saveOctoChatKeys)
const fetchMock = vi.fn()
const authHeader = vi.fn(async () => "Basic dXNlcjpwdw==")

const KEYS = {
  edPriv: "ed-priv",
  edPub: "ed-pub",
  kemPriv: "kem-priv",
  kemPub: "kem-pub",
}

function identityResponse(address: string, signature: string): Response {
  return {
    ok: true,
    status: 200,
    json: async () => ({ address, signature }),
  } as unknown as Response
}

beforeEach(() => {
  mockedDerive
    .mockReset()
    .mockResolvedValue({ userId: "u-1", keys: KEYS } as never)
  mockedLoad.mockReset().mockResolvedValue(null)
  mockedSave.mockReset().mockResolvedValue(undefined)
  mockedClearSpaceAccessStore.mockReset()
  mockedKvRemove.mockReset().mockResolvedValue(undefined)
  fetchMock.mockReset()
  authHeader.mockClear()
  vi.stubGlobal("localStorage", { getItem: vi.fn(() => "0xWALLET") })
  vi.stubGlobal("fetch", fetchMock)
})

afterEach(() => {
  vi.unstubAllGlobals()
})

describe("hexToBytes", () => {
  it("decodes hex with and without a 0x prefix", () => {
    expect(Array.from(hexToBytes("0x0a0b10"))).toEqual([10, 11, 16])
    expect(Array.from(hexToBytes("0a0b10"))).toEqual([10, 11, 16])
  })
})

describe("getWalletBoundIdentity", () => {
  it("derives from the wallet signature and caches it keyed by address", async () => {
    fetchMock.mockResolvedValue(identityResponse("0xWalleT", "0xabcd"))

    const identity = await getWalletBoundIdentity(authHeader)

    expect(identity).toEqual({ userId: "u-1", keys: KEYS })
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/config/octochat-identity",
      expect.objectContaining({
        headers: { Authorization: "Basic dXNlcjpwdw==" },
      }),
    )
    expect(mockedDerive).toHaveBeenCalledTimes(1)
    const arg = mockedDerive.mock.calls[0][0]
    expect(arg.address).toBe("0xWalleT")
    expect(arg.challenge).toBe(OCTOCHAT_IDENTITY_CHALLENGE)
    expect(Array.from(arg.signature)).toEqual([0xab, 0xcd])
    // cached lowercased by address
    const saved = JSON.parse(mockedSave.mock.calls[0][0])
    expect(saved).toEqual({ address: "0xwallet", userId: "u-1", keys: KEYS })
  })

  it("returns the cached identity for the same wallet without re-deriving", async () => {
    mockedLoad.mockResolvedValue(
      JSON.stringify({ address: "0xwallet", userId: "u-1", keys: KEYS }),
    )

    const identity = await getWalletBoundIdentity(authHeader)

    expect(identity).toEqual({ userId: "u-1", keys: KEYS })
    expect(fetchMock).not.toHaveBeenCalled()
    expect(mockedDerive).not.toHaveBeenCalled()
  })

  it("re-derives when the cached identity belongs to a different wallet", async () => {
    mockedLoad.mockResolvedValue(
      JSON.stringify({ address: "0xother", userId: "old", keys: KEYS }),
    )
    fetchMock.mockResolvedValue(identityResponse("0xWALLET", "0x01"))

    await getWalletBoundIdentity(authHeader)

    expect(fetchMock).toHaveBeenCalledTimes(1)
    expect(mockedDerive).toHaveBeenCalledTimes(1)
  })

  it("clears the previous identity's space-access store when the wallet changes", async () => {
    mockedLoad.mockResolvedValue(
      JSON.stringify({ address: "0xother", userId: "old-user-id", keys: KEYS }),
    )
    fetchMock.mockResolvedValue(identityResponse("0xWALLET", "0x01"))

    await getWalletBoundIdentity(authHeader)

    expect(mockedClearSpaceAccessStore).toHaveBeenCalledOnce()
    expect(mockedKvRemove).toHaveBeenCalledWith(
      "octospaces.spaceaccess.old-user-id",
    )
  })

  it("does not clear the space-access store on a cache hit for the same wallet", async () => {
    mockedLoad.mockResolvedValue(
      JSON.stringify({ address: "0xwallet", userId: "u-1", keys: KEYS }),
    )

    await getWalletBoundIdentity(authHeader)

    expect(mockedClearSpaceAccessStore).not.toHaveBeenCalled()
    expect(mockedKvRemove).not.toHaveBeenCalled()
  })

  it("throws when the identity endpoint fails", async () => {
    fetchMock.mockResolvedValue({ ok: false, status: 401 } as Response)
    await expect(getWalletBoundIdentity(authHeader)).rejects.toThrow(/401/)
    expect(mockedDerive).not.toHaveBeenCalled()
  })
})
