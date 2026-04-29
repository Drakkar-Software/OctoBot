---
title: Commons
description: Shared foundations for all OctoBot packages — enums, constants, configuration, databases, logging, signals, DSL, and more.
sidebar_position: 1
---

# OctoBot Commons

The `octobot_commons` package is the foundational library shared by every other OctoBot package. It owns cross-cutting concerns — configuration, databases, async utilities, a DSL interpreter, and more — so no other package needs to re-implement them.

## Configuration and profiles

Configuration is organized into two layers that are merged at runtime. The global config (`config/config.json`) holds exchange credentials and per-installation settings. The profile (`user/profiles/<profile>/profile.json`) holds everything that defines a trading strategy and can be freely shared or committed to version control, because API credentials are always kept in the global config and never written into a profile. When a profile specifies exchange settings, only the non-secret fields travel with it.

`update_config_fields` applies dot-path updates in-place without reloading from disk, which is how the web UI saves small changes without unnecessary churn. Profile metadata flags carry runtime meaning beyond simple display: `read_only` prevents deletion of non-imported profiles, `hidden` excludes a profile from the main list for internal and template purposes, and `auto_update` makes the bot poll an origin URL on a configurable interval.

## Databases

The database layer is organized in three levels. Adaptors define the async CRUD contract. `DBWriter` and `DBReader` sit above them — the writer stages writes through an in-memory cache or row-buffering for backtesting throughput, while the reader wraps access in a chronological read cache. `MetaDatabase` is the single entry point for the trading engine, grouping all databases for a run under one async context manager.

`RunDatabasesIdentifier` generates all file paths for a run by encoding the trading mode class, campaign, and run type into the path. Run IDs are assigned by scanning for the next available integer, so runs are never overwritten. `RunDatabasesProvider` is a process-global singleton that shares one `MetaDatabase` connection per run, which prevents competing file handles from different packages.

The TinyDB backend auto-wipes corrupted files on known errors rather than failing hard. The SQLite backend uses an async cursor pool to avoid blocking the event loop. `CacheWrapper` stores computed indicator values keyed by timestamp and honors `DO_NOT_CACHE` and `DO_NOT_OVERRIDE_CACHE` sentinels so evaluators can skip storage without special-casing at the call site. A metadata table tracks configuration and version for stale-cache detection. `GlobalSharedMemoryStorage` is a simpler in-process singleton dict for transient cross-component state that does not need to survive a restart.

## DSL interpreter

The DSL interpreter accepts Python-syntax strings, parses them with `ast.parse`, and converts the resulting AST into a tree of `Operator` instances. Literals stay as plain Python values; everything else becomes an operator subclass. The design is built around a two-phase contract: `pre_compute()` walks the tree bottom-up to handle any async work — I/O, cache lookups — before `compute()` runs top-down synchronously. Operators that need async data inherit from `PreComputingCallOperator`, which stores the fetched value during `pre_compute()` and returns it from `compute()`. Calling `compute()` before `pre_compute()` on such an operator raises immediately.

Operator registration is name-keyed: each subclass exposes a static `get_name()` returning the token as it appears in DSL source. The interpreter resolves function calls, binary and unary operators, comparisons, boolean operators, subscripts, and even `raise` statements against this dict. New operators can be injected into an existing interpreter instance via `extend()`, which is how higher-level packages augment a base set without subclassing the interpreter. `Operator.get_parameters()` returns a typed parameter list that drives both runtime validation and user-facing documentation generation via `get_docs()`.

A few behaviors are worth knowing before working with the DSL. Chained comparisons like `a < b < c` are decomposed into pairwise `Compare` operators joined by the registered `And` operator — if `And` is absent, chained comparisons fail at parse time even when individual comparisons would succeed. Expressions that are not valid in `eval` mode are retried in `single` statement mode. `interpreter.prepare(expr)` builds the operator tree once so that subsequent evaluations re-execute pre-compute and compute against the same tree, making repeated evaluation against changing data cheap. `ReCallableOperatorMixin` enables stateful operators by carrying a serialized `last_execution_result` back into the next call, letting operators implement waiting periods or incremental state across evaluations without external storage.
