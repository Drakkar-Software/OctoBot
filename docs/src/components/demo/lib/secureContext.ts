// The SDK needs `crypto.subtle`, which the platform only exposes in a
// secure context — `localhost` counts, an arbitrary LAN IP does not. This
// bites hardest exactly when this demo is most useful: `vite --host` on a
// LAN IP to test the QR-scan flow from a phone. Same check
// node_web_interface uses (`src/lib/secure-context.ts`), for the same
// reason.
export function isWebCryptoAvailable(): boolean {
  return (
    typeof window !== "undefined" &&
    window.isSecureContext === true &&
    !!window.crypto?.subtle
  )
}
