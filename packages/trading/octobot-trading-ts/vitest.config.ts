import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    globals: false,
    include: ['tests/**/*.test.ts'],
    exclude: process.env.VITEST_REAL_EXCHANGES === '1'
      ? ['node_modules/**', 'dist/**']
      : ['node_modules/**', 'dist/**', 'tests/realExchanges/**'],
    testTimeout: 30000,
    coverage: {
      provider: 'v8',
      reporter: ['text', 'lcov'],
    },
  },
  resolve: {
    alias: {
      '@': new URL('./src/', import.meta.url).pathname,
    },
  },
});
