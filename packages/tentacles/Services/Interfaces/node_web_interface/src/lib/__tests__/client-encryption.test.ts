import { beforeAll, describe, expect, it } from "vitest"
import { p256 } from "@noble/curves/nist.js"

import {
  CLIENT_KEY_LABELS,
  CLIENT_KEY_NAMES,
  areClientKeysConfigured,
  decryptAndVerify,
  derivePublicPemsFromPrivates,
  emptyKeys,
  encryptAndSign,
  pemToDer,
} from "../client-encryption"
import type { ClientKeys } from "../client-encryption"

function toPem(header: string, der: ArrayBuffer): string {
  const b64 = btoa(String.fromCharCode(...new Uint8Array(der)))
  const lines = b64.match(/.{1,64}/g)?.join("\n") ?? b64
  return `-----BEGIN ${header}-----\n${lines}\n-----END ${header}-----`
}

function b64ToBytes(b64: string): Uint8Array<ArrayBuffer> {
  return new Uint8Array(Uint8Array.from(atob(b64), (c) => c.charCodeAt(0)).buffer as ArrayBuffer)
}

/**
 * Simulate what the Python server does: AES-GCM encrypt the result,
 * RSA-OAEP wrap the AES key with the user's RSA public key,
 * ECDSA-sign (ciphertext + wrappedKey + iv) with the server's ECDSA private key,
 * produce DER-encoded signature (matching Python's cryptography library output).
 * Returns { content: b64(ciphertext), result_metadata: plain JSON string }.
 */
async function serverEncryptResult(
  result: string,
  userRsaPublicKey: CryptoKey,
  serverEcdsaPrivKey: CryptoKey,
): Promise<{ content: string; result_metadata: string }> {
  const b64 = (buf: Uint8Array) => btoa(String.fromCharCode(...buf))
  const aesKey = await crypto.subtle.generateKey({ name: "AES-GCM", length: 256 }, true, ["encrypt"])
  const iv = crypto.getRandomValues(new Uint8Array(12))
  const ciphertext = new Uint8Array(
    await crypto.subtle.encrypt({ name: "AES-GCM", iv }, aesKey, new TextEncoder().encode(result)),
  )
  const wrappedKey = new Uint8Array(
    await crypto.subtle.wrapKey("raw", aesKey, userRsaPublicKey, { name: "RSA-OAEP" }),
  )
  const dataToSign = new Uint8Array(ciphertext.length + wrappedKey.length + iv.length)
  dataToSign.set(ciphertext, 0)
  dataToSign.set(wrappedKey, ciphertext.length)
  dataToSign.set(iv, ciphertext.length + wrappedKey.length)
  const p1363 = new Uint8Array(
    await crypto.subtle.sign({ name: "ECDSA", hash: "SHA-256" }, serverEcdsaPrivKey, dataToSign),
  )
  // WebCrypto produces P1363 (compact); Python cryptography library produces DER — convert to match server output
  const derSig = p256.Signature.fromBytes(p1363, "compact").toBytes("der") as Uint8Array
  return {
    content: b64(ciphertext),
    result_metadata: JSON.stringify({
      ENCRYPTED_AES_KEY_B64: b64(wrappedKey),
      IV_B64: b64(iv),
      SIGNATURE_B64: b64(derSig),
    }),
  }
}

let testKeys: ClientKeys
let serverRsaPublicPem: string
let serverEcdsaPublicPem: string
let rsaPrivateKey: CryptoKey
let ecdsaPublicKey: CryptoKey
let rsaPublicDer: ArrayBuffer
let ecdsaPrivateDer: ArrayBuffer
// server-side keys (simulate TASKS_SERVER_ECDSA_PRIVATE_KEY / SERVER_ECDSA_PUBLIC_KEY)
let serverEcdsaPrivateKey: CryptoKey
let serverEcdsaPublicDer: ArrayBuffer
// user's RSA public key (given to server as TASKS_USER_RSA_PUBLIC_KEY)
let userRsaPublicKey: CryptoKey

describe("client-encryption", () => {
  beforeAll(async () => {
    // RSA-2048 for speed; same algorithm as production RSA-4096
    const rsaPair = await crypto.subtle.generateKey(
      {
        name: "RSA-OAEP",
        modulusLength: 2048,
        publicExponent: new Uint8Array([1, 0, 1]),
        hash: "SHA-256",
      },
      true,
      ["wrapKey", "unwrapKey"],
    )
    // User's ECDSA key pair (signs task INPUTS)
    const ecdsaPair = await crypto.subtle.generateKey(
      { name: "ECDSA", namedCurve: "P-256" },
      true,
      ["sign", "verify"],
    )
    // Server's ECDSA key pair (signs task RESULTS)
    const serverEcdsaPair = await crypto.subtle.generateKey(
      { name: "ECDSA", namedCurve: "P-256" },
      true,
      ["sign", "verify"],
    )

    rsaPublicDer = await crypto.subtle.exportKey("spki", rsaPair.publicKey)
    ecdsaPrivateDer = await crypto.subtle.exportKey("pkcs8", ecdsaPair.privateKey)
    const rsaPrivateDer = await crypto.subtle.exportKey("pkcs8", rsaPair.privateKey)
    serverEcdsaPublicDer = await crypto.subtle.exportKey("spki", serverEcdsaPair.publicKey)

    rsaPrivateKey = rsaPair.privateKey
    ecdsaPublicKey = ecdsaPair.publicKey
    serverEcdsaPrivateKey = serverEcdsaPair.privateKey
    userRsaPublicKey = rsaPair.publicKey

    serverRsaPublicPem = toPem("PUBLIC KEY", rsaPublicDer)
    serverEcdsaPublicPem = toPem("PUBLIC KEY", serverEcdsaPublicDer)

    testKeys = {
      ecdsa_private: toPem("PRIVATE KEY", ecdsaPrivateDer),
      rsa_private: toPem("PRIVATE KEY", rsaPrivateDer),
    }
  }, 15_000)

  describe("emptyKeys", () => {
    it("returns two keys all empty strings", () => {
      const keys = emptyKeys()
      expect(Object.keys(keys)).toHaveLength(2)
      expect(Object.values(keys).every((v) => v === "")).toBe(true)
    })
  })

  describe("areClientKeysConfigured", () => {
    it("returns true when both keys are non-empty", () => {
      expect(areClientKeysConfigured(testKeys)).toBe(true)
    })

    it("returns true when both keys are filled", () => {
      const full: ClientKeys = { ecdsa_private: "a", rsa_private: "b" }
      expect(areClientKeysConfigured(full)).toBe(true)
    })

    it("returns false when any single key is empty", () => {
      const names: (keyof ClientKeys)[] = ["ecdsa_private", "rsa_private"]
      for (const name of names) {
        const keys: ClientKeys = { ecdsa_private: "a", rsa_private: "b" }
        keys[name] = ""
        expect(areClientKeysConfigured(keys)).toBe(false)
      }
    })

    it("returns false when a key is whitespace-only", () => {
      const keys: ClientKeys = { ecdsa_private: "a", rsa_private: "   " }
      expect(areClientKeysConfigured(keys)).toBe(false)
    })

    it("returns false for freshly created emptyKeys()", () => {
      expect(areClientKeysConfigured(emptyKeys())).toBe(false)
    })
  })

  describe("CLIENT_KEY_NAMES / CLIENT_KEY_LABELS", () => {
    it("exposes exactly two key names matching ClientKeys shape", () => {
      expect(CLIENT_KEY_NAMES).toHaveLength(2)
      const keySet = new Set<string>(["ecdsa_private", "rsa_private"])
      for (const name of CLIENT_KEY_NAMES) {
        expect(keySet.has(name)).toBe(true)
      }
    })

    it("has a non-empty label for every key name", () => {
      for (const name of CLIENT_KEY_NAMES) {
        expect(CLIENT_KEY_LABELS[name].length).toBeGreaterThan(0)
      }
    })
  })

  describe("pemToDer", () => {
    it("decodes a standard well-formed PEM to the original DER bytes", () => {
      const pem = toPem("PUBLIC KEY", rsaPublicDer)
      const decoded = pemToDer(pem)
      expect(decoded).toEqual(new Uint8Array(rsaPublicDer))
    })

    it("decodes PEM with literal \\n escape sequences (JSON-pasted key)", () => {
      const jsonEscaped = toPem("PUBLIC KEY", rsaPublicDer).replace(/\n/g, "\\n")
      const decoded = pemToDer(jsonEscaped)
      expect(decoded).toEqual(new Uint8Array(rsaPublicDer))
    })

    it("decodes PEM with Windows CRLF line endings", () => {
      const crlf = toPem("PUBLIC KEY", rsaPublicDer).replace(/\n/g, "\r\n")
      const decoded = pemToDer(crlf)
      expect(decoded).toEqual(new Uint8Array(rsaPublicDer))
    })

    it("decodes PEM with extra leading and trailing whitespace", () => {
      const padded = `\n  ${toPem("PUBLIC KEY", rsaPublicDer)}  \n`
      const decoded = pemToDer(padded)
      expect(decoded).toEqual(new Uint8Array(rsaPublicDer))
    })

    it("decodes PEM with mixed CRLF and extra blank lines", () => {
      const messy = toPem("PUBLIC KEY", rsaPublicDer).replace(/\n/g, "\r\n") + "\r\n\r\n"
      const decoded = pemToDer(messy)
      expect(decoded).toEqual(new Uint8Array(rsaPublicDer))
    })
  })

  describe("encryptAndSign", () => {
    it("produces base64-encoded content and content_metadata", async () => {
      const { content, content_metadata } = await encryptAndSign("hello world", testKeys, serverRsaPublicPem)
      expect(content.length).toBeGreaterThan(0)
      expect(content_metadata.length).toBeGreaterThan(0)
      expect(() => atob(content)).not.toThrow()
      expect(() => atob(content_metadata)).not.toThrow()
    })

    it("content_metadata decodes to JSON with ENCRYPTED_AES_KEY_B64, IV_B64, SIGNATURE_B64", async () => {
      const { content_metadata } = await encryptAndSign("hello", testKeys, serverRsaPublicPem)
      const metadata = JSON.parse(atob(content_metadata))
      expect(metadata).toHaveProperty("ENCRYPTED_AES_KEY_B64")
      expect(metadata).toHaveProperty("IV_B64")
      expect(metadata).toHaveProperty("SIGNATURE_B64")
      expect(Object.keys(metadata)).toHaveLength(3)
    })

    it("produces different ciphertext and metadata on each call (fresh IV and AES key)", async () => {
      const msg = "same message"
      const { content: c1, content_metadata: m1 } = await encryptAndSign(msg, testKeys, serverRsaPublicPem)
      const { content: c2, content_metadata: m2 } = await encryptAndSign(msg, testKeys, serverRsaPublicPem)
      expect(c1).not.toBe(c2)
      expect(m1).not.toBe(m2)
    })

    it("IV is exactly 12 bytes (AES-GCM standard)", async () => {
      const { content_metadata } = await encryptAndSign("test", testKeys, serverRsaPublicPem)
      const { IV_B64 } = JSON.parse(atob(content_metadata))
      expect(b64ToBytes(IV_B64).byteLength).toBe(12)
    })

    it("wrapped AES key length matches RSA modulus size in bytes", async () => {
      const { content_metadata } = await encryptAndSign("test", testKeys, serverRsaPublicPem)
      const { ENCRYPTED_AES_KEY_B64 } = JSON.parse(atob(content_metadata))
      // RSA-2048 → 256 bytes, RSA-4096 → 512 bytes
      expect([256, 512]).toContain(b64ToBytes(ENCRYPTED_AES_KEY_B64).byteLength)
    })

    it("signature is DER-encoded (starts with 0x30 SEQUENCE tag)", async () => {
      const { content_metadata } = await encryptAndSign("test", testKeys, serverRsaPublicPem)
      const { SIGNATURE_B64 } = JSON.parse(atob(content_metadata))
      expect(b64ToBytes(SIGNATURE_B64)[0]).toBe(0x30)
    })

    it("decrypted ciphertext matches original content (full roundtrip)", async () => {
      const original = "round-trip test payload"
      const { content, content_metadata } = await encryptAndSign(original, testKeys, serverRsaPublicPem)

      const { ENCRYPTED_AES_KEY_B64, IV_B64 } = JSON.parse(atob(content_metadata))
      const ciphertext = b64ToBytes(content)
      const encryptedAesKey = b64ToBytes(ENCRYPTED_AES_KEY_B64)
      const iv = b64ToBytes(IV_B64)

      const aesKey = await crypto.subtle.unwrapKey(
        "raw",
        encryptedAesKey,
        rsaPrivateKey,
        { name: "RSA-OAEP" },
        { name: "AES-GCM", length: 256 },
        false,
        ["decrypt"],
      )
      const plaintext = await crypto.subtle.decrypt({ name: "AES-GCM", iv }, aesKey, ciphertext)
      expect(new TextDecoder().decode(plaintext)).toBe(original)
    })

    it("ECDSA signature over ciphertext+wrappedKey+IV verifies with ECDSA public key", async () => {
      const original = "sig-verify test"
      const { content, content_metadata } = await encryptAndSign(original, testKeys, serverRsaPublicPem)

      const { ENCRYPTED_AES_KEY_B64, IV_B64, SIGNATURE_B64 } = JSON.parse(atob(content_metadata))
      const ciphertext = b64ToBytes(content)
      const encryptedAesKey = b64ToBytes(ENCRYPTED_AES_KEY_B64)
      const iv = b64ToBytes(IV_B64)
      const derSig = b64ToBytes(SIGNATURE_B64)

      const dataToSign = new Uint8Array(ciphertext.length + encryptedAesKey.length + iv.length)
      dataToSign.set(ciphertext)
      dataToSign.set(encryptedAesKey, ciphertext.length)
      dataToSign.set(iv, ciphertext.length + encryptedAesKey.length)

      const p1363Sig = p256.Signature.fromBytes(derSig, "der").toBytes("compact") as Uint8Array
      const valid = await crypto.subtle.verify({ name: "ECDSA", hash: "SHA-256" }, ecdsaPublicKey, p1363Sig.buffer as ArrayBuffer, dataToSign)
      expect(valid).toBe(true)
    })

    it("roundtrip succeeds with PEM keys containing literal \\n escape sequences (JSON-pasted)", async () => {
      const jsonEscapedKeys: ClientKeys = {
        ...testKeys,
        ecdsa_private: testKeys.ecdsa_private.replace(/\n/g, "\\n"),
      }
      const original = "json-escaped pem roundtrip"
      const { content, content_metadata } = await encryptAndSign(original, jsonEscapedKeys, serverRsaPublicPem.replace(/\n/g, "\\n"))

      const { ENCRYPTED_AES_KEY_B64, IV_B64 } = JSON.parse(atob(content_metadata))
      const aesKey = await crypto.subtle.unwrapKey(
        "raw",
        b64ToBytes(ENCRYPTED_AES_KEY_B64),
        rsaPrivateKey,
        { name: "RSA-OAEP" },
        { name: "AES-GCM", length: 256 },
        false,
        ["decrypt"],
      )
      const plaintext = await crypto.subtle.decrypt(
        { name: "AES-GCM", iv: b64ToBytes(IV_B64) },
        aesKey,
        b64ToBytes(content),
      )
      expect(new TextDecoder().decode(plaintext)).toBe(original)
    })

    it("roundtrip succeeds with PEM keys containing Windows CRLF line endings", async () => {
      const crlfKeys: ClientKeys = {
        ...testKeys,
        ecdsa_private: testKeys.ecdsa_private.replace(/\n/g, "\r\n"),
      }
      const original = "crlf pem roundtrip"
      const { content, content_metadata } = await encryptAndSign(original, crlfKeys, serverRsaPublicPem.replace(/\n/g, "\r\n"))

      const { ENCRYPTED_AES_KEY_B64, IV_B64 } = JSON.parse(atob(content_metadata))
      const aesKey = await crypto.subtle.unwrapKey(
        "raw",
        b64ToBytes(ENCRYPTED_AES_KEY_B64),
        rsaPrivateKey,
        { name: "RSA-OAEP" },
        { name: "AES-GCM", length: 256 },
        false,
        ["decrypt"],
      )
      const plaintext = await crypto.subtle.decrypt(
        { name: "AES-GCM", iv: b64ToBytes(IV_B64) },
        aesKey,
        b64ToBytes(content),
      )
      expect(new TextDecoder().decode(plaintext)).toBe(original)
    })

    it("handles empty string content", async () => {
      const { content, content_metadata } = await encryptAndSign("", testKeys, serverRsaPublicPem)
      const { ENCRYPTED_AES_KEY_B64, IV_B64 } = JSON.parse(atob(content_metadata))
      const aesKey = await crypto.subtle.unwrapKey(
        "raw",
        b64ToBytes(ENCRYPTED_AES_KEY_B64),
        rsaPrivateKey,
        { name: "RSA-OAEP" },
        { name: "AES-GCM", length: 256 },
        false,
        ["decrypt"],
      )
      const plaintext = await crypto.subtle.decrypt(
        { name: "AES-GCM", iv: b64ToBytes(IV_B64) },
        aesKey,
        b64ToBytes(content),
      )
      expect(new TextDecoder().decode(plaintext)).toBe("")
    })

    it("handles unicode content", async () => {
      const unicode = "héllo wörld 🔐"
      const { content, content_metadata } = await encryptAndSign(unicode, testKeys, serverRsaPublicPem)

      const { ENCRYPTED_AES_KEY_B64, IV_B64 } = JSON.parse(atob(content_metadata))
      const aesKey = await crypto.subtle.unwrapKey(
        "raw",
        b64ToBytes(ENCRYPTED_AES_KEY_B64),
        rsaPrivateKey,
        { name: "RSA-OAEP" },
        { name: "AES-GCM", length: 256 },
        false,
        ["decrypt"],
      )
      const plaintext = await crypto.subtle.decrypt(
        { name: "AES-GCM", iv: b64ToBytes(IV_B64) },
        aesKey,
        b64ToBytes(content),
      )
      expect(new TextDecoder().decode(plaintext)).toBe(unicode)
    })
  })

  describe("decryptAndVerify", () => {
    it("roundtrip: server-encrypted result decrypts to original plaintext", async () => {
      const original = "server roundtrip payload"
      const { content, result_metadata } = await serverEncryptResult(original, userRsaPublicKey, serverEcdsaPrivateKey)
      const decrypted = await decryptAndVerify(content, result_metadata, testKeys, serverEcdsaPublicPem)
      expect(decrypted).toBe(original)
    })

    it("decrypted result differs between calls (unique AES key and IV each time)", async () => {
      const { content: c1, result_metadata: m1 } = await serverEncryptResult("msg", userRsaPublicKey, serverEcdsaPrivateKey)
      const { content: c2, result_metadata: m2 } = await serverEncryptResult("msg", userRsaPublicKey, serverEcdsaPrivateKey)
      expect(c1).not.toBe(c2)
      expect(m1).not.toBe(m2)
    })

    it("metadata is plain JSON (not base64) — passing base64-encoded metadata throws", async () => {
      const { content, result_metadata } = await serverEncryptResult("test", userRsaPublicKey, serverEcdsaPrivateKey)
      const b64Metadata = btoa(result_metadata)
      await expect(decryptAndVerify(content, b64Metadata, testKeys, serverEcdsaPublicPem)).rejects.toThrow("Invalid result metadata")
    })

    it("rejects tampered ciphertext (signature covers content)", async () => {
      const { content, result_metadata } = await serverEncryptResult("tamper test", userRsaPublicKey, serverEcdsaPrivateKey)
      const tampered = btoa(atob(content).slice(0, -4) + "XXXX")
      await expect(decryptAndVerify(tampered, result_metadata, testKeys, serverEcdsaPublicPem)).rejects.toThrow("Signature verification failed")
    })

    it("rejects tampered IV (signature covers IV)", async () => {
      const { content, result_metadata } = await serverEncryptResult("tamper IV", userRsaPublicKey, serverEcdsaPrivateKey)
      const meta = JSON.parse(result_metadata)
      const ivBytes = b64ToBytes(meta.IV_B64)
      ivBytes[0] ^= 0xff
      const tamperedMeta = JSON.stringify({ ...meta, IV_B64: btoa(String.fromCharCode(...ivBytes)) })
      await expect(decryptAndVerify(content, tamperedMeta, testKeys, serverEcdsaPublicPem)).rejects.toThrow("Signature verification failed")
    })

    it("rejects tampered encrypted AES key (signature covers wrapped key)", async () => {
      const { content, result_metadata } = await serverEncryptResult("tamper key", userRsaPublicKey, serverEcdsaPrivateKey)
      const meta = JSON.parse(result_metadata)
      const keyBytes = b64ToBytes(meta.ENCRYPTED_AES_KEY_B64)
      keyBytes[0] ^= 0xff
      const tamperedMeta = JSON.stringify({ ...meta, ENCRYPTED_AES_KEY_B64: btoa(String.fromCharCode(...keyBytes)) })
      await expect(decryptAndVerify(content, tamperedMeta, testKeys, serverEcdsaPublicPem)).rejects.toThrow("Signature verification failed")
    })

    it("rejects metadata missing required fields", async () => {
      await expect(
        decryptAndVerify("abc", JSON.stringify({ ENCRYPTED_AES_KEY_B64: "x" }), testKeys, serverEcdsaPublicPem),
      ).rejects.toThrow("Missing required fields")
    })

    it("rejects with specific error for invalid SERVER_ECDSA_PUBLIC_KEY", async () => {
      const { content, result_metadata } = await serverEncryptResult("test", userRsaPublicKey, serverEcdsaPrivateKey)
      await expect(decryptAndVerify(content, result_metadata, testKeys, "notapem")).rejects.toThrow("Invalid SERVER_ECDSA_PUBLIC_KEY")
    })

    it("rejects with specific error for invalid USER_RSA_PRIVATE_KEY", async () => {
      const { content, result_metadata } = await serverEncryptResult("test", userRsaPublicKey, serverEcdsaPrivateKey)
      // Put the ECDSA private key into the RSA private key field — wrong key type, same PEM format
      const badKeys: ClientKeys = { ...testKeys, rsa_private: toPem("PRIVATE KEY", ecdsaPrivateDer) }
      await expect(decryptAndVerify(content, result_metadata, badKeys, serverEcdsaPublicPem)).rejects.toThrow("Invalid USER_RSA_PRIVATE_KEY")
    })

    it("wrong server ECDSA key fails signature verification (not key import)", async () => {
      const { content, result_metadata } = await serverEncryptResult("test", userRsaPublicKey, serverEcdsaPrivateKey)
      const wrongPair = await crypto.subtle.generateKey({ name: "ECDSA", namedCurve: "P-256" }, true, ["sign", "verify"])
      const wrongPublicDer = await crypto.subtle.exportKey("spki", wrongPair.publicKey)
      await expect(decryptAndVerify(content, result_metadata, testKeys, toPem("PUBLIC KEY", wrongPublicDer))).rejects.toThrow("Signature verification failed")
    })

    it("handles empty string result", async () => {
      const { content, result_metadata } = await serverEncryptResult("", userRsaPublicKey, serverEcdsaPrivateKey)
      const decrypted = await decryptAndVerify(content, result_metadata, testKeys, serverEcdsaPublicPem)
      expect(decrypted).toBe("")
    })

    it("handles unicode result", async () => {
      const unicode = "héllo wörld 🔐"
      const { content, result_metadata } = await serverEncryptResult(unicode, userRsaPublicKey, serverEcdsaPrivateKey)
      const decrypted = await decryptAndVerify(content, result_metadata, testKeys, serverEcdsaPublicPem)
      expect(decrypted).toBe(unicode)
    })

    it("handles large result payload", async () => {
      const large = JSON.stringify({ data: "x".repeat(10_000) })
      const { content, result_metadata } = await serverEncryptResult(large, userRsaPublicKey, serverEcdsaPrivateKey)
      const decrypted = await decryptAndVerify(content, result_metadata, testKeys, serverEcdsaPublicPem)
      expect(decrypted).toBe(large)
    })

    it("roundtrip with JSON-escaped PEM keys (\\\\n format)", async () => {
      const { content, result_metadata } = await serverEncryptResult("json-escaped pem", userRsaPublicKey, serverEcdsaPrivateKey)
      const escapedKeys: ClientKeys = {
        ...testKeys,
        rsa_private: testKeys.rsa_private.replace(/\n/g, "\\n"),
      }
      const decrypted = await decryptAndVerify(content, result_metadata, escapedKeys, serverEcdsaPublicPem.replace(/\n/g, "\\n"))
      expect(decrypted).toBe("json-escaped pem")
    })

    it("roundtrip with CRLF line endings in PEM keys", async () => {
      const { content, result_metadata } = await serverEncryptResult("crlf pem", userRsaPublicKey, serverEcdsaPrivateKey)
      const crlfKeys: ClientKeys = {
        ...testKeys,
        rsa_private: testKeys.rsa_private.replace(/\n/g, "\r\n"),
      }
      const decrypted = await decryptAndVerify(content, result_metadata, crlfKeys, serverEcdsaPublicPem.replace(/\n/g, "\r\n"))
      expect(decrypted).toBe("crlf pem")
    })
  })

  describe("derivePublicPemsFromPrivates", () => {
    it("derived RSA public key matches the private key (encrypt + decrypt roundtrip)", async () => {
      const { rsa_public_pem } = await derivePublicPemsFromPrivates(testKeys)
      const derivedPub = await crypto.subtle.importKey(
        "spki",
        pemToDer(rsa_public_pem).buffer as ArrayBuffer,
        { name: "RSA-OAEP", hash: "SHA-256" },
        false,
        ["wrapKey"],
      )
      const aesKey = await crypto.subtle.generateKey({ name: "AES-GCM", length: 256 }, true, ["encrypt"])
      const wrapped = await crypto.subtle.wrapKey("raw", aesKey, derivedPub, { name: "RSA-OAEP" })
      const unwrapped = await crypto.subtle.unwrapKey(
        "raw", wrapped, rsaPrivateKey, { name: "RSA-OAEP" }, { name: "AES-GCM", length: 256 }, false, ["decrypt"],
      )
      const iv = crypto.getRandomValues(new Uint8Array(12))
      const cipher = await crypto.subtle.encrypt({ name: "AES-GCM", iv }, aesKey, new TextEncoder().encode("roundtrip"))
      const plain = await crypto.subtle.decrypt({ name: "AES-GCM", iv }, unwrapped, cipher)
      expect(new TextDecoder().decode(plain)).toBe("roundtrip")
    })

    it("derived ECDSA public key matches the private key (sign + verify roundtrip)", async () => {
      const { ecdsa_public_pem } = await derivePublicPemsFromPrivates(testKeys)
      const derivedPub = await crypto.subtle.importKey(
        "spki",
        pemToDer(ecdsa_public_pem).buffer as ArrayBuffer,
        { name: "ECDSA", namedCurve: "P-256" },
        false,
        ["verify"],
      )
      const ecPriv = await crypto.subtle.importKey(
        "pkcs8",
        pemToDer(testKeys.ecdsa_private).buffer as ArrayBuffer,
        { name: "ECDSA", namedCurve: "P-256" },
        false,
        ["sign"],
      )
      const data = new TextEncoder().encode("sign-verify roundtrip")
      const sig = await crypto.subtle.sign({ name: "ECDSA", hash: "SHA-256" }, ecPriv, data)
      const valid = await crypto.subtle.verify({ name: "ECDSA", hash: "SHA-256" }, derivedPub, sig, data)
      expect(valid).toBe(true)
    })

    it("derived PEMs are in SPKI format (-----BEGIN PUBLIC KEY-----)", async () => {
      const { rsa_public_pem, ecdsa_public_pem } = await derivePublicPemsFromPrivates(testKeys)
      expect(rsa_public_pem).toContain("-----BEGIN PUBLIC KEY-----")
      expect(ecdsa_public_pem).toContain("-----BEGIN PUBLIC KEY-----")
    })
  })
})
