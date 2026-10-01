# Pytest (OctoBot agents)

> **Test failing?** Jump to [When tests fail](#when-tests-fail). **Step 1:** re-run the failing test with [visible logs](#1-re-run-with-visible-logs)—then follow the rest of the protocol; do not patch symptoms first.

## CI run matrix

Run from **OctoBot repo root** after `source .cursor/env.sh`. `DISABLE_SENTRY=True` matches CI.

| Package | cwd | PYTHONPATH / notes | Example |
|---------|-----|-------------------|---------|
| `octobot` | repo root | default venv | `pytest tests -n auto --dist loadfile` |
| `octobot` (tentacles tests) | repo root | installed tentacles | `pytest --ignore=tentacles/Trading/Exchange tentacles -n auto --dist loadfile` |
| `packages/node` | repo root | `PYTHONPATH=.:$PYTHONPATH` | `pytest packages/node/tests -n auto --dist loadfile` |
| `packages/flow` | repo root | `PYTHONPATH=.:$PYTHONPATH` | `pytest packages/flow/tests -n auto --dist loadfile` |
| `packages/copy` | repo root | `PYTHONPATH=.:$PYTHONPATH` | `pytest packages/copy/tests -n auto --dist loadfile` |
| `packages/tentacles_manager` | `packages/tentacles_manager` | — | `pytest tests` (no xdist in CI) |
| `packages/protocol` | `packages/protocol` | — | `pytest test` |
| `packages/agents` | `packages/agents` | — | `pytest tests -n auto --dist loadfile` |
| `packages/async_channel` | `packages/async_channel` | — | `pytest tests -n auto --dist loadfile` |
| `packages/backtesting` | `packages/backtesting` | — | `pytest tests -n auto --dist loadfile` |
| `packages/commons` | `packages/commons` | — | `pytest tests -n auto --dist loadfile` |
| `packages/evaluators` | `packages/evaluators` | — | `pytest tests -n auto --dist loadfile` |
| `packages/services` | `packages/services` | — | `pytest tests -n auto --dist loadfile` |
| `packages/sync` | `packages/sync` | — | `pytest tests -n auto --dist loadfile` |
| `packages/trading` | `packages/trading` | — | `pytest tests -n auto --dist loadfile` |

**Tentacles install** required for: `octobot`, `packages/node`, `packages/flow`, `packages/copy` (CI `USES_TENTACLES`).

**Pylint:** `pylint --rcfile=<pkg>/standard.rc <pkg>/` or root `standard.rc` (see CI `main.yml`).

**tools tests (CI `extended_linter` job):** `PYTHONPATH=.:$PYTHONPATH pytest tools/tests -q`

**extended_linter only (no tentacles):** `PYTHONPATH=. pytest tools/tests/extended_linter -q`

## When tests fail

Use this protocol **before** widening mocks, seeds, timeouts, or expectations—especially for integration, functional, scheduler, or cross-package tests (`packages/node`, `packages/flow`, `packages/sync`, `tentacles/`, and similar).

### 1. Re-run with visible logs

Re-run the **single** failing file, class, or test node with logging enabled **before** changing code or the harness. The first pytest traceback alone is often not enough for integration failures.

- **Cloud:** `source .cursor/env.sh`; `source .cursor/pythonpath.sh` when the matrix requires `PYTHONPATH=.`; use `python -m pytest` if `pytest` is not on `PATH`.
- **Monorepo local:** full `PYTHONPATH` from `.vscode/settings.json`; `OctoBot/venv13/Scripts/python.exe -m pytest` on Windows.
- Append: `-s --log-cli-level INFO --log-cli-format "%(asctime)s.%(msecs)03d - %(levelname)-8s %(name)-24s %(message)s"` (PowerShell: quote the format string).
- **Omit** `-n auto` on debug reruns (single process; worker logs are hard to read).
- Quick green checks may still use `-q` from the matrix; this step is for **investigation**, not full CI sweeps.

```bash
python -m pytest path/to/test_module.py::TestClass::test_name -s --log-cli-level INFO --log-cli-format '%(asctime)s.%(msecs)03d - %(levelname)-8s %(name)-24s %(message)s'
```

Read the log output while you work through steps 2–9. If logs are still empty, check whether the code path uses `logging` vs `print` before adding more flags.

### 2. State the invariant

Write one sentence: what must be true when the test passes (workflow state, sync write, HTTP status, portfolio field, order created, and so on). Everything else is diagnosis.

### 3. Find the failure boundary

Locate the **last layer where the invariant still holds** and the **first layer where it breaks** (zero, empty, wrong type, exception). Fix at the **smallest layer that explains the break**, not necessarily in the test file. If setup looks correct but computed output is zero or empty, suspect **transformation logic** in another package (`packages/trading`, `packages/protocol`, `packages/commons`, tentacles) before blaming seed data in the harness.

### 4. Contradictory evidence

| Observation | Default hypothesis |
|-------------|-------------------|
| Upstream state looks correct; downstream output is zero or empty | Bug in **transformation** between them |
| Two logs disagree about the same entity | Different **code paths** or **representations** |
| Error implies missing resource; resource appears elsewhere | Message may be **generic**; trace **computed inputs** to the failing check |

Do not increase fixtures, balances, or retries until the failure boundary is identified.

### 5. Parallel paths must agree

When one code path correctly handles a domain concept (simulated vs live, user-action type, sync vs debug API, and similar):

1. Identify the **canonical helper or branch** used there.
2. Search for other operations on the same concept that do not use it.
3. Prefer aligning call sites to the canonical path over duplicating logic in tests.

Read colocated **`AGENTS.md`** before edits across package boundaries; the fix may live outside the test’s package.

### 6. Test metadata is not root cause

`xfail`, `skip`, TODO comments, and “known broken” notes describe **process**, not technical proof. When fixing behavior, do not stop at metadata that excuses failure. If you keep `xfail` or `skip`, name **observable failure** (layer + symptom), not a vague narrative.

### 7. Before proposing edits

For integration or functional failures, note briefly:

- **Invariant**
- **Last good layer** (package + what was still true)
- **First bad layer** (package + what broke)
- **Planned fix location** (may differ from the test package)

Only then change production code or the test harness.

### 8. What not to do by default

- Do not widen mocks or inflate seeds to mask zero or empty computed values.
- Do not adjust only timeouts or polling unless the failure boundary is timing, not wrong logic.
- Do not assume the bug lives in the same package as the test file.

### 9. After the fix

Run targeted pytest per the [CI run matrix](#ci-run-matrix) above. Prefer the smallest test that reproduces the failure boundary, then the original failing test.
