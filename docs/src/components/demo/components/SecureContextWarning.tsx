import { useEffect, useState } from "react"
import { isWebCryptoAvailable } from "../lib/secureContext"

// The docs site is HTTPS, so a normal visit satisfies this. It matters for
// two real cases this component now exists to catch: a reader running the
// site locally over plain `http://192.168.x.x` (LAN, e.g. to test the QR-scan
// flow from a phone), and any future non-HTTPS deployment of the docs build.
// `isWebCryptoAvailable()` reads `window`, so this must only ever evaluate to
// `true` after mount — SSR/prerender has no `window` and must not flag a
// false warning.
export function SecureContextWarning() {
  const [unavailable, setUnavailable] = useState(false)

  useEffect(() => {
    setUnavailable(!isWebCryptoAvailable())
  }, [])

  if (!unavailable) return null

  return (
    <div className="mb-6 border border-danger bg-wire-surface p-3">
      <p className="font-mono text-[12px] text-danger">
        This page isn't a secure context (no `crypto.subtle`) — the SDK below
        will throw on every derivation. Load it over HTTPS or from
        `localhost`; a plain-HTTP LAN address won't work.
      </p>
    </div>
  )
}
