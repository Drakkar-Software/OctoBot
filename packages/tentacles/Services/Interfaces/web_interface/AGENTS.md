# Agents: web_interface

## Role

Classic OctoBot **Flask** web UI: Jinja templates, static assets, and controllers that drive user-facing pages.

## End-user UX (mandatory)

Read skill **end-user-ui** (`.cursor/skills/end-user-ui/SKILL.md`) before templates, flash messages, modal titles, or any user-visible string change.

- Entry-level trading terms OK; no pro-trader jargon.
- Minimal UI; one primary goal per screen.
- No AI slop; no em dash (`—`) in user-visible strings.

## Owns

- `templates/`, `static/`, and user-visible controller copy under **this** `packages/tentacles/.../web_interface/` path
- Tests under `tests/` when present

## Do not

- Edit repo-root `tentacles/` (install output). After source changes: `bash .cursor/reinstall-tentacles.sh`

## Tests

- Pytest under this tentacle's `tests/` when present; follow [`packages/tentacles/AGENTS.md`](../../../AGENTS.md) for broader tentacles pytest invocations

## Related

- Tentacles index: [`packages/tentacles/AGENTS.md`](../../../AGENTS.md)

## Last reviewed

- 2026-09-19
