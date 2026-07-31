import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

vi.mock("@/lib/device-key", () => ({
  loadPassword: vi.fn(),
}))

import { loadPassword } from "@/lib/device-key"
import { buildAuthHeader, fetchNodeConfig } from "@/lib/node-config"

const mockedLoadPassword = vi.mocked(loadPassword)
const fetchMock = vi.fn()

beforeEach(() => {
  mockedLoadPassword.mockReset().mockResolvedValue("pw")
  fetchMock.mockReset()
  vi.stubGlobal("fetch", fetchMock)
})

afterEach(() => {
  vi.unstubAllGlobals()
})

describe("buildAuthHeader", () => {
  it("throws instead of authenticating as a fabricated 'node' user when no session exists", async () => {
    // Regression test for https://github.com/Drakkar-Software/OctoBot/issues/3593:
    // falling back to a literal "node" username sent Basic auth for a wallet
    // that doesn't exist, which the server rejected as "Incorrect address or
    // passphrase" — surfacing as an unexpected auth failure right after setup.
    vi.stubGlobal("localStorage", { getItem: vi.fn(() => null) })
    await expect(buildAuthHeader()).rejects.toThrow("No active wallet session")
  })

  it("throws instead of sending an empty password when the wallet address is known but the device-stored password is missing", async () => {
    // Regression test for the reporter's actual state in #3593: a wallet address
    // is stored (setup completed) but the IndexedDB password never landed. This
    // previously sent `Basic address:` and the server rejected it as
    // "Incorrect address or passphrase" — same confusing message, different cause.
    vi.stubGlobal("localStorage", { getItem: vi.fn(() => "0xwallet") })
    mockedLoadPassword.mockResolvedValue(null)
    await expect(buildAuthHeader()).rejects.toThrow("No active wallet session")
  })

  it("builds a Basic header from the stored wallet address and password", async () => {
    vi.stubGlobal("localStorage", { getItem: vi.fn(() => "0xwallet") })
    const header = await buildAuthHeader()
    expect(header).toBe(`Basic ${btoa("0xwallet:pw")}`)
  })
})

describe("fetchNodeConfig", () => {
  it("propagates the no-session error instead of calling the API", async () => {
    vi.stubGlobal("localStorage", { getItem: vi.fn(() => null) })
    await expect(fetchNodeConfig()).rejects.toThrow("No active wallet session")
    expect(fetchMock).not.toHaveBeenCalled()
  })

  it("sends the Basic auth header when a session exists", async () => {
    vi.stubGlobal("localStorage", { getItem: vi.fn(() => "0xwallet") })
    fetchMock.mockResolvedValue({
      json: async () => ({ external_host: null }),
    })
    await fetchNodeConfig()
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/nodes/config",
      expect.objectContaining({
        headers: { Authorization: `Basic ${btoa("0xwallet:pw")}` },
      }),
    )
  })
})
