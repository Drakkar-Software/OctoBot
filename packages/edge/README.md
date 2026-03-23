# OctoBot Edge

Universal CCXT wrapper with Rust-accelerated crypto and polyfills. Available as both a **Python package** (`octobot-edge`) and an **npm package** (`@octobot/edge`), sharing a single Rust core for HMAC, hashing, buffer operations, and HTTP fetch.

Formerly `edge-ccxt` — all code from that repository is now integrated here.

## Concept

CCXT requires crypto (HMAC, hashing), Buffer, and fetch operations that are unavailable or slow on some platforms. OctoBot Edge provides all of these through a compiled Rust core, enabling CCXT to run on mobile (iOS/Android), browser, and server with optimal performance.

Instead of forking CCXT, it monkey-patches `exchange.hmac()` at runtime and provides globalThis polyfills — keeping CCXT up to date while accelerating the hot path.

### Architecture

```
┌─────────────────────────────────────────────────────┐
│                 Rust Core (rust/core/)               │
│  HMAC · Hash · Random · Buffer · Fetch · Encoding   │
└──────────┬──────────┬──────────┬──────────┬─────────┘
           │          │          │          │
           ▼          ▼          ▼          ▼
         PyO3       NAPI       WASM      UniFFI
       (Python)  (Node/Bun)  (Browser) (iOS/Android)
```

When the Rust bridge is unavailable, both Python and JS gracefully fall back to their respective standard library implementations.

## Polyfill Coverage

| Polyfill             | Node/Bun | Browser (WASM) | React Native (UniFFI) | Python |
|----------------------|----------|----------------|-----------------------|--------|
| HMAC (sha256/512)    | Rust     | Rust           | Rust                  | Rust   |
| Hash (sha*/md5)      | Rust     | Rust           | Rust                  | Rust   |
| randomBytes          | Rust     | Rust           | Rust                  | -      |
| Buffer               | Native   | Rust-backed    | Rust-backed           | -      |
| TextEncoder/Decoder  | Native   | Native         | JS polyfill           | -      |
| fetch                | Native   | Native         | Rust (reqwest)        | -      |
| URLSearchParams      | Native   | Native         | JS polyfill           | -      |
| btoa/atob            | Native   | Native         | JS polyfill           | -      |
| Exchange signing     | Rust     | Rust           | Rust                  | Rust   |

## Supported Runtimes

| Runtime        | Rust Bridge     | Status     |
|----------------|-----------------|-----------|
| Python ≥ 3.10  | PyO3 native ext | Full      |
| Node.js ≥ 20   | NAPI native     | Full      |
| Bun ≥ 1.0      | NAPI native     | Full      |
| Deno (local)   | WASM            | Full      |
| Browser        | WASM            | Full      |
| React Native   | UniFFI (iOS/Android) | Full |

## Installation

### Python

```bash
pip install octobot-edge
```

From source (requires Rust toolchain):

```bash
cd packages/edge
pip install -r requirements.txt
cd rust/py && maturin develop --release && cd ../..
pip install -e .
```

### JavaScript / TypeScript

```bash
npm install @octobot/edge
```

## Usage

### Python

```python
from octobot_edge.exchange.client import create_exchange

# Sync exchange
exchange = create_exchange("binance", {
    "apiKey": "your_key",
    "secret": "your_secret",
})

# Async exchange
exchange = create_exchange("binance", {
    "apiKey": "your_key",
    "secret": "your_secret",
}, async_mode=True)

ticker = await exchange.fetch_ticker("BTC/USDT")
```

Direct crypto access:

```python
from octobot_edge.crypto.hmac import hmac_sha256

signature = hmac_sha256(b"secret_key", b"message")
print(signature.hex())
```

### Node.js / Bun

```typescript
import { init, createExchange } from "@octobot/edge"

// Initialize once — auto-detects NAPI (Node/Bun) or WASM (browser/Deno)
await init()

const binance = createExchange("binance", {
  apiKey: "your_key",
  secret: "your_secret",
})

const ticker = await binance.fetchTicker("BTC/USDT")
```

### Browser

```typescript
import { init, createExchange } from "@octobot/edge"

// Loads WASM + installs crypto/Buffer polyfills automatically
await init()

const exchange = createExchange("binance", {
  proxy: "https://your-proxy.example.com/proxy/",
})
```

### React Native (iOS/Android)

```typescript
// 1. Import mobile polyfills BEFORE ccxt (installs crypto, Buffer, fetch, etc.)
import "@octobot/edge/polyfills/mobile"

// 2. Then use normally
import { init, createExchange } from "@octobot/edge"
await init()
const exchange = createExchange("binance", { apiKey: "...", secret: "..." })
```

### Deno

```typescript
import { init, createExchange } from "npm:@octobot/edge"
await init()
```

## Testing

### Python tests (81 tests)

```bash
cd packages/edge
pip install -r full_requirements.txt
pytest tests -v
```

### JavaScript tests

```bash
cd packages/edge/js
npm install
npm test                           # All tests
npm run test:binance               # Live Binance API integration tests
```

### Rust tests

```bash
cd packages/edge/rust
cargo test
```

## Building from Source

### Prerequisites

```bash
# Rust toolchain
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
rustup target add wasm32-unknown-unknown

# Build tools
cargo install wasm-pack
npm install -g @napi-rs/cli
pip install maturin

# For React Native (optional)
cargo install cargo-ndk
npm install -g uniffi-bindgen-react-native
rustup target add aarch64-apple-ios aarch64-linux-android
```

### Build all targets

```bash
cd packages/edge

# 1. Python extension
cd rust/py && maturin develop --release && cd ../..

# 2. WASM (browser + Deno)
cd js && npm run build:wasm && cd ..

# 3. NAPI (Node.js + Bun)
cd js && npm run build:napi && cd ..

# 4. Mobile (React Native)
cd js && npm run build:mobile:ios && cd ..    # iOS
cd js && npm run build:mobile:android && cd .. # Android

# 5. TypeScript → JavaScript
cd js && npm run build && cd ..
```

## Project Layout

```
packages/edge/
├── octobot_edge/              # Python package
│   ├── exchange/              # Exchange factory + normalization
│   ├── crypto/                # HMAC with Rust fallback
│   └── _native.pyi            # Type stubs for Rust extension
├── tests/                     # Python tests
│   └── static/                # Test fixtures (API response samples)
├── rust/                      # Rust workspace
│   ├── core/                  # Shared crypto/buffer/fetch logic (no FFI)
│   ├── wasm/                  # wasm-bindgen target (browser)
│   ├── napi/                  # napi-rs target (Node/Bun)
│   ├── py/                    # PyO3/maturin target (Python)
│   └── mobile/                # UniFFI target (iOS/Android)
├── js/                        # npm package (@octobot/edge)
│   ├── src/
│   │   ├── polyfills/
│   │   │   ├── browser.ts     # WASM crypto + Buffer polyfill
│   │   │   ├── mobile.ts      # UniFFI crypto + Buffer + fetch + URLSearchParams
│   │   │   ├── encoding.ts    # TextEncoder/Decoder for Hermes
│   │   │   ├── crypto.ts      # Basic crypto polyfill
│   │   │   ├── detect.ts      # Runtime detection
│   │   │   └── node.ts        # Node.js test polyfills
│   │   ├── rust-bridge/       # NAPI + WASM loaders
│   │   └── exchange/          # CCXT hmac() patching
│   ├── tests/                 # JS tests
│   ├── scripts/               # Build helpers
│   └── ubrn.config.yaml       # UniFFI React Native config
├── BUILD                      # Pants build targets
├── pyproject.toml             # Python package config
├── requirements.txt           # Python runtime deps
└── full_requirements.txt      # Python dev/test deps
```

## Design Decisions

1. **Shared Rust core** — All crypto, buffer, and fetch operations are implemented once in Rust and exposed via PyO3, NAPI, wasm-bindgen, and UniFFI. No duplicated logic.

2. **Full polyfill coverage** — Beyond HMAC, provides Buffer, fetch, URLSearchParams, btoa/atob, process, and DOMException polyfills for React Native where Node.js APIs are absent.

3. **Graceful fallback** — Python falls back to `hmac`/`hashlib` from stdlib. JS falls back to native `crypto`. The package always works, Rust just makes it faster.

4. **CCXT patching, not forking** — Monkey-patching `exchange.hmac()` at runtime means CCXT stays on the latest version with full exchange support.

5. **No embedded JS interpreter** — Unlike alternatives that bundle QuickJS/Hermes (5+ MB), CCXT runs in the host JS runtime. Only crypto/buffer/fetch are delegated to Rust, resulting in 75% smaller bundles.

## CI/CD

The workflow at `.github/workflows/edge.yml` runs on changes to `packages/edge/`:

- **rust-tests** — `cargo test` on Linux, macOS, Windows
- **build-wasm** — WASM target build + artifact upload
- **build-napi** — Native addons for Linux, macOS, Windows
- **build-python** — Maturin wheel build
- **js-build-test** — TypeScript build + Jest tests
- **python-tests** — pytest with compiled Rust extension
- **publish-npm** / **publish-python** — On `edge-*` tags
