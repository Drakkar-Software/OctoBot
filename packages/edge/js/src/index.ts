import ccxt from "ccxt"
import { detectRuntime } from "./polyfills/detect"
import { installEncodingPolyfill } from "./polyfills/encoding"
import { installCryptoPolyfill } from "./polyfills/crypto"
import { installBrowserPolyfills } from "./polyfills/browser"
import { loadNative } from "./rust-bridge/native"
import { loadWasm } from "./rust-bridge/wasm"
import { patchExchange } from "./exchange/patch"
import type { RustBridge } from "./rust-bridge/types"

let _bridge: RustBridge | null = null
let _initPromise: Promise<void> | null = null
let _initResolved = false

/**
 * Initialize the Rust bridge. Call once before creating exchanges.
 * Automatically selects NAPI (Node/Bun) or WASM (browser/Deno).
 * Safe to call concurrently — only runs once.
 * Must be awaited before calling createExchange().
 */
export async function init(): Promise<void> {
  if (_initPromise) return _initPromise
  _initPromise = _doInit()
  return _initPromise
}

async function _doInit(): Promise<void> {
  const runtime = detectRuntime()

  // Install encoding polyfills early for environments without TextEncoder (e.g. Hermes/RN)
  if (runtime === "react-native") {
    installEncodingPolyfill()
  }

  if (runtime === "node" || runtime === "bun") {
    _bridge = await loadNative()
  }

  if (!_bridge) {
    _bridge = await loadWasm()
  }

  // Install full polyfills (crypto, Buffer, etc.) for environments that need them
  if (_bridge) {
    if (runtime === "browser" || runtime === "deno") {
      await installBrowserPolyfills(_bridge)
    } else if (runtime === "react-native") {
      // React Native polyfills are loaded via separate import:
      //   import '@octobot/edge/polyfills/mobile'
      // The mobile.ts module self-installs on import (uses UniFFI bindings).
      // Here we just install the basic crypto polyfill as a fallback.
      installCryptoPolyfill(_bridge)
    }
  } else {
    console.warn(
      "@octobot/edge: no Rust bridge available (NAPI and WASM both failed to load). " +
      "Exchange signing will use the default (slower) ccxt implementation.",
    )
  }

  _initResolved = true
}

/**
 * Create a ccxt exchange instance with Rust-accelerated signing.
 * Throws if init() has not been called and awaited.
 */
export function createExchange<T extends keyof typeof ccxt>(
  exchangeId: T,
  config: Record<string, unknown> = {},
): InstanceType<(typeof ccxt)[T]> {
  if (!_initPromise) {
    throw new Error("@octobot/edge: init() must be called before createExchange()")
  }
  if (!_initResolved) {
    throw new Error("@octobot/edge: init() must be awaited before calling createExchange()")
  }
  const Cls = ccxt[exchangeId] as new (cfg: Record<string, unknown>) => InstanceType<(typeof ccxt)[T]>
  const exchange = new Cls(config)
  patchExchange(exchange as any, _bridge)
  return exchange
}

/** Re-export ccxt for consumers */
export { ccxt }
export type { Runtime } from "./polyfills/detect"
export type { RustBridge } from "./rust-bridge/types"
