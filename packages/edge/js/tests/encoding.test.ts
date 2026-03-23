import { describe, test, expect, beforeAll, afterAll } from '@jest/globals';
import { installEncodingPolyfill } from '../src/polyfills/encoding';

describe('TextEncoder/TextDecoder polyfill', () => {
  // Save originals and remove them to force polyfill installation
  const origEncoder = globalThis.TextEncoder;
  const origDecoder = globalThis.TextDecoder;

  beforeAll(() => {
    (globalThis as any).TextEncoder = undefined;
    (globalThis as any).TextDecoder = undefined;
    installEncodingPolyfill();
  });

  afterAll(() => {
    (globalThis as any).TextEncoder = origEncoder;
    (globalThis as any).TextDecoder = origDecoder;
  });

  describe('TextEncoder', () => {
    test('encodes ASCII correctly', () => {
      const encoder = new globalThis.TextEncoder();
      const result = encoder.encode('hello');
      expect(Array.from(result)).toEqual([0x68, 0x65, 0x6c, 0x6c, 0x6f]);
    });

    test('encodes 2-byte UTF-8 (Latin characters)', () => {
      const encoder = new globalThis.TextEncoder();
      // é = U+00E9 → 0xC3 0xA9
      const result = encoder.encode('é');
      expect(Array.from(result)).toEqual([0xc3, 0xa9]);
    });

    test('encodes 3-byte UTF-8 (CJK characters)', () => {
      const encoder = new globalThis.TextEncoder();
      // 中 = U+4E2D → 0xE4 0xB8 0xAD
      const result = encoder.encode('中');
      expect(Array.from(result)).toEqual([0xe4, 0xb8, 0xad]);
    });

    test('encodes 4-byte UTF-8 (emoji)', () => {
      const encoder = new globalThis.TextEncoder();
      // 😀 = U+1F600 → 0xF0 0x9F 0x98 0x80
      const result = encoder.encode('😀');
      expect(Array.from(result)).toEqual([0xf0, 0x9f, 0x98, 0x80]);
    });

    test('encodes mixed ASCII and multi-byte', () => {
      const encoder = new globalThis.TextEncoder();
      const result = encoder.encode('a中😀');
      expect(Array.from(result)).toEqual([
        0x61,                         // 'a'
        0xe4, 0xb8, 0xad,            // '中'
        0xf0, 0x9f, 0x98, 0x80,      // '😀'
      ]);
    });

    test('matches native TextEncoder output', () => {
      const native = new origEncoder();
      const polyfill = new globalThis.TextEncoder();
      const testStrings = ['hello', 'café', '日本語', '🎉🎊', 'a\u0000b', ''];
      for (const s of testStrings) {
        expect(Array.from(polyfill.encode(s))).toEqual(Array.from(native.encode(s)));
      }
    });
  });

  describe('TextDecoder', () => {
    test('decodes ASCII correctly', () => {
      const decoder = new globalThis.TextDecoder();
      const result = decoder.decode(new Uint8Array([0x68, 0x65, 0x6c, 0x6c, 0x6f]));
      expect(result).toBe('hello');
    });

    test('decodes 2-byte UTF-8', () => {
      const decoder = new globalThis.TextDecoder();
      const result = decoder.decode(new Uint8Array([0xc3, 0xa9]));
      expect(result).toBe('é');
    });

    test('decodes 3-byte UTF-8 (CJK)', () => {
      const decoder = new globalThis.TextDecoder();
      const result = decoder.decode(new Uint8Array([0xe4, 0xb8, 0xad]));
      expect(result).toBe('中');
    });

    test('decodes 4-byte UTF-8 (emoji)', () => {
      const decoder = new globalThis.TextDecoder();
      const result = decoder.decode(new Uint8Array([0xf0, 0x9f, 0x98, 0x80]));
      expect(result).toBe('😀');
    });

    test('handles truncated sequences with replacement char', () => {
      const decoder = new globalThis.TextDecoder();
      // Truncated 2-byte sequence: just the lead byte
      const result = decoder.decode(new Uint8Array([0xc3]));
      expect(result).toBe('\ufffd');
    });

    test('handles invalid continuation bytes', () => {
      const decoder = new globalThis.TextDecoder();
      // 0xc3 expects a continuation byte, but 0x41 is ASCII
      const result = decoder.decode(new Uint8Array([0xc3, 0x41]));
      expect(result).toBe('\ufffd' + 'A');
    });

    test('roundtrips with TextEncoder', () => {
      const encoder = new globalThis.TextEncoder();
      const decoder = new globalThis.TextDecoder();
      const testStrings = ['hello', 'café', '日本語テスト', '🎉 party 🎊', ''];
      for (const s of testStrings) {
        expect(decoder.decode(encoder.encode(s))).toBe(s);
      }
    });

    test('roundtrip matches native implementation', () => {
      const nativeEnc = new origEncoder();
      const nativeDec = new origDecoder();
      const polyEnc = new globalThis.TextEncoder();
      const polyDec = new globalThis.TextDecoder();

      const testStrings = ['hello world', 'Ünïcödé', '漢字', '🇺🇸🏳️‍🌈', 'mixed café 中文 😀'];
      for (const s of testStrings) {
        // Polyfill encode → polyfill decode
        expect(polyDec.decode(polyEnc.encode(s))).toBe(s);
        // Native encode → polyfill decode
        expect(polyDec.decode(nativeEnc.encode(s))).toBe(s);
        // Polyfill encode → native decode
        expect(nativeDec.decode(polyEnc.encode(s))).toBe(s);
      }
    });
  });
});
