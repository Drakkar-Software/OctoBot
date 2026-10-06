# Agent seed demo wallet (local / Cloud QA)

> **Warning — demo-only fixture**
>
> This wallet uses **publicly committed private key material** in `tools/agent_seed/secrets.py`.
> It is for **local development, automated agents, and Cloud manual QA only**.
> **Never fund it on mainnet** and **never use it for real trading**.

Canonical operator guide for `tools.agent_seed`. Short agent procedure: skill **agent-seed** (`.cursor/skills/agent-seed/SKILL.md`). Code layout: [ARCHITECTURE.md](ARCHITECTURE.md).

## When you need this

**Most agent work does not use agent-seed.** `pytest`, linters, and package/backend tests do not require `user/agent-seed` or `seed-agent.sh`. Use [`.cursor/skills/octobot-cloud/reference-pytest.md`](../../.cursor/skills/octobot-cloud/reference-pytest.md) (after `source .cursor/env.sh`; on failure see [When tests fail](../../.cursor/skills/octobot-cloud/reference-pytest.md#when-tests-fail)) and colocated `AGENTS.md` **Tests** sections.

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
| `bootstrap [--scenario …]` | HTTP bootstrap of the seeded automations, grid by default (node must be listening). See **Bootstrap scenarios** |
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

Bootstrap and agents may call the debug API with HTTP Basic (`wallet_address:passphrase`), same as [`operations/bootstrap_http.py`](operations/bootstrap_http.py). This is the headless equivalent of **`/app/debug`** (no separate “orders” or “trades” REST resources).

| Method | Path | Role |
|--------|------|------|
| `GET` | `/api/v1/debug/` | Read wallet-scoped debug snapshot (`DebugState`) |
| `POST` | `/api/v1/debug/` | Enqueue a `UserAction` (accepted asynchronously) |

Optional query on both: **`?wallet_address=<evm>`** — resolve debug state or execute actions for another wallet. **Superusers** may pass any wallet; normal users may only pass their own address (otherwise **403**). Omitted `wallet_address` uses the authenticated wallet.

Wire types live in [`packages/protocol/openapi.json`](../../packages/protocol/openapi.json) (`DebugState`, `Debug`, `AutomationState`, …). **HTTP route list** (everything else under `/api/v1/…`): fetch **`GET /api/v1/openapi.json`** from a running node (`node_api_interface` serves it). **Do not invent** paths such as `/api/v1/orders` or `/api/v1/trades` — they are not part of the Node REST API.

### `GET /api/v1/debug/` response shape

Top level (`DebugState`):

| Field | Meaning |
|-------|---------|
| `version` | Debug state schema version (sync constant) |
| `debug` | Wallet snapshot (`Debug`); may be omitted when empty |

Inside `debug` (`Debug`):

| Field | Meaning |
|-------|---------|
| `automations` | **Required.** Running/historical automation snapshots (`AutomationState`) |
| `user_actions` | **Required.** Journaled user actions (create/stop/signal/…) with status and results |
| `accounts` | Exchange/blockchain accounts for this wallet |
| `exchange_configs` | Exchange connection configs referenced by accounts |
| `account_tradings` | Per-account trading snapshots (`account_id` + `account_trading`) |
| `local_strategies` | Strategy definitions stored for this wallet |

Each **`automations[]`** entry (`AutomationState`) includes workflow fields agents often need: `id`, `status`, `metadata` (name/description), `error` / `error_message`, `actions`, `priority_actions`, `exchanges`, `exchange_account_ids`, `assets`, thin `orders` / `trades` / `positions` summaries, and optional `child_octobot_process`.

Each **`user_actions[]`** entry includes `id`, `status`, `configuration` (flattened `action_type` + payload), and `result` (including automation errors when failed). Bootstrap polls these after `POST` create-automation; see [`operations/bootstrap_grid.py`](operations/bootstrap_grid.py).

### Orders, trades, portfolio

**Thin summaries on automations (counts / IDs only)**

- `debug.automations[].orders` → `OrderSummary`: `{ "id", "symbol" }` only
- `debug.automations[].trades` → `TradeSummary`: `{ "id", "symbol" }` only

Use these to see how many open orders/trades an automation references or to list IDs/symbols. They do **not** include side, price, quantity, or status.

**Full orders and trades**

- Full `Order` objects (side, price, quantity, `filled`, `status`, `created_at`, …) and full `Trade` objects live under:
  - `debug.account_tradings[].account_trading.orders`
  - `debug.account_tradings[].account_trading.trades`
- Each `account_tradings[]` row has `account_id` and nested `account_trading` (also `positions`, `transactions`, `updated_at` when present).

**Join automations to account trading**

1. Read `automation.exchange_account_ids` (often one simulated Kraken account for the seeded grid).
2. Find `account_tradings[]` where `account_id` is in that list (same helper logic as the debug UI: `getTradingSummariesForAutomation` in `node_web_interface` `display-utils.ts`).
3. Optionally filter full orders/trades to the automation’s thin summaries by matching `OrderSummary.id` / `TradeSummary.id` to full records (UI: `resolveOrdersFromSummaries` / `resolveTradesFromSummaries`).

**Portfolio / balances**

- **`accounts[].assets`**: grouped by `trading_type` (`DetailedAssetsForTradingType` → nested `DetailedAsset` with `symbol`, `total`, `available`).
- **`automations[].assets`**: schema allows the same grouped shape; in practice the debug UI treats automation assets as a **flat** `DetailedAsset` list (`symbol`, `total`, `available`). For **deployed grid balances tied to the running automation**, prefer **`automations[].assets`** over raw `accounts[].assets` when both exist.

There is **no** dedicated REST endpoint for orders or trades; stay on `GET /api/v1/debug/` or use account/historical routes listed in OpenAPI if the task needs something else.

### curl → file → jq (keep context small)

Save the snapshot once, then query with `jq` instead of pasting multi‑MB JSON into the agent context:

```bash
BASE="http://127.0.0.1:8000"
WALLET="0x70997970c51812dc3a010c7d01b50e0d17dc79c8"
PASS="demodemo"

curl -sS -u "${WALLET}:${PASS}" \
  -o /tmp/debug.json \
  "${BASE}/api/v1/debug/"

jq '.debug.automations[] | {name: .metadata.name, status, order_count: (.orders | length)}' /tmp/debug.json

jq --arg aid "$(jq -r '.debug.automations[0].exchange_account_ids[0]' /tmp/debug.json)" \
  '.debug.account_tradings[] | select(.account_id == $aid) | .account_trading.orders[] | {id, symbol, side, price, quantity, status}' \
  /tmp/debug.json
```

### `POST /api/v1/debug/`

Body: JSON **`UserAction`** (`id` + `configuration` with `action_type`). Returns **204 No Content** when the action is **accepted** and queued — not when work finishes. Poll `GET /api/v1/debug/` and inspect `user_actions[]` for completion or failure.

[`protocol/builders.py`](protocol/builders.py) includes payloads for grid/index create, stop, and restart; scenario-specific sequences are documented under **Bootstrap scenarios** below.

Bootstrap fails fast with `RuntimeError` if the tracked create-automation user action reaches **failed** (includes `error_message` / `error_details` when present on the automation result).

### HTTP status codes (debug routes)

| Code | When |
|------|------|
| **200** | `GET` succeeded |
| **204** | `POST` user action accepted |
| **400** | Invalid JSON body or user action payload (e.g. missing `configuration`) |
| **401** | Missing/invalid HTTP Basic; wrong passphrase; unknown wallet (`detail.code`: `auth_invalid_passphrase`, `auth_wallet_not_found`, …) |
| **403** | Demo wallet forbids the action (`DEMO_AGENT_SEED_FORBIDDEN_ACTION_DETAIL`); or `wallet_address` query targets another user’s wallet (non-superuser) |
| **404** | Node-side encryption enabled (debug disabled); or `POST` stop/signal/restart when automation not found for caller (and not resolved via superuser owner lookup) |
| **503** | Scheduler not initialized yet (node still starting) |

Agent-seed demo expects node-side encryption **off** so debug routes stay available.

### Node web UI routes (`/app/*`)

Vite `base` is `/app/`. After login, common paths (from TanStack Router):

| Path | Purpose |
|------|---------|
| `/app/login` | Passphrase login |
| `/app/login/recover-seed` | Recover wallet from seed |
| `/app/setup`, `/app/setup/welcome`, `/app/setup/connect`, `/app/setup/first-bot`, `/app/setup/mobile-app` | First-run setup |
| `/app` | Redirects to `/app/octobots` |
| `/app/octobots` | Automations list |
| `/app/octobots/new`, `…/presets`, `…/builder`, `…/defaults` | Create automation |
| `/app/octobots/import`, `/app/octobots/export` | Import/export |
| `/app/settings`, `/app/settings/connect` | Settings |
| `/app/debug` | Debug tables + submit user actions |
| `/app/support` | Support |
| `/app/dsl-keywords` | DSL keyword reference |

## Seeded identifiers (verification)

From `octobot_node.agent_seed.constants`:

| Kind | Value |
|------|--------|
| Grid automation name | `Agent seed BTC/USDC grid` |
| Grid automation id | `a0000000-0000-4000-8000-000000000001` |
| Index automation name / id | `Agent seed BTC/ETH/SOL index` / `a0000000-0000-4000-8000-000000000002` |
| Stopped (completed) index automation name / id | `Agent seed stopped index` / `a0000000-0000-4000-8000-000000000003` |
| Account display names | **Seed kraken A** (grid), **Seed kraken B** (index; idle until `index` or `completed` scenario) |

## Demo wallet restrictions

The demo wallet is sandboxed in `octobot_node/agent_seed/demo_wallet.py`: it **cannot create live exchange accounts or live automations** (`DEMO_AGENT_SEED_FORBIDDEN_ACTION_DETAIL`). Automations must use **simulated** accounts only. Forbidden actions submitted via **`POST /api/v1/debug/`** return **403** with that detail message.

## What gets seeded

- `config.json` pointing at master reference tentacles + profiles (readonly)
- Kraken **simulated** exchange config and accounts **Seed kraken A** (1000 USDC, grid) and **Seed kraken B** (500 USDC, index; idle until `index` or `completed` scenario)
- Grid strategy on **BTC/USDC** (3 buy / 3 sell, spread 2000, increment 500)
- Index strategy on **BTC / ETH / SOL** (10% rebalance trigger)
- Bootstrap (optional/`--full`) starts the grid automation via `POST /api/v1/debug/`; CLI exits with error if debug shows that create user action **failed**. More automations on the same fixtures: see **Bootstrap scenarios**.

## Bootstrap scenarios

`bootstrap` (and `all`) take repeatable `--scenario` options, via `bash .cursor/seed-agent.sh bootstrap --scenario index` or `python -m tools.agent_seed bootstrap --scenario index`. Every scenario is idempotent: one already in its target state does nothing. Automations are created and controlled only through the debug API, with the same user actions the UI sends.

| Scenario | Result | Why it exists |
|----------|--------|---------------|
| `grid` (default) | Grid automation on **Seed kraken A** is RUNNING | The default demo automation |
| `index` | Index automation on **Seed kraken B** is RUNNING | Uses the seeded index strategy and the second account |
| `completed` | Another index automation on **Seed kraken B** is created, then stopped (COMPLETED) | Gives the UI a completed automation to show |
| `lifecycle` | Stops and restarts the grid automation, then checks it is RUNNING with its display name | Regression check for the stop and restart user actions. It raises `AutomationNameLostError` (exit 1) if the name is lost |
| `all` | The four above, in that order | |

There is no seeded errored automation. An automation that fails keeps retrying and stays RUNNING until the scheduler runs out of recovery attempts, which is neither quick nor reliable to trigger from user actions. Cover the errored state with unit tests instead.

Do not re-run `grid` after `lifecycle` on the same node: the grid check finds its automation by display name.

## Against a PyInstaller binary

The same fixtures work with a CI-built binary instead of `start.py`. `seed` and `bootstrap` still run from this repo (Python), only the node process is the binary. Set `OCTOBOT_AGENT_SEED_MASTER_USER_ROOT` to the `user/` folder the binary created when it installed tentacles, put that run folder on `PYTHONPATH` so `tentacles` resolves, then start the binary with `--master --user-folder user/agent-seed` plus the same `SCHEDULER_SQLITE_FILE` and `EXIT_BEFORE_TENTACLES_AUTO_REINSTALL` variables as `seed-agent.sh start`. Full steps and the checks to run: [`packages/binary/BINARY_TESTING_INSTRUCTIONS.md`](../../packages/binary/BINARY_TESTING_INSTRUCTIONS.md) (section **Seeded QA**).

## Troubleshooting

| Symptom | Likely fix |
|---------|------------|
| Clear/seed fails on sqlite | Stop OctoBot first (`Agent seed clear failed: stop the OctoBot node first — tasks.db is locked`) |
| Bootstrap timeout or HTTP errors | Node not listening; run `start` then `bootstrap` |
| Bootstrap `RuntimeError` with user action failed | Read automation error in message; fix node/fixtures, re-seed if needed |
| Debug UI/API 404 | Node-side encryption enabled — not supported for debug QA |
| `--full` bootstrap flaky | Node still booting; retry `bootstrap` |
| `bootstrap --scenario lifecycle` exits 1 with `AutomationNameLostError` | The restarted automation lost its name (restart user action). Real node bug, not a seed problem |
