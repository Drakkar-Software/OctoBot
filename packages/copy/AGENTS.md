# Agents: copy

## Role

Copy trading / mirror trading features between accounts and followers.

## Owns

- `packages/copy/octobot_copy/` (per repo layout)
- `packages/copy/tests/`

## Public surface

- Copy trading APIs consumed by tentacles and node

## May depend on

- `octobot_commons`, `octobot_trading`

## Do not

- Bypass trading order safeguards

## Tests

- **cwd:** repo root
- **PYTHONPATH:** `PYTHONPATH=.:$PYTHONPATH`
- **Tentacles:** required
- **Example:** `pytest packages/copy/tests -n auto --dist loadfile`

## Last reviewed

- 2026-09-16
