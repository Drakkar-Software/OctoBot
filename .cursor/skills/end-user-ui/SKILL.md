---
name: end-user-ui
description: >-
  End-user UX for node_web_interface (React) and web_interface (Flask/templates):
  entry-level trading terms OK, no pro-trader jargon, minimal UI, situational focus,
  no AI slop, no em dash in UI strings. Apply on any UI copy,
  layout, error, or help change.
paths:
  - packages/tentacles/Services/Interfaces/node_web_interface/**
  - packages/tentacles/Services/Interfaces/web_interface/**
---

# End-user UI (node + classic web)

Apply whenever you change user-visible copy, layout, errors, or help in the Node React UI or the classic Flask web UI tentacles.

## Sources only (tentacles)

- Edit UI only under `packages/tentacles/Services/Interfaces/node_web_interface/` or `packages/tentacles/Services/Interfaces/web_interface/`.
- Do not open or patch repo-root `tentacles/` (install output). After tentacles source changes: `bash .cursor/reinstall-tentacles.sh`.

Colocated guides: `packages/tentacles/Services/Interfaces/node_web_interface/AGENTS.md`, `.../web_interface/AGENTS.md`. Technical Node UI workflow (when present in the monorepo): workspace skill **node-web-interface-workflow**; cloud agents: skill **octobot-cloud** and `node_web_interface/README.md` for npm cwd.

## Audience

- Assume an **average non-technical** user who may be new to OctoBot but is using a **trading bot**. Not a developer, not a pro desk.
- One primary goal per screen or step: show status, fix one problem, or confirm one action.

## Language: entry-level trading OK; pro/advanced not

- **OK:** everyday trading vocabulary users expect: buy/sell, order, pair, exchange, balance, profit/loss, stop loss, take profit, market/limit, position (when the feature uses it). Keep terms **short and consistent** with labels elsewhere in the app.
- **Avoid:** advanced or pro-trader jargon: maker/taker fee tiers, funding rate mechanics, delta-neutral, basis, slippage models, OCO/iceberg unless the UI is explicitly an advanced screen; desk slang; dense acronyms without expansion on first use in that flow.
- **Dev/infra:** still translate. Avoid "credentials", "auth payload", "session invalidated" without plain-language equivalent ("password" / "passphrase" per product).

## Understandable

- Short sentences; active voice; say what happened and what to do next.
- If a term is required, prefer **entry-level trading** over **pro**; add one short gloss only when the screen cannot work without it (not a glossary block).
- Errors: **title + one explanation**; optional **at most 1–2** tips only when they change behavior. Not a wall of suggestions.

## Simple (less is better)

- Remove or defer secondary info, debug detail, and duplicate controls.
- Progressive disclosure: advanced fields behind "Advanced" or debug routes only (`/app/debug` stays operator-facing).
- Empty states: one line what this is plus one action. Not essays.

## No AI slop

- Ban list (examples): filler openers ("Certainly", "Great question"), **marketing** buzzwords ("seamless", "robust", "empower", "leverage" as hype), emoji decoration, generic tip lists, three-panel "guidance" when one line suffices, marketing tone in errors.
- **No em dash (`—`) in user-visible UI copy** (labels, titles, errors, toasts, template text). Use a period, comma, colon, or parentheses instead; match punctuation already used on the same screen.
- Match **existing** OctoBot/Node UI tone in nearby components; read siblings before inventing new patterns.
- Do not add UI "just to be helpful" if Vitest/API already cover behavior; user-visible text must earn its space.

## By stack

| Stack | Where copy lives |
|-------|------------------|
| `node_web_interface` | React components, route copy, toasts; keep logic in code/tests per skill **octobot-cloud** (Vitest, no e2e). |
| `web_interface` | Jinja templates, flash messages, modal titles; Python strings visible in templates. |

## Before handoff (UI PR)

- Re-read changed strings aloud as a non-expert.
- `npm test` in `packages/tentacles/Services/Interfaces/node_web_interface/` when touched; pytest for `web_interface/tests` when touched.
- No new Playwright e2e; agent-seed only if the user asked for live QA.
