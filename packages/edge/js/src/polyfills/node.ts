/**
 * Node.js polyfills for testing.
 * Patches globalThis to use Node.js built-in crypto and Buffer.
 */

import * as nodeCrypto from 'crypto';

if (!globalThis.crypto) {
  (globalThis as any).crypto = {};
}

(globalThis.crypto as any).createHmac = (algorithm: string, key: string | Buffer) => {
  const hmac = nodeCrypto.createHmac(algorithm, key);
  const builder = {
    update: (data: string | Buffer) => {
      hmac.update(data);
      return builder;
    },
    digest: (encoding: string) => {
      return hmac.digest(encoding as any);
    },
  };
  return builder;
};

(globalThis.crypto as any).createHash = (algorithm: string) => {
  const hash = nodeCrypto.createHash(algorithm);
  const builder = {
    update: (data: string | Buffer) => {
      hash.update(data);
      return builder;
    },
    digest: (encoding: string) => {
      return hash.digest(encoding as any);
    },
  };
  return builder;
};

(globalThis.crypto as any).randomBytes = nodeCrypto.randomBytes;

if (!globalThis.Buffer) {
  (globalThis as any).Buffer = Buffer;
}

export {};
