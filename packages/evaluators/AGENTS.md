# Agents: evaluators

## Role

TA evaluators, matrices, and signals feeding trading decisions and tentacles.

## Owns

- `packages/evaluators/octobot_evaluators/`
- `packages/evaluators/tests/`

## Public surface

- `octobot_evaluators` evaluator classes and matrix APIs

## May depend on

- `octobot_commons`

## Do not

- Import trading exchange connectors directly for new features (use trading APIs)
- Edit installed tentacles instead of evaluator tentacles under `packages/tentacles`

## Tests

- **cwd:** `packages/evaluators`
- **Example:** `pytest tests -n auto --dist loadfile`

## Last reviewed

- 2026-09-16
