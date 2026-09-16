# OctoBot Cursor Cloud environment

CI-parity install and validation for [Cursor Cloud Agents](https://cursor.com/docs/cloud-agent/setup).

## Profiles (`OCTOBOT_CLOUD_PROFILE`)

| Profile | Layers |
|---------|--------|
| `package-only` | L1–L3 (no tentacles install) |
| `ci-tentacles` | L1–L5 (**default** in `environment.json`) |
| `ui-node-web` | L1–L6 (includes `node_web_interface` build) |

Install: `bash .cursor/cloud-install.sh` (profile via env var).

## Agent / shell usage

```bash
source .cursor/env.sh
# Python, OctoBot CLI, pytest
```

After editing `packages/tentacles/`: `bash .cursor/reinstall-tentacles.sh` (do not edit repo-root `tentacles/`).

## Validate environment (on demand)

```bash
source .cursor/env.sh
bash .cursor/cloud-validate.sh --profile ci-tentacles --json
```

Not run from install; use after Build changes or when debugging a broken env.

## Debugging failures

| Surface | What to search |
|---------|----------------|
| Cursor Cloud Build log | `OCTOBOT_CLOUD_FAILED` or `==> [L` step markers |
| GitHub `cloud-env-validate` | Same markers; `cloud-validate.json` artifact on failure |
| Success install | `OCTOBOT_CLOUD_INSTALL_OK` |

If a dashboard environment snapshot shadows this repo config, remove the saved snapshot so committed `environment.json` wins.
