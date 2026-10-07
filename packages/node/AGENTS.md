# Agents: node

## Role

`octobot_node` is **durable orchestration** for OctoBot Node: FastAPI, DBOS scheduling, and protocol APIs. It runs work; **`octobot_flow`** executes automation logic statelessly inside DBOS steps.

- **Service:** master and/or consumer roles; **SQLite** DBOS for single-node dev, CI, and cloud agents; **PostgreSQL** only for multi-node—do not assume shared Postgres in cloud unless the user configures it.
- **User actions (how clients drive the node):** Web UI (`node_api_interface`), sync, and other callers submit **`protocol_models.UserAction`**. `execute_user_action` journals the request and triggers **`user_action_workflow`**. Executors under `scheduler/user_actions/user_actions_executor/` implement accounts, account auth, automations (create/stop/restart/signal), strategies, historical data refresh, and related commands—users manage the node **without editing flow DAGs** directly.
- **Two user-action paths:** (1) **User-action workflow** — discrete API commands as their own DBOS workflow. (2) **In-flight automation** — DBOS messages on topic `"user_actions"` while an automation runs (overrides between DAG iterations).
- **Scheduled work:** automation iterations as child DBOS workflows (`execute_iteration` as a DBOS step); portfolio history, global view, and cleanup under `scheduler/workflows/`.
- **Bridge to flow:** `octobot_flow_client` runs `octobot_flow` jobs inside steps; optional `encrypted_task` wrapper—flow stays encryption-agnostic.
- **Not here:** DAG action bodies, ccxt plumbing, evaluator tentacles. Tentacle HTTP routes live in **`packages/tentacles`** but must delegate to node protocol and scheduler APIs.
- **OpenAPI:** Node **REST** spec is owned by tentacles (`node_api_interface` → `node_web_interface/openapi.json` — do not hand-edit); shared **wire** types live in **`packages/protocol/openapi.json`** (`npm run generate:all`). See [`../tentacles/AGENTS.md`](../tentacles/AGENTS.md#node-rest-openapi-node_api_interface--node_web_interface) and [`../protocol/AGENTS.md`](../protocol/AGENTS.md).

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
- Construct `dbos.Queue(...)` or enqueue scheduler workflows via the `dbos.DBOS` class—use `octobot_node.enums.SchedulerQueues`, [`octobot_node/scheduler/queues.py`](octobot_node/scheduler/queues.py) after launch, and `SCHEDULER.INSTANCE.enqueue_workflow_async` (see `octobot_node/scheduler/tasks.py`)

## Agent seed (demo wallet / Cloud QA)

Only when driving the **live Node web UI** or debug view — not for routine `pytest` in this package.

- Operator docs: [`tools/agent_seed/README.md`](../../tools/agent_seed/README.md) and skill **agent-seed** (`.cursor/skills/agent-seed/SKILL.md`).
- Fixtures: `python -m tools.agent_seed seed` or `bash .cursor/seed-agent.sh seed|bootstrap|start|--full|--clear` (after `.cursor/agent-seed.env`).
- After seed: login passphrase; full **`/app`** UI for QA; **`/app/debug`** to submit user actions and inspect automations.
- Runtime sandbox: `packages/node/octobot_node/agent_seed/` (`is_demo_agent_seed_user`, demo wallet action guards).

## Tests

- **cwd:** repo root
- **PYTHONPATH:** `PYTHONPATH=.:$PYTHONPATH`
- **Tentacles:** required (CI installs tentacles)
- **DBOS:** SQLite-backed scheduler tests are OK in Cursor Cloud (same as local dev)
- **Example:** `pytest packages/node/tests -n auto --dist loadfile`

## Related human doc

- `docs/content/developers/packages/node.md`

## Last reviewed

- 2026-09-22
