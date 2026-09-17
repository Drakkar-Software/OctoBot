---
name: agent-seed
description: >-
  Demo Node UI QA: seed/clear/bootstrap, first login passphrase, full /app UI for
  bugs and experiments, /app/debug to send user actions. Skip for pytest-only work.
---

# Agent seed (Node UI demo)

Full reference: [`tools/agent_seed/README.md`](../../../tools/agent_seed/README.md). Code layout: [`tools/agent_seed/ARCHITECTURE.md`](../../../tools/agent_seed/ARCHITECTURE.md).

## When to use / when to skip

| Task | Agent-seed? |
|------|-------------|
| `pytest`, linters, package tests | **Skip** |
| Live Node web UI (any `/app` page or debug) | **Use** this skill |

| Goal | Command (node stopped unless noted) |
|------|-------------------------------------|
| First UI fixture data | `--full` or `seed` then `start` (+ optional `bootstrap`) |
| Wipe + fresh fixtures | `--clear` → `start` or `--full` |
| Node already up, need grid RUNNING | `bootstrap` only |
| Node up, UI only | Login → use `/app` as needed; `/app/debug` when sending user actions |

- **`seed`**: fixtures + wallet (required for UI).
- **`bootstrap`**: start grid automation (optional unless task needs RUNNING grid).

## Prep

```bash
source .cursor/env.sh
source .cursor/agent-seed.env
```

Master tentacles on `user/reference_tentacles_config/` must exist (see `tools/agent_seed/README.md`).

## Commands (OctoBot repo root)

```bash
bash .cursor/seed-agent.sh --full    # seed + background start + bootstrap — stop node first; do NOT run start again
bash .cursor/seed-agent.sh --clear   # wipe + re-seed — stop node first
bash .cursor/seed-agent.sh bootstrap # node must already listen on AGENT_SEED_BASE_URL
bash .cursor/seed-agent.sh start     # foreground start only
```

**`--full` starts OctoBot.** Never double-start. Stop before `--full` or `--clear`.

## After seed: interact with the UI

1. Open **`http://127.0.0.1:8000/app/login`** (or `/app` → login).
2. Enter passphrase **`demodemo`** (every new browser session).
3. Use the **full Node UI under `/app`** to find bugs, reproduce issues, or experiment with seeded accounts and strategies.
4. Use **`/app/debug`** when the task is to **send commands to the node** — user actions, automation controls, and debug tables (automations, accounts, user-action history). This is usually the most useful page for driving the scheduler, not the only page you may visit.

Credentials: wallet `0x70997970c51812dc3a010c7d01b50e0d17dc79c8`, display name `demo` — see fixture README.

HTTP Basic (`wallet:passphrase`) works for **`/api/v1/debug/`** without a browser session (headless equivalent of debug-view user actions).

## Demo-only

Committed insecure wallet in `tools/agent_seed/secrets.py` — never mainnet / real trading. Sandbox blocks live exchange/automation creation (`octobot_node/agent_seed/demo_wallet.py`).
