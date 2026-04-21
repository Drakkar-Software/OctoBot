import { p256 } from "@noble/curves/nist.js"

export const CLIENT_KEY_NAMES = ["ecdsa_private", "rsa_private"] as const
export type ClientKeyName = (typeof CLIENT_KEY_NAMES)[number]

export const CLIENT_KEY_LABELS: Record<ClientKeyName, string> = {
  ecdsa_private: "USER_ECDSA_PRIVATE_KEY",
  rsa_private: "USER_RSA_PRIVATE_KEY",
}

export type ClientKeys = Record<ClientKeyName, string>

export function emptyKeys(): ClientKeys {
  return { ecdsa_private: "", rsa_private: "" }
}

export function areClientKeysConfigured(keys: ClientKeys): boolean {
  return CLIENT_KEY_NAMES.every((k) => keys[k].trim())
}

export function pemToDer(pem: string): Uint8Array {
  const b64 = pem
    .replace(/\\n/g, "\n")
    .replace(/-----[^-]+-----/g, "")
    .replace(/[^A-Za-z0-9+/=]/g, "")
  return Uint8Array.from(atob(b64), (c) => c.charCodeAt(0))
}

function toB64(buf: Uint8Array): string {
  let binary = ""
  for (let i = 0; i < buf.length; i++) binary += String.fromCharCode(buf[i])
  return btoa(binary)
}

/**
 * Encrypt content for the server using browser-stored keys.
 * Encrypts with serverRsaPublicPem (SERVER_RSA_PUBLIC), signs with USER_ECDSA_PRIVATE (keys.ecdsa_private).
 * Returns base64-encoded ciphertext and base64(JSON) metadata matching the server's decrypt_task_content format.
 */
export async function encryptAndSign(
  content: string,
  keys: ClientKeys,
  serverRsaPublicPem: string,
): Promise<{ content: string; content_metadata: string }> {
  let rsaPublicKey: CryptoKey
  try {
    rsaPublicKey = await crypto.subtle.importKey(
      "spki",
      pemToDer(serverRsaPublicPem).buffer as ArrayBuffer,
      { name: "RSA-OAEP", hash: "SHA-256" },
      false,
      ["wrapKey"],
    )
  } catch {
    throw new Error("Invalid SERVER_RSA_PUBLIC_KEY — expected RSA public key in SPKI PEM format (-----BEGIN PUBLIC KEY-----)")
  }

  if (/BEGIN EC PRIVATE KEY/.test(keys.ecdsa_private)) {
    throw new Error(
      "USER_ECDSA_PRIVATE_KEY is in SEC1 format (-----BEGIN EC PRIVATE KEY-----). " +
      "Convert to PKCS#8: openssl pkcs8 -topk8 -nocrypt -in ecdsa.pem -out ecdsa_pkcs8.pem"
    )
  }

  let ecdsaPrivateKey: CryptoKey
  try {
    ecdsaPrivateKey = await crypto.subtle.importKey(
      "pkcs8",
      pemToDer(keys.ecdsa_private).buffer as ArrayBuffer,
      { name: "ECDSA", namedCurve: "P-256" },
      false,
      ["sign"],
    )
  } catch {
    const der = pemToDer(keys.ecdsa_private)
    const hint = der.length > 500
      ? " — the key looks like RSA; check you put the ECDSA key in the correct field"
      : ""
    throw new Error(`Invalid USER_ECDSA_PRIVATE_KEY — expected P-256 ECDSA private key in PKCS#8 PEM format (-----BEGIN PRIVATE KEY-----)${hint}`)
  }

  const aesKey = await crypto.subtle.generateKey({ name: "AES-GCM", length: 256 }, true, ["encrypt"])
  const iv = crypto.getRandomValues(new Uint8Array(12))
  const ciphertext = new Uint8Array(
    await crypto.subtle.encrypt({ name: "AES-GCM", iv }, aesKey, new TextEncoder().encode(content)),
  )
  const wrappedKey = new Uint8Array(
    await crypto.subtle.wrapKey("raw", aesKey, rsaPublicKey, { name: "RSA-OAEP" }),
  )

  const dataToSign = new Uint8Array(ciphertext.length + wrappedKey.length + iv.length)
  dataToSign.set(ciphertext, 0)
  dataToSign.set(wrappedKey, ciphertext.length)
  dataToSign.set(iv, ciphertext.length + wrappedKey.length)

  const p1363 = new Uint8Array(
    await crypto.subtle.sign({ name: "ECDSA", hash: "SHA-256" }, ecdsaPrivateKey, dataToSign),
  )
  // WebCrypto produces IEEE P1363 (compact); Python's cryptography library expects DER
  const derSig = p256.Signature.fromBytes(p1363, "compact").toBytes("der") as Uint8Array

  const metadata = JSON.stringify({
    ENCRYPTED_AES_KEY_B64: toB64(wrappedKey),
    IV_B64: toB64(iv),
    SIGNATURE_B64: toB64(derSig),
  })
  return {
    content: toB64(ciphertext),
    content_metadata: btoa(metadata),
  }
}

/**
 * Decrypt and verify a task result produced by the server.
 * Verifies with serverEcdsaPublicPem (SERVER_ECDSA_PUBLIC), decrypts with USER_RSA_PRIVATE (keys.rsa_private).
 * resultMetadata is plain JSON (not base64), matching the server's encrypt_task_result format.
 */
export async function decryptAndVerify(
  encryptedResult: string,
  resultMetadata: string,
  keys: ClientKeys,
  serverEcdsaPublicPem: string,
): Promise<string> {
  let parsed: { ENCRYPTED_AES_KEY_B64: string; IV_B64: string; SIGNATURE_B64: string }
  try {
    parsed = JSON.parse(resultMetadata)
  } catch {
    throw new Error("Invalid result metadata — expected plain JSON (not base64)")
  }
  const { ENCRYPTED_AES_KEY_B64, IV_B64, SIGNATURE_B64 } = parsed
  if (!ENCRYPTED_AES_KEY_B64 || !IV_B64 || !SIGNATURE_B64) {
    throw new Error("Missing required fields in result metadata (ENCRYPTED_AES_KEY_B64, IV_B64, SIGNATURE_B64)")
  }

  const fromB64 = (b64: string) => Uint8Array.from(atob(b64), (c) => c.charCodeAt(0))
  const ciphertext = fromB64(encryptedResult)
  const encryptedAesKey = fromB64(ENCRYPTED_AES_KEY_B64)
  const iv = fromB64(IV_B64)
  // Server produces DER-encoded signature; WebCrypto verify expects IEEE P1363 (compact)
  const p1363Sig = p256.Signature.fromBytes(fromB64(SIGNATURE_B64), "der").toBytes("compact") as Uint8Array

  let ecdsaPublicKey: CryptoKey
  try {
    ecdsaPublicKey = await crypto.subtle.importKey(
      "spki",
      pemToDer(serverEcdsaPublicPem).buffer as ArrayBuffer,
      { name: "ECDSA", namedCurve: "P-256" },
      false,
      ["verify"],
    )
  } catch {
    throw new Error("Invalid SERVER_ECDSA_PUBLIC_KEY — expected P-256 ECDSA public key in SPKI PEM format (-----BEGIN PUBLIC KEY-----)")
  }

  const dataToVerify = new Uint8Array(ciphertext.length + encryptedAesKey.length + iv.length)
  dataToVerify.set(ciphertext, 0)
  dataToVerify.set(encryptedAesKey, ciphertext.length)
  dataToVerify.set(iv, ciphertext.length + encryptedAesKey.length)

  const valid = await crypto.subtle.verify(
    { name: "ECDSA", hash: "SHA-256" },
    ecdsaPublicKey,
    p1363Sig.buffer as ArrayBuffer,
    dataToVerify,
  )
  if (!valid) {
    throw new Error("Signature verification failed — result may have been tampered with")
  }

  let rsaPrivateKey: CryptoKey
  try {
    rsaPrivateKey = await crypto.subtle.importKey(
      "pkcs8",
      pemToDer(keys.rsa_private).buffer as ArrayBuffer,
      { name: "RSA-OAEP", hash: "SHA-256" },
      false,
      ["unwrapKey"],
    )
  } catch {
    const hint = pemToDer(keys.rsa_private).length < 200
      ? " — the key looks like ECDSA; check you put the RSA key in the correct field"
      : ""
    throw new Error(`Invalid USER_RSA_PRIVATE_KEY — expected RSA private key in PKCS#8 PEM format (-----BEGIN PRIVATE KEY-----)${hint}`)
  }

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
  return new TextDecoder().decode(plaintext)
}
