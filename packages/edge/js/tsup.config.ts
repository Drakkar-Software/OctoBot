import { defineConfig } from "tsup"

export default defineConfig([
  // ESM for Node / Bun / Deno
  {
    entry: {
      index: "src/index.ts",
      "polyfills/node": "src/polyfills/node.ts",
      "polyfills/browser": "src/polyfills/browser.ts",
      "polyfills/crypto": "src/polyfills/crypto.ts",
    },
    format: ["esm"],
    outDir: "dist/esm",
    dts: true,
    splitting: false,
    sourcemap: true,
    target: "node20",
    external: ["ccxt"],
  },
  // CJS for Node require()
  {
    entry: {
      index: "src/index.ts",
      "polyfills/node": "src/polyfills/node.ts",
    },
    format: ["cjs"],
    outDir: "dist/cjs",
    dts: false,
    splitting: false,
    sourcemap: true,
    target: "node20",
    external: ["ccxt"],
  },
  // Browser bundle (no Node built-ins, WASM-only Rust bridge)
  {
    entry: {
      index: "src/index.ts",
      "polyfills/browser": "src/polyfills/browser.ts",
    },
    format: ["esm"],
    outDir: "dist/browser",
    outExtension: () => ({ js: ".mjs" }),
    dts: false,
    platform: "browser",
    env: { RUNTIME: "browser" },
    external: ["ccxt"],
  },
  // React Native (CommonJS, no crypto.subtle assumption)
  {
    entry: {
      index: "src/index.ts",
      "polyfills/mobile": "src/polyfills/mobile.ts",
    },
    format: ["cjs"],
    outDir: "dist/rn",
    dts: false,
    platform: "neutral",
    env: { RUNTIME: "react-native" },
    external: ["ccxt", "react-native"],
  },
])
