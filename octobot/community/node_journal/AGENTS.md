# Agents: node_journal

## Role

Append-only **node journal**: record lifecycle and user-journey events for diagnostics, analytics, and **export/sharing** (e.g. upload envelope). Tier-1 API: `octobot.community.node_journal` (see [`__init__.py`](__init__.py) import tiers).

## Owns

- `octobot/community/node_journal/` (recording, store, state, journey export)

## Public surface (integrators)

- **Write:** `record`, `record_*` helpers exported from `octobot.community.node_journal`
- **Read (export only):** `read_events`, `build_journey_summary`, `build_upload_envelope` for journal export pipeline inside this package (and tests)

## External integrators (`packages/sync`, wallet, node, tentacles, etc.)

- **Record only.** Do not call `read_events`, read journal files on disk, or use journal contents for control flow.
- Do not treat journal or [`state.py`](state.py) persistence as source of truth for app behavior.

## Not a source of truth

- Do not store data in journal payloads to reuse later for non-journal features.
- Authoritative state lives in config, databases, sync collections, and domain modules, not the journal.

## Literals

- Journal-specific events and wire keys: [`events.py`](events.py), [`constants.py`](constants.py), [`enums.py`](enums.py) (large dedicated set; submodule files are the exception to package-top-level constants).
- Extend those modules; do not inline strings in recording code.

## Layers

- Follow layer rules in package docstring: `journal` / `store` / `state` must not import from `recording/` or `lifecycle` in forbidden directions; feature code uses the public API only.

## Tests

- **cwd:** repo root
- **Example:** `pytest tests/unit_tests/community/node_journal`

## Related

- Skill **node-journal** (`.cursor/skills/node-journal/SKILL.md`)
- [`octobot/AGENTS.md`](../../AGENTS.md)

## Last reviewed

- 2026-09-21
