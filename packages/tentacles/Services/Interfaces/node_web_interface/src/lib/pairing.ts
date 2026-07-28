import { SetupService } from "@/client"
import { loadPassword } from "@/lib/device-key"
import { fetchNodeConfig } from "@/lib/node-config"

export function buildOriginWithHostname(origin: string, hostname: string): string {
  const url = new URL(origin)
  url.hostname = hostname
  return url.origin
}

export function resolveExternalHostUrl(
  externalHost: string,
  protocol: string,
): string {
  return /^https?:\/\//i.test(externalHost)
    ? externalHost
    : `${protocol}//${externalHost}`
}

export function resolvePairingNodeHostname(
  vpnIp: string | null | undefined,
  localIp: string | null | undefined,
  browserOrigin: string,
): string {
  if (vpnIp) {
    return buildOriginWithHostname(browserOrigin, vpnIp)
  }
  if (localIp) {
    return buildOriginWithHostname(browserOrigin, localIp)
  }
  return browserOrigin
}

export async function resolvePairingNodeUrl(): Promise<string> {
  // P0: admin-configured external host (reverse proxy / tailscale serve).
  try {
    const config = await fetchNodeConfig()
    if (config?.external_host) {
      return resolveExternalHostUrl(config.external_host, window.location.protocol)
    }
  } catch (error) {
    console.error("resolvePairingNodeUrl: failed to fetch node config", error)
  }

  // P1: Tailscale IP, P2: LAN IP, P3: browser origin fallback.
  const [vpnResult, localResult] = await Promise.allSettled([
    SetupService.getVpnNetworkAddress(),
    SetupService.getLocalNetworkAddress(),
  ])

  const vpnIp =
    vpnResult.status === "fulfilled"
      ? (vpnResult.value.vpn_network_ip ?? null)
      : null
  const localIp =
    localResult.status === "fulfilled"
      ? (localResult.value.local_network_ip ?? null)
      : null

  return resolvePairingNodeHostname(vpnIp, localIp, window.location.origin)
}

export async function buildPairingQrValue() {
  const address = localStorage.getItem("auth_username") || ""
  const passphrase = (await loadPassword()) ?? ""
  if (!address || !passphrase) {
    throw new Error(
      "No active wallet session — log out and back in to refresh device key.",
    )
  }
  const url = await resolvePairingNodeUrl()
  return JSON.stringify({
    url,
    address,
    passphrase,
  })
}
