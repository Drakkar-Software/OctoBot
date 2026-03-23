/**
 * Browser polyfills — patches globalThis with:
 *   - crypto.createHmac / createHash / randomBytes
 *   - Buffer (BrowserBuffer backed by Rust ops via RustBridge)
 *
 * Call installBrowserPolyfills() once before importing ccxt.
 */
import type { RustBridge } from "../rust-bridge/types"

interface HashBuilder {
  update(data: string | Uint8Array): HashBuilder
  digest(encoding: string): string
}

let installed = false

export async function installBrowserPolyfills(bridge: RustBridge): Promise<void> {
  if (installed) return
  installed = true

  const g = globalThis as any

  // ── crypto ─────────────────────────────────────────────────────────────

  const enc = new TextEncoder()

  function concatChunks(chunks: Uint8Array[]): Uint8Array {
    const total = chunks.reduce((s, c) => s + c.length, 0)
    const result = new Uint8Array(total)
    let offset = 0
    for (const c of chunks) { result.set(c, offset); offset += c.length }
    return result
  }

  function makeHmacBuilder(algorithm: string, secret: string): HashBuilder {
    const chunks: Uint8Array[] = []
    const builder: HashBuilder = {
      update(data: string | Uint8Array): HashBuilder {
        chunks.push(typeof data === "string" ? enc.encode(data) : data)
        return builder
      },
      digest(encoding: string): string {
        const message = concatChunks(chunks)
        const secretBytes = enc.encode(secret)
        const algo = algorithm.toLowerCase()
        // Use byte-level bridge methods to avoid lossy string roundtripping
        if (algo === "sha256" && encoding === "hex") return bridge.hmacSha256Hex(secretBytes, message)
        if (algo === "sha512" && encoding === "hex") return bridge.hmacSha512Hex(secretBytes, message)
        // Fallback to string-based bridge for other algorithms/encodings
        const accumulated = new TextDecoder().decode(message)
        return bridge.hmac(algorithm, secret, accumulated, encoding)
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
        const result = bridge.hash(algorithm, accumulated, encoding)
        accumulated = ""
        return result
      },
    }
    return builder
  }

  const cryptoObj = (g.crypto ?? {}) as any
  const originalGetRandomValues = typeof cryptoObj.getRandomValues === "function"
    ? cryptoObj.getRandomValues.bind(cryptoObj)
    : undefined

  const defineCryptoMethod = (name: string, value: unknown) => {
    try {
      Object.defineProperty(cryptoObj, name, {
        value,
        configurable: true,
        enumerable: false,
        writable: true,
      })
    } catch {
      cryptoObj[name] = value
    }
  }

  defineCryptoMethod("createHmac", (algorithm: string, secret: string) =>
    makeHmacBuilder(algorithm, secret),
  )
  defineCryptoMethod("createHash", (algorithm: string) =>
    makeHashBuilder(algorithm),
  )
  defineCryptoMethod("randomBytes", (size: number) => {
    const bytes = bridge.randomBytes(size)
    return new BrowserBuffer(bytes)
  })
  if (originalGetRandomValues) {
    defineCryptoMethod("getRandomValues", originalGetRandomValues)
  }
  g.crypto = cryptoObj

  // ── Buffer ─────────────────────────────────────────────────────────────

  class BrowserBuffer extends Uint8Array {
    // Use a static method name that doesn't conflict with Uint8Array.from overloads
    static fromValue(
      value: string | ArrayLike<number> | ArrayBufferLike,
      encoding?: string,
    ): BrowserBuffer {
      if (typeof value === "string") {
        const enc = encoding ?? "utf8"
        let bytes: Uint8Array
        if (enc === "hex") bytes = new Uint8Array(bridge.bufferFromHex(value))
        else if (enc === "base64") bytes = new Uint8Array(bridge.bufferFromBase64(value))
        else if (enc === "binary" || enc === "latin1") {
          bytes = new Uint8Array(value.length)
          for (let i = 0; i < value.length; i++) bytes[i] = value.charCodeAt(i) & 0xff
        } else bytes = new TextEncoder().encode(value)
        // Use bytes directly (not bytes.buffer) to avoid aliasing WASM linear memory
        return new BrowserBuffer(bytes)
      }
      if (value instanceof ArrayBuffer || (typeof SharedArrayBuffer !== "undefined" && value instanceof SharedArrayBuffer)) {
        return new BrowserBuffer(new Uint8Array(value as ArrayBuffer))
      }
      return new BrowserBuffer(value as ArrayLike<number>)
    }
    static alloc(size: number) { return new BrowserBuffer(size) }
    static concat(bufs: BrowserBuffer[]): BrowserBuffer {
      const total = bufs.reduce((s, b) => s + b.length, 0)
      const result = new BrowserBuffer(total)
      let offset = 0
      for (const b of bufs) { result.set(b, offset); offset += b.length }
      return result
    }
    static byteLength(str: string) { return bridge.bufferByteLength(str) }
    static isBuffer(obj: unknown) { return obj instanceof BrowserBuffer }
    override toString(encoding?: string): string {
      if (encoding === "hex") return bridge.bufferToHex(this)
      if (encoding === "base64") return bridge.bufferToBase64(this)
      if (encoding === "binary" || encoding === "latin1") {
        let result = ""
        for (let i = 0; i < this.length; i++) result += String.fromCharCode(this[i])
        return result
      }
      return new TextDecoder().decode(this)
    }
  }

  // Alias .from to .fromValue — avoids TypeScript override conflict with Uint8Array.from
  ;(BrowserBuffer as any).from = BrowserBuffer.fromValue
  g.Buffer = BrowserBuffer
}
