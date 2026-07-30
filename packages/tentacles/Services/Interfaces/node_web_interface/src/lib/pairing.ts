import { SetupService } from "@/client"
import { loadPassword } from "@/lib/device-key"
import { fetchNodeConfig } from "@/lib/node-config"
import { fetchOwnWalletExport, type WalletExportData } from "@/lib/wallet-export"

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

/** The secret a scanner should import.
 *
 *  `seed` wins when there is one: a mnemonic restores anywhere, and a node set
 *  up from a raw key has none to give.
 *
 *  The `0x` prefix is not cosmetic. Wallet storage strips it before saving
 *  (`WalletEntry.private_key = private_key.removeprefix("0x")`), so the export
 *  hands back bare hex, and the scanner has nothing but the value's shape to
 *  tell a key from a phrase by. Unprefixed, a private key reads as a seed
 *  phrase and fails to import. */
export function pairingSecretFromWallet(wallet: WalletExportData): string {
  if (wallet.seed) return wallet.seed
  return wallet.private_key.startsWith("0x")
    ? wallet.private_key
    : `0x${wallet.private_key}`
}

/** The QR carries the wallet itself, not a way to ask this node for it: the
 *  export happens here, while the browser still holds an authenticated session.
 *  A phone that scans it can restore the account with the node switched off. */
export async function buildPairingQrValue() {
  const address = localStorage.getItem("auth_username") || ""
  const password = (await loadPassword()) ?? ""
  if (!address || !password) {
    throw new Error(
      "No active wallet session — log out and back in to refresh device key.",
    )
  }
  const url = await resolvePairingNodeUrl()
  const wallet = await fetchOwnWalletExport()
  return JSON.stringify({
    url,
    address,
    password: pairingSecretFromWallet(wallet),
  })
}
