# Agents: node_web_interface

## Role

Node product **React** web UI (`octobot-node`): Vite, TanStack Router/Query, Tailwind. Built bundle in `dist/` ships with the tentacle.

## End-user UX (mandatory)

Read skill **end-user-ui** (`.cursor/skills/end-user-ui/SKILL.md`) before any user-visible copy, layout, error, or help change.

- Entry-level trading terms OK; no pro-trader jargon.
- Minimal UI; one primary goal per screen.
- No AI slop; no em dash (`—`) in user-visible strings.

## Owns

- `src/`, tests, `package.json` under **this** `packages/tentacles/.../node_web_interface/` path
- Not `src/client/*` (generated via `npm run generate-client`)
- Not repo-root `tentacles/` (install output)

## Do not

- Edit repo-root `tentacles/`; after source changes run `bash .cursor/reinstall-tentacles.sh`
- Hand-edit `openapi.json` or generated client files (see [`../../../AGENTS.md`](../../../AGENTS.md#node-rest-openapi-node_api_interface--node_web_interface))
- Add Playwright e2e under `e2e/` (`path.deny_node_web_playwright_e2e`)

## Tests

- `npm test` (Vitest) from this directory; see [README.md](README.md)

## Related

- Tentacles index: [`packages/tentacles/AGENTS.md`](../../../AGENTS.md)
- Node REST OpenAPI: `node_api_interface` tentacle (same parent `Services/Interfaces/`)

## Last reviewed

- 2026-09-19
