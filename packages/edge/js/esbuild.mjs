import { build } from "esbuild";

// Bundle ccxt for browser — used by both mobile (React Native) and browser builds.
// Node.js built-ins are shimmed away since we provide crypto/fetch/Buffer
// as Rust-backed polyfills patched onto globalThis.
const NODE_BUILTINS = [
  "assert", "buffer", "crypto", "events", "http", "https",
  "net", "stream", "tls", "url", "util", "zlib", "dns",
  "node:assert", "node:buffer", "node:crypto", "node:events",
  "node:http", "node:https", "node:net", "node:stream",
  "node:tls", "node:url", "node:util", "node:zlib", "node:dns",
  "http-proxy-agent", "socks-proxy-agent",
];

const EMPTY_MODULE = "export default {}; export const PassThrough = class {}; export const pipeline = () => {}; export const Buffer = { from: () => new Uint8Array(), alloc: () => new Uint8Array(), isBuffer: () => false }; export const types = {}; export const deprecate = (fn) => fn; export const promisify = (fn) => fn; export const inherits = () => {}; export const isIP = () => 0; export const format = () => ''; export const once = async () => [];";

const nodeShimPlugin = {
  name: "node-builtins-shim",
  setup(b) {
    const builtinFilter = new RegExp(
      "^(" + NODE_BUILTINS.map((n) => n.replace(":", "\\:")).join("|") + ")$",
    );
    b.onResolve({ filter: builtinFilter }, (args) => ({
      path: args.path,
      namespace: "node-shim",
    }));

    b.onResolve({ filter: /^protobufjs/ }, (args) => ({
      path: args.path,
      namespace: "node-shim",
    }));

    b.onLoad({ filter: /.*/, namespace: "node-shim" }, () => ({
      contents: EMPTY_MODULE,
      loader: "js",
    }));
  },
};

await build({
  entryPoints: ["node_modules/ccxt/dist/cjs/ccxt.js"],
  bundle: true,
  outfile: "dist/ccxt.bundle.js",
  format: "cjs",
  platform: "neutral",
  target: "es2020",
  mainFields: ["browser", "module", "main"],
  conditions: ["browser", "import", "default"],
  define: {
    "process.env.NODE_ENV": '"production"',
    "process.version": '"v20.0.0"',
    "process.browser": "true",
    global: "globalThis",
  },
  plugins: [nodeShimPlugin],
  minify: true,
  logLevel: "info",
});
