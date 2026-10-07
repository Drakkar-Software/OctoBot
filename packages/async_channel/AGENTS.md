# Agents: async_channel

## Role

Async consumer/producer channels and queues between OctoBot subsystems.

## Owns

- `packages/async_channel/octobot_async_channel/`
- `packages/async_channel/tests/`

## Public surface

- `octobot_async_channel` channel primitives

## May depend on

- Standard library + small deps only

## Do not

- Pull in trading or tentacles

## Tests

- **cwd:** `packages/async_channel`
- **Example:** `pytest tests -n auto --dist loadfile`

## Last reviewed

- 2026-09-16
