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
- Hand-edit generated trees (`octobot_protocol/`, `octobot_protocol_ts/`, root `test/test_*.py`) — regenerate from `openapi.json`

## OpenAPI and codegen

- **Source of truth:** `openapi.json` in this package — **schemas only** (no HTTP paths). Edit manually when changing wire types.
- **cwd:** `packages/protocol` for all commands below.
- **One-time:** user runs `npm install` (agents do not install per repo policy).
- **After every `openapi.json` change:** run **`npm run generate:all`** (Python + TypeScript codegen).
- **Compatibility PRs** (same PR as the spec change): `npm run generate:all` → `python -m scripts.build_openapi_schema_manifest` → `npm run generate:fixtures` → `pytest test` (or `npm run test:pytest`). Breaking changes, promote, legacy wire — follow [`README.md`](README.md) § “Backwards compatibility workflow”.
- **Not** `node_web_interface/openapi.json` (Node REST, generated from FastAPI). See [`../tentacles/AGENTS.md`](../tentacles/AGENTS.md).

## Tests

- **cwd:** `packages/protocol`
- **Example:** `pytest test`
- After spec changes: `generate:all` and compat steps above before merging.

## Last reviewed

- 2026-09-18
