# Agents: binary

## Role

Builds the single-file PyInstaller executables of OctoBot (Linux, Windows, macOS) that CI publishes as workflow artifacts and release assets. Holds the build scripts and the helpers that list modules and fetch data for PyInstaller. It does not contain application logic.

## Owns

- `packages/binary/build_scripts/` (per-platform build entry points)
- `packages/binary/scripts/` (`python_file_lister.py`, `fetch_nltk_data.py`)
- `packages/binary/requirements.txt`
- `packages/binary/README.md`
- `packages/binary/BINARY_TESTING_INSTRUCTIONS.md`

## Public surface

- CI calls `build_scripts/unix.sh` and `build_scripts/windows.ps1`, which use `bin/start.spec` at the repo root.
- Output artifacts: `OctoBot_linux_x64`, `OctoBot_windows_x64.exe`, `OctoBot_macos_arm64`.

## May depend on

- The repo-root `bin/` PyInstaller spec and hooks, and the packages the binary bundles (`octobot`, `packages/*`)

## Do not

- Put application logic here, it belongs in `octobot/` or `packages/*`
- Commit built binaries, `user/`, `logs/` or `tentacles/` data
- Bypass tentacles signature verification (`ALLOW_UNSIGNED_TENTACLES`) when testing a binary

## Tests

- Quick check of a built binary: `packages/binary/scripts/smoke_test.sh <binary>` (curl only, exit code 0 or 1).
- Full testing of a built binary (download from CI, `TENTACLES_URL_TAG` rules, run, UI and API checks): follow [BINARY_TESTING_INSTRUCTIONS.md](BINARY_TESTING_INSTRUCTIONS.md). Builds from branch `bin_factory` need `TENTACLES_URL_TAG=latest`, other builds do not.
- The instructions also cover seeded QA against the binary (`tools/agent_seed`, skill **agent-seed**), debug API user actions, the scheduler DB, the node journal, the REST spec and restart recovery. Use `pkill -INT -x OctoBot_x64` to stop it, never `pkill -f`.
- No pytest suite under this package.

## Related human doc

- [README.md](README.md)

## Last reviewed

- 2026-09-29
