# Agents: octobot (core application)

## Role

Top-level OctoBot app: CLI entry, configuration, community features, orchestration of packages. Wires trading, evaluators, services, and tentacles at runtime.

## Owns

- `octobot/` Python package at repo root
- Root `tests/` (application integration)
- User-facing config templates under app paths (not `user/` runtime data)

## Public surface

- `OctoBot` CLI (installed wheel)
- `octobot` modules consumed by tentacles and startup

## May depend on

- `octobot_commons`, `octobot_trading`, `octobot_evaluators`, `octobot_services`, tentacles manager, installed `tentacles/`

## Do not

- Edit repo-root `tentacles/` (install output)
- Put secrets or `user/` data in tree
- Duplicate logic that belongs in `packages/*`
- Use **node journal** for reads or control flow outside export: record-only via `octobot.community.node_journal` from the rest of the app (see [`community/node_journal/AGENTS.md`](community/node_journal/AGENTS.md), skill **node-journal**)
- Duplicate shared wire/config/event strings; use package-top [`constants.py`](constants.py) / [`enums.py`](enums.py) (or the owning package’s equivalents)
- Use `from xxx import yyy` or lazy imports in normal modules (only `__init__.py` re-exports; see [CONTRIBUTING-agent.md](../CONTRIBUTING-agent.md) — **Python conventions (agents)**)

## Tests

- **cwd:** repo root
- **Tentacles:** required (install via `ci-tentacles` / `reinstall-tentacles.sh`)
- **Example:** `pytest tests -n auto --dist loadfile` and tentacles test pass per [reference-pytest.md](../.cursor/skills/octobot-cloud/reference-pytest.md) ([When tests fail](../.cursor/skills/octobot-cloud/reference-pytest.md#when-tests-fail) for red tests)

## Related human doc

- `docs/content/developers/environment/setup-your-environment.md`

## Last reviewed

- 2026-09-21
