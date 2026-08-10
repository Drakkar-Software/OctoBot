---
title: "User Actions"
description: "Writes are a queue, not an RPC call: the append-only user-actions collection, ActionHandle semantics, action statuses, and the two-phase automation-create race the SDK sequences around."
sidebar_position: 3
mdx:
  format: mdx
---

import DemoEmbed from '@site/src/components/demo/Embed';

# User actions

<DemoEmbed section="queue" />

## Writes are a queue, not an RPC call

`accounts.create()` and `automations.create()` don't make an RPC call that finishes when the promise
resolves. They append an action to `users/{identity}/actions` — a push-only, append-only collection —
and hand back an `ActionHandle` **the instant that append happens**:

```ts
const action = await client.automations.create({ name, strategy, accountIds })
// `action` already has work running — appending happened before create() returned.
const automation = await action.settled()
```

A caller who reads the resolved `create()` promise as "it's created now" is already wrong.
`settled()` only lets you watch what the node does with the append afterward — a caller who never
calls `settled()` at all hasn't left anything half-done; the append still happened without them
watching.

Every appended element is a **command the node consumes and executes exactly once**. There is no
"PUT the current state" here — appending the same configuration twice creates the resource twice (or
fails the second time, depending on the action). Results never come back through the `actions`
collection itself — pulling it always returns empty. The node reports execution status back through
the `user-data` pull, correlated by the action's `id`.

## Statuses

| `UserAction.status` | Meaning |
|---|---|
| `pending` | Appended, not yet picked up by the node. |
| `running` | The node is executing it. |
| `completed` | Done. `settled()` resolves. |
| `failed` | The node rejected it. `settled()` rejects with `OctoBotActionError`, carrying `.detail`. |

A `failed` action is **not retriable by resubmitting the same configuration** — whatever the node
objected to (a validation error, an already-existing id, a missing dependency) is still true. Fix the
input and emit a new action.

## `ActionHandle`

- **`settled()` is memoized.** Await it from two places; the underlying poll only runs once.
- **`ids` grows as phases start.** A single-action call (`automations.stop`) has one id from the
  start; a multi-phase call (`automations.create`) adds its second id once the first phase confirms —
  reading `action.ids` right after the call resolves can legitimately show fewer ids than the action
  will eventually have.
- **`status()` is a one-shot peek**, independent of the ongoing `settled()` work — useful for a
  progress UI that polls on its own cadence without driving the actual wait.

## The two-phase automation race

Creating an automation from a fresh strategy is two actions, not one: `strategy_create` then
`automation_create`. This is sequenced deliberately. The node executes queued actions **concurrently**,
and `automation_create` resolves its strategy by `(id, version)` against the node's own
StrategyProvider — which is populated *only* by strategy actions. If `automation_create` ran before
`strategy_create` registered the strategy, it would fail non-retriably with `strategy_not_found`.

`client.automations.create()` handles this for you: it appends `strategy_create`, polls until the
node confirms it, *then* appends `automation_create`. Watch it happen with `onProgress`:

```ts
await octobot.automations.create(input, {
  onProgress: (p) => console.log(p.phase, p.done ? 'done' : 'waiting'),
  // p.phase: 'strategy' | 'automation'
})
```

See `protocol/orchestration/createAutomation.ts` if you're building your own orchestration on the
lower-level `protocol`/`transport` exports instead of the facade — see
[Advanced primitives](advanced-primitives.md).

## Account deletes don't cascade

Deleting an account is three actions, not one — `account_delete` plus the two companion items the
protocol account graph splits out (`account_auth_delete`, `exchange_config_delete`). The node does
not cascade; `client.accounts.delete()` emits whichever of the three actually apply. See
[Accounts](accounts.md) for the full account graph.
