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

Stop it with `pkill -INT -f OctoBot_x64` (or Ctrl+C in the foreground). It exits in about 2 seconds. The log line `forcing immediate process exit without stop_tasks()` is the normal handling of an interrupt, not a crash.

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

Run these in order on a fresh directory. Everything below was seen passing on the `bin_factory` Linux x64 build.

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

## 5. Clean up

```bash
pkill -INT -f OctoBot_x64
cd .. && rm -rf octobot-test
```

The wallet created during testing is a throwaway. Never reuse a test seed phrase or passphrase for real funds.

## 6. What to report

State the artifact (run id, branch, commit, artifact id and sha256), whether `TENTACLES_URL_TAG` was set, the result of each check in section 4, and any `ERROR` or `Traceback` lines other than the known one. Attach the relevant part of `octobot.log` for anything that failed.
