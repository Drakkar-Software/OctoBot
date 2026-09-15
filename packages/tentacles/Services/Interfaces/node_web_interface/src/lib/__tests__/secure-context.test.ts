import { describe, expect, it } from "vitest"

import {
  buildHttpsNodeUrlFromHostname,
  buildSameComputerLoopbackUrl,
  buildTailscaleServeCommand,
  getLoopbackUrl,
  getNodeUiPortFromHref,
  parseMagicDnsHostnameInput,
} from "../secure-context"
import {
  MAGIC_DNS_BAD_CHARACTERS,
  MAGIC_DNS_ENTER_NAME,
  MAGIC_DNS_INVALID_SHAPE,
  MAGIC_DNS_REMOVE_SPACES,
  MAGIC_DNS_TRAILING_INVALID,
} from "../ui-recovery-constants"

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

describe("buildSameComputerLoopbackUrl", () => {
  it("maps 0.0.0.0 like getLoopbackUrl", () => {
    expect(buildSameComputerLoopbackUrl("http://0.0.0.0:8000/app")).toBe(
      "http://127.0.0.1:8000/app",
    )
  })

  it("rewrites LAN IP to 127.0.0.1 preserving port and path", () => {
    expect(buildSameComputerLoopbackUrl("http://192.168.1.50:8000/app/setup?x=1#h")).toBe(
      "http://127.0.0.1:8000/app/setup?x=1#h",
    )
  })
})

describe("parseMagicDnsHostnameInput", () => {
  it("accepts trimmed hostname", () => {
    expect(parseMagicDnsHostnameInput("  my-pc.tailnet.ts.net  ")).toEqual({
      ok: true,
      hostname: "my-pc.tailnet.ts.net",
    })
  })

  it("accepts https URL with path", () => {
    expect(parseMagicDnsHostnameInput("https://my-pc.tailnet.ts.net/app")).toEqual({
      ok: true,
      hostname: "my-pc.tailnet.ts.net",
    })
  })

  it("accepts https URL with path and query", () => {
    expect(parseMagicDnsHostnameInput("https://my-pc.tailnet.ts.net/app?x=1")).toEqual({
      ok: true,
      hostname: "my-pc.tailnet.ts.net",
    })
  })

  it("accepts host with path segment", () => {
    expect(parseMagicDnsHostnameInput("my-pc.tailnet.ts.net/some/path")).toEqual({
      ok: true,
      hostname: "my-pc.tailnet.ts.net",
    })
  })

  it("accepts host with port", () => {
    expect(parseMagicDnsHostnameInput("my-pc.tailnet.ts.net:443")).toEqual({
      ok: true,
      hostname: "my-pc.tailnet.ts.net",
    })
  })

  it("rejects empty input", () => {
    expect(parseMagicDnsHostnameInput("")).toEqual({
      ok: false,
      message: MAGIC_DNS_ENTER_NAME,
    })
  })

  it("rejects internal spaces", () => {
    expect(parseMagicDnsHostnameInput("my pc.tailnet.ts.net")).toEqual({
      ok: false,
      message: MAGIC_DNS_REMOVE_SPACES,
    })
  })

  it("rejects hostname without a dot", () => {
    expect(parseMagicDnsHostnameInput("localhost")).toEqual({
      ok: false,
      message: MAGIC_DNS_INVALID_SHAPE,
    })
  })

  it("rejects trailing dot", () => {
    expect(parseMagicDnsHostnameInput("my-pc.tailnet.ts.net.")).toEqual({
      ok: false,
      message: MAGIC_DNS_TRAILING_INVALID,
    })
  })

  it("rejects trailing hyphen", () => {
    expect(parseMagicDnsHostnameInput("my-pc.tailnet.ts.net-")).toEqual({
      ok: false,
      message: MAGIC_DNS_TRAILING_INVALID,
    })
  })

  it("rejects invalid characters", () => {
    expect(parseMagicDnsHostnameInput("bad@host.ts.net")).toEqual({
      ok: false,
      message: MAGIC_DNS_BAD_CHARACTERS,
    })
  })
})

describe("buildHttpsNodeUrlFromHostname", () => {
  it("builds https URL with path from current href", () => {
    expect(
      buildHttpsNodeUrlFromHostname(
        "my-pc.tailnet.ts.net",
        "http://192.168.0.1:8000/app/setup?x=1#tab",
      ),
    ).toBe("https://my-pc.tailnet.ts.net/app/setup?x=1#tab")
  })
})

describe("getNodeUiPortFromHref", () => {
  it("uses explicit port", () => {
    expect(getNodeUiPortFromHref("http://0.0.0.0:5001/app")).toBe("5001")
  })

  it("defaults to 8000 when port is empty", () => {
    expect(getNodeUiPortFromHref("http://192.168.0.1/app")).toBe("8000")
  })
})

describe("buildTailscaleServeCommand", () => {
  it("includes port from href", () => {
    expect(buildTailscaleServeCommand("http://192.168.0.1:5001/app")).toBe(
      "tailscale serve --bg http://127.0.0.1:5001",
    )
  })
})
