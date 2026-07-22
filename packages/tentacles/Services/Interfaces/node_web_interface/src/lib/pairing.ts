import { loadPassword } from "@/lib/device-key"
import { fetchNodeConfig } from "@/lib/node-config"

export async function buildPairingQrValue() {
  const address = localStorage.getItem("auth_username") || ""
  const passphrase = (await loadPassword()) ?? ""
  if (!address || !passphrase) {
    throw new Error(
      "No active wallet session — log out and back in to refresh device key.",
    )
  }
  // Prefer the admin-configured external host (e.g. behind a reverse proxy
  // like tailscale serve) over the browser's own origin, which may be a LAN
  // IP or localhost that the pairing mobile device can't reach.
  let url = window.location.origin
  try {
    const config = await fetchNodeConfig()
    if (config?.external_host) {
      url = /^https?:\/\//i.test(config.external_host)
        ? config.external_host
        : `${window.location.protocol}//${config.external_host}`
    }
  } catch (e) {
    console.error("buildPairingQrValue: failed to fetch node config", e)
  }
  return JSON.stringify({
    url,
    address,
    passphrase,
  })
}
