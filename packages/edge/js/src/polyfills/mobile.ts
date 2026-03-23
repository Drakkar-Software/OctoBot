/**
 * Mobile polyfills (iOS + Android via UniFFI Turbo Module).
 *
 * Patches globalThis before ccxt loads with:
 *   - crypto (createHmac, createHash, randomBytes)
 *   - fetch (Rust reqwest fallback if native unavailable)
 *   - Buffer (RustBackedBuffer)
 *   - URLSearchParams, btoa/atob, process, performance, DOMException
 *
 * Import this module BEFORE loading ccxt:
 *   import '@octobot/edge/polyfills/mobile'
 */

// These imports are resolved by uniffi-bindgen-react-native at build time.
// In development/testing, this module is not imported directly.
import {
  hmac,
  hash,
  randomBytesHex,
  randomBytes,
  bufferToHex,
  bufferFromHex,
  bufferToBase64,
  bufferFromBase64,
  bufferByteLength,
  fetch as rustFetch,
  type FetchRequest,
  type FetchResponse,
} from "../generated/octobot_edge_mobile"

// ── 1. crypto ───────────────────────────────────────────────────────────────
//
// CCXT calls: crypto.createHmac(algo, key).update(data).digest(enc)

interface HashBuilder {
  update(data: string | Uint8Array): HashBuilder
  digest(encoding: string): string
}

function makeHmacBuilder(algorithm: string, secret: string): HashBuilder {
  // Accumulate as string since the mobile UniFFI bridge only exposes string-based hmac().
  // In the mobile/ccxt signing path, data is always ASCII query strings, so this is safe.
  let accumulated = ""
  const builder: HashBuilder = {
    update(data: string | Uint8Array): HashBuilder {
      accumulated += typeof data === "string"
        ? data
        : new TextDecoder().decode(data)
      return builder
    },
    digest(encoding: string): string {
      const result = hmac(algorithm, secret, accumulated, encoding)
      accumulated = ""
      return result
    },
  }
  return builder
}

function makeHashBuilder(algorithm: string): HashBuilder {
  let accumulated = ""
  const builder: HashBuilder = {
    update(data: string | Uint8Array): HashBuilder {
      accumulated += typeof data === "string"
        ? data
        : new TextDecoder().decode(data)
      return builder
    },
    digest(encoding: string): string {
      const result = hash(algorithm, accumulated, encoding)
      accumulated = ""
      return result
    },
  }
  return builder
}

// Mutate the existing crypto object rather than spreading it, to preserve
// non-enumerable properties, getters (e.g. subtle), and the prototype chain.
const cryptoObj: any = (globalThis as any).crypto ?? {}

cryptoObj.createHmac = (algorithm: string, secret: string) =>
  makeHmacBuilder(algorithm, secret)

cryptoObj.createHash = (algorithm: string) =>
  makeHashBuilder(algorithm)

cryptoObj.randomBytes = (size: number): InstanceType<typeof RustBackedBuffer> => {
  const bytes = randomBytes(size)
  return RustBackedBuffer.from(bytes)
}

;(globalThis as any).crypto = cryptoObj

// ── 2. fetch ────────────────────────────────────────────────────────────────
//
// Prefer React Native's native fetch; keep Rust fetch as fallback.

const nativeFetch = (globalThis as any).fetch?.bind(globalThis)

if (typeof nativeFetch !== "function") {
  ;(globalThis as any).fetch = async (
    url: string,
    options: {
      method?: string
      headers?: Record<string, string>
      body?: string
    } = {},
  ): Promise<{
    status: number
    ok: boolean
    headers: { get: (name: string) => string | null }
    text: () => Promise<string>
    json: () => Promise<unknown>
  }> => {
    const req: FetchRequest = {
      url,
      method: options.method ?? "GET",
      headers: Object.entries(options.headers ?? {}).map(([name, value]) => ({
        name,
        value,
      })),
      body: options.body ?? null,
    }

    const res: FetchResponse = await rustFetch(req)
    const headerMap = new Map(res.headers.map((h: any) => [h.name.toLowerCase(), h.value]))

    return {
      status: res.status,
      ok: res.ok,
      headers: {
        get: (name: string) => headerMap.get(name.toLowerCase()) ?? null,
      },
      text: async () => res.body,
      json: async () => JSON.parse(res.body),
    }
  }
}

// ── 3. Buffer ───────────────────────────────────────────────────────────────
//
// CCXT uses Buffer for: from(str, enc), toString(enc), concat, byteLength.

class RustBackedBuffer extends Uint8Array {
  // Use a static method name that doesn't conflict with Uint8Array.from overloads
  static fromValue(
    value: string | ArrayLike<number> | ArrayBufferLike,
    encoding?: string,
  ): RustBackedBuffer {
    if (typeof value === "string") {
      const enc = encoding ?? "utf8"
      let bytes: Uint8Array
      if (enc === "hex") {
        bytes = new Uint8Array(bufferFromHex(value))
      } else if (enc === "base64") {
        bytes = new Uint8Array(bufferFromBase64(value))
      } else if (enc === "binary" || enc === "latin1") {
        // Latin-1: each char code (0-255) maps to one byte
        bytes = new Uint8Array(value.length)
        for (let i = 0; i < value.length; i++) {
          bytes[i] = value.charCodeAt(i) & 0xff
        }
      } else {
        bytes = new TextEncoder().encode(value)
      }
      return new RustBackedBuffer(bytes.buffer as ArrayBuffer)
    }
    if (value instanceof ArrayBuffer || (typeof SharedArrayBuffer !== "undefined" && value instanceof SharedArrayBuffer)) {
      return new RustBackedBuffer(new Uint8Array(value as ArrayBuffer))
    }
    return new RustBackedBuffer(value as ArrayLike<number>)
  }

  static alloc(size: number): RustBackedBuffer {
    return new RustBackedBuffer(size)
  }

  static concat(bufs: RustBackedBuffer[]): RustBackedBuffer {
    const total = bufs.reduce((s, b) => s + b.length, 0)
    const result = new RustBackedBuffer(total)
    let offset = 0
    for (const b of bufs) {
      result.set(b, offset)
      offset += b.length
    }
    return result
  }

  static byteLength(str: string): number {
    return bufferByteLength(str)
  }

  static isBuffer(obj: unknown): boolean {
    return obj instanceof RustBackedBuffer
  }

  override toString(encoding?: string): string {
    const enc = encoding ?? "utf8"
    if (enc === "hex") return bufferToHex(this)
    if (enc === "base64") return bufferToBase64(this)
    if (enc === "binary" || enc === "latin1") {
      let result = ""
      for (let i = 0; i < this.length; i++) {
        result += String.fromCharCode(this[i])
      }
      return result
    }
    return new TextDecoder("utf-8").decode(this)
  }
}

// Alias .from to .fromValue — avoids TypeScript override conflict with Uint8Array.from
;(RustBackedBuffer as any).from = RustBackedBuffer.fromValue
;(globalThis as any).Buffer = RustBackedBuffer

// ── 4. Remaining pure-JS polyfills ──────────────────────────────────────────

if (typeof (globalThis as any).URLSearchParams === "undefined") {
  ;(globalThis as any).URLSearchParams = class URLSearchParams {
    private _params: [string, string][] = []
    constructor(init?: Record<string, string> | string) {
      if (typeof init === "string") {
        init
          .replace(/^\?/, "")
          .split("&")
          .forEach((pair) => {
            const idx = pair.indexOf("=")
            const k = idx >= 0 ? pair.slice(0, idx) : pair
            const v = idx >= 0 ? pair.slice(idx + 1) : ""
            if (k) this._params.push([decodeURIComponent(k), decodeURIComponent(v)])
          })
      } else if (init) {
        Object.entries(init).forEach(([k, v]) => this._params.push([k, v]))
      }
    }
    append(k: string, v: string) { this._params.push([k, String(v)]) }
    get(k: string) { return this._params.find((p) => p[0] === k)?.[1] ?? null }
    getAll(k: string) { return this._params.filter((p) => p[0] === k).map((p) => p[1]) }
    has(k: string) { return this._params.some((p) => p[0] === k) }
    set(k: string, v: string) {
      this._params = this._params.filter((p) => p[0] !== k)
      this._params.push([k, String(v)])
    }
    delete(k: string) { this._params = this._params.filter((p) => p[0] !== k) }
    *keys() { for (const [k] of this._params) yield k }
    *values() { for (const [, v] of this._params) yield v }
    *entries() { for (const pair of this._params) yield pair as [string, string] }
    forEach(cb: (value: string, key: string, parent: URLSearchParams) => void) {
      for (const [k, v] of this._params) cb(v, k, this)
    }
    [Symbol.iterator]() { return this.entries() }
    toString() {
      return this._params
        .map((p) => `${encodeURIComponent(p[0])}=${encodeURIComponent(p[1])}`)
        .join("&")
    }
  }
}

if (typeof (globalThis as any).btoa === "undefined") {
  // btoa/atob use Latin-1 (each char code 0-255 maps to one byte)
  ;(globalThis as any).btoa = (str: string): string => {
    const bytes = new Uint8Array(str.length)
    for (let i = 0; i < str.length; i++) {
      const code = str.charCodeAt(i)
      if (code > 255) throw new Error("btoa: character out of Latin-1 range")
      bytes[i] = code
    }
    return bufferToBase64(bytes)
  }
  ;(globalThis as any).atob = (b64: string): string => {
    const bytes = new Uint8Array(bufferFromBase64(b64))
    let result = ""
    for (let i = 0; i < bytes.length; i++) {
      result += String.fromCharCode(bytes[i])
    }
    return result
  }
}

;(globalThis as any).process = (globalThis as any).process ?? { env: Object.create(null), version: "v18.0.0" }
;(globalThis as any).performance = (globalThis as any).performance ?? { now: () => Date.now() }

if (typeof (globalThis as any).DOMException === "undefined") {
  class RNPolyfillDOMException extends Error {
    name: string
    constructor(message = "", name = "Error") {
      super(message)
      this.name = name
    }
  }
  ;(globalThis as any).DOMException = RNPolyfillDOMException
}

export {}
