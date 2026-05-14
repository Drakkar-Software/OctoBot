# TODO — Programmatic pages: build dependency

The programmatic SEO pages (per-coin, per-exchange, crypto converter matrix) are
**implemented** in this repo but **cannot build** until one external dependency ships:
a public OctoBot Cloud endpoint that returns the slug / coin / exchange list.

Until that endpoint exists, `docusaurus build` fails by design — there is no committed
fallback data (deliberate choice: builds must reflect live data or fail loudly).

---

## What is already done (in this repo)

- `docs/plugins/programmatic-pages/index.js` — Docusaurus plugin. Fetches the endpoint
  once per locale at build time, derives the route sets, registers every route via
  `addRoute`.
- `docs/docusaurus.config.ts` — plugin registered in `plugins:`.
- `docs/src/components/pages/programmatic/` — the 5 Neo Glass Dark page templates
  (`WhatIsCrypto`, `CryptoPrediction`, `ConverterPair`, `ExchangeTradingBot`,
  `ExchangeMarketMaker`), shared types, and the static-rate `ConverterWidget`.
- `docs/src/components/landing/TradingViewWidget/` — client-only price-chart embed.

Verified end-to-end against a throwaway local fixture: `tsc` clean, `docusaurus build`
succeeds for `en` + `fr`, all route families render with SSR content.

---

## What is missing — the endpoint

### 1. Build and deploy the endpoint

A public, unauthenticated, cacheable JSON endpoint on OctoBot Cloud:

```
GET https://www.octobot.cloud/api/programmatic-slugs?locale=<en|fr>
```

- **Public + unauthenticated** — the docs build has no credentials.
- **Cacheable** — hit once per locale per build; a CDN cache (e.g. 24 h) is fine.
- **Localized** — the `locale` query param selects the language of the prose fields
  (`whatIs`, `faq`). Structural fields (symbols, slugs, prices) are locale-independent.
- Data source: the same Supabase tables Astrolab reads (`cryptocurrency`, `exchange`).
  Mirror the logic in `Astrolab/frontend/web/app/app/sitemap.ts` →
  `getDynamicRoutes()`, and the repository calls in the Astrolab
  `(programmatic)/[slug]/page.tsx` + `tools/converter/[base]/[quote]/page.tsx` files.

### 2. Response format

```jsonc
{
  "cryptocurrencies": [
    {
      "symbol": "BTC",              // uppercase ticker — used for chart symbol + prediction slug
      "name": "Bitcoin",            // display name
      "slug": "bitcoin",            // url slug for /what-is-<slug>
      "lastPrice": 64000,           // last price in USD (number) — drives the converter rate
      "whatIs": "Bitcoin is ...",   // localized prose; OMIT or empty -> no /what-is-<slug> page
      "hasPrediction": true,        // true -> emit /<symbol>-prediction page
      "faq": [                      // localized; optional; rendered in the FAQ accordion
        { "question": "What is Bitcoin?", "answer": "A decentralized digital currency." }
      ]
    }
  ],
  "exchanges": [
    {
      "name": "Binance",            // display name
      "slug": "binance",            // url slug for /<slug>-trading-bot and /<slug>-market-maker
      "internalName": "binance",    // OctoBot internal exchange id (reserved; not yet rendered)
      "tier1": true,                // optional — shows a "Tier-1 exchange" chip
      "supports": {                 // support level per product; values: "supported" | "partial" | "unsupported"
        "spot": "supported",        // "supported" -> trading-bot page uses the Cloud copy variant
        "open_source": "supported", // "supported" (without spot) -> open-source copy variant
        "market_making": "supported"// "supported" -> emit /<slug>-market-maker page
      }
    }
  ]
}
```

**Field rules the plugin relies on:**

| Field                          | Effect if present / value                                   |
|--------------------------------|-------------------------------------------------------------|
| `cryptocurrencies[].whatIs`    | non-empty → generates `/what-is-<slug>`                     |
| `cryptocurrencies[].hasPrediction` | `true` → generates `/<symbol-lowercase>-prediction`    |
| every `cryptocurrencies[]`     | enters the converter matrix (N×N + each × USD)             |
| `exchanges[].supports.spot` or `.open_source` = `"supported"` | generates `/<slug>-trading-bot` |
| `exchanges[].supports.market_making` = `"supported"`          | generates `/<slug>-market-maker` |

The plugin **throws** (build fails) if: the endpoint is unreachable, returns non-200,
or the JSON is missing the `cryptocurrencies` / `exchanges` arrays. There is no fallback.

### 3. Routes that will be generated

For ~N coins and ~M exchanges, per locale (`en`, `fr`):

- `/what-is-<slug>` — one per coin with `whatIs`
- `/<symbol>-prediction` — one per coin with `hasPrediction`
- `/tools/converter/<base>/<quote>` — **full N×N matrix** + each coin × `usd`
  (≈ N² pages — this is the heavy one; keep the coin list curated server-side)
- `/<slug>-trading-bot` — one per spot/open-source exchange
- `/<slug>-market-maker` — one per market-making exchange

Scope is controlled entirely server-side by what the endpoint returns — no docs-repo
change is needed to grow or shrink the list.

### Future programmatic family — per-exchange token listing

`/features/token-listing` covers the listing keyword cluster generically. The
per-exchange variants ("MEXC listing requirements", "how to list a token on
Binance", "<exchange> token listing cost") are programmatic-shaped — one page
per exchange, same data the plugin already fetches (`exchanges[]`). Worth adding
as an `ExchangeTokenListing` template + route family once the endpoint ships;
do not hand-write 20+ of these.

---

## How to finish

1. **Backend**: implement + deploy the endpoint above on OctoBot Cloud.
2. **Verify the contract**:
   ```bash
   curl "https://www.octobot.cloud/api/programmatic-slugs?locale=en" | head -c 400
   curl "https://www.octobot.cloud/api/programmatic-slugs?locale=fr" | head -c 400
   ```
   Confirm both return the shape above.
3. **Build the docs**:
   ```bash
   cd docs
   npx tsc --noEmit                        # must be clean
   ./node_modules/.bin/docusaurus build    # must SUCCEED for build/ and build/fr/
   ```
   The default endpoint URL is baked into the plugin; override for staging with
   `OCTOBOT_PROGRAMMATIC_ENDPOINT=<url> ./node_modules/.bin/docusaurus build`.
4. **Spot-check** one page per family (no docs navbar, Neo Glass Dark theme,
   FAQ accordion works, converter widget calculates, TradingView embed loads):
   - `build/what-is-bitcoin.html`
   - `build/btc-prediction.html`
   - `build/tools/converter/btc/eth.html`
   - `build/binance-trading-bot.html`
   - `build/binance-market-maker.html`
5. Delete this file once the endpoint is live and builds pass.

---

## Local verification without the endpoint (optional)

To test the plugin + templates before the real endpoint exists, serve a fixture
matching the format above and point the build at it:

```bash
# minimal fixture server on :8799 returning the JSON shape documented here
OCTOBOT_PROGRAMMATIC_ENDPOINT="http://localhost:8799" ./node_modules/.bin/docusaurus build
```

Do **not** commit a fixture — the production build must use the live endpoint.
