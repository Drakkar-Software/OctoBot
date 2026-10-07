# Agents: flow

## Role

`octobot_flow` is a **stateless automation runner**: `AutomationState` in, updated state out. **Node** (or serverless callers) persist scheduling, encryption, and DBOS; flow does not.

- **Execution:** action DAG (`actions_dag`, `actions_dag_parser`); ready actions run through **`DSLExecutor`** (commons DSL plus **tentacle-registered operators**). **Priority actions** run before the normal cycle (e.g. `apply_configuration` on first run). `wait()` can reset dependents via `ReCallingOperatorResult`.
- **Exchange per job:** `ExchangeContextMixin` builds and tears down `ExchangeManager` with storage disabled; simulated repositories without credentials; live OHLCV when needed; **explicit** portfolio sync after actions—not trading-mode automatic sync.
- **Job entry points:** `automation_job`, `automation_runner_job`, `portfolio_history_job`, `global_view_account_job`, `exchange_account_job`—invoked from node’s `octobot_flow_client`, not from DBOS code in this package.
- **Not here:** DBOS, task encryption, REST routes, tentacle pack/install, or long-lived scheduler state.

## Owns

- `packages/flow/octobot_flow/`
- `packages/flow/tests/`

## Public surface

- `octobot_flow.entities` — `AutomationState`, accounts, actions
- `octobot_flow.jobs` — automation, portfolio history, global view jobs
- `octobot_flow.parsers` — DAG and automation state readers
- `octobot_flow.logic.dsl` — `DSLExecutor` and execution context
- `octobot_flow.repositories` — exchange and community data access for jobs

## May depend on

- `octobot_commons`, `octobot_trading` (per-job `ExchangeManager`), imports used by jobs today

## Do not

- Import DBOS or node scheduler modules into flow
- Break wire/protocol enums or action contracts without updating **node** and **tentacles** API layers
- Assume flow runs without importable **tentacles** (operators register via `octobot_flow.environment.initialize_environment`)

## Tests

- **cwd:** repo root
- **PYTHONPATH:** `PYTHONPATH=.:$PYTHONPATH`
- **Tentacles:** required
- **Example:** `pytest packages/flow/tests -n auto --dist loadfile`

## Related human doc

- `docs/content/developers/packages/flow.md`

## Last reviewed

- 2026-09-16
