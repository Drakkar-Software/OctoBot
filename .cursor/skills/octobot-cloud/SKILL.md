---
name: octobot-cloud
description: >-
  OctoBot git repo on Cursor Cloud Agent: bash, cloud-install, tentacles reinstall,
  pytest/pylint, debugging failing pytest (integration/functional, cross-package),
  extended_linter, changes under octobot/, packages/, packages/tentacles/.
---

# OctoBot Cloud Agent

Multi-step **roadmap** plans (title or description contains `roadmap`): author with skill **cloud-roadmap** (`.cursor/skills/cloud-roadmap/SKILL.md`); execute with this skill.

## Workflow

1. `source .cursor/env.sh` before Python tooling.
2. Checkout **`dev`** (or user base) → create feature branch → implement → commit → PR to **`dev`** (match `--base` on extended_linter to PR target).
3. After `packages/tentacles/` edits: `bash .cursor/reinstall-tentacles.sh`.
4. Before handoff: `python -m tools.extended_linter --base origin/dev` (or `origin/<base_ref>`).
5. Run targeted pytest per [reference-pytest.md](reference-pytest.md) (CI matrix). **If any test fails,** start with [step 1 — visible logs](reference-pytest.md#1-re-run-with-visible-logs), then follow [When tests fail](reference-pytest.md#when-tests-fail) **before** changing production code or the harness.

## Install and env

- Profile default: **`ci-tentacles`** (`environment.json` → `OCTOBOT_CLOUD_PROFILE=ci-tentacles bash .cursor/cloud-install.sh`).
- **Success:** Build log contains `OCTOBOT_CLOUD_INSTALL_OK`. Do not guess from UI alone.
- **Validate:** `bash .cursor/cloud-validate.sh --profile ci-tentacles --json`
- Profiles: `package-only` (no tentacles), `ci-tentacles` (CI parity), `ui-node-web` (+ web UI build).

## Layout

- Repo root: OctoBot application, `packages/*`, `tools/`, root `AGENTS.md` (package boundaries colocated as `AGENTS.md`).
- Installed tentacles output: repo-root `tentacles/` (generated — never edit).
- Tentacles sources: `packages/tentacles/`.

## Policy and verify

- Machine rules: `tools/extended_linter/config/policy.yaml` (extend via `tools/extended_linter/ARCHITECTURE.md`)
- CLI: `python -m tools.extended_linter --base origin/dev --continue --report json`
- Read reports: `rule_id`, `file`, `line`, `hint` blocks.

## Architecture docs

- Index: root `AGENTS.md` (when to read, CI matrix table)
- Per-package: `octobot/AGENTS.md`, `packages/tentacles/AGENTS.md`, `packages/<name>/AGENTS.md`
- Read colocated `AGENTS.md` before cross-package or tentacles changes.

## Formatting (touched paths only in 1b)

- Python: `ruff format` / `ruff check` when configured (CI enforce later).
- `node_web_interface`: Biome in `packages/tentacles/Services/Interfaces/node_web_interface/`.

## Pytest

See **[reference-pytest.md](reference-pytest.md)** for cwd and PYTHONPATH per CI matrix package.

### When a test fails

1. **Re-run** the failing node with log-cli per [step 1](reference-pytest.md#1-re-run-with-visible-logs) (single process; omit `-n auto`).
2. State the **invariant** (one sentence: what must be true when the test passes).
3. Find the **failure boundary** (last good layer vs first bad layer); do not widen mocks, seeds, or timeouts until that boundary is clear.
4. Apply the full protocol in [When tests fail](reference-pytest.md#when-tests-fail) before editing production code or the harness.

## Node UI manual QA (agent seed)

**Not required** for normal pytest / `ci-tentacles` package work — only when the task uses the live Node web UI.

For **`ui-node-web`**: follow skill **agent-seed** (`.cursor/skills/agent-seed/SKILL.md`). Typical one-shot: `source .cursor/env.sh`, `source .cursor/agent-seed.env`, stop any running node, then `bash .cursor/seed-agent.sh --full`. After startup, log in with passphrase **`demodemo`**; use the full **`/app`** UI as needed, and **`/app/debug`** to send user actions.

## Out of scope unless asked

- Live bot ports, docker image publish, signed tentacles release pipeline.
- `pip install` / `npm install` to fix imports.
