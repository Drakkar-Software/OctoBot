---
title: Tentacles Manager
description: Lifecycle management for OctoBot tentacle plugins — install, update, uninstall, configure, export, and publish.
sidebar_position: 1
---

# Tentacles Manager

`octobot_tentacles_manager` is responsible for the full lifecycle of OctoBot tentacles — the plugin system that extends OctoBot with trading modes, evaluators, exchange connectors, services, and more. It handles everything from downloading and installing a tentacle bundle to generating the Python import infrastructure that makes tentacles loadable at runtime.

## What the manager does

Installation works by downloading a ZIP archive (from a URL or a local path), extracting it, and copying each tentacle into the bot's `tentacles/` tree while resolving any cross-tentacle requirements declared in `metadata.json`. An update pass skips tentacles whose installed version is already current, making it safe to re-run against the same source. Uninstall removes the relevant directories and regenerates the `__init__.py` import files so the rest of the tree stays consistent.

The generated `__init__.py` files are a first-class output of this package, not a side effect. Each one is built around a call to `check_tentacle_version()` that gates the import on the minimum compatible version for the tentacle's origin package. If a tentacle's declared version is too old, its import is silently skipped rather than raising an exception, which means a single outdated tentacle cannot break startup for the others.

A **repair** operation regenerates missing `__init__.py` files and folder structure without touching tentacle configs. This is the recovery path for a broken installation where the code is intact but the import machinery has gone out of sync.

## Configuration management

The manager reads and writes two distinct kinds of configuration. The first is `tentacles_setup_config.json` at the profile root, which records which tentacles are activated in a given profile. Evaluators and trading modes are deactivated by default and must be explicitly enabled; services and utility tentacles activate automatically on install. The second is per-tentacle JSON config files, each stored inside the tentacle's own `config/` directory as the reference default. When a user customizes a tentacle, a profile-specific copy is written to the profile's `specific_config/` folder and takes precedence over the reference at runtime.

## Discovery and loading

At startup, OctoBot calls the manager to scan the `tentacles/` tree up to three folder levels deep, looking for directories that contain a `metadata.json`. Each discovered module is parsed into a `Tentacle` model that tracks the type path, class names, version, origin package, and optional tentacle group. The result is cached in a module-level dict keyed by class name, and everything downstream — activation checks, configuration resolution, documentation loading, resource path lookups — reads from that cache.

## Export and distribution

The manager can also produce redistributable artifacts. A pack operation copies or zips a set of tentacles from an installed tree into a bundle, with optional Cython compilation for distributing compiled-only packages. The upload path pushes those artifacts to S3 or Nexus artifact repositories.

## CLI

The manager ships with a standalone command-line interface and also exposes a `register_tentacles_manager_arguments()` function that OctoBot uses to attach tentacle sub-commands to its own argument parser. This lets the same install, update, repair, and pack operations be driven from either the manager's own CLI or from within `octobot --install`, depending on context.
