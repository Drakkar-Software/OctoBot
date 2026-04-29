---
title: Tentacles
description: Overview of the tentacles package — OctoBot's plugin system providing all default evaluators, strategies, trading modes, services, and automation components.
sidebar_position: 1
---

# Tentacles Package

The `tentacles` package is OctoBot's default plugin bundle — the concrete implementation layer that sits on top of the abstract framework packages (`octobot_evaluators`, `octobot_trading`, etc.). Every evaluator, trading mode, service, AI agent, automation rule, and exchange connector ships as a tentacle.

## What a tentacle is

A tentacle is a self-contained directory that lives under the `tentacles/` tree and follows a fixed layout: a Python module with your implementation, a `metadata.json` descriptor, and optionally a `config/` subdirectory containing default configuration files (one JSON per class) and a JSON schema for the form renderer.

`metadata.json` is the authoritative descriptor for the unit. It declares the tentacle's `version`, the `origin_package` it belongs to (used by the version gate), the list of `tentacles` (Python class names) it exports, and an optional `tentacles-requirements` list naming sibling tentacle modules that must be present for this one to work correctly.

The top-level `__init__.py` files throughout the tree are **generated** by `tentacles_manager`, not hand-written. Each one is built around a call to `check_tentacle_version()`: if the version declared in `metadata.json` falls below the minimum compatible version for its package, the import is skipped and an error is logged — the rest of the system continues unaffected. This makes the plugin boundary hard-isolated: a bad tentacle cannot crash OctoBot at startup.

## Discovery and loading

At startup, `octobot_tentacles_manager` scans the `tentacles/` directory tree up to three folder levels deep, looking for any directory that contains subdirectories with a `metadata.json` file. That heuristic determines the tentacle type path (e.g. `Evaluator/TA`, `Trading/Mode`) without requiring a registry or any explicit registration call. Each discovered module is parsed into a `Tentacle` model object that tracks the type path, class names, version, origin package, and optional `tentacle_group`.

The result is cached in a module-level dict keyed by class name. Everything downstream — activation checks, configuration resolution, documentation loading, and resource path lookups — goes through that cache via the `loaders` API.

Tentacles can also be registered programmatically via `register_extra_tentacle_data` for cases where a tentacle class cannot be discovered from disk (e.g. dynamically generated or compiled tentacles).

## Configuration: reference vs. profile-specific

Every tentacle class has a **reference config** stored inside its own `config/` directory. That file is the factory default and is never modified at runtime.

When a user (or a profile) customises a tentacle, a **profile-specific copy** is written to the active profile's `specific_config/` folder. At runtime, `get_config()` checks for a profile-specific file first; if none exists it falls back to the reference config. A factory reset simply copies the reference file back over the profile-specific one.

Activation state — which evaluators and trading modes are actually turned on — is stored separately in `tentacles_config.json` at the profile root. This file is also managed by `TentaclesSetupConfiguration`, which knows that evaluator and trading mode sub-types are deactivated by default (users must explicitly enable them in a profile), whereas services and utility tentacles activate automatically on install. When a new tentacle is installed into a `tentacle_group`, the manager can automatically swap the default group member's activation state to avoid running duplicate implementations.

Profiles bundled inside the `tentacles/profiles/` directory ship with their own `tentacles_config.json` and `specific_config/` files, so a profile can override both activation state and parameter values out of the box.

## Relationship to tentacles_manager

The `tentacles` package (this repo) only contains implementations. All lifecycle operations — install, update, uninstall, packaging, init-file generation, version gating, configuration management — live in the separate `octobot_tentacles_manager` package. The two are coupled only through the file layout convention and the generated `__init__.py` contract. This separation means the framework can work with any conforming plugin bundle, not just the default one bundled here.

## Evaluators

Evaluators analyze market data and produce a normalized signal (`eval_note` in `[-1, 1]`). Four types exist: **TA** evaluators trigger on each closed candle and use technical indicators, **RealTime** evaluators react to live market events, **Social** evaluators consume external data feeds (fear & greed, news, etc.), and **Strategy** evaluators aggregate signals from other evaluators into a final trading decision.

LLM-backed strategy evaluators can use either a fast parallel agent pattern or a LangChain supervisor for deeper reasoning. DSL-based evaluators let users define custom evaluation logic as scripts.

## Trading Modes

Trading modes define how OctoBot translates signals into orders. Each mode splits into a producer (decides what and when to trade) and a consumer (executes order operations on the exchange).

The package ships grid/staggered modes, index rebalancing modes, DCA modes, daily signal-based modes, copy-trading modes that replicate remote signals or profiles, and DSL modes where the entire trading logic is a user-written script. AI-powered index modes use agent teams to determine target portfolio allocations instead of fixed weights.

Exchange connectors are mostly CCXT-based, with notable exceptions for prediction markets (Polymarket with on-chain EVM settlement) and perpetual DEXs (Hyperliquid). A generic CCXT connector handles any exchange without a dedicated tentacle.

## AI Agents

Agent teams orchestrate multiple LLM-powered sub-agents for market analysis. A simple team runs sub-agents in parallel and summarizes results for low latency. A deep team uses a LangChain supervisor for higher reasoning depth. For index trading, a structured bull/bear debate pattern with risk assessment and memory-enabled allocation decisions is used.

LLM backends support OpenAI, Anthropic, Ollama, Gemini, Azure, Bedrock, and other providers. Agents declare a speed/quality preference so the system selects the appropriate model tier.

## Services and Automation

Service feeds bridge external data sources to the evaluator system. Interfaces provide a web dashboard, Telegram bot, and a Node API for multi-instance management. Notifiers dispatch messages via Telegram, Twitter/X, and WebSocket.

The automation system is declarative: a trigger event (price, portfolio, P&L, volatility, or time threshold) combined with an optional condition guard and an action (notify, sell all, cancel orders, stop trading, pause strategies). Conditions can be DSL scripts for complex logic. Each trigger supports one-shot and minimum re-trigger frequency settings.

## DSL and Scripting

The DSL layer registers operators with the commons interpreter for technical indicators, exchange data access, order management, blockchain wallets, and automation rules. A higher-level scripting library provides an async API for trading modes — covering order creation, position sizing, order chaining and grouping, chart annotations, and index distribution.

## User Inputs

Every configurable tentacle implements `init_user_inputs`, which registers parameters with the UI framework. This serializes into a JSON schema rendered as a configuration form in the web interface.
