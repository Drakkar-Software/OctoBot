import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    include: ['tests/**/*.test.ts'],
    exclude: ['node_modules/**', 'dist/**'],
    testTimeout: 10000,
  },
});
