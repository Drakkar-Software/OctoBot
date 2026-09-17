# Agent seed demo wallet (local / Cloud QA)

> **Warning — demo-only fixture**
>
> This wallet uses **publicly committed private key material** in `tools/agent_seed/secrets.py`.
> It is for **local development, automated agents, and Cloud manual QA only**.
> **Never fund it on mainnet** and **never use it for real trading**.

Canonical operator guide for `tools.agent_seed`. Short agent procedure: skill **agent-seed** (`.cursor/skills/agent-seed/SKILL.md`). Code layout: [ARCHITECTURE.md](ARCHITECTURE.md).

## When you need this

**Most agent work does not use agent-seed.** `pytest`, linters, and package/backend tests do not require `user/agent-seed` or `seed-agent.sh`. Use [`.cursor/skills/octobot-cloud/reference-pytest.md`](../../.cursor/skills/octobot-cloud/reference-pytest.md) (after `source .cursor/env.sh`) and colocated `AGENTS.md` **Tests** sections.

Use agent-seed **only when the task needs the live Node web UI** (browser or debug view), for example Cloud profile **`ui-node-web`**, manual QA, or driving `/app/debug`.

| Goal | What to run |
|------|-------------|
| First time this environment needs UI fixture data | Stop any node → **`seed`** or **`--full`** (seed + background start + bootstrap) |
| UI work and you need a **clean wipe** | Stop node → **`--clear`** (wipe + re-seed) → **`start`** or **`--full`** if the node is not running |
| UI/debug only, fixtures already present | **`start`** if node down; optional **`bootstrap`** if grid automation must be RUNNING |
| Code/tests only | **Nothing** from agent-seed |

**Seed vs bootstrap**

- **`seed`**: sync collections, demo wallet, `config.json` — **required** for meaningful UI/debug (accounts, strategies, login wallet).
- **`bootstrap`**: `POST /api/v1/debug/` create-automation + wait for grid RUNNING — **optional** unless the task needs an active grid; debug view works with seeded data alone.

**`python -m tools.agent_seed all`** runs seed + bootstrap only (no `start.py`). Shell **`--full`** also starts OctoBot in the background.

## Prerequisites

- Tentacles installed on the **master** user folder (`OctoBot/user/reference_tentacles_config/tentacles_config.json` must exist). Typical: `ci-tentacles` / cloud install, or one normal OctoBot run on `user/` with `start.py tentacles --install --all`.
- Optional override: `OCTOBOT_AGENT_SEED_MASTER_USER_ROOT` (repo-relative or absolute) if master user data is not at `OctoBot/user/`.

## Login (Node web UI / HTTP Basic)

| Field | Value |
|-------|--------|
| Wallet address | `0x70997970c51812dc3a010c7d01b50e0d17dc79c8` (`DEMO_AGENT_SEED_WALLET_EVM_ADDRESS`) |
| Passphrase | `demodemo` (8+ chars required by Node wallet; see `tools/agent_seed/secrets.py`) |
| Display name | `demo` |

After seed, the UI shows **login** (passphrase), not wallet onboarding. **Every new browser session** must enter the passphrase once before using the app or debug view.

## Environment (`.cursor/agent-seed.env`)

From the OctoBot repo root, `seed-agent.sh` sources `.cursor/env.sh` and `.cursor/agent-seed.env`, then resolves paths under the repo.

| Variable | Role | Typical value (repo-relative) |
|----------|------|-------------------------------|
| `OCTOBOT_AGENT_SEED_USER_FOLDER` | Demo user data for `start.py --user-folder` and seed CLI | `user/agent-seed` |
| `NODE_SQLITE_FILE` | Scheduler DB for **seed/clear** wipe only | `user/agent-seed/tasks.db` |
| `AGENT_SEED_BASE_URL` | Bootstrap HTTP target (optional) | `http://127.0.0.1:8000` |

When **starting** OctoBot (not the seed CLI), set runtime scheduler DB via env **`SCHEDULER_SQLITE_FILE`** (see `octobot_services.constants.ENV_NODE_SQLITE_FILE`) to the full path of `user/agent-seed/tasks.db`. Do not confuse with **`NODE_SQLITE_FILE`**, which is only for seed/clear.

Also set **`EXIT_BEFORE_TENTACLES_AUTO_REINSTALL=true`** on agent demo `start.py` launches (`seed-agent.sh start` sets this automatically).

## `seed-agent.sh` commands

From OctoBot repo root (after sourcing env files):

| Command | Effect |
|---------|--------|
| `seed` | Write/refresh fixtures (idempotent; no wipe) |
| `seed` with second arg `--clear` | Not used by shell; use `--clear` below |
| `--clear` | Wipe user folder + sqlite, then re-seed (**node must be stopped**) |
| `start` | `start.py --master --user-folder …` (foreground) |
| `bootstrap` | HTTP bootstrap grid automation (node must be listening) |
| `--full` | `seed` → **`start.py` in background** → `bootstrap` |

### Node process rules

- **`--full` already starts OctoBot** (`run_start &`). Do **not** run `start` again afterward (port 8000 / duplicate process).
- **Stop the running node** before **`--full`** or **`--clear`**.
- Node **already running** and you only need bootstrap or UI: use **`bootstrap`** or open the UI — **not** `--full`.
- Prefer **stop → seed → start** over seeding while the node is up.

| Situation | Command |
|-----------|---------|
| Cold start: seed + node + bootstrap | Stop node → `--full` |
| Wipe fixture data (UI) | Stop node → `--clear` → `start` or `--full` |
| Node up, grid not RUNNING | `bootstrap` |
| Node up, UI only | Login → navigate `/app` as needed (no seed script); use `/app/debug` to send user actions |

## One-shot setup (UI)

```bash
source .cursor/env.sh
source .cursor/agent-seed.env
bash .cursor/seed-agent.sh --full
```

Stop any running node first. Wait for the background `start.py` before assuming bootstrap succeeded; if bootstrap races startup, run `bash .cursor/seed-agent.sh bootstrap` after the node listens.

Wipe only:

```bash
bash .cursor/seed-agent.sh --clear
# then start or --full
```

`seed` and `seed --clear` **always rewrite** `user/agent-seed/config.json` (accepted terms + readonly overlays to master `user/`). Re-running `seed` without `--clear` is safe: config and wallet are refreshed and partial sync data is completed. Sync is skipped only when the full demo fixture set is already present.

## After seed: Node UI and debug view

- App URL: **`http://127.0.0.1:8000/app`** (default bootstrap base URL).
- Log in at **`/app/login`** with passphrase **`demodemo`** (wallet auto-selected when only the demo wallet exists).
- After login, the **whole UI under `/app`** is available — use product pages to find bugs, reproduce issues, or experiment with seeded data.
- Prefer **`/app/debug`** when you need to **drive the node** (submit **user actions**, inspect automations, accounts, and user-action history). Same state as **`GET /api/v1/debug/`** when authenticated.

If you used **`--full`**, the node is already starting — do not launch a second `start.py`.

Manual start when you did not use `--full`:

```bash
bash .cursor/seed-agent.sh start
```

Set on your start configuration: `--user-folder` → `user/agent-seed`, **`SCHEDULER_SQLITE_FILE`** → full path to `tasks.db`, **`EXIT_BEFORE_TENTACLES_AUTO_REINSTALL=true`**.

## Headless / debug API

Bootstrap and agents may call the debug API with HTTP Basic (`wallet_address:passphrase`), same as [`operations/bootstrap_http.py`](operations/bootstrap_http.py):

- `GET /api/v1/debug/` — poll state (automations, `user_actions`, accounts, …)
- `POST /api/v1/debug/` — enqueue a user action (204 = accepted, not completed)

Bootstrap fails fast with `RuntimeError` if the tracked create-automation user action reaches **failed** (includes `error_message` / `error_details`).

Debug routes return **404** when node-side encryption is enabled; agent-seed demo expects encryption **off**.

## Seeded identifiers (verification)

From `octobot_node.agent_seed.constants`:

| Kind | Value |
|------|--------|
| Grid automation name | `Agent seed BTC/USDC grid` |
| Grid automation id | `a0000000-0000-4000-8000-000000000001` |
| Account display names | **Seed kraken A** (grid), **Seed kraken B** (index idle) |

## Demo wallet restrictions

The demo wallet is sandboxed in `octobot_node/agent_seed/demo_wallet.py`: it **cannot create live exchange accounts or live automations** (`DEMO_AGENT_SEED_FORBIDDEN_ACTION_DETAIL`). Automations must use **simulated** accounts only. Forbidden actions submitted via **`POST /api/v1/debug/`** return **403** with that detail message.

## What gets seeded

- `config.json` pointing at master reference tentacles + profiles (readonly)
- Kraken **simulated** exchange config and accounts **Seed kraken A** (1000 USDC, grid) and **Seed kraken B** (500 USDC, index idle)
- Grid strategy on **BTC/USDC** (3 buy / 3 sell, spread 2000, increment 500)
- Index strategy on **BTC / ETH / SOL** (10% rebalance trigger)
- Bootstrap (optional/`--full`) starts the grid automation via `POST /api/v1/debug/`; CLI exits with error if debug shows that create user action **failed**.

## Troubleshooting

| Symptom | Likely fix |
|---------|------------|
| Clear/seed fails on sqlite | Stop OctoBot first (`Agent seed clear failed: stop the OctoBot node first — tasks.db is locked`) |
| Bootstrap timeout or HTTP errors | Node not listening; run `start` then `bootstrap` |
| Bootstrap `RuntimeError` with user action failed | Read automation error in message; fix node/fixtures, re-seed if needed |
| Debug UI/API 404 | Node-side encryption enabled — not supported for debug QA |
| `--full` bootstrap flaky | Node still booting; retry `bootstrap` |
