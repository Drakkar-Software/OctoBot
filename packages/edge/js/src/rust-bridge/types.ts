export interface RustBridge {
  // HMAC
  hmacSha256(key: Uint8Array, message: Uint8Array): Uint8Array
  hmacSha256Hex(key: Uint8Array, message: Uint8Array): string
  hmacSha512(key: Uint8Array, message: Uint8Array): Uint8Array
  hmacSha512Hex(key: Uint8Array, message: Uint8Array): string
  hmac(algorithm: string, secret: string, data: string, encoding: string): string
  hash(algorithm: string, data: string, encoding: string): string

  // Random
  randomBytesHex(size: number): string
  randomBytes(size: number): Uint8Array

  // Buffer operations
  bufferToHex(data: Uint8Array): string
  bufferFromHex(hexStr: string): Uint8Array
  bufferToBase64(data: Uint8Array): string
  bufferFromBase64(b64: string): Uint8Array
  bufferByteLength(utf8Str: string): number
}
