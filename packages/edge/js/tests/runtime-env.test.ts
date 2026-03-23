/**
 * Runtime environment simulation tests.
 *
 * Simulates WASM, React Native, and Deno environments by manipulating
 * globalThis to verify runtime detection and polyfill behavior.
 */
import { describe, test, expect, beforeEach, afterEach, afterAll } from '@jest/globals';
import { detectRuntime } from '../src/polyfills/detect';
import { installEncodingPolyfill } from '../src/polyfills/encoding';
import { createHmac, createHash, randomBytes } from 'crypto';

// Save original globalThis state
const originalDeno = (globalThis as any).Deno;
const originalBun = (globalThis as any).Bun;
const originalWindow = (globalThis as any).window;
const originalNavigator = (globalThis as any).navigator;
const originalTextEncoder = globalThis.TextEncoder;
const originalTextDecoder = globalThis.TextDecoder;

function cleanGlobalThis() {
  delete (globalThis as any).Deno;
  delete (globalThis as any).Bun;
  delete (globalThis as any).window;
  // navigator may not be deletable in all envs
  try { (globalThis as any).navigator = undefined; } catch {}
}

function restoreGlobalThis() {
  if (originalDeno !== undefined) (globalThis as any).Deno = originalDeno;
  else delete (globalThis as any).Deno;
  if (originalBun !== undefined) (globalThis as any).Bun = originalBun;
  else delete (globalThis as any).Bun;
  if (originalWindow !== undefined) (globalThis as any).window = originalWindow;
  else delete (globalThis as any).window;
  if (originalNavigator !== undefined) (globalThis as any).navigator = originalNavigator;
  (globalThis as any).TextEncoder = originalTextEncoder;
  (globalThis as any).TextDecoder = originalTextDecoder;
}

// ── Runtime detection tests ────────────────────────────────────────────────

describe('Runtime detection', () => {
  beforeEach(cleanGlobalThis);
  afterEach(restoreGlobalThis);

  test('detects Node.js by default', () => {
    expect(detectRuntime()).toBe('node');
  });

  test('detects Deno when globalThis.Deno exists', () => {
    (globalThis as any).Deno = { version: { deno: '1.40.0' } };
    expect(detectRuntime()).toBe('deno');
  });

  test('detects Bun when globalThis.Bun exists', () => {
    (globalThis as any).Bun = { version: '1.0.0' };
    expect(detectRuntime()).toBe('bun');
  });

  test('detects browser when window exists', () => {
    (globalThis as any).window = {};
    expect(detectRuntime()).toBe('browser');
  });

  test('detects React Native when navigator.product is ReactNative', () => {
    (globalThis as any).navigator = { product: 'ReactNative' };
    expect(detectRuntime()).toBe('react-native');
  });

  test('Deno takes priority over window', () => {
    (globalThis as any).Deno = {};
    (globalThis as any).window = {};
    expect(detectRuntime()).toBe('deno');
  });

  test('Bun takes priority over window', () => {
    (globalThis as any).Bun = {};
    (globalThis as any).window = {};
    expect(detectRuntime()).toBe('bun');
  });
});

// ── React Native polyfill simulation ───────────────────────────────────────

describe('React Native environment simulation', () => {
  beforeEach(() => {
    cleanGlobalThis();
    (globalThis as any).navigator = { product: 'ReactNative' };
  });

  afterEach(restoreGlobalThis);

  test('runtime detected as react-native', () => {
    expect(detectRuntime()).toBe('react-native');
  });

  test('TextEncoder polyfill works when native is missing', () => {
    // Simulate Hermes: no TextEncoder
    (globalThis as any).TextEncoder = undefined;
    (globalThis as any).TextDecoder = undefined;

    installEncodingPolyfill();

    const encoder = new globalThis.TextEncoder();

    // ASCII
    expect(Array.from(encoder.encode('hello'))).toEqual([0x68, 0x65, 0x6c, 0x6c, 0x6f]);

    // Multi-byte (emoji — 4-byte UTF-8)
    expect(Array.from(encoder.encode('😀'))).toEqual([0xf0, 0x9f, 0x98, 0x80]);

    // CJK (3-byte UTF-8)
    expect(Array.from(encoder.encode('中'))).toEqual([0xe4, 0xb8, 0xad]);
  });

  test('TextDecoder polyfill roundtrips correctly', () => {
    (globalThis as any).TextEncoder = undefined;
    (globalThis as any).TextDecoder = undefined;

    installEncodingPolyfill();

    const encoder = new globalThis.TextEncoder();
    const decoder = new globalThis.TextDecoder();

    const testStrings = [
      'hello world',
      'café au lait',
      '日本語テスト',
      '🎉🚀💻🎊',
      'mixed ASCII 中文 and émoji 🎉',
      '',
      'a\0b',  // null byte
    ];

    for (const s of testStrings) {
      const encoded = encoder.encode(s);
      const decoded = decoder.decode(encoded);
      expect(decoded).toBe(s);
    }
  });

  test('TextEncoder polyfill matches native for exchange signing payloads', () => {
    (globalThis as any).TextEncoder = undefined;
    (globalThis as any).TextDecoder = undefined;

    installEncodingPolyfill();

    const polyfillEncoder = new globalThis.TextEncoder();

    // Typical exchange API payloads
    const payloads = [
      'symbol=BTCUSDT&side=BUY&type=LIMIT&timeInForce=GTC&quantity=1&price=50000.00&timestamp=1700000000000',
      'api_key=abc123def456&sign=abcdef0123456789',
      'GET\n/api/v5/account/balance\n1700000000.000\n',
      'timestamp=1700000000000&recvWindow=5000',
    ];

    for (const payload of payloads) {
      const polyfillResult = polyfillEncoder.encode(payload);
      const nativeResult = originalTextEncoder ? new originalTextEncoder().encode(payload) : polyfillResult;
      expect(Array.from(polyfillResult)).toEqual(Array.from(nativeResult));
    }
  });
});

// ── WASM environment simulation ────────────────────────────────────────────

describe('WASM/browser environment simulation', () => {
  beforeEach(() => {
    cleanGlobalThis();
    (globalThis as any).window = {};
  });

  afterEach(restoreGlobalThis);

  test('runtime detected as browser', () => {
    expect(detectRuntime()).toBe('browser');
  });

  test('crypto polyfills can create HMAC in browser-like env', async () => {
    // The node polyfills module installs crypto.createHmac on globalThis
    // This simulates what happens when the WASM bridge loads
    await import('../src/polyfills/node');

    const g = globalThis as any;
    const result = g.crypto
      .createHmac('sha256', 'NhqPtmdSJYdKjVHjA7PZj4Mge3R5YNiP1e3UZjInClVN65XAbvqqM6A7H5fATj0j')
      .update('symbol=LTCBTC&side=BUY&type=LIMIT&timeInForce=GTC&quantity=1&price=0.1&recvWindow=5000&timestamp=1499827319559')
      .digest('hex');

    expect(result).toBe('c8db56825ae71d6d79447849e617115f4a920fa2acdcab2b053c4b2838bd6b71');
  });

  test('crypto polyfills produce correct sha512 HMAC', async () => {
    await import('../src/polyfills/node');

    const g = globalThis as any;
    const result = g.crypto
      .createHmac('sha512', 'secret_key')
      .update('test_message')
      .digest('hex');

    const expected = createHmac('sha512', 'secret_key').update('test_message').digest('hex');
    expect(result).toBe(expected);
  });

  test('crypto polyfills support hash chaining', async () => {
    await import('../src/polyfills/node');

    const g = globalThis as any;
    const result = g.crypto
      .createHash('sha256')
      .update('part1')
      .update('part2')
      .update('part3')
      .digest('hex');

    const expected = createHash('sha256').update('part1').update('part2').update('part3').digest('hex');
    expect(result).toBe(expected);
  });

  test('Buffer polyfill is available', async () => {
    await import('../src/polyfills/node');

    const g = globalThis as any;
    expect(g.Buffer).toBeDefined();

    // Test Buffer operations used by ccxt
    const b = g.Buffer.from('68656c6c6f', 'hex');
    expect(b.toString('utf8')).toBe('hello');

    const b2 = g.Buffer.from('hello', 'utf8');
    expect(b2.toString('hex')).toBe('68656c6c6f');

    const b3 = g.Buffer.from('aGVsbG8=', 'base64');
    expect(b3.toString('utf8')).toBe('hello');
  });

  test('randomBytes produces correct length', async () => {
    await import('../src/polyfills/node');

    const g = globalThis as any;
    for (const len of [16, 32, 48, 64]) {
      const bytes = g.crypto.randomBytes(len);
      expect(bytes.length).toBe(len);
    }
  });
});

// ── Deno environment simulation ────────────────────────────────────────────

describe('Deno environment simulation', () => {
  beforeEach(() => {
    cleanGlobalThis();
    (globalThis as any).Deno = { version: { deno: '2.0.0' } };
  });

  afterEach(restoreGlobalThis);

  test('runtime detected as deno', () => {
    expect(detectRuntime()).toBe('deno');
  });

  test('Deno has native TextEncoder so polyfill is not needed', () => {
    // In real Deno, TextEncoder exists natively
    // Just verify our detection picks deno runtime
    expect(globalThis.TextEncoder).toBeDefined();
  });
});

// ── Cross-environment HMAC consistency ─────────────────────────────────────

describe('Cross-environment signing consistency', () => {
  const SECRET = 'NhqPtmdSJYdKjVHjA7PZj4Mge3R5YNiP1e3UZjInClVN65XAbvqqM6A7H5fATj0j';
  const QUERY = 'symbol=LTCBTC&side=BUY&type=LIMIT&timeInForce=GTC&quantity=1&price=0.1&recvWindow=5000&timestamp=1499827319559';
  const EXPECTED = 'c8db56825ae71d6d79447849e617115f4a920fa2acdcab2b053c4b2838bd6b71';

  test('Node crypto produces correct Binance signature', () => {
    const result = createHmac('sha256', SECRET).update(QUERY).digest('hex');
    expect(result).toBe(EXPECTED);
  });

  test('TextEncoder-based signing matches crypto-based signing', () => {
    // This is what the bridge does: encode strings to Uint8Array then HMAC
    const enc = new TextEncoder();
    const keyBytes = enc.encode(SECRET);
    const msgBytes = enc.encode(QUERY);

    // Node's createHmac accepts Uint8Array
    const result = createHmac('sha256', keyBytes).update(msgBytes).digest('hex');
    expect(result).toBe(EXPECTED);
  });

  test('Uint8Array key produces same result as string key for ASCII', () => {
    const enc = new TextEncoder();

    // This verifies our patching approach: we encode(secret) and encode(request)
    // which must produce the same HMAC as using raw strings
    const stringResult = createHmac('sha256', SECRET).update(QUERY).digest('hex');
    const bytesResult = createHmac('sha256', enc.encode(SECRET))
      .update(enc.encode(QUERY))
      .digest('hex');

    expect(bytesResult).toBe(stringResult);
  });

  test('multiple exchange secrets produce unique signatures', () => {
    const secrets = [
      'NhqPtmdSJYdKjVHjA7PZj4Mge3R5YNiP1e3UZjInClVN65XAbvqqM6A7H5fATj0j',
      't7T0YlFnYXk0Fx3JswQsDrViLg1Gh3DUU5Mr',
      'kQwJkAx1rvnmEd9mLqPZBjXhxYIjVHMO',
      'VGhpcyBpcyBhIHRlc3Qgc2VjcmV0IGtleQ==',
    ];

    const results = new Set(
      secrets.map((s) => createHmac('sha256', s).update(QUERY).digest('hex'))
    );

    expect(results.size).toBe(secrets.length);
  });
});
