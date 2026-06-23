import { describe, expect, it } from "vitest"

import { getLoopbackUrl } from "../secure-context"

describe("getLoopbackUrl", () => {
  it("maps 0.0.0.0 to 127.0.0.1, preserving port, path, query, hash", () => {
    expect(getLoopbackUrl("http://0.0.0.0:8000/app/setup?x=1#h")).toBe(
      "http://127.0.0.1:8000/app/setup?x=1#h",
    )
  })

  it("maps [::] to [::1]", () => {
    expect(getLoopbackUrl("http://[::]:8000/app")).toBe("http://[::1]:8000/app")
  })

  it("returns null for 127.0.0.1 (already secure loopback)", () => {
    expect(getLoopbackUrl("http://127.0.0.1:8000/app")).toBeNull()
  })

  it("returns null for localhost (already secure loopback)", () => {
    expect(getLoopbackUrl("http://localhost:8000/app")).toBeNull()
  })

  it("returns null for a real LAN IP (no safe local equivalent)", () => {
    expect(getLoopbackUrl("http://192.168.1.50:8000/app")).toBeNull()
  })

  it("returns null for HTTPS (already secure)", () => {
    expect(getLoopbackUrl("https://example.com/app")).toBeNull()
  })
})
