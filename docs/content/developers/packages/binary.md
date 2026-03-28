---
title: Binary
description: PyInstaller-based pipeline that compiles OctoBot into self-contained executables for Windows, Linux, and macOS.
sidebar_position: 1
---

# Binary

The `binary` package contains the tooling that packages OctoBot into standalone, single-file executables using [PyInstaller](https://pyinstaller.org/). The resulting binaries run on Windows, Linux, and macOS without requiring Python or any dependencies to be installed on the target machine.

## The core problem

PyInstaller works by statically tracing imports and bundling everything it finds. OctoBot's plugin architecture defeats this: tentacles are discovered at runtime by scanning the filesystem, not by static imports, so PyInstaller cannot see them. The solution is a pre-processing pipeline that runs before PyInstaller and makes the invisible visible.

## Build pipeline

The pipeline has four steps. First, a module discovery script walks all installed site-packages and the local repository to find every `octobot*` module and the `async_channel` library, producing a list of dotted import paths that feeds directly into PyInstaller's `hiddenimports`. This covers the runtime-discovered plugin code.

Second, hidden import patching handles a specific case that the discovery step cannot: the `gevent` async driver for `python-engineio` is loaded via string lookup at runtime and has no static import anywhere in the codebase. The pipeline appends an explicit import statement to the CLI entry point before compilation to force PyInstaller to include it.

Third, NLTK corpus bundling ensures that sentiment analysis works inside the binary. The NLTK `words` corpus cannot be downloaded at runtime inside a packaged executable, so it is downloaded before packaging and bundled as a static asset.

Fourth, PyInstaller is invoked against a custom spec file rather than a plain entry point. The spec gives precise control over data assets, hidden imports, and exclusions. Notably, the `tentacles/`, `logs/`, and `user/` directories are excluded from the bundle — they are runtime-only and must live outside the executable on the user's machine.

After the build completes, CI validates the output by running `OctoBot --version` and renames the artifact to the platform-specific filename.

## Design decisions

The `hiddenimports` list in the spec file is maintained manually rather than generated, because fully automated discovery would include test dependencies and dev tools that should not ship in a production binary. The list reflects libraries that use dynamic import patterns: exchange connectivity libraries, web interface async transports, notification service integrations, blockchain connectivity, and sentiment analysis. The `websockets.legacy.*` sub-modules are listed explicitly because PyInstaller does not recurse into namespace packages automatically.

PyInstaller is pinned to a specific version across all CI runs to ensure reproducible builds. Floating the version would risk silent behavioral changes in how PyInstaller traces imports, which can produce a binary that passes `--version` but silently omits a module that only matters at runtime.
