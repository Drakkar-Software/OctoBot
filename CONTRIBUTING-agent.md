# Contributing (agents and automation)

## Cloud environment

See [`.cursor/README.md`](.cursor/README.md). Install profile **`ci-tentacles`** for CI parity. Confirm `OCTOBOT_CLOUD_INSTALL_OK` in Build logs.

## Workflow

1. Branch from `dev` (or user-specified base).
2. For cross-package work, read root [`AGENTS.md`](AGENTS.md) and each colocated `AGENTS.md` for packages you touch.
3. Run `python -m tools.extended_linter --base origin/<pr-base>` before handoff.
4. CI: **OctoBot-CI** job **`extended_linter`** (`pytest tools/tests` with wheel + tentacles; PR policy with `--skip-tentacles-reinstall`, no `cloud-install`). Package **`tests`** matrix unchanged.

## Adding a policy rule

See [tools/extended_linter/README.md#adding-a-rule](tools/extended_linter/README.md) and [ARCHITECTURE.md](tools/extended_linter/ARCHITECTURE.md).

1. Edit `tools/extended_linter/config/policy.yaml` with a new stable `rule_id`.
2. Extend `layers/` if a new `kind` is needed.
3. Add tests under `tools/tests/extended_linter/layers/`.
4. Summarize in `octobot-cloud` skill only for human context; YAML is the contract.

## AGENTS.md hygiene (guidance, not CI in v1)

When you change package boundaries (owns, public API, test cwd), update the matching colocated `AGENTS.md` (`octobot/`, `packages/<name>/`, or `packages/tentacles/`) and bump **Last reviewed**. CI does not enforce this yet.

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

## Formatting

Ruff/Biome configs are present; mass format and CI enforce land in later phases. Do not run repo-wide reformat in routine agent PRs unless requested.
