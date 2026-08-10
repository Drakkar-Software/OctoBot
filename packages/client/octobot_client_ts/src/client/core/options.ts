/** A `DerivationScheme.id` (see `identity/derivationSchemes.ts`) or `'auto'`. */
export type SeedDerivation = string

export type ConnectOptions = {
  /** Node origin: `'http://192.168.1.10:5001'`, `'https://mybot.example.com'`.
   *  A bare `host` / `host:port` is also accepted (parsed the same way the
   *  node-pairing flow parses one). */
  url: string
  /** BIP39 seed phrase, or a 0x-prefixed secp256k1 private key. */
  seed: string
  /** Which derivation turns the phrase into the wallet.
   *  - `'bip44'` (default) — the standard `m/44'/60'/0'/0/0` path, what a
   *    node's own pairing QR carries. The only scheme this package ships;
   *    register another via `registerDerivationScheme` for a different
   *    wallet type and pass its id here.
   *  - `'auto'` — try every registered scheme, probe the node, keep whichever
   *    it authorizes. Costs one extra round-trip per scheme; only meaningful
   *    with `verify: true` (the default). */
  seedDerivation?: SeedDerivation
  /** HTTP Basic credentials for the node's `/api/v1` REST surface. Only a
   *  node paired by an older QR has these — without them `client.node.wallet`,
   *  `.dslKeywords` and `.exportWallet`/`.createGenericProcessBot` throw
   *  `OctoBotConfigError`. */
  basicAuth?: { address: string; password: string }
  /** Injected fetch — proxies, mTLS, React Native polyfills, test stubs.
   *  Default: `globalThis.fetch`. */
  fetch?: typeof fetch
  /** Default per-request timeout, ms. Default 10_000. */
  timeoutMs?: number
  /** Aborts the connect handshake only — not the returned client. */
  signal?: AbortSignal
  /** Probe the node and the sync auth before resolving. Default `true`.
   *  `false` skips all I/O in `connectOctoBot()` — the first real call
   *  surfaces any problem instead. */
  verify?: boolean
}

/** Every method that does I/O takes these last. */
export type CallOptions = {
  signal?: AbortSignal
  timeoutMs?: number
}
