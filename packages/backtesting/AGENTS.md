# Agents: backtesting

## Role

Historical simulation and backtesting engine over trading + evaluators data.

## Owns

- `packages/backtesting/octobot_backtesting/`
- `packages/backtesting/tests/`

## Public surface

- `octobot_backtesting` APIs used by tentacles and CLI

## May depend on

- `octobot_commons`, `octobot_trading`, `octobot_evaluators` (as existing imports)

## Do not

- Change exchange live-trading connectors for backtest-only shortcuts without tests

## Tests

- **cwd:** `packages/backtesting`
- **Example:** `pytest tests -n auto --dist loadfile`

## Last reviewed

- 2026-09-16
