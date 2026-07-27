import { useState } from "react"

import { SetupNodeAddressPanel } from "@/components/Setup/SetupNodeAddressPanel"
import { Button } from "@/components/ui/button"
import { useLocalNetworkHostname } from "@/hooks/useLocalNetworkHostname"
import { useVpnNetworkHostname } from "@/hooks/useVpnNetworkHostname"
import { OCTOBOT_TAILSCALE_CONNECT_GUIDE_URL } from "@/lib/external-links"

type ConnectAddressAudience = "web" | "mobile"
type ConnectAddressMethod = "local" | "vpn"

const LOCAL_NETWORK_INTRO: Record<ConnectAddressAudience, string> = {
  mobile:
    "Your phone must be connected to the same local network as this node to reach it.",
  web: "Your browser must be on the same local network as this node to reach it.",
}

const VPN_NETWORK_INTRO: Record<ConnectAddressAudience, string> = {
  mobile:
    "If your node runs on a computer, server, or Raspberry Pi and you want to manage it from the new app anywhere, use a Tailscale private network instead of exposing your node on the public internet. Tailscale lets you run your node on any machine and control it from the new OctoBot interface or Android beta app over a secure private network.",
  web:
    "If your node runs on a computer, server, or Raspberry Pi and you want to manage it from the OctoBot web interface anywhere, use a Tailscale private network instead of exposing your node on the public internet. Tailscale lets you run your node on any machine and control it from the OctoBot web interface over a secure private network.",
}

type NodeConnectAddressTabsProps = {
  audience: ConnectAddressAudience
}

export function NodeConnectAddressTabs({ audience }: NodeConnectAddressTabsProps) {
  const [connectAddressMethod, setConnectAddressMethod] =
    useState<ConnectAddressMethod>("local")
  const {
    hostname: localHostname,
    hostnameHelperText: localHostnameHelperText,
    isPending: isLocalPending,
  } = useLocalNetworkHostname()
  const {
    hostname: vpnHostname,
    couldNotDetect: couldNotDetectVpn,
    isPending: isVpnPending,
    isFetching: isVpnFetching,
    refresh: refreshVpnHostname,
  } = useVpnNetworkHostname()

  const vpnHostnameHelperText = couldNotDetectVpn ? (
    <>
      Tailscale may not be running or is disconnected.{" "}
      <button
        type="button"
        className="underline"
        onClick={() => setConnectAddressMethod("local")}
      >
        Use local network instead
      </button>
    </>
  ) : undefined

  return (
    <div className="flex flex-col gap-3">
      <div className="flex rounded-md border text-sm">
        <button
          type="button"
          onClick={() => setConnectAddressMethod("local")}
          className={`flex flex-1 items-center justify-center rounded-l-md px-4 py-2 transition-colors ${
            connectAddressMethod === "local"
              ? "bg-primary text-primary-foreground"
              : "hover:bg-muted"
          }`}
        >
          Local network
        </button>
        <button
          type="button"
          onClick={() => setConnectAddressMethod("vpn")}
          className={`flex flex-1 items-center justify-center rounded-r-md px-4 py-2 transition-colors ${
            connectAddressMethod === "vpn"
              ? "bg-primary text-primary-foreground"
              : "hover:bg-muted"
          }`}
        >
          VPN
        </button>
      </div>

      {connectAddressMethod === "local" ? (
        <>
          <p className="text-sm text-muted-foreground">
            {LOCAL_NETWORK_INTRO[audience]}
          </p>
          <SetupNodeAddressPanel
            hostname={localHostname}
            hostnameHelperText={localHostnameHelperText}
            hostnameLoading={isLocalPending}
          />
        </>
      ) : (
        <>
          <p className="text-sm text-muted-foreground">
            {VPN_NETWORK_INTRO[audience]}
          </p>
          <div className="flex justify-center">
            <a
              href={OCTOBOT_TAILSCALE_CONNECT_GUIDE_URL}
              target="_blank"
              rel="noopener noreferrer"
            >
              <Button type="button" variant="outline">
                Read the Tailscale guide
              </Button>
            </a>
          </div>
          <SetupNodeAddressPanel
            hostname={vpnHostname}
            hostnameLabel="Tailscale IP address or MagicDNS"
            hostnameHelperText={vpnHostnameHelperText}
            hostnameLoading={isVpnPending || isVpnFetching}
            onHostnameRefresh={() => {
              void refreshVpnHostname()
            }}
            hostnameRefreshPending={isVpnFetching}
            hostnameRefreshAriaLabel="Refresh Tailscale address"
          />
        </>
      )}
    </div>
  )
}
