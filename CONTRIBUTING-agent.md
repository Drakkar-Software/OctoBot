# Contributing (agents and automation)

## Cloud environment

See [`.cursor/README.md`](.cursor/README.md). Install profile **`ci-tentacles`** for CI parity. Confirm `OCTOBOT_CLOUD_INSTALL_OK` in Build logs.

## Workflow

1. Branch from `dev` (or user-specified base).
2. For cross-package work, read root [`AGENTS.md`](AGENTS.md) and each colocated `AGENTS.md` for packages you touch.
3. Run `python -m tools.extended_linter --base origin/<pr-base>` before handoff.
4. Do not commit agent session plans (`path.deny_agent_plans`: `PLAN-*.md`, `*.plan.md`, `.cursor/plans/`). Node UI: Vitest + Python/API tests only — no Playwright e2e under `node_web_interface/e2e/` (`path.deny_node_web_playwright_e2e`).
5. **Agent docs:** edit `AGENTS.md`, `.cursor/skills/**`, `.cursor/rules/**`, `.cursor/README.md`, `CONTRIBUTING-agent.md`, and `tools/**/README.md` / `tools/**/ARCHITECTURE.md` only when the PR owns them. `extended_linter` blocks shrink/backdated **Last reviewed** (where present) vs merge-base (`agent_docs.no_regression_vs_merge_base`). Large trims need explicit reviewer intent.
6. CI: **OctoBot-CI** job **`extended_linter`** (`pytest tools/tests` with wheel + tentacles; PR policy with `--skip-tentacles-reinstall`, no `cloud-install`). Package **`tests`** matrix unchanged.

## Adding a policy rule

See [tools/extended_linter/README.md#adding-a-rule](tools/extended_linter/README.md) and [ARCHITECTURE.md](tools/extended_linter/ARCHITECTURE.md).

1. Edit `tools/extended_linter/config/policy.yaml` with a new stable `rule_id`.
2. Extend `layers/` if a new `kind` is needed.
3. Add tests under `tools/tests/extended_linter/layers/`.
4. Summarize in `octobot-cloud` skill only for human context; YAML is the contract.

## AGENTS.md hygiene

When you change package boundaries (owns, public API, test cwd), update the matching colocated `AGENTS.md` (`octobot/`, `packages/<name>/`, or `packages/tentacles/`) and bump **Last reviewed**. `extended_linter` enforces no shrink/backdate on agent-doc paths vs merge-base (`agent_docs.no_regression_vs_merge_base`); it does not require updates when boundaries change.

### AGENTS.md sections (new packages)

Use this outline in `packages/<name>/AGENTS.md` (or `octobot/AGENTS.md` for core app):

```markdown
# Agents: `<package>`

## Role

One paragraph: what this package does in OctoBot.

## Owns

- `packages/<name>/...` paths agents may edit for tasks here.

## Public surface

- Import paths / modules other packages should use.

## May depend on

- Upstream packages (import direction).

## Do not

- Forbidden imports, layers to bypass, paths owned elsewhere.

## Tests

- **cwd:** `packages/<name>` or repo root
- **PYTHONPATH:** if any
- **Example:** `pytest ...`

## Related human doc

- Link to `docs/content/developers/packages/...` when it exists.

## Last reviewed

- YYYY-MM-DD
```

## Node journal

The node journal (`octobot.community.node_journal`) is an append-only event log for diagnostics, journey analytics, and **export/sharing**. It is **not** a source of truth.

- **Outside `octobot/community/node_journal/`:** call Tier-1 **`record_*`** / `record` only. Do not call `read_events`, read journal files on disk, or branch product logic on journal contents.
- **Inside the package:** `read_events`, `build_journey_summary`, and `build_upload_envelope` are for the **export pipeline** (plus unit tests).
- Do not store data in journal payloads to reuse later for non-journal features; use config, DB, sync collections, or domain stores instead.
- Details: [`octobot/community/node_journal/AGENTS.md`](octobot/community/node_journal/AGENTS.md) and skill **node-journal** (`.cursor/skills/node-journal/SKILL.md`).

## Python conventions (agents)

Authoritative rules for Python in `octobot/` and `packages/`. Cloud agents: also summarized in `.cursor/rules/octobot-cloud.mdc`.

### Shared literals (magic strings)

- Put cross-module identifiers in the **owning package** at **package top level** when only a few literals are needed: e.g. [`octobot/constants.py`](octobot/constants.py), [`octobot/enums.py`](octobot/enums.py), or `packages/<name>/octobot_<name>/constants.py` and `enums.py`.
- TypeScript: `constants.ts` / `wireConstants.ts` where applicable; see [`docs/content/client-sdk/wire-contract.md`](docs/content/client-sdk/wire-contract.md) for cross-language wire literals.
- Callers use `import module as alias` and `alias.NAME`; do not duplicate the same string in multiple files.
- **OK inline:** log/debug text; truly local one-off values never compared or reused elsewhere.
- **Submodule `constants.py` / `enums.py`:** only when a sub-area owns a **large** dedicated literal surface (exemplar: [`octobot/community/node_journal/constants.py`](octobot/community/node_journal/constants.py), [`enums.py`](octobot/community/node_journal/enums.py)). Do not add deep per-folder constant files for a handful of strings.

### Imports

- Prefer imports at **module top level**.
- Use `import xxx` or `import xxx as yy`; access via `xxx.name` or `yy.name`.
- Avoid `from xxx import yy` in normal module code; avoid lazy (function-scoped) imports unless breaking a documented import cycle or loading an optional heavy dependency on a rare path.
- **`from xxx import yyy` is allowed only in `__init__.py`** when re-exporting the public surface (see below).

### Package `__init__.py` as public bridge

- Re-export the **public surface** from each package/subpackage `__init__.py` so callers use one stable import (e.g. `import octobot_trading.personal_data as personal_data`) instead of deep internal paths.
- Example: [`packages/trading/octobot_trading/personal_data/__init__.py`](packages/trading/octobot_trading/personal_data/__init__.py).
- When adding a new public symbol, export it from the appropriate `__init__.py`.

## Formatting

Ruff/Biome configs are present; mass format and CI enforce land in later phases. Do not run repo-wide reformat in routine agent PRs unless requested.
