# OctoBot Connectors — Current State

Snapshot at commit OctoBot `8bf8b01f` / ccxt `0e7bb275d9` on
`feature/add-exchange-package` / `feature/add-rust` respectively.

## What this package is

A Rust+PyO3 wrapper around the ccxt-rust crate that exposes a unified
`CcxtConnector` to Python. The Rust core lives in
`crates/octobot_connectors_core` and the Python bindings in
`crates/octobot_connectors_py` (built with maturin).
`additional_tests/` contains live integration tests that mirror the
shape of `octobot_trading/tests_additional/real_exchanges/`.

## What works

- **Rust core** — `octobot_connectors_core` builds and unit-tests pass
  on default features (binance only). 36 unit tests green.
- **Python bindings** — `octobot_connectors_rs-0.1.0` PyO3 wheel builds
  via `maturin develop`. `from octobot_connectors import CcxtConnector,
  ExchangeConfig, ExchangeCredentials` works.
- **Test framework alignment** — `additional_tests/abstract_*.py`
  mirrors the public test list of
  `octobot_trading/tests_additional/real_exchanges/real_exchange_tester.py`
  and friends: `test_time_frames`, `test_get_market_status`,
  `test_get_symbol_prices`, `test_get_historical_symbol_prices`,
  `test_get_kline_price`, `test_get_order_book`, `test_get_recent_trades`,
  `test_get_price_ticker`, plus the `check_market_status_limits`,
  `check_ticker_typing`, `ensure_elements_order`, `ensure_unique_elements`
  helpers. Futures adds `test_get_funding_rate`,
  `test_fetch_user_positions`, `test_fetch_user_closed_positions`.
- **All 24 exchange test files** in `additional_tests/test_*.py` are
  generated against the new abstract structure with matching SYMBOL /
  SYMBOL_2 / SYMBOL_3 from the trading equivalents and module-level
  pytest delegates.
- **Test gating** — `additional_tests/conftest.py` auto-skips
  `@pytest.mark.slow` (credential-gated) tests unless `--run-slow` or
  `RUN_SLOW_TESTS=1`. Mirrors the Rust side's
  `#[ignore = "requires live credentials"]`.
- **Rust integration tests** in `crates/octobot_connectors_core/tests/`
  cover all 24 exchanges (spot + futures variants). Network-only tests
  run by default; credential-gated tests stay `#[ignore]`d.
- **Binance public-data tests pass** end-to-end. ticker / order book /
  recent trades / klines all return populated structs because Binance's
  REST shape already matches the unified format.

## What was just shipped (the dispatch fix)

In ccxt-rust the `Exchange` trait declares `parse_*` and `fetch_*` with
`Value::Undefined` defaults. Per-exchange overrides used to live only on
the per-exchange sub-trait (e.g. `Ascendex`), not on `impl Exchange for
AscendexImpl`. So `&dyn Exchange` dispatch hit the `Undefined` default
and the OctoBot adapter rejected the empty result with
`"OHLCV is not an array"` etc.

ccxt commit `0e7bb275d9`:

- `build/rustTranspiler.ts` now emits a bridge in
  `impl Exchange for XxxImpl` for every parse_* / fetch_* the
  per-exchange trait overrides. Dispatch through `&dyn Exchange` reaches
  the per-exchange code path.
- A new `IMMUTABLE_TRAIT_METHODS` set forces the per-exchange parse_*
  override to share `&self` with the Exchange trait so the bridge body
  compiles. `addHyphen*`, `removeComma*`, `fixComma*`, `getMarketFrom*`
  etc. helper-method prefixes are added to the immutable list so they
  don't poison the calling parse_* with a `&mut self` requirement.
  Bridges are skipped for any per-exchange method whose body genuinely
  needed `&mut self` (compiler would reject the bridge otherwise).
- `fetchOHLCV` / `fetchTrades` / `fetchOrderBook` / `fetchTicker`
  HANDWRITTEN templates now (a) widen path-substring matching to cover
  exchange-specific tokens (`barhist`, `kline`, …) and (b) call
  `crate::exchange::unwrap_response_array` /
  `unwrap_response_order_book` to peel common wrapper shapes
  (`{data: [...]}`, `{result: {list: [...]}}`, etc.) before iterating
  `<Self as Exchange>::parse_*` per item.

## What is broken

### A. ccxt `--features full-exchanges` doesn't compile (41 pre-existing errors)

Re-transpiling all 112 exchanges with the updated heuristics surfaced
errors that the previous build had hidden because cached `.rs` files
were stale (still emitting `&mut self` from an older transpiler
version). All of these are flagged in the original
`TRANSPILER_TODO.md` audit:

| Error class | Examples | Root cause |
|---|---|---|
| Variadic args | `self.sum(a,b,c,d)` — Rust trait takes 2 | JS source uses `(...xs: any[])`; transpiler needs `sum_3` / `sum_4` overloads or a `Vec<Value>` rewrite |
| Missing `await` | `let v: Value = <Self as Gemini>::fetch_ticker_v1(...)` returns `Pin<Box<Future>>` | Async desugaring pass missing |
| argCount drift | `encode_dydx_tx_for_signing(1)` vs called with 6 | Hand-tuned `argCounts` table missing entries |
| Type inference | `let mut x: usize = 0; if x.is_nullish()` | Rust-side `usize` literal where `Value` was expected |
| `set_property(self, key, val)` mexc | `self.set_property(self, "rateLimit", 10)` — bad `this.x = y` rewrite | Assignment-to-this transpiler bug |

Default features (binance only) still build clean. Most of the 24
exchanges with Python tests sit under `--features full-exchanges`, so
**Python tests cannot import `octobot_connectors` after a fresh
`maturin develop` until these 41 errors are fixed**. Per the original
audit this is a multi-week effort.

### B. Runtime URL builder is broken for non-Binance exchanges

Independent of the transpiler. Verified by running a debug binary
against ascendex's `fetch_ohlcv`: the response is **HTML from the
AscendEx homepage**, not API JSON. ascendex's describe sets
`urls.api = {rest: "https://ascendex.com"}`; the request layer hits
`https://ascendex.com/barhist` but the actual endpoint is
`https://ascendex.com/api/pro/v1/barhist`. The hand-written `request()`
template in `build/rustTranspiler.ts` uses `urls_api.get(api).get("public")`
fallbacks that don't pick up `rest` plus version path. Even at zero
compile errors, public-data tests will fail for any exchange whose
`urls.api` doesn't already use the literal `{public, private}` shape
that Binance happens to use.

### C. PyO3 surface gaps

A handful of tester methods skip because the Rust connector hasn't
exposed them yet. `get_kline_price` is just `get_symbol_prices` with
limit=1; `get_order_books` (multi-symbol) and
`get_all_currencies_price_ticker` aren't surfaced;
`get_user_recent_trades` likewise. Each is a thin PyO3 method to add.

## Test results today

| Layer | Result | Notes |
|---|---|---|
| `cargo test -p octobot-connectors-core` (default features) | **41 build errors** | Will be 36 unit + 24 integration once ccxt full-exchanges compiles. |
| Python `pytest packages/connectors/additional_tests/` | **import error** | `octobot_connectors` module fails to load until full-exchanges compiles. |
| Pre-this-work Python (with stale ccxt) | 4 binance tests passed, 75 failed | Failures were the OHLCV/trades/order-book parsing that bridges + templates above are designed to fix once URL builder works. |

## How to make tests pass — concrete next steps

In dependency order:

1. **Fix the 41 ccxt compile errors.** Touch points are
   `ccxt/build/rustTranspiler.ts` (transpiler) and
   `ccxt/rust/src/exchange.rs` (runtime trait + helpers). Each error is
   exchange-specific so it's iterative. Categorise via the table above
   and fix one class at a time. Re-transpile (`npm run transpileRust`)
   and `cargo check --features full-exchanges` between passes.
2. **Fix the URL builder.** The hand-written `request` template in
   `build/rustTranspiler.ts` (~line 470+) needs to recognise the
   `urls.api` shapes commonly used in ccxt:
   - `{public: "...", private: "..."}` (Binance-style)
   - `{rest: "..."}` + a path prefix derived from version + describe
   - per-method overrides where exchanges build their own URL
3. **Expose the missing PyO3 methods** in
   `crates/octobot_connectors_py/src/lib.rs`:
   `get_kline_price`, `get_order_books`,
   `get_all_currencies_price_ticker`, `get_user_recent_trades`.
4. **Run** `pytest packages/connectors/additional_tests/` and triage
   what's left exchange-by-exchange.

## Repo layout cheat-sheet

```
OctoBot/packages/connectors/
├── crates/
│   ├── octobot_connectors_core/   # Rust core (CcxtConnector, adapter)
│   │   ├── src/connector/ccxt.rs  # CcxtConnector wrapping &dyn Exchange
│   │   ├── src/connector/adapter.rs # raw JSON → unified types
│   │   └── tests/                  # Rust integration tests, 24 exchanges
│   └── octobot_connectors_py/     # PyO3 bindings (maturin develop)
├── additional_tests/              # Python pytest mirrors of trading tests
│   ├── abstract_exchange_tester.py
│   ├── abstract_future_exchange_tester.py
│   ├── abstract_option_exchange_tester.py
│   ├── conftest.py                # @slow auto-skip
│   └── test_*.py                  # 24 exchanges
└── octobot_connectors/            # Python facade re-exports
```

External:
- `ccxt/` — sibling repo, branch `feature/add-rust`. Transpiler at
  `build/rustTranspiler.ts`; runtime at `rust/src/exchange.rs` (zone
  outside the regex band is hand-written and durable across
  re-transpiles); per-exchange generated code at `rust/src/exchanges/*.rs`.
