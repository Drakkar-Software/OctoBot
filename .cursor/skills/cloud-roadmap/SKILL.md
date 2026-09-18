---
name: cloud-roadmap
description: >-
  Authors Cursor Plans for the OctoBot git repo that run on Cursor Cloud Agents.
  Automatically applies whenever CreatePlan is used and the plan title or
  overview/description contains "roadmap" (case-insensitive). Also applies when
  the user asks for a cloud roadmap, cloud-safe multi-step plan, or names
  cloud-roadmap. Requires repo-relative paths only, package/module responsibility
  maps, clarify-before-assume, validation milestones with unit tests (pytest or
  npm test/vitest) and functional tests when relevant, package ownership, and
  clarification before guessing.
---

# Cloud roadmap (Plan authoring)

Execution after the plan: skill **octobot-cloud** (`.cursor/skills/octobot-cloud/SKILL.md`).

## Activation

**Mandatory** before `CreatePlan` when the plan **name, title, or overview/description** contains `roadmap` (any case).

Also when the user invokes **cloud-roadmap** or asks for a **cloud-safe multi-step plan**.

1. Read **octobot-cloud** first.
2. Skim root `AGENTS.md` and every colocated `AGENTS.md` for packages in scope.
3. If not in Plan mode but the user wants a roadmap-style plan, use the same rules in the reply or switch to Plan + `CreatePlan`.

**Output:** submit via **CreatePlan** only. Do **not** write `.cursor/roadmaps/*.md` unless the user asks to persist a file. Never commit plan artifacts in the repo (`PLAN-*.md`, `*.plan.md`, `.cursor/plans/`) — `path.deny_agent_plans`.

## Clarify first; never guess

Cloud agents cannot load workspace-only skills. Mirror clarify-dont-assume here.

- If scope, PR target, behavior, boundaries, or **which package owns a change** is unclear, **stop and ask** (**AskQuestion** when available; otherwise 1–2 focused questions). Do **not** call **CreatePlan** until resolved or labeled **user must choose**.
- Plans may only use: (1) user input, (2) facts **verified** in this repo (`AGENTS.md`, search), (3) answers after you asked.
- Ask when: multiple owners, cross-package impact, tentacles vs `octobot` vs `tools/`, missing acceptance criteria, fix vs refactor, unknown PR base.

## Hard constraints (every roadmap plan)

| Rule | Detail |
|------|--------|
| Scope | OctoBot repo only: `octobot/`, `packages/`, `tools/`, `.cursor/`, `tests/`. No monorepo siblings, `cursor_cloud_env/`, or workspace-only skills. |
| Paths | Repo-relative from OctoBot root. Forbidden: `C:\...`, `/Users/...`, `../OctoBot/`, `OctoBot/` prefix at repo root. |
| Env | `source .cursor/env.sh` before Python/shell test steps. |
| Install | No `pip install` / `npm install` to fix imports. |
| Tentacles | Edit `packages/tentacles/` only; after edits `bash .cursor/reinstall-tentacles.sh`; never edit repo-root `tentacles/`. |

## Responsibility map (required section in the plan)

Place **before** phased steps. Verify paths; cite `AGENTS.md`.

```markdown
## Responsibility map

| Concern / behavior | Package | Module or path (repo-relative) | Role in this roadmap |
|--------------------|---------|--------------------------------|----------------------|
| … | `packages/<name>` or `octobot` | `…/module.py` or subpath | Owns … / calls … / exposes … |
```

- One **primary owner** per concern; others as **depends on** or **integration point**.
- **Module** = real file or directory (search repo; read **Owns** in `AGENTS.md`). If still ambiguous, **ask** before locking the table.
- Each implementation **step** references at least one row.

## Plan shape

Use **phases** and **steps**. Each step ends with a **Validation milestone** including **tests**.

```markdown
### Step N — [short title]
**Work:** …
**Owns:** `packages/<pkg>/…` (from responsibility map)
**Validation milestone:**
- **Unit tests (required):**
  - Test file(s): `…`
  - Cases: each behavior (happy path, regression, edges for edited APIs)
  - **Command:** `pytest …` or `npm test` (cwd per below)
  - **Pass criteria:** all listed tests green; no untested new public behavior
- **Functional tests:** propose explicitly, or **N/A — reason**
- **Other checks:** reinstall tentacles, cloud-validate, etc. if needed
- **If fail:** …
```

Rules:

- Steps that **create or edit** code or runtime policy YAML need a **complete** unit-test list for that step’s delta (map each new/changed symbol or config key to a scenario).
- Unit tests in the **same step** as the code (test-first or test-same-step).
- **Functional tests:** required to propose or decline with reason when the step touches HTTP/API, tentacles loading, multi-package flows, CLI, Node UI, or trading/backtesting pipelines.
- Final phase: handoff `python -m tools.extended_linter --base origin/dev` (or `origin/<pr-base>`).
- Prefer steps sized for **one Cloud session**; note dependencies.

## Testing in milestones

Pytest matrix: [reference-pytest.md](../octobot-cloud/reference-pytest.md) (skill **octobot-cloud**); on failure see [When tests fail](../octobot-cloud/reference-pytest.md#when-tests-fail).

| Layer | Requirement | Where |
|-------|-------------|--------|
| Unit (Python) | Test path + enumerated behaviors | Package `tests/` or `tools/tests/…` per `AGENTS.md` **Tests** |
| Unit (Node UI) | TS under `packages/tentacles/Services/Interfaces/node_web_interface/` | `src/**/__tests__`; cwd that directory; `npm test` (vitest). Profile **`ui-node-web`** if build env needed. |
| Functional / integration | Cross-package or I/O flows | `tools/tests`, integration dirs, tentacles-dependent pytest |
| UI functional | Browser / seeded grid | Default **N/A — Vitest + API tests**; **agent-seed** only when the user explicitly wants manual `/app` QA — **not** new Playwright `e2e/` files in git (`path.deny_node_web_playwright_e2e`) |

**Milestone catalog**

| Type | When |
|------|------|
| Env | `source .cursor/env.sh` at start of implementation |
| Unit tests | Every code/policy step — `pytest` or `npm test` |
| Install health | After `.cursor/` changes — `bash .cursor/cloud-validate.sh --profile ci-tentacles --json` |
| Tentacles sync | After `packages/tentacles/**` — `bash .cursor/reinstall-tentacles.sh` + related pytest if needed |
| PR gate | Handoff — `python -m tools.extended_linter --base origin/dev` |
| Functional / UI | Per step when relevant; **agent-seed** for `/app` |

## Skill and doc routing

| Situation | Use |
|-----------|-----|
| Implement / verify in cloud | **octobot-cloud** |
| Pytest cwd / PYTHONPATH | **octobot-cloud** → `reference-pytest.md` |
| Node UI unit tests | `packages/tentacles/Services/Interfaces/node_web_interface/` → `npm test` |
| Node UI browser QA | **agent-seed** |
| Package boundaries | colocated `AGENTS.md` |
| Contributor workflow | `CONTRIBUTING-agent.md` |
| Cloud install | `.cursor/README.md` |

## Checklist before CreatePlan

- [ ] Ambiguities resolved or marked **user must choose**
- [ ] **Responsibility map** complete
- [ ] Every code step: unit tests (files, scenarios, command)
- [ ] Every code step: functional tests proposed or **N/A — reason**
- [ ] No absolute or out-of-repo paths
- [ ] Steps name owning package/module
- [ ] Git/PR to **`dev`** (or stated base) if the roadmap includes git work
