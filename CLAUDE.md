# OctoBot

## Environment

### Installing pants

Pants is not bundled. Install the `scie-pants` launcher once (bootstraps pants 2.30.0 from `pants.toml` on first run):

```bash
curl -fsSL https://github.com/pantsbuild/scie-pants/releases/latest/download/scie-pants-linux-x86_64 \
  -o /usr/local/bin/pants
chmod +x /usr/local/bin/pants
pants --version   # triggers bootstrap; prints 2.30.0 when done
```

If the GitHub releases URL is reachable but the internal pex download is not, point pants at a locally cached pex binary by adding to `pants.toml` temporarily (do not commit):

```toml
[pex-cli]
url_template = "file:///path/to/pex"
```

### Python virtualenv

Resolves are disabled (`enable_resolves = false` in `pants.toml`) — no lockfile is committed. Pants resolves requirements directly from `python_requirement` targets each run.

Create a local virtualenv from the project requirements for IDE / debugging:

```bash
python3.13 -m venv .venv
.venv/bin/pip install -r requirements.txt -r full_requirements.txt
```

Use `.venv/bin/python` as the interpreter for running and debugging.

> **Interpreter constraint**: `pants.toml` pins `interpreter_constraints = ["==3.13.*"]` (wildcard required — `==3.13` matches only 3.13.0 exactly and rejects 3.13.1+).

### PYTHONPATH

```bash
ROOT=$PWD
# Without tentacles (bare start.py, no tentacle features):
export PYTHONPATH="$ROOT:$ROOT/packages/agents:$ROOT/packages/async_channel:$ROOT/packages/backtesting:$ROOT/packages/binary:$ROOT/packages/commons:$ROOT/packages/copy:$ROOT/packages/evaluators:$ROOT/packages/flow:$ROOT/packages/node:$ROOT/packages/protocol:$ROOT/packages/services:$ROOT/packages/sync:$ROOT/packages/tentacles_manager:$ROOT/packages/trading"

# With tentacles (after python start.py tentacles install):
export PYTHONPATH="$ROOT:$ROOT/packages/agents:$ROOT/packages/async_channel:$ROOT/packages/backtesting:$ROOT/packages/binary:$ROOT/packages/commons:$ROOT/packages/copy:$ROOT/packages/evaluators:$ROOT/packages/flow:$ROOT/packages/node:$ROOT/packages/protocol:$ROOT/packages/services:$ROOT/packages/sync:$ROOT/packages/tentacles:$ROOT/packages/tentacles_manager:$ROOT/packages/trading"
```

PYTHONPATH must use absolute paths (`$PWD`-based) — build subprocesses run from tentacle subdirectories and need to resolve all packages.

## Tentacles

- **Source of truth**: `packages/tentacles/` — all tentacle changes go here.
- **Never edit `tentacles/` directly** — it is generated from `packages/tentacles/` via export+install and will be overwritten.
- After any change to `packages/tentacles/`, run the **tentacle-manager** agent to export and install.

## Agents

Custom agents live in `.claude/agents/`. They are **not** dispatchable via `subagent_type` — trigger them with `@agent-<name>` in your prompt (e.g. `@agent-test-runner run node tests`), or use `claude --agent <name>` to make one the session agent.

### tentacle-manager

Manages the OctoBot tentacles lifecycle: export from source, install from zip, and generate CCXT exchange tentacles. Mirrors the VSCode "Install tentacles zip" launch configuration.

Use when: installing tentacles after code changes, generating exchange tentacles from CCXT, or running any `python start.py tentacles` command.

Trigger: `@agent-tentacle-manager` · Definition: `.claude/agents/tentacle-manager.md`

### test-runner

Runs and debugs OctoBot Python tests. Handles root-level tests (`tests/`) and per-package tests (`packages/<name>/tests/`). On failure, reads the test and source code, diagnoses the issue, fixes it, and re-runs.

Use when: running tests, debugging test failures, or verifying changes after code modifications.

Trigger: `@agent-test-runner` · Definition: `.claude/agents/test-runner.md`

## Code Conventions

### Enums
Place enums in `<package_root>/enums.py` (e.g. `octobot/enums.py`, `packages/node/octobot_node/enums.py`). Never define enums inline in module files.

### Constants
Place module-wide constants in `<package_root>/constants.py`. Private module constants (used only within one file) may stay in that file, prefixed with `_`.

### Typed errors
Define a typed error hierarchy rather than raising bare `ValueError`/`KeyError`. Pattern:
```python
# errors.py (sibling to the feature module)
class FeatureError(Exception): pass
class SpecificError(FeatureError): pass
```
Re-export from the package `__init__.py`. Use typed catches everywhere — never inspect `str(err).lower()`, and never catch bare `ValueError`/`KeyError` for domain errors.

### TypedDicts for structured dicts
When a dict has a fixed schema (e.g. wallet info returned to callers), define a `typing.TypedDict`. Place it in the module that owns the data, before the class that produces it.

### Import priority in tentacle files
Prefer the installed `tentacles.Services.Interfaces.*` path first; fall back to bare direct imports (build-time fallback). Pattern:
```python
try:
    from tentacles.Services.Interfaces.node_api_interface.api.deps import X
except ImportError:
    from api.deps import X  # type: ignore[no-redef]
```
All files within a tentacle package should use the same priority order.

### Log levels
- `debug`: verbose diagnostics, expected no-ops.
- `info`: normal operational events (startup, shutdown, config loaded).
- `warning`: unexpected but recoverable (auto-unlock skipped, optional feature unavailable).
- `error`: configuration/state errors that affect functionality (wallet missing, key wrong).
- `exception`: unexpected exceptions — always re-raise after logging unless the function is a top-level "best-effort" path that must not crash the caller.

### Shared filter helpers
Filtering logic used in multiple places belongs in a shared utility module (e.g. `workflows_util.py`), not duplicated inline. Name with a verb: `filter_by_wallet`, not `_filter`.

## Documentation

Documentation lives in `docs/content/` and is built with Docusaurus 3. Package docs go under `docs/content/developers/packages/<pkg-name>/`.

### Tone

Write descriptive prose that explains what things do and why, not how they're implemented line by line. Favor plain-language explanations over technical detail. Reference class or function names when they help anchor the explanation, but don't build the doc around them — the reader should understand the concepts even if names change. The style should be descriptive yet grounded in code, explains design decisions and non-obvious behavior, mentions concrete names only when they clarify the concept.

### What to include

- Architecture and design decisions
- How components interact and why
- Important concepts and patterns
- Code snippets that illustrate non-obvious behavior
- Configuration that users/developers need to know about

### What NOT to include

The code is the source of truth. Don't duplicate anything that can be read from source or will break on the next refactor:

- **API surfaces**: function signatures, parameter lists, return types, class hierarchies, enum/constant values, error classes
- **Project structure**: directory trees, package layouts, dependency lists, requirements, version numbers
- **Categorized lists**: sections that just group and list code elements (helpers, classes, endpoints) without explaining why they exist
- **Implementation details**: build config specifics, hidden imports, lifecycle step-by-step sequences

### File format

Each `.md` file must have Docusaurus frontmatter:

```yaml
---
title: <Title>
description: <One-line description>
sidebar_position: <number>
---
```

The sidebar uses `autogenerated` for `developers/packages`, so new files appear automatically.
