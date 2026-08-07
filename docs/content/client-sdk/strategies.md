---
title: "Strategies"
description: "The protocol/strategy/ module map, building strategies with the strategy.* facade, reading them back from action history, and editing via patch/toInput."
sidebar_position: 7
---

# Strategies

## The module map

`protocol/strategy/` is deliberately split into four files with four different jobs — this replaced
an earlier design (`strategyConfig.ts` + `strategyPatch.ts` + `strategyDoc.ts`) that mixed all four
in two files and ended up with `StrategyKind` declared three separate times across the codebase.

| File | Job |
|---|---|
| `kinds.ts` | The ONE `StrategyKind` definition. Everything else imports it. |
| `builders.ts` | Per-kind pure builders: `buildDCAConfig`, `buildGridConfig`, `buildMarketMakingConfig`, `buildIndexConfig`, `buildCopyConfig`, `buildSignalConfig`, `buildGenericProcessConfig`. Each takes a friendly input shape and returns a protocol `configuration`. |
| `build.ts` | The `StrategyInput` discriminated union and `buildStrategy()` — wraps a builder's output into a full `Strategy` (id, version, timestamps, `reference_market`). |
| `patch.ts` | The inverse: `protocolStrategyToInput()` recovers an editable input from a `Strategy` the node returned. Kept separate from `build.ts` on purpose — construction and incremental editing are different concerns with different failure modes (patch must tolerate configs written by older or foreign clients; build never has to). |

The public facade (`strategy.dca()`, `.grid()`, etc in the root export) is a thin wrapper over
`builders.ts` + `build.ts`; `strategy.toInput()` wraps `patch.ts`.

## Building

```ts
import { strategy } from '@drakkar.software/octobot-client'

strategy.dca({ pairs: ['BTC/USDT'], buyOrderAmount: '25' })
strategy.grid({ pairs: ['BTC/USDT'], lower: 60000, upper: 70000, levels: 20, currentPrice: 65000 })
strategy.marketMaking({ exchange: 'binance', pairs: ['BTC/USDT'], refsByPair: {}, spreadBp: 50, perSide: 5, sizeBase: 0.1, shape: 'flat' })
strategy.index({ pairs: ['BTC', 'ETH'], basketWeights: { BTC: 70, ETH: 30 } })
strategy.copy({ sourceId: 'strategy-id-to-mirror' })
strategy.signal({ webhookId, webhookSecret, pair: 'BTC/USDT', sideMode: 'buy', orderType: 'market', sizeMode: 'percent', sizeValue: 10 })
strategy.genericProcess()
```

Every builder returns a complete protocol `Strategy` (`id`, `version: '1.0.0'`, `reference_market`
derived from the traded pairs' quote currency, `created_at`/`updated_at`). Override any of that with
the second argument: `strategy.dca(input, { id, version, name, description, referenceMarket })`.

## Reading

```ts
const strategies = await octobot.strategies.list()
const one = await octobot.strategies.get(id, version)
```

Reconstructed from `strategy_create`/`strategy_edit` user actions in the action history — the node
exposes no strategies collection of its own. For a given `(id, version)`, the newest action wins.

## Editing

```ts
const input = strategy.toInput(existing)          // -> StrategyInputPatch
// ...mutate the relevant fields of `input`...
const edited = strategy.build(input, { id: existing.id, version: strategy.bumpVersion(existing.version!) })
await (await octobot.strategies.update(edited)).settled()
```

`toInput()` never throws on a config from an older or foreign client — an unrecognized shape falls
back to `{ kind: 'custom' }` rather than crashing an editor.
