# Agents: tentacles (sources vs install)

## Role

**Default plugin bundle** for OctoBot: concrete evaluators, trading modes, exchange connectors, services, automation pieces, AI agents, and DSL operators on top of framework packages (`octobot_trading`, `octobot_evaluators`, etc.).

- **Sources vs runtime:** edit **`packages/tentacles/`** (`Evaluator/`, `Trading/`, `Services/`, …). After pack/install, Python loads repo-root **`tentacles/`**—that tree is **generated**; never commit edits there.
- **Layout contract:** each tentacle has `metadata.json`, reference `config/`, and version-gated imports (`check_tentacle_version()` in generated `__init__.py`). Install, update, and packaging live in **`octobot_tentacles_manager`**, not in ad-hoc scripts here.
- **Node product UI:** `Services/Interfaces/node_api_interface` exposes FastAPI routes that submit **`UserAction`** to the node; `node_web_interface` is the Vite/React app (Biome, vitest). Action **business logic** belongs in **node** executors—do not duplicate it only in tentacle routes.
- **Profiles:** shipped profiles and `specific_config/` appear under the **installed** tree; feature work stays under sources paths above.

## Owns

- `packages/tentacles/**` for feature work (strategies, exchanges, services, node UI tentacles, etc.)

## Public surface

- Tentacle modules discovered after install (paths mirror sources under repo-root `tentacles/`)
- Loaders and activation via `octobot_tentacles_manager`—not a single top-level Python package name in this repo layout

## May depend on

- All relevant `octobot_*` packages; `node_web_interface` uses npm build in the tentacles tree

## Do not

- Commit changes under repo-root `tentacles/` (generated)
- Skip `bash .cursor/reinstall-tentacles.sh` after source edits in cloud or agent handoff flows
- Hand-edit generated `__init__.py` in sources without understanding tentacles_manager regeneration
- Rewrite core `ExchangeManager` here—subclass connectors and modes in tentacles

## Tests

- Often via `octobot` job: `pytest --ignore=tentacles/Trading/Exchange tentacles`
- UI: `packages/tentacles/Services/Interfaces/node_web_interface` (npm/vitest)

## Related human doc

- `docs/content/developers/packages/tentacles.md`
- `docs/content/guides/octobot-tentacles/`

## Last reviewed

- 2026-09-16
