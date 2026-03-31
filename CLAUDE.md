# CLAUDE.md

## Environment

```bash
ROOT=$PWD
export PYTHONPATH="$ROOT:$ROOT/packages/agents:$ROOT/packages/async_channel:$ROOT/packages/backtesting:$ROOT/packages/binary:$ROOT/packages/commons:$ROOT/packages/evaluators:$ROOT/packages/flow:$ROOT/packages/node:$ROOT/packages/services:$ROOT/packages/sync:$ROOT/packages/tentacles:$ROOT/packages/tentacles_manager:$ROOT/packages/trading:$ROOT/packages/trading_backend"
```

- **Python**: `venv/bin/python` (workspace venv, one level above repo root)
- PYTHONPATH must be absolute (`$PWD`-based) — build subprocesses run from tentacle subdirectories and need to resolve all packages.

## Tentacles

- **Source of truth**: `packages/tentacles/` — all tentacle changes go here.
- **Never edit `tentacles/` directly** — it is generated from `packages/tentacles/` via export+install and will be overwritten.
- After any change to `packages/tentacles/`, run the **tentacle-manager** agent to export and install.

## Agents

Custom agents live in `.claude/agents/`. They are **not** dispatchable via `subagent_type` — trigger them with `@agent-<name>` in your prompt (e.g. `@agent-test-runner run node tests`), or use `claude --agent <name>` to make one the session agent.

### tentacle-manager

Manages the OctoBot tentacles lifecycle: export from source, install from zip, and generate CCXT exchange tentacles. Mirrors the VSCode "Install tentacles zip" launch configuration.

Use when: installing tentacles after code changes, generating exchange tentacles from CCXT, or running any `python start.py tentacles` command.

Trigger: `@agent-tentacle-manager` · Definition: `.claude/agents/tentacle-manager.md`

### test-runner

Runs and debugs OctoBot Python tests. Handles root-level tests (`tests/`) and per-package tests (`packages/<name>/tests/`). On failure, reads the test and source code, diagnoses the issue, fixes it, and re-runs.

Use when: running tests, debugging test failures, or verifying changes after code modifications.

Trigger: `@agent-test-runner` · Definition: `.claude/agents/test-runner.md`
