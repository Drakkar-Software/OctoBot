# @drakkarsoftware/octobot-node

Stateless automation runner for OctoBot. Register automations at startup, fire one, many, or all of them against a `state` bag whose shape is defined in [`@drakkarsoftware/octobot-protocol`](../../protocol/octobot-protocol-ts/), and get back an updated `state` with one `Execution` record per automation that fired. The library owns no storage — the caller decides how to persist the returned state.

## What it does

- **Automation registry**: `(id, name, description?, shouldRun?, run)` quadruples held in memory.
- **One entrypoint**: `node.run({ state, reason, automationIds?, signal? })` returns `{ executions, nextState }`.
- **Execution tracking**: every fire produces a typed `Execution` row (`id, automationId, reason, startedAt, completedAt, status, input, result, error`) appended to the relevant automation's history in `nextState`.
- **`shouldRun(state)` gating**: lets each automation decide whether to fire based on prior executions in the state (rate limits, "ran less than 6h ago", "previous run failed", etc.).
- **Cooperative cancel**: caller passes an `AbortSignal`; in-flight automations transition to `cancelled`, not-yet-started ones never produce a row.

## Quick start

```ts
import { createOctobotNode, emptyState } from "@drakkarsoftware/octobot-node";

const node = createOctobotNode();

node.registerAutomation({
  id: "morning-summary",
  name: "Morning Summary",
  shouldRun: (state) => {
    const last = node.latestForAutomation(state, "morning-summary");
    return !last || (Date.now() - (last.completedAt ?? 0)) > 6 * 3600_000;
  },
  run: async (ctx, state) => {
    ctx.logger.info("running summary");
    return { sentAt: Date.now() };
  },
});

let state = emptyState();
const { executions, nextState } = await node.run({ state, reason: "user pulled to refresh" });
state = nextState;
console.log(executions);
```

## Workspace

Lives in the OctoBot pnpm workspace at `OctoBot/`. Dependencies: `@drakkarsoftware/octobot-commons` (logger, AbortSignal helpers, typed errors) and `@drakkarsoftware/octobot-protocol` (state and execution types). From the workspace root:

```bash
pnpm install
pnpm --filter @drakkarsoftware/octobot-node run build
pnpm --filter @drakkarsoftware/octobot-node run test
```

## Persistence

Out of scope on purpose. The caller stores `nextState` however it wants — Redux, SQLite, a server round-trip, anything that round-trips through the protocol's `AutomationsState` JSON shape.
