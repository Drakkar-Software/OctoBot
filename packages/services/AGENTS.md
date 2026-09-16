# Agents: services

## Role

Notifications, interfaces, and service abstractions (web, telegram, etc.) consumed by the bot and tentacles.

## Owns

- `packages/services/octobot_services/`
- `packages/services/tests/`

## Public surface

- `octobot_services` service base classes and interface hooks

## May depend on

- `octobot_commons`

## Do not

- Embed trading execution logic
- Confuse with `packages/tentacles/Services` tentacle implementations (those extend services)

## Tests

- **cwd:** `packages/services`
- **Example:** `pytest tests -n auto --dist loadfile`

## Last reviewed

- 2026-09-16
