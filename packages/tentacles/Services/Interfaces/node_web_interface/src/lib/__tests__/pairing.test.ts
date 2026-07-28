import { describe, expect, it } from "vitest"

import {
  buildOriginWithHostname,
  pairingSecretFromWallet,
  resolveExternalHostUrl,
  resolvePairingNodeHostname,
} from "@/lib/pairing"

describe("pairingSecretFromWallet", () => {
  const KEY = "4c0883a69102937d6231471b5dbb6204fe5129617082792ae468d01a3f362318"
  const SEED =
    "legal winner thank year wave sausage worth useful legal winner thank yellow"

  it("prefers the mnemonic when the wallet has one", () => {
    expect(pairingSecretFromWallet({ private_key: KEY, seed: SEED })).toBe(SEED)
  })

  it("0x-prefixes a raw private key, which storage saves bare", () => {
    // Without the prefix a scanner reads the key as a seed phrase and rejects
    // it, so every mnemonic-less node would fail to pair.
    expect(pairingSecretFromWallet({ private_key: KEY })).toBe(`0x${KEY}`)
  })

  it("leaves an already-prefixed key alone", () => {
    expect(pairingSecretFromWallet({ private_key: `0x${KEY}` })).toBe(`0x${KEY}`)
  })

  it("falls back to the key when seed is null or empty", () => {
    expect(pairingSecretFromWallet({ private_key: KEY, seed: null })).toBe(`0x${KEY}`)
    expect(pairingSecretFromWallet({ private_key: KEY, seed: "" })).toBe(`0x${KEY}`)
  })
})

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
