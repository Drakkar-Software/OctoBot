# extended_linter

PR policy linter for OctoBot (git scope, path denies, diff content rules). Used by cloud agents and **OctoBot-CI** job `extended_linter`.

## Run

```bash
source .cursor/env.sh   # when tentacles reinstall may run
python -m tools.extended_linter --base origin/dev --continue
```

| Flag | Purpose |
|------|---------|
| `--base` | Merge base ref (match PR target: `origin/dev`, `origin/master`, …) |
| `--continue` | Run all layers (default behavior) |
| `--report json` | Machine-readable stdout |
| `--write-report-json PATH` | JSON file in one run (CI) |
| `--skip-tentacles-reinstall` | Skip `.cursor/reinstall-tentacles.sh` hook |

Policy file: [`config/policy.yaml`](config/policy.yaml).

## CI vs local / agents

| Context | Install | Tentacles hook |
|---------|---------|----------------|
| **OctoBot-CI** job `extended_linter` — **tools tests** | Wheel + `dev_requirements.txt` + tentacles (same as matrix `tests` with `USES_TENTACLES`) | N/A (pytest only) |
| **OctoBot-CI** job `extended_linter` — **PR policy** | Already installed from tools tests step | **`--skip-tentacles-reinstall`** (policy is git + YAML only) |
| **Cloud agent / local handoff** | `source .cursor/env.sh` after `cloud-install` | Omit `--skip-tentacles-reinstall` when `packages/tentacles/` may have changed |

Matrix **`tests`** jobs still use wheel + tentacles where required; tool unit tests run in **`extended_linter`**, not `pytest tests`.

## Tests

```bash
# extended_linter only (no tentacles)
PYTHONPATH=. pytest tools/tests/extended_linter -q

# all tools tests (wheel + tentacles; matches CI tools tests step)
PYTHONPATH=.:$PYTHONPATH pytest tools/tests -q
```

## Adding a rule

1. Read [ARCHITECTURE.md](ARCHITECTURE.md) (layers vs hooks).
2. Add a `rule_id` entry to `config/policy.yaml`.
3. If needed, extend `layers/path_policy.py` or `layers/diff_policy.py` (`kind` handler).
4. Add a test under `tools/tests/extended_linter/layers/` (catalog test covers bundled rules).
5. Do **not** duplicate enforceable rules in `.cursor/skills/` — YAML is the contract.

See also [CONTRIBUTING-agent.md](../../CONTRIBUTING-agent.md) at repo root.
