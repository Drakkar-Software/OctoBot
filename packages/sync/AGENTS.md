# Agents: sync

## Role

Cloud sync, backup, and replication helpers for OctoBot profiles and node state.

## Owns

- `packages/sync/octobot_sync/` (per repo layout)
- `packages/sync/tests/`
- Rust backend optional (`pytest --backend=rust` in CI when crates exist)

## Public surface

- Sync client/server modules imported by node and services

## May depend on

- `octobot_commons`, protocol as needed

## Do not

- Store credentials in repo; use config patterns documented for sync

## Tests

- **cwd:** `packages/sync`
- **Example:** `pytest tests -n auto --dist loadfile`

## Last reviewed

- 2026-09-16
