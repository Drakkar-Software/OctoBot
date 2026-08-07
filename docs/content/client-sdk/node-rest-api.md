---
title: "Node REST API"
description: "client.node.* — the OctoBot node's direct REST API for market-data lookups and Basic-auth-gated setup endpoints (DSL keywords, wallet export, generic-process bots)."
sidebar_position: 11
---

# Node REST API

Alongside the Starfish sync transport, a node exposes a direct REST API at `{origin}/api/v1`, used
for market-data lookups and a handful of authenticated setup endpoints. `client.node.*` wraps it.

## Unauthenticated

```ts
await octobot.node.status()
// { reachable: boolean, configured: boolean }

await octobot.node.tradedPairs({ id: 'x', name: 'x', exchange: 'binance' }, { withVolume: true })
await octobot.node.predictedOrderBook(exchangeConfig, marketMakingConfig)
await octobot.node.requiredFunds(exchangeConfig, marketMakingConfig)
```

## Authenticated — requires `ConnectOptions.basicAuth`

Only a node paired by an **older** pairing QR hands you an HTTP Basic password (a current QR carries
the wallet directly and never routes through Basic auth). Without `basicAuth`, these throw
`OctoBotConfigError` immediately rather than making a request that would 401:

```ts
const octobot = await connectOctoBot({
  url, seed,
  basicAuth: { address: '0x...', password: '...' },
})

await octobot.node.dslKeywords()
await octobot.node.exportWallet()
await octobot.node.createGenericProcessBot('My Bot')
```

## Errors

A non-2xx response throws `OctoBotHttpError` with `.status` set — branch on it rather than parsing
the message (e.g. `tradedPairs` internally retries once without `withVolume` on a 501, since that
means the exchange doesn't support the volume lookup, not that the call itself failed).
