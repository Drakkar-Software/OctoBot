# Pytest matrix (CI parity)

Run from **OctoBot repo root** after `source .cursor/env.sh`. `DISABLE_SENTRY=True` matches CI.

| Package | cwd | PYTHONPATH / notes | Example |
|---------|-----|-------------------|---------|
| `octobot` | repo root | default venv | `pytest tests -n auto --dist loadfile` |
| `octobot` (tentacles tests) | repo root | installed tentacles | `pytest --ignore=tentacles/Trading/Exchange tentacles -n auto --dist loadfile` |
| `packages/node` | repo root | `PYTHONPATH=.:$PYTHONPATH` | `pytest packages/node/tests -n auto --dist loadfile` |
| `packages/flow` | repo root | `PYTHONPATH=.:$PYTHONPATH` | `pytest packages/flow/tests -n auto --dist loadfile` |
| `packages/copy` | repo root | `PYTHONPATH=.:$PYTHONPATH` | `pytest packages/copy/tests -n auto --dist loadfile` |
| `packages/tentacles_manager` | `packages/tentacles_manager` | — | `pytest tests` (no xdist in CI) |
| `packages/protocol` | `packages/protocol` | — | `pytest test` |
| `packages/agents` | `packages/agents` | — | `pytest tests -n auto --dist loadfile` |
| `packages/async_channel` | `packages/async_channel` | — | `pytest tests -n auto --dist loadfile` |
| `packages/backtesting` | `packages/backtesting` | — | `pytest tests -n auto --dist loadfile` |
| `packages/commons` | `packages/commons` | — | `pytest tests -n auto --dist loadfile` |
| `packages/evaluators` | `packages/evaluators` | — | `pytest tests -n auto --dist loadfile` |
| `packages/services` | `packages/services` | — | `pytest tests -n auto --dist loadfile` |
| `packages/sync` | `packages/sync` | — | `pytest tests -n auto --dist loadfile` |
| `packages/trading` | `packages/trading` | — | `pytest tests -n auto --dist loadfile` |

**Tentacles install** required for: `octobot`, `packages/node`, `packages/flow`, `packages/copy` (CI `USES_TENTACLES`).

**Pylint:** `pylint --rcfile=<pkg>/standard.rc <pkg>/` or root `standard.rc` (see CI `main.yml`).

**extended_linter tests:** `PYTHONPATH=. pytest tools/extended_linter/tests -q`
