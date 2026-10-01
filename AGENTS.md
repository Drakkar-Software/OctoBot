# Agent quick pointer (OctoBot repo)

This repository is the **OctoBot** application and its `packages/*` monorepo. Default integration branch: **`dev`** (open PRs to `dev` unless told otherwise).

## Cursor Cloud

- Environment: [`.cursor/README.md`](.cursor/README.md), `environment.json`, `source .cursor/env.sh`
- Skill (procedures): `.cursor/skills/octobot-cloud/SKILL.md`
- Roadmap plans: before `CreatePlan`, if the plan title or description contains `roadmap`, follow `.cursor/skills/cloud-roadmap/SKILL.md`
- Always-on rules: `.cursor/rules/octobot-cloud.mdc`

## Before you finish

```bash
source .cursor/env.sh
python -m tools.extended_linter --base origin/dev
```

Use `origin/<base>` matching your PR target. Policy: `tools/extended_linter/config/policy.yaml` — see `tools/extended_linter/ARCHITECTURE.md`. No agent plan files or Node UI Playwright e2e in the diff (`path.deny_agent_plans`, `path.deny_node_web_playwright_e2e`). No accidental agent-doc regressions (`agent_docs.no_regression_vs_merge_base`; see `octobot-cloud.mdc`).

## Architecture for agents

Colocated **`AGENTS.md`** files describe package boundaries (owns, deps, tests). They are for automation; human docs live under `docs/content/` (Docusaurus).

### When to read

| Situation | Read |
|-----------|------|
| Single package task | `packages/<name>/AGENTS.md` |
| Core app / CLI / config | [`octobot/AGENTS.md`](octobot/AGENTS.md) |
| Tentacles sources vs install | [`packages/tentacles/AGENTS.md`](packages/tentacles/AGENTS.md) |
| Node UI or classic web UI (copy, layout, errors) | [`packages/tentacles/Services/Interfaces/node_web_interface/AGENTS.md`](packages/tentacles/Services/Interfaces/node_web_interface/AGENTS.md), [`packages/tentacles/Services/Interfaces/web_interface/AGENTS.md`](packages/tentacles/Services/Interfaces/web_interface/AGENTS.md), skill **end-user-ui** (`.cursor/skills/end-user-ui/SKILL.md`) |
| Node journal (record / export) | [`octobot/community/node_journal/AGENTS.md`](octobot/community/node_journal/AGENTS.md), skill **node-journal** (`.cursor/skills/node-journal/SKILL.md`) |
| Python style (imports, literals, `__init__.py` API) | [CONTRIBUTING-agent.md](CONTRIBUTING-agent.md) — **Python conventions (agents)** |
| Cross-package or tentacles | This file + every involved colocated `AGENTS.md` |
| Node UI demo / agent-seed QA | [`tools/agent_seed/README.md`](tools/agent_seed/README.md) + skill **agent-seed** (`.cursor/skills/agent-seed/SKILL.md`) |

### Dependency sketch

```mermaid
flowchart TB
  octobot[octobot app]
  commons[commons]
  trading[trading]
  evaluators[evaluators]
  services[services]
  tentacles_pkg[packages/tentacles sources]
  octobot --> commons
  octobot --> trading
  octobot --> evaluators
  octobot --> services
  trading --> commons
  evaluators --> commons
  tentacles_pkg --> services
```

### CI matrix packages (colocated `AGENTS.md`)

| Package | Path |
|---------|------|
| Core application | [`octobot/AGENTS.md`](octobot/AGENTS.md) |
| Tentacles sources | [`packages/tentacles/AGENTS.md`](packages/tentacles/AGENTS.md) |
| agents | [`packages/agents/AGENTS.md`](packages/agents/AGENTS.md) |
| async_channel | [`packages/async_channel/AGENTS.md`](packages/async_channel/AGENTS.md) |
| backtesting | [`packages/backtesting/AGENTS.md`](packages/backtesting/AGENTS.md) |
| commons | [`packages/commons/AGENTS.md`](packages/commons/AGENTS.md) |
| copy | [`packages/copy/AGENTS.md`](packages/copy/AGENTS.md) |
| evaluators | [`packages/evaluators/AGENTS.md`](packages/evaluators/AGENTS.md) |
| flow | [`packages/flow/AGENTS.md`](packages/flow/AGENTS.md) |
| node | [`packages/node/AGENTS.md`](packages/node/AGENTS.md) |
| protocol | [`packages/protocol/AGENTS.md`](packages/protocol/AGENTS.md) |
| services | [`packages/services/AGENTS.md`](packages/services/AGENTS.md) |
| sync | [`packages/sync/AGENTS.md`](packages/sync/AGENTS.md) |
| tentacles_manager | [`packages/tentacles_manager/AGENTS.md`](packages/tentacles_manager/AGENTS.md) |
| trading | [`packages/trading/AGENTS.md`](packages/trading/AGENTS.md) |

New packages: follow **AGENTS.md sections** in [CONTRIBUTING-agent.md](CONTRIBUTING-agent.md).

## Humans

- [CONTRIBUTING-agent.md](CONTRIBUTING-agent.md) — agents, policy, boundaries
