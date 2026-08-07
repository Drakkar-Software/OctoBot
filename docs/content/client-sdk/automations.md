---
title: "Automations"
description: "Create, read, stop, and update running bots (automations) with the OctoBot client SDK — progress reporting, status mapping, and strategy versioning on edit."
sidebar_position: 6
---

# Automations

An automation is a running bot: a strategy configuration bound to one or more accounts. See
[User actions](user-actions.md) for the two-phase create race this package sequences
around, and [Strategies](strategies.md) for building the `strategy` argument itself.

## Create

```ts
import { strategy } from '@drakkar.software/octobot-client'

const dca = strategy.dca({ pairs: ['BTC/USDT'], buyOrderAmount: '25' })
const action = await octobot.automations.create({
  name: 'My DCA',
  strategy: dca,
  accountIds: [account.id],
})
const automation = await action.settled()
```

Progress reporting, since this is a two-phase operation under the hood:

```ts
await octobot.automations.create(input, {
  onProgress: (p) => console.log(p.phase, p.done ? 'done' : 'waiting'),
  // p.phase: 'strategy' | 'automation'
})
```

## Reading state

```ts
const automations = await octobot.automations.list()
for (const a of automations) {
  console.log(a.id, a.status, a.accountIds, a.error)
}
```

`AutomationView.status` is a coarse `'live' | 'draft' | 'stopped'` — collapsed from the node's own
`WorkflowStatus` enum (`scheduled`/`periodic`/`running` → `live`; `pending` → `draft`; everything
else, including `canceled`/`failed`/`completed`, → `stopped`, so a non-running workflow never renders
as live).

`AutomationView.strategy` is recovered from the action history, not the node's own state — the
node's `AutomationState` carries no strategy reference at all. If the automation was created by a
different client (or a client that's since lost its action history), this can come back `null`.

## Stop

```ts
const action = await octobot.automations.stop(automation.id)
await action.settled()
```

## Update

```ts
const edited = strategy.dca({ pairs: ['BTC/USDT'], buyOrderAmount: '50' }, { id: dca.id, version: strategy.bumpVersion(dca.version!) })
const action = await octobot.automations.update(automation.id, {
  name: automation.name, strategy: edited, accountIds: automation.accountIds,
})
await action.settled()
```

The node treats strategies as replace-by-id — an edit is a `strategy_edit` action carrying the same
`id` with a bumped `version`, followed by `automation_edit`. `update()` emits both.
