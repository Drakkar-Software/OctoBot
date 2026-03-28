---
title: Packages Overview
description: Overview of OctoBot's monorepo package architecture. Each package encapsulates a specific domain of the trading bot.
keywords: [octobot, packages, architecture, monorepo, trading, evaluators, commons]
slug: /developers/packages/overview
sidebar_position: 0
---

# Packages

OctoBot is organized into self-contained packages under `packages/`. Each package owns a specific domain and has a clear boundary: it exposes a public API to the rest of the system and manages its own dependencies. Packages with Rust components include a `crates/` directory with PyO3 bridge code alongside the Python source, allowing performance-critical paths to run in Rust while remaining callable from Python.

## Core packages

**Trading** is the center of the system. It owns orders, portfolio management, exchange interactions, and position tracking — everything that touches real money flows through here. **Commons** provides the shared utilities and data structures used across all other packages; it has no dependencies on the rest of the stack. **Evaluators** handles technical analysis, social signal evaluation, and strategy composition, turning market data into normalized signals that trading modes can act on. **Async Channel** is the messaging backbone: a multi-task asynchronous communication layer that enables real-time data flow between components without tight coupling.

## Infrastructure packages

**Tentacles Manager** handles the plugin lifecycle — discovering, installing, updating, and removing tentacle bundles, as well as generating the Python import infrastructure that makes them loadable. **Backtesting** runs strategies against historical data, using the same evaluator and trading mode code as live trading. **Services** integrates external services for notifications, the web interface, and APIs. **Trading Backend** provides low-level trading primitives with optional Rust acceleration via PyO3.

## Supporting packages

**Flow** orchestrates the data flow between evaluators, trading modes, and services, wiring them together at runtime. **Node** manages distributed OctoBot deployments, providing durable task execution for automations across multiple instances. **Agents** is the multi-agent AI orchestration layer, coordinating LLM-powered agents for automated analysis and decision-making. **Sync** handles multi-instance coordination, letting separate OctoBot instances share configurations, signals, and account data through a cryptographically authenticated sync server.
