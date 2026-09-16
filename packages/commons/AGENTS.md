# Agents: commons

## Role

Shared utilities: logging, configuration helpers, databases, time, enums, and cross-cutting types used by most packages.

## Owns

- `packages/commons/octobot_commons/`
- `packages/commons/tests/`

## Public surface

- `octobot_commons.*` — prefer stable helpers here over duplicating in trading/node

## May depend on

- Minimal third-party stack; avoid importing `octobot_trading` or app layer

## Do not

- Import from `packages/trading`, `octobot` app, or tentacles
- Add trading-specific logic (belongs in trading)

## Tests

- **cwd:** `packages/commons`
- **Example:** `pytest tests -n auto --dist loadfile`

## Related human doc

- `docs/content/developers/packages/commons.md` (if present)

## Last reviewed

- 2026-09-16
