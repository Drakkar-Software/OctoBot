# @drakkarsoftware/octobot-trading

Browser-first TypeScript wrapper around [CCXT](https://github.com/ccxt/ccxt) that exposes the same uniformized exchange interface OctoBot's Python `octobot_trading.exchanges` module gives the rest of the bot. Use it from a frontend to talk to any CCXT-supported exchange via one normalized REST + WebSocket API instead of dealing with each venue's quirks.

## What's in scope

REST + WebSocket + adapters: `RestExchange`, `WebSocketExchange`, `CCXTConnector`, `CCXTWebsocketConnector`, `CCXTAdapter`, `ExchangeMarketStatusFixer`, `ExchangeManager`, market filters, configuration data structures, and the typed error hierarchy.

Out of scope (server-side concepts): trader/order-execution lifecycle, backtesting simulator, `async_channel` pubsub bus, tentacle plugin loader, personal_data integration. WebSocket push events are surfaced via a tiny `EventBus` that callers subscribe to.

## Quick start

```ts
import { ExchangeBuilder } from "@drakkarsoftware/octobot-trading";

const manager = new ExchangeBuilder("kraken").asSpot().build();
await manager.initialize();

const ticker = await manager.exchange!.getPriceTicker("BTC/USDT");
//   ticker is in OctoBot's normalized shape regardless of the venue:
//   { symbol, timestamp, datetime, high, low, bid, ask, last, ... }

await manager.stop();
```

WebSocket feeds (when supported by the underlying CCXT exchange):

```ts
const manager = new ExchangeBuilder("binance").asSpot().enableWebSocket().build();
await manager.initialize();

manager.events.on("ticker", (t) => console.log("normalized ticker:", t));
manager.exchangeWebSocket!.watchTicker("BTC/USDT");
```

## Workspace and consumers

This package lives in the OctoBot pnpm workspace at `OctoBot/`. It depends on `@drakkarsoftware/octobot-commons` (logger, async tools, event bus, decimal helpers, symbol parsing) via the `workspace:*` protocol. From the workspace root:

```bash
pnpm install
pnpm -r --filter "@drakkarsoftware/*" run build
pnpm -r --filter "@drakkarsoftware/*" run test
```

## Verifying in the browser

`dist/octobot-trading.browser.min.js` is the UMD bundle. Run `npm run build` once, then load it directly:

```html
<script src="./dist/octobot-trading.browser.min.js"></script>
<script>
  const { createExchangeBuilderInstance } = window.octobotTrading;
  const m = createExchangeBuilderInstance("kraken").asSpot().build();
  m.initialize().then(async () => {
    console.log(await m.exchange.getPriceTicker("BTC/USDT"));
  });
</script>
```

## Real-exchange test suite

Live tests under `tests/realExchanges/` are skipped by default. Run them against the catalog of 35+ exchanges with:

```bash
VITEST_REAL_EXCHANGES=1 pnpm test:real
```

These hit real APIs and may rate-limit; pass credentials per spec when authenticated paths are needed.
