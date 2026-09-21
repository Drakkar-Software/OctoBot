---
name: node-journal
description: >-
  Node journal (octobot.community.node_journal): record-only from outside the
  package; reads only for export inside node_journal; not a source of truth.
  Apply when editing node_journal or adding/changing record_* calls elsewhere.
paths:
  - octobot/community/node_journal/**
---

# Node journal

Full rules: [`octobot/community/node_journal/AGENTS.md`](../../../octobot/community/node_journal/AGENTS.md).

## Purpose

Append-only **event log** for diagnostics, journey analytics, and **export/sharing** (upload envelope). Not authoritative application state.

## Integrators (outside `node_journal/`)

- Import `octobot.community.node_journal` and call Tier-1 **`record_*`** / `record` only.
- Do **not** call `read_events`, read journal files on disk, or branch product logic on journal contents.
- Do **not** store data in journal payloads to reuse later for non-journal features. Use config, DB, sync collections, or domain stores as source of truth.

## Inside `octobot/community/node_journal/`

- **`read_events`**, `build_journey_summary`, and `build_upload_envelope` belong to the **export pipeline** (plus unit tests).
- Event and wire literals: extend [`events.py`](../../../octobot/community/node_journal/events.py), [`constants.py`](../../../octobot/community/node_journal/constants.py), [`enums.py`](../../../octobot/community/node_journal/enums.py); do not inline strings in recording code.
- Respect import tiers in package [`__init__.py`](../../../octobot/community/node_journal/__init__.py); feature code must not reach into `store` / `state` except via the public API.

## Related

- Core app boundaries: [`octobot/AGENTS.md`](../../../octobot/AGENTS.md)
- Python conventions (shared literals, imports): [CONTRIBUTING-agent.md](../../../CONTRIBUTING-agent.md) — **Python conventions (agents)**
