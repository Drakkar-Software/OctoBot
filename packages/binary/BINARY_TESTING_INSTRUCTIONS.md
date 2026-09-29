# Binary testing instructions

How to download a PyInstaller build of OctoBot from CI, run it, and check that it works. Written from a real run of the Linux x64 build on a headless Linux machine (build from branch `bin_factory`, OctoBot `3.0.0-beta3`, Python 3.13).

## 1. Get the binary

Every CI run of the `OctoBot-CI` workflow (`.github/workflows/main.yml`) uploads one artifact per platform:

| Artifact name | Platform |
|---------------|----------|
| `OctoBot_linux_x64` | Linux x86_64 |
| `OctoBot_windows_x64.exe` | Windows x64 |
| `OctoBot_macos_arm64` | macOS Apple silicon |
| `octobot-wheel` | Python wheel (not a binary) |

Find the run under the repository Actions tab. Artifacts are kept for 90 days.

Download with a GitHub token (the artifact URL needs authentication, a browser download also works):

```bash
RUN_ARTIFACT_ID=10993723554   # id from the artifact URL
curl -sS -L -o artifact.zip \
  -H "Authorization: Bearer $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github+json" \
  https://api.github.com/repos/Drakkar-Software/OctoBot/actions/artifacts/$RUN_ARTIFACT_ID/zip
```

The API answers with a redirect to Azure blob storage (`*.blob.core.windows.net`). On a machine with an egress allowlist, that host must be allowed or the download fails with a 403 on the proxy tunnel.

Check the download against the `digest` shown for the artifact in the run page or in the API listing, then unpack:

```bash
sha256sum artifact.zip
unzip artifact.zip          # the Linux zip contains a single file: OctoBot_x64
chmod +x OctoBot_x64
```

The file is a single executable of about 150 MB. Nothing else has to be installed, Python is bundled.

## 2. Choose the tentacles tag

On first start the binary downloads and installs the default tentacles for its own version. Which package it asks for depends on `TENTACLES_URL_TAG`.

- **Build from branch `bin_factory`:** always set `export TENTACLES_URL_TAG=latest` before running. These builds carry an unreleased version (for example `3.0.0-beta3`) that has no tentacles package, so the default request returns 404 and the bot cannot install its default profiles.
- **Any other build (a release, or a branch whose version has published tentacles):** do not set the variable. The default is the binary's own version.

You can check whether a version has tentacles with `curl -I https://tentacles.octobot.online/officials/packages/full/base/<tag>/any_platform.zip` (200 means yes).

The variable is only needed while tentacles are being installed. Once the `tentacles/` folder exists, restarts work without it.

## 3. Run it

Always start from a new empty directory. The binary writes `user/`, `logs/` and `tentacles/` into the current directory and never asks before doing so.

```bash
mkdir octobot-test && cd octobot-test
export TENTACLES_URL_TAG=latest          # bin_factory builds only, see section 2
./path/to/OctoBot_x64 > octobot.log 2>&1 &
```

Expected behavior:

- The binary starts in **node mode** (`Using node OctoBot distribution`). The Node UI (React, `node_web_interface`) is the interface. The classic Flask web interface is disabled (`Web interface disabled`).
- The Node API and UI listen on **port 8000**, on all interfaces. The UI is at `http://127.0.0.1:8000/app`.
- The log also prints `Interface successfully initialized and accessible at: http://127.0.0.1:5001`. Nothing listens on 5001 in node mode. Ignore that line.
- Start-up takes a few seconds once tentacles are installed. The first start is longer because it downloads and installs them (about 12 MB).

Wait for readiness instead of sleeping:

```bash
until curl -sf -o /dev/null http://127.0.0.1:8000/app; do sleep 2; done && echo ready
```

Stop it with `pkill -INT -x OctoBot_x64` (or Ctrl+C in the foreground). It exits in about 2 seconds. The log line `forcing immediate process exit without stop_tasks()` is the normal handling of an interrupt, not a crash.

### When the machine cannot reach the tentacles host directly

The tentacles downloader uses its own HTTP client, which does not read `HTTPS_PROXY`. On a machine where outbound traffic only works through a proxy (for example a cloud sandbox), the first start fails with:

```
Failed to download file at url : https://tentacles.octobot.online/... (status: 403, text: Host not in allowlist ...)
Missing default profiles. OctoBot can't start without a valid default profile configuration.
```

`curl` does use the proxy, so fetch the package yourself and install it from the local file with the binary's own command. Keep the `.signature` file next to the zip, the install refuses unsigned packages:

```bash
BASE=https://tentacles.octobot.online/officials/packages/full/base/latest
curl -sS -o tentacles.zip           $BASE/any_platform.zip
curl -sS -o tentacles.zip.signature $BASE/any_platform.zip.signature
TENTACLES_URL_TAG=latest ./path/to/OctoBot_x64 tentacles --install --all --force --location "$PWD/tentacles.zip"
```

Then start the bot as above. Do not set `ALLOW_UNSIGNED_TENTACLES` to get around a signature error, that turns off the check that protects the install.

## 4. Test it

Run these in order on a fresh directory. Everything below was seen passing on the `bin_factory` Linux x64 build, except where a finding says otherwise.

### 4.0 Automated smoke test (curl only)

`scripts/smoke_test.sh` runs sections 3, 4.1, 4.2, 4.5 and the setup and debug API checks of 4.6 and 4.8 in one go. It needs only bash, curl, grep and sed, so it runs on a plain machine with the binary and nothing else.

```bash
TENTACLES_URL_TAG=latest packages/binary/scripts/smoke_test.sh ./OctoBot_x64      # bin_factory build: keep the variable, other builds: drop it
```

It boots the binary in a temporary empty directory, checks the HTTP surface, creates a throwaway wallet through the setup API, checks the debug API with that wallet, scans the log for `Traceback` and unexpected `ERROR` lines, stops the node gracefully, restarts it without `TENTACLES_URL_TAG` and checks the wallet survived. It exits 0 when everything passes and 1 otherwise (the work dir is then kept and its path printed). Set `SMOKE_TENTACLES_ZIP` to a local signed tentacles package (section 3) when the machine cannot reach the tentacles host, `SMOKE_TIMEOUT` to change the 180 s start-up wait, and pass a second argument to choose the work dir. It stops the node by PID and never by process name pattern.

The manual sections below cover what a script cannot: the UI, the wizard, and the seeded automations.

### 4.1 Boot

- [ ] Process stays up and the log reaches `Uvicorn running on http://0.0.0.0:8000`.
- [ ] `grep -E "ERROR|Traceback" octobot.log` shows nothing except the known message below.
- [ ] The scheduler starts: `Scheduler: initialize_scheduler completed`, and the recurring workflows (`global_view_refresh`, `portfolio_history`, `dbos_cleanup`) log success.
- [ ] Tentacles are installed: `tentacles/` exists with `Agent`, `Automation`, `Backtesting`, `Evaluator`, `Meta`, `Services`, `Trading` and `profiles/`.

Known, harmless log line on machines where the tentacles host is only reachable through a proxy: `Error when checking ssl certificates: fetching .../metadata.yaml returned 403. Considering certificates as valid.` This is a certificate pre-check that is allowed to fail.

### 4.2 HTTP surface

| Request | Expected on a fresh install |
|---------|-----------------------------|
| `GET /` | 307 redirect to `/app` |
| `GET /app` | 200, HTML titled `OctoBot Node` |
| `GET /app/assets/index-*.js` and `.css` (names are in the HTML) | 200 |
| `GET /api/v1/wallets/` | 200, `[]` |
| `GET /api/v1/nodes/config` | 503, `{"detail":{"code":"auth_node_not_configured",...}}` (no wallet yet) |

### 4.3 Node UI

Open `http://127.0.0.1:8000/app` in a browser. On a fresh install:

- [ ] It redirects to `/app/setup/welcome` and shows the "Welcome to OctoBot Node" card with a **Get started** button.
- [ ] `/app/debug` also redirects to setup until a wallet exists. Once a wallet exists, a new browser session must enter the passphrase before using the app or `/app/debug`.
- [ ] **Get started** opens `/app/setup`, "Step 1 / 5, Set up your wallet". Entering a passphrase and confirming it, then **Generate wallet**, moves to "Step 2 / 5, Save your seed phrase" and shows 12 words.
- [ ] `GET /api/v1/wallets/` now returns one wallet.

For a headless check, drive it with Playwright and the Chromium already installed on the machine (`PLAYWRIGHT_BROWSERS_PATH`, do not download a browser). Collect `console` errors and failed requests. In a sandbox with a TLS-intercepting proxy, Google Fonts requests fail with `ERR_CERT_AUTHORITY_INVALID`. That is the only expected failure, everything served by the bot itself must return below 400.

### 4.4 UI copy

Per `.cursor/skills/end-user-ui/SKILL.md`, user-visible text must use entry-level trading vocabulary, stay short, and contain no em dash. Skim each screen you open for these.

### 4.5 Persistence and restart

- [ ] Stop the bot, start it again in the same directory **without** `TENTACLES_URL_TAG`. It boots (tentacles already installed) and `GET /api/v1/wallets/` still returns the wallet created earlier.

### 4.6 Seeded QA (agent-seed)

The demo fixtures from `tools/agent_seed` (see its [README](../../tools/agent_seed/README.md) and skill **agent-seed**) work unchanged against the binary. This is the way to test a logged-in node with accounts, strategies and a running automation, and it is the documented QA path for the Node UI.

Only the seed and bootstrap commands need the source checkout: they are Python code that has to run from the repo root in a Python 3.13 environment that has all the repo requirement files loaded: root `requirements.txt`, `full_requirements.txt` and `extra_requirements.txt`, then every `packages/*/requirements.txt` and every `packages/*/full_requirements.txt`. The `full_requirements.txt` files matter: `jsonschema`, `aiosqlite`, `psutil` and others are only declared there. Add `pytest` and its plugins as well if you want to run `tools/tests`. The binary itself needs nothing besides the tentacles from section 3, so use a scratch environment outside the repo and do not commit anything from it.

Use the directory where the binary already installed its tentacles (call it `$RUN`). Two paths differ from the source-tree flow:

- `OCTOBOT_AGENT_SEED_MASTER_USER_ROOT=$RUN/user` points the seed at the reference tentacles config and profiles the binary created.
- `PYTHONPATH` must list the repo root, every `packages/*` folder except `tentacles` and `binary`, and `$RUN` itself so that `import tentacles` finds the installed tentacles.

```bash
export OCTOBOT_AGENT_SEED_MASTER_USER_ROOT=$RUN/user
python -m tools.agent_seed seed --user-folder $RUN/user/agent-seed     # run from the repo root, prints nothing on success

cd $RUN
export EXIT_BEFORE_TENTACLES_AUTO_REINSTALL=true
export SCHEDULER_SQLITE_FILE=$RUN/user/agent-seed/tasks.db
./path/to/OctoBot_x64 --master --user-folder user/agent-seed &         # same as `seed-agent.sh start`, with the binary

python -m tools.agent_seed bootstrap --base-url http://127.0.0.1:8000  # from the repo root, once the node listens: starts the grid automation
python -m tools.agent_seed bootstrap --scenario index --scenario completed
python -m tools.agent_seed bootstrap --scenario lifecycle              # see the finding in 4.10, fails on this build
```

`bootstrap` takes repeatable `--scenario` options, all idempotent (a scenario already in its target state does nothing):

| Scenario | Result |
|----------|--------|
| `grid` (default) | Grid automation `...0001` on Seed kraken A is `running` |
| `index` | Index automation `...0002` (BTC, ETH, SOL) on Seed kraken B is `running` |
| `completed` | Index automation `...0003` on Seed kraken B is created, then stopped, so it shows as completed |
| `lifecycle` | Stops and restarts the grid automation, then checks it is `running` again with its name |
| `all` | The four above in that order |

There is no seeded "errored" automation on purpose: a failing automation keeps retrying and stays `running`, and it only becomes `failed` after the scheduler exhausts its recovery attempts, so it cannot be produced quickly and reliably from user actions.

Checks, all seen passing on the `bin_factory` Linux x64 build:

- [ ] `GET /api/v1/wallets/` lists the demo wallet `0x70997970c51812dc3a010c7d01b50e0d17dc79c8`, name `demo`.
- [ ] `GET /api/v1/debug/` without credentials returns 401. With HTTP Basic `wallet:demodemo` it returns 200 with accounts **Seed kraken A** (1000 USDC) and **Seed kraken B** (500 USDC), one exchange config, two strategies.
- [ ] `/app` redirects to `/app/login` ("Unlock your node"). The passphrase `demodemo` opens `/app/octobots`. `/app/debug` shows the debug view with the seeded counts and no browser errors.
- [ ] `bootstrap` exits 0. The automation `a0000000-0000-4000-8000-000000000001` is `running`, the create user action is `completed`, and the log shows the simulated trader placing 3 buy and 3 sell BTC/USDC limit orders.
- [ ] `/app/octobots` shows one active OctoBot as Running.
- [ ] After `--scenario index --scenario completed`: automation `...0002` is `running` with the name `Agent seed BTC/ETH/SOL index`, and `...0003` is `completed` with the name `Agent seed stopped index`. `/app/octobots` counts 2 active and 1 completed. Running the same command again changes nothing.

### 4.7 User actions through the debug API

`POST /api/v1/debug/` (HTTP Basic, body is a `UserAction` as JSON) returns 204 when the action is accepted. Poll `GET /api/v1/debug/` until the action in `user_actions` is `completed` or `failed`. Build payloads with `tools.agent_seed.protocol.builders` and send them with `json.loads(user_action.to_json())`.

- [ ] Creating a **live** (not simulated) account returns 403 with `Demo agent-seed wallet cannot create live exchange accounts or automations`. This is the demo wallet guard, not a bug.
- [ ] Creating a **simulated** account returns 204 and completes. The account list grows.
- [ ] `automation_stop` (with `cancel_orders`) returns 204, completes, and the automation status becomes `completed`.
- [ ] `automation_restart` returns 204, completes, and the automation is `running` again.

### 4.8 Node internals (packages/node, node_journal, node_api_interface)

- [ ] **Scheduler:** `user/agent-seed/tasks.db` (SQLite, set by `SCHEDULER_SQLITE_FILE`) has successful `execute_user_action`, `execute_automation`, `global_view_refresh`, `portfolio_history_collection` and `dbos_cleanup` workflows.
- [ ] **Journal (record-only):** `<user folder>/node_journal/events.jsonl` and `onboarding_segment.jsonl` contain the events for what you did (`external_action_received`, `account_create_attempt`, `automation_stopped`, `automation_restarted`, `first_automation_started`, `node_process_startup_succeeded`). Nothing in the app should read them back.
- [ ] **REST spec:** `GET /api/v1/openapi.json` returns 200 (about 100 KB). `/docs` and `/redoc` return 200. `/openapi.json` returns 404, that is expected.
- [ ] **Encryption:** debug routes answer 404 when node-side encryption is on. The seeded demo expects it off.

### 4.9 Restart recovery

- [ ] With the automation running, stop the bot (`pkill -INT -x OctoBot_x64`) and start it again with the same command. The log shows `Recovering 1 workflows from application version octobot_node_v1`, the automation is `running` again with its 6 orders, accounts and strategies are unchanged, and there is no `ERROR` or `Traceback`.

### 4.10 Known findings on this build

These were seen on the `bin_factory` build. They do not block boot or the checks above, and none is caused by the binary packaging itself.

- `bootstrap --scenario lifecycle` fails on this build with `AutomationNameLostError` and exit code 1. That is the finding below, the check is doing its job. It also means `grid` cannot be re-run afterwards on the same node, because the grid check finds its automation by name.
- After `automation_restart`, the automation `metadata.name` is empty, so the Node UI titles the card `OctoBot a00000` instead of `Agent seed BTC/USDC grid`. The name is correct until the restart. The restart executor rebuilds the task from the latest terminal workflow (`user_actions_executor/automation/restart_automation.py`).
- One `ERROR GridTradingModeProducer Error reading fees for BTC/USDC: '>' not supported between instances of 'NoneType' and 'NoneType'` is logged when the grid starts, because Kraken returns no maker or taker fee for the pair. It is caught in the staggered orders tentacle and the grid still places all its orders.
- The log line pointing to `http://127.0.0.1:5001` is misleading in node mode (section 3).

## 5. Clean up

Stop the bot by exact process name. Do not use `pkill -f OctoBot_x64`, it also matches the shell that runs the command and kills it.

```bash
pkill -INT -x OctoBot_x64
cd .. && rm -rf octobot-test
```

The wallet created during testing is a throwaway. Never reuse a test seed phrase or passphrase for real funds.

## 6. What to report

State the artifact (run id, branch, commit, artifact id and sha256), whether `TENTACLES_URL_TAG` was set, the result of each check in section 4, and any `ERROR` or `Traceback` lines other than the known one. Attach the relevant part of `octobot.log` for anything that failed.
