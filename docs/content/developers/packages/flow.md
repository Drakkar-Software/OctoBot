---
title: Flow
description: Architecture and concepts of the octobot_flow package — OctoBot's serverless automation runner.
sidebar_position: 1
---

# Flow Package

`octobot_flow` is a stateless automation execution engine. An `AutomationState` object is passed in at the start of each invocation, the job runs, and the updated state is returned via `AutomationJob.dump()`. Nothing is held in memory between calls, which means the engine can run as a serverless function and multiple automations are naturally isolated from one another.

## Execution model

Each job runs a DAG of actions. The DAG identifies which actions are ready — not yet completed, with all dependencies satisfied — resolves any DSL placeholders by injecting upstream results, and executes them via `DSLExecutor`. After execution, exchange state is synced back into the automation state.

Priority actions stored in `AutomationState.priority_actions` run before the normal DAG cycle but use the main DAG as their resolution context. This is the mechanism for bootstrapping: on the very first invocation, when there is no previous execution and no exchange account, only `apply_configuration` actions are processed to set up the exchange account from config before the regular cycle runs.

A DAG reset can be triggered mid-run by a `ReCallingOperatorResult`, which the `wait()` operator returns when its condition is not yet met. A reset computes the transitive closure of dependents from the target action, saves their current results into `previous_execution_result`, and clears their execution timestamps so they re-run on the next invocation. The saved previous result lets re-running operators resume from where they left off rather than starting cold.

## DSL execution

`DSLExecutor` wraps the `octobot_commons` DSL interpreter with operator sets registered by tentacles. A fresh interpreter is created per action to prevent state leakage between actions in the same run. DSL scripts are parsed before the exchange is initialised so that required symbols and time frames can be extracted upfront — only the OHLCV data that scripts actually reference is fetched.

## Simulated and live modes

When no credentials are present, `ExchangeRepositoryFactory` returns simulated implementations that read from `FetchedExchangeData` snapshots instead of making live API calls. OHLCV data is still fetched live even in simulated mode because it is public. A portfolio can be forced onto the simulated exchange manager to test strategies against a specific account state.

The ticker cache, with a five-minute TTL and a fifty-entry cap, serves as a fallback when OHLCV data is unavailable during initialisation. Community repositories intentionally use non-singleton auth instances per job — no session is shared between automations, which prevents credential leakage.

## Exchange lifecycle

`ExchangeContextMixin` manages the full exchange lifecycle for each job: build config, initialise `ExchangeManager` with storage disabled, apply any forced portfolio for simulated runs, then tear down after the job completes. Portfolio sync is disabled during order creation because the flow package manages portfolio state explicitly through post-action sync calls rather than relying on automatic sync triggered by order events.
