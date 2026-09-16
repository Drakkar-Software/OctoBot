# Agents: tentacles_manager

## Role

Pack, install, and manage tentacles archives and metadata.

## Owns

- `packages/tentacles_manager/octobot_tentacles_manager/`
- `packages/tentacles_manager/tests/`

## Public surface

- Tentacles manager CLI hooks used by `OctoBot tentacles` commands

## May depend on

- `octobot_commons`

## Do not

- Edit `packages/tentacles` content here (that's tentacle sources)
- Commit `output/*.zip` or repo-root `tentacles/` as part of feature work

## Tests

- **cwd:** `packages/tentacles_manager`
- **Example:** `pytest tests` (CI runs without xdist)

## Last reviewed

- 2026-09-16
