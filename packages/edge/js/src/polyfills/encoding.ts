/**
 * TextEncoder/Decoder polyfill for Hermes (React Native).
 * Only installed if not already available.
 */
export function installEncodingPolyfill(): void {
  if (typeof globalThis.TextEncoder === "undefined") {
    (globalThis as any).TextEncoder = class TextEncoder {
      encode(input: string): Uint8Array {
        // Proper UTF-8 encoding: handle multi-byte characters and surrogate pairs
        const bytes: number[] = []
        for (let i = 0; i < input.length; i++) {
          let cp = input.codePointAt(i)!
          if (cp >= 0xd800 && cp <= 0xdfff) {
            // Lone surrogate — encode as U+FFFD replacement character (3-byte UTF-8)
            cp = 0xfffd
          }
          if (cp < 0x80) {
            bytes.push(cp)
          } else if (cp < 0x800) {
            bytes.push(0xc0 | (cp >> 6), 0x80 | (cp & 0x3f))
          } else if (cp < 0x10000) {
            bytes.push(0xe0 | (cp >> 12), 0x80 | ((cp >> 6) & 0x3f), 0x80 | (cp & 0x3f))
          } else {
            bytes.push(
              0xf0 | (cp >> 18),
              0x80 | ((cp >> 12) & 0x3f),
              0x80 | ((cp >> 6) & 0x3f),
              0x80 | (cp & 0x3f),
            )
            i++ // skip low surrogate of the pair
          }
        }
        return new Uint8Array(bytes)
      }
    }
  }

  if (typeof globalThis.TextDecoder === "undefined") {
    (globalThis as any).TextDecoder = class TextDecoder {
      decode(input: Uint8Array): string {
        // Proper UTF-8 decoding: reconstruct multi-byte sequences
        let result = ""
        let i = 0
        while (i < input.length) {
          const b0 = input[i]
          if (b0 < 0x80) {
            // 1-byte (ASCII)
            result += String.fromCodePoint(b0)
            i += 1
          } else if ((b0 & 0xe0) === 0xc0) {
            // 2-byte sequence
            if (i + 1 >= input.length) { result += "\ufffd"; i += 1; continue }
            const b1 = input[i + 1]
            if ((b1 & 0xc0) !== 0x80) { result += "\ufffd"; i += 1; continue }
            const cp = ((b0 & 0x1f) << 6) | (b1 & 0x3f)
            // Reject overlong encoding
            result += cp >= 0x80 ? String.fromCodePoint(cp) : "\ufffd"
            i += 2
          } else if ((b0 & 0xf0) === 0xe0) {
            // 3-byte sequence
            if (i + 2 >= input.length) { result += "\ufffd"; i += 1; continue }
            const b1 = input[i + 1]
            const b2 = input[i + 2]
            if ((b1 & 0xc0) !== 0x80 || (b2 & 0xc0) !== 0x80) { result += "\ufffd"; i += 1; continue }
            const cp = ((b0 & 0x0f) << 12) | ((b1 & 0x3f) << 6) | (b2 & 0x3f)
            // Reject overlong and surrogate range
            if (cp < 0x800 || (cp >= 0xd800 && cp <= 0xdfff)) {
              result += "\ufffd"
            } else {
              result += String.fromCodePoint(cp)
            }
            i += 3
          } else if ((b0 & 0xf8) === 0xf0) {
            // 4-byte sequence
            if (i + 3 >= input.length) { result += "\ufffd"; i += 1; continue }
            const b1 = input[i + 1]
            const b2 = input[i + 2]
            const b3 = input[i + 3]
            if ((b1 & 0xc0) !== 0x80 || (b2 & 0xc0) !== 0x80 || (b3 & 0xc0) !== 0x80) { result += "\ufffd"; i += 1; continue }
            const cp = ((b0 & 0x07) << 18) | ((b1 & 0x3f) << 12) | ((b2 & 0x3f) << 6) | (b3 & 0x3f)
            // Reject overlong and out-of-range
            if (cp < 0x10000 || cp > 0x10ffff) {
              result += "\ufffd"
            } else {
              result += String.fromCodePoint(cp)
            }
            i += 4
          } else {
            // Invalid lead byte
            result += "\ufffd"
            i += 1
          }
        }
        return result
      }
    }
  }
}
