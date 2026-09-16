# Agents: node

## Role

`octobot_node` is **durable orchestration** for OctoBot Node: FastAPI, DBOS scheduling, and protocol APIs. It runs work; **`octobot_flow`** executes automation logic statelessly inside DBOS steps.

- **Service:** master and/or consumer roles; **SQLite** DBOS for single-node dev, CI, and cloud agents; **PostgreSQL** only for multi-node—do not assume shared Postgres in cloud unless the user configures it.
- **User actions (how clients drive the node):** Web UI (`node_api_interface`), sync, and other callers submit **`protocol_models.UserAction`**. `execute_user_action` journals the request and triggers **`user_action_workflow`**. Executors under `scheduler/user_actions/user_actions_executor/` implement accounts, account auth, automations (create/stop/restart/signal), strategies, historical data refresh, and related commands—users manage the node **without editing flow DAGs** directly.
- **Two user-action paths:** (1) **User-action workflow** — discrete API commands as their own DBOS workflow. (2) **In-flight automation** — DBOS messages on topic `"user_actions"` while an automation runs (overrides between DAG iterations).
- **Scheduled work:** automation iterations as child DBOS workflows (`execute_iteration` as a DBOS step); portfolio history, global view, and cleanup under `scheduler/workflows/`.
- **Bridge to flow:** `octobot_flow_client` runs `octobot_flow` jobs inside steps; optional `encrypted_task` wrapper—flow stays encryption-agnostic.
- **Not here:** DAG action bodies, ccxt plumbing, evaluator tentacles. Tentacle HTTP routes live in **`packages/tentacles`** but must delegate to node protocol and scheduler APIs.

## Owns

- `packages/node/octobot_node/`
- `packages/node/tests/`
- Optional Rust crates under `packages/node/crates/` (clippy in CI)

## Public surface

- `octobot_node.protocol` — `user_actions`, accounts, automations, debug
- `octobot_node.scheduler.tasks` — workflow triggers
- `octobot_node.scheduler.workflows` — including `user_action_workflow`
- `octobot_node.scheduler.user_actions` — executors and factories
- `octobot_node.constants` — `SCHEDULER_APPLICATION_VERSION`, scheduler executor id

## May depend on

- `octobot_commons`, `octobot_trading`, `octobot_agents`, `octobot_flow`, protocol/sync as imported today

## Do not

- Add new user-facing operations only in tentacle routes—extend protocol, executor, and **node** tests for new action types
- Change `actions_dag` or `AutomationJob` semantics without matching **flow** changes
- Assume shared **PostgreSQL** multi-node DBOS in cloud unless configured (default dev/CI and cloud agents use **SQLite** DBOS locally)

## Tests

- **cwd:** repo root
- **PYTHONPATH:** `PYTHONPATH=.:$PYTHONPATH`
- **Tentacles:** required (CI installs tentacles)
- **DBOS:** SQLite-backed scheduler tests are OK in Cursor Cloud (same as local dev)
- **Example:** `pytest packages/node/tests -n auto --dist loadfile`

## Related human doc

- `docs/content/developers/packages/node.md`

## Last reviewed

- 2026-09-16
