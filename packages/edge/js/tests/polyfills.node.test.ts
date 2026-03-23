import { describe, test, expect, beforeAll } from '@jest/globals';
import { createHash as nodeCreateHash, createHmac as nodeCreateHmac, randomBytes as nodeRandomBytes } from 'crypto';

describe('Node polyfills', () => {
  beforeAll(async () => {
    await import('../src/polyfills/node');
  });

  test('crypto.createHmac supports chained updates', () => {
    const g = globalThis as any;
    const actual = g.crypto
      .createHmac('sha256', 'secret')
      .update('hello ')
      .update('world')
      .digest('hex');

    const expected = nodeCreateHmac('sha256', 'secret').update('hello ').update('world').digest('hex');
    expect(actual).toBe(expected);
  });

  test('crypto.createHash supports chained updates', () => {
    const g = globalThis as any;
    const actual = g.crypto
      .createHash('sha256')
      .update('hello ')
      .update('world')
      .digest('hex');

    const expected = nodeCreateHash('sha256').update('hello ').update('world').digest('hex');
    expect(actual).toBe(expected);
  });

  test('crypto.randomBytes matches requested length', () => {
    const g = globalThis as any;
    const len = 32;
    const a = g.crypto.randomBytes(len);
    const b = nodeRandomBytes(len);

    expect(a).toBeInstanceOf(Buffer);
    expect(a.length).toBe(len);
    expect(b.length).toBe(len);
  });

  test('Buffer is available globally', () => {
    const g = globalThis as any;
    const buf = g.Buffer.from('ccxt', 'utf8');
    expect(buf.toString('hex')).toBe('63637874');
  });
});
