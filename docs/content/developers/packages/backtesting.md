---
title: Backtesting
description: Architecture and key concepts of the octobot_backtesting package — the engine that runs trading strategies against historical or social data.
sidebar_position: 1
---

# Backtesting Package

`octobot_backtesting` provides a time-driven simulation loop that replays historical market or social data through the same channel infrastructure that live trading uses. Because the backtesting engine feeds data through `async_channel` producers the same way a live exchange connector does, trading modes and evaluators require no modifications to run in either context.

## Simulation loop

The loop is driven by `TimeUpdater`, which advances a clock managed by `TimeManager` and pushes each timestamp through a `TimeChannel`. At each tick, the channel manager flushes producers in ascending priority order, fully draining one priority level before moving to the next. This ordering replicates live causal sequencing: raw price data completes before evaluators compute signals, which completes before strategies issue orders. After all producers are flushed, the loop yields to the asyncio event loop before advancing the clock, ensuring any triggered coroutines run at the correct simulated moment.

After the first successful iteration, the loop prunes producers whose channels have no consumers and rebuilds the priority-level map. This removes irrelevant work from every subsequent tick rather than re-checking it each time.

When multiple backtests run in the same process — as happens during optimisation runs — each `Backtesting` instance registers its `TimeChannel` under a namespaced key so their clocks do not interfere.

## Clock and timestamp control

`TimeManager` holds the starting and finishing timestamps, the current position, and a configurable time interval that defaults to 50 seconds. Advancing the clock is normally just adding the interval, but a whitelist mode is available for cases where only specific timestamps matter — sparse social data feeds, for example. When a whitelist is active, `next_timestamp()` skips any timestamp not present in the sorted whitelist deque. The deque pops stale entries as it advances, keeping the scan cheap. A callback can bypass the whitelist for a specific tick when needed.

## Data files

Historical data lives in `.data` files, which are SQLite databases. A `description` table records the file's version, type (exchange or social), exchange name, symbols, time frames, and the time range covered. During collection the database is written to a `.part` path and atomically renamed to `.data` on completion, so importers never encounter a partial file.

The file name encodes the collector class that produced it. When an importer is created from a file name, the package resolves the collector class by name and reads its `IMPORTER` attribute to instantiate the right importer. If no match is found it falls back to the default exchange history importer, which handles renamed files gracefully.

The description schema has evolved across format versions. Version 2.0 separates exchange and social data types and adds `start_timestamp`; older versions are exchange-only and lack that field. Importers detect the version on initialisation and parse accordingly.

## Exchange and social importers

`ExchangeDataImporter` probes each table at startup and records only the non-empty ones, so time-range queries only touch tables that actually contain data. `SocialDataImporter` stores events with a service name, channel, symbol, and a JSON payload; its description encodes a services list rather than an exchange name.

Both importers maintain a chronological read cache keyed by symbol, time frame, and data type. The first query fetches all rows from the requested timestamp onwards and populates the cache; subsequent queries slice the already-loaded list. This forward-only contract means backward seeks return stale results unless the cache is explicitly reset — which is the correct behaviour for sequential replay and efficient for the optimisation case where the same file is replayed many times.

## Collectors

`DataCollector` is the base class for anything that writes a `.data` file. It manages path creation, constructs the database at the `.part` path, holds an HTTP session, and provides a retry-capable request helper and a recursive pagination helper for APIs that return continuation URLs. Exchange and social branches extend it with typed save helpers. The concrete collector implementation for a given context is resolved via tentacle discovery, so tentacle packages can override collection behaviour without touching core code.

## Multi-run sharing and progress

`BacktestData` pre-initialises importers once and shares them across multiple `Backtesting` instances. It also manages pre-warmed candle arrays keyed by exchange, symbol, time frame, and time range. Between sequential runs, resetting the importer cache indexes rewinds the read position without reopening SQLite connections.

Progress is exposed as a 0.0–1.0 float based on remaining versus total iterations. Completion is signalled via an `asyncio.Event` that callers can await; there is no need to poll. A per-priority-level drain timeout of 15 seconds guards against stuck consumers — a timeout is logged but does not abort the run.
