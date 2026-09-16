# Agents: protocol

## Role

Shared protocol messages and schemas between node, clients, and services.

## Owns

- `packages/protocol/octobot_protocol/` (per repo layout)
- `packages/protocol/test/` (note CI uses `pytest test`)

## Public surface

- Protocol models and serialization used by node and clients

## May depend on

- `octobot_commons`

## Do not

- Embed HTTP route handlers (belongs in node/services/tentacles)

## Tests

- **cwd:** `packages/protocol`
- **Example:** `pytest test`

## Last reviewed

- 2026-09-16
