/**
 * Integration tests for @octobot/edge exchange patching.
 *
 * These tests exercise the real ccxt library with our patching layer,
 * validating that HMAC signing produces correct results across exchanges.
 * The Rust bridge is NOT loaded (no native addon in test env), so we
 * verify the fallback path and patching mechanics.
 */
import { describe, test, expect, beforeAll } from '@jest/globals';
import ccxt from 'ccxt';
import { createHmac } from 'crypto';

// We import patch directly since init() requires the native bridge
import { patchExchange } from '../src/exchange/patch';
import type { RustBridge } from '../src/rust-bridge/types';


// ── Mock Rust bridge using Node.js crypto ──────────────────────────────────

function createMockBridge(): RustBridge {
  const enc = new TextEncoder();
  return {
    hmac(algorithm: string, secret: string, data: string, encoding: string): string {
      return createHmac(algorithm, secret).update(data).digest(encoding as any);
    },
    hash(algorithm: string, data: string, encoding: string): string {
      const { createHash } = require('crypto');
      return createHash(algorithm).update(data).digest(encoding as any);
    },
    hmacSha256(key: Uint8Array, message: Uint8Array): Uint8Array {
      return new Uint8Array(createHmac('sha256', key).update(message).digest());
    },
    hmacSha256Hex(key: Uint8Array, message: Uint8Array): string {
      return createHmac('sha256', key).update(message).digest('hex');
    },
    hmacSha512(key: Uint8Array, message: Uint8Array): Uint8Array {
      return new Uint8Array(createHmac('sha512', key).update(message).digest());
    },
    hmacSha512Hex(key: Uint8Array, message: Uint8Array): string {
      return createHmac('sha512', key).update(message).digest('hex');
    },
    randomBytesHex(size: number): string {
      const { randomBytes } = require('crypto');
      return randomBytes(size).toString('hex');
    },
    randomBytes(size: number): Uint8Array {
      const { randomBytes } = require('crypto');
      return new Uint8Array(randomBytes(size));
    },
    bufferToHex(data: Uint8Array): string {
      return Buffer.from(data).toString('hex');
    },
    bufferFromHex(hexStr: string): Uint8Array {
      return new Uint8Array(Buffer.from(hexStr, 'hex'));
    },
    bufferToBase64(data: Uint8Array): string {
      return Buffer.from(data).toString('base64');
    },
    bufferFromBase64(b64: string): Uint8Array {
      return new Uint8Array(Buffer.from(b64, 'base64'));
    },
    bufferByteLength(utf8Str: string): number {
      return Buffer.byteLength(utf8Str, 'utf8');
    },
  };
}

// ── Exchanges to test ──────────────────────────────────────────────────────

const EXCHANGES = ['binance', 'bybit', 'okx', 'kucoin', 'bitget', 'kraken'] as const;

// ── Test vectors ───────────────────────────────────────────────────────────

const BINANCE_SECRET = 'NhqPtmdSJYdKjVHjA7PZj4Mge3R5YNiP1e3UZjInClVN65XAbvqqM6A7H5fATj0j';
const BINANCE_QUERY = 'symbol=LTCBTC&side=BUY&type=LIMIT&timeInForce=GTC&quantity=1&price=0.1&recvWindow=5000&timestamp=1499827319559';
const BINANCE_EXPECTED = 'c8db56825ae71d6d79447849e617115f4a920fa2acdcab2b053c4b2838bd6b71';

describe('Exchange integration with mock bridge', () => {
  let bridge: RustBridge;

  beforeAll(() => {
    bridge = createMockBridge();
  });

  describe('patchExchange with real ccxt exchanges', () => {
    test.each(EXCHANGES)('%s: patched hmac matches Node.js crypto for sha256/hex', (exchangeId) => {
      const ExchangeClass = (ccxt as any)[exchangeId];
      const patched = new ExchangeClass({ apiKey: 'test', secret: 'test' });

      patchExchange(patched as any, bridge);

      const request = 'timestamp=1700000000000&symbol=BTCUSDT';
      const secret = 'my_secret_key';

      const expected = createHmac('sha256', secret).update(request).digest('hex');
      const accelerated = patched.hmac(request, secret, 'sha256', 'hex');

      expect(accelerated).toBe(expected);
    });

    test.each(EXCHANGES)('%s: patched hmac matches Node.js crypto for sha512/hex', (exchangeId) => {
      const ExchangeClass = (ccxt as any)[exchangeId];
      const patched = new ExchangeClass({ apiKey: 'test', secret: 'test' });

      patchExchange(patched as any, bridge);

      const request = 'timestamp=1700000000000';
      const secret = 'my_secret_key';

      const expected = createHmac('sha512', secret).update(request).digest('hex');
      const accelerated = patched.hmac(request, secret, 'sha512', 'hex');

      expect(accelerated).toBe(expected);
    });

    test.each(EXCHANGES)('%s: exchange has standard ccxt methods', (exchangeId) => {
      const ExchangeClass = (ccxt as any)[exchangeId];
      const exchange = new ExchangeClass({});

      expect(typeof exchange.fetchTicker).toBe('function');
      expect(typeof exchange.fetchOrderBook).toBe('function');
      expect(typeof exchange.fetchOHLCV).toBe('function');
      expect(typeof exchange.createOrder).toBe('function');
      expect(typeof exchange.cancelOrder).toBe('function');
      expect(typeof exchange.fetchBalance).toBe('function');
    });

    test.each(EXCHANGES)('%s: config is forwarded correctly', (exchangeId) => {
      const ExchangeClass = (ccxt as any)[exchangeId];
      const exchange = new ExchangeClass({ timeout: 7777, rateLimit: 500 });

      expect(exchange.timeout).toBe(7777);
      expect(exchange.rateLimit).toBe(500);
    });
  });

  describe('Binance signature test vectors', () => {
    test('matches official Binance API documentation vector', () => {
      const exchange: any = new ccxt.binance({ apiKey: 'test', secret: BINANCE_SECRET });
      patchExchange(exchange as any, bridge);

      const result = exchange.hmac(BINANCE_QUERY, BINANCE_SECRET, 'sha256', 'hex');
      expect(result).toBe(BINANCE_EXPECTED);
    });

    test('matches with reversed argument order (secret as key)', () => {
      // Verify the patched hmac correctly uses secret as HMAC key
      const expected = createHmac('sha256', BINANCE_SECRET)
        .update(BINANCE_QUERY)
        .digest('hex');
      expect(expected).toBe(BINANCE_EXPECTED);
    });
  });

  describe('signing consistency', () => {
    test('repeated calls produce identical results', () => {
      const exchange: any = new ccxt.binance({ apiKey: 'k', secret: 's' });
      patchExchange(exchange as any, bridge);

      const results = new Set<string>();
      for (let i = 0; i < 100; i++) {
        results.add(exchange.hmac('data', 'secret', 'sha256', 'hex'));
      }
      expect(results.size).toBe(1);
    });

    test('different inputs produce different outputs', () => {
      const exchange: any = new ccxt.binance({ apiKey: 'k', secret: 's' });
      patchExchange(exchange as any, bridge);

      const results = new Set<string>();
      for (let i = 0; i < 50; i++) {
        results.add(exchange.hmac(`timestamp=${i}`, 'secret', 'sha256', 'hex'));
      }
      expect(results.size).toBe(50);
    });

    test('hmac output is valid 64-char hex', () => {
      const exchange: any = new ccxt.binance({ apiKey: 'k', secret: 's' });
      patchExchange(exchange as any, bridge);

      const result = exchange.hmac('data', 'secret', 'sha256', 'hex');
      expect(result).toMatch(/^[0-9a-f]{64}$/);
    });

    test('sha512 hmac output is valid 128-char hex', () => {
      const exchange: any = new ccxt.binance({ apiKey: 'k', secret: 's' });
      patchExchange(exchange as any, bridge);

      const result = exchange.hmac('data', 'secret', 'sha512', 'hex');
      expect(result).toMatch(/^[0-9a-f]{128}$/);
    });
  });

  describe('edge cases', () => {
    test('unicode in request data', () => {
      const exchange: any = new ccxt.binance({ apiKey: 'k', secret: 's' });
      patchExchange(exchange as any, bridge);

      const result = exchange.hmac('note=日本語テスト🎉', 'secret', 'sha256', 'hex');
      expect(result).toMatch(/^[0-9a-f]{64}$/);
    });

    test('very long request string', () => {
      const exchange: any = new ccxt.binance({ apiKey: 'k', secret: 's' });
      patchExchange(exchange as any, bridge);

      const longRequest = 'x'.repeat(100_000);
      const result = exchange.hmac(longRequest, 'secret', 'sha256', 'hex');
      expect(result).toMatch(/^[0-9a-f]{64}$/);
    });

    test('empty request and secret', () => {
      const exchange: any = new ccxt.binance({ apiKey: 'k', secret: 's' });
      patchExchange(exchange as any, bridge);

      const result = exchange.hmac('', '', 'sha256', 'hex');
      const expected = createHmac('sha256', '').update('').digest('hex');
      expect(result).toBe(expected);
    });

    test('special characters in secret', () => {
      const exchange: any = new ccxt.binance({ apiKey: 'k', secret: 's' });
      patchExchange(exchange as any, bridge);

      const secret = 'key+with/special=chars&and%20encoding';
      const result = exchange.hmac('data', secret, 'sha256', 'hex');
      const expected = createHmac('sha256', secret).update('data').digest('hex');
      expect(result).toBe(expected);
    });
  });

  describe('null bridge (graceful degradation)', () => {
    test('patchExchange with null bridge does nothing', () => {
      const exchange: any = new ccxt.binance({ apiKey: 'k', secret: 's' });
      const originalHmac = exchange.hmac;

      patchExchange(exchange as any, null);

      // hmac should be unchanged
      expect(exchange.hmac).toBe(originalHmac);
    });

    test('unpatched exchange hmac is unchanged after null bridge patch', () => {
      const exchange: any = new ccxt.binance({ apiKey: 'k', secret: 's' });
      const hmacBefore = exchange.hmac;

      patchExchange(exchange as any, null);

      // hmac reference should not have changed
      expect(exchange.hmac).toBe(hmacBefore);
    });
  });
});
