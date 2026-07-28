import { describe, expect, it } from "vitest"

import {
  buildOriginWithHostname,
  resolveExternalHostUrl,
  resolvePairingNodeHostname,
} from "@/lib/pairing"

describe("buildOriginWithHostname", () => {
  it("replaces hostname while preserving protocol and port", () => {
    expect(
      buildOriginWithHostname("http://localhost:8000", "192.168.0.10"),
    ).toBe("http://192.168.0.10:8000")
  })

  it("replaces hostname when origin has no explicit port", () => {
    expect(
      buildOriginWithHostname("https://localhost", "100.64.0.1"),
    ).toBe("https://100.64.0.1")
  })
})

describe("resolveExternalHostUrl", () => {
  it("returns full URLs unchanged", () => {
    expect(
      resolveExternalHostUrl("https://node.example.com", "http:"),
    ).toBe("https://node.example.com")
  })

  it("prefixes host-only values with the browser protocol", () => {
    expect(
      resolveExternalHostUrl("node.example.com:443", "https:"),
    ).toBe("https://node.example.com:443")
  })
})

describe("resolvePairingNodeHostname", () => {
  const browserOrigin = "http://localhost:8000"

  it("prefers Tailscale IP when both VPN and LAN IPs are available", () => {
    expect(
      resolvePairingNodeHostname("100.64.0.1", "192.168.0.10", browserOrigin),
    ).toBe("http://100.64.0.1:8000")
  })

  it("uses LAN IP when VPN IP is unavailable", () => {
    expect(
      resolvePairingNodeHostname(null, "192.168.0.10", browserOrigin),
    ).toBe("http://192.168.0.10:8000")
  })

  it("falls back to browser origin when both IPs are unavailable", () => {
    expect(resolvePairingNodeHostname(null, null, browserOrigin)).toBe(
      browserOrigin,
    )
  })
})
