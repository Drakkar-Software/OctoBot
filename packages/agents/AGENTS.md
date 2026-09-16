# Agents: agents

## Role

Agent automation primitives (OctoBot agents package) used by newer automation flows.

## Owns

- `packages/agents/octobot_agents/` (layout per repo)
- `packages/agents/tests/`

## Public surface

- `octobot_agents` modules referenced by node/automation features

## May depend on

- `octobot_commons` and packages declared in agents `requirements`

## Do not

- Couple directly to tentacle UI without going through documented APIs

## Tests

- **cwd:** `packages/agents`
- **Example:** `pytest tests -n auto --dist loadfile`

## Last reviewed

- 2026-09-16
