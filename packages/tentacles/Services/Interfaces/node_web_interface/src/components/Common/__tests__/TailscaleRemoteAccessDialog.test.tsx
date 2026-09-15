import { describe, expect, it, vi } from "vitest"
import { renderToStaticMarkup } from "react-dom/server"

import { MagicDnsRemoteUrlField } from "@/components/Common/MagicDnsRemoteUrlField"
import { TailscaleRemoteAccessDialog } from "@/components/Common/TailscaleRemoteAccessDialog"
import { OCTOBOT_TAILSCALE_CONNECT_GUIDE_URL } from "@/lib/external-links"
import {
  MAGIC_DNS_INVALID_SHAPE,
  MAGIC_DNS_OPEN_IN_BROWSER_LABEL,
  TAILSCALE_ADMIN_CONSOLE_MACHINES_URL,
  TAILSCALE_MAGICDNS_REACHABILITY_LEAD,
  TAILSCALE_SERVE_NOT_ENABLED_ON_TAILNET_MESSAGE,
  TAILSCALE_SERVE_STARTED_RUNNING_MESSAGE,
} from "@/lib/ui-recovery-constants"

vi.mock("@/components/ui/dialog", () => ({
  Dialog: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  DialogContent: ({ children }: { children: React.ReactNode }) => (
    <div>{children}</div>
  ),
  DialogHeader: ({ children }: { children: React.ReactNode }) => (
    <div>{children}</div>
  ),
  DialogFooter: ({ children }: { children: React.ReactNode }) => (
    <div>{children}</div>
  ),
  DialogTitle: ({ children }: { children: React.ReactNode }) => (
    <h2>{children}</h2>
  ),
  DialogDescription: ({ children }: { children: React.ReactNode }) => (
    <div>{children}</div>
  ),
  DialogClose: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}))

const pageHref = "http://192.168.0.10:5001/app/setup?x=1#tab"

describe("TailscaleRemoteAccessDialog", () => {
  it("shows tailscale serve command with port from location", () => {
    vi.stubGlobal("window", {
      location: { href: pageHref, port: "5001" },
    })
    const markup = renderToStaticMarkup(
      <TailscaleRemoteAccessDialog open={true} onOpenChange={() => {}} />,
    )
    expect(markup).toContain("tailscale serve --bg http://127.0.0.1:5001")
    expect(markup).toContain(TAILSCALE_SERVE_NOT_ENABLED_ON_TAILNET_MESSAGE)
    expect(markup).toContain(TAILSCALE_SERVE_STARTED_RUNNING_MESSAGE)
    expect(markup).toContain("printed Tailscale link")
    expect(markup).toContain("tailscale up")
    expect(markup).not.toContain('value="tailscale status"')
    expect(markup).toContain("Full domain")
    expect(markup).toContain(TAILSCALE_ADMIN_CONSOLE_MACHINES_URL)
    expect(markup).not.toContain("ERR_SSL_PROTOCOL_ERROR")
    expect(markup).toContain("this computer")
    expect(markup).toContain("run the command below")
    expect(markup).toContain(TAILSCALE_MAGICDNS_REACHABILITY_LEAD)
    expect(markup).toContain('readOnly=""')
    expect(markup).not.toContain('aria-label="Copy command"')
    expect(markup).not.toContain('aria-label="Copy URL"')
    expect(markup).toContain(OCTOBOT_TAILSCALE_CONNECT_GUIDE_URL)
    vi.unstubAllGlobals()
  })
})

describe("MagicDnsRemoteUrlField", () => {
  it("shows selectable remote URL and open link for valid hostname", () => {
    const markup = renderToStaticMarkup(
      <MagicDnsRemoteUrlField
        pageHref={pageHref}
        value="my-node.tailnet.ts.net"
        onValueChange={() => {}}
      />,
    )
    expect(markup).toContain("https://my-node.tailnet.ts.net/app/setup?x=1#tab")
    expect(markup).toContain('readOnly=""')
    expect(markup).toContain(MAGIC_DNS_OPEN_IN_BROWSER_LABEL)
    expect(markup).toContain("ERR_SSL_PROTOCOL_ERROR")
    expect(markup).toContain("step 2 command")
    expect(markup).not.toContain('aria-label="Copy URL"')
  })

  it("shows error for invalid hostname", () => {
    const markup = renderToStaticMarkup(
      <MagicDnsRemoteUrlField
        pageHref={pageHref}
        value="not-valid"
        onValueChange={() => {}}
      />,
    )
    expect(markup).toContain(MAGIC_DNS_INVALID_SHAPE)
    expect(markup).not.toContain("https://not-valid")
  })

  it("normalizes pasted https URL into remote link", () => {
    const markup = renderToStaticMarkup(
      <MagicDnsRemoteUrlField
        pageHref={pageHref}
        value="https://my-node.tailnet.ts.net/app"
        onValueChange={() => {}}
      />,
    )
    expect(markup).toContain("https://my-node.tailnet.ts.net/app/setup?x=1#tab")
    expect(markup).toContain(MAGIC_DNS_OPEN_IN_BROWSER_LABEL)
  })
})
