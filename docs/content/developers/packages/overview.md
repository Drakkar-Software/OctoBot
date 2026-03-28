---
title: Packages Overview
description: Overview of OctoBot's monorepo package architecture. Each package encapsulates a specific domain of the trading bot.
keywords: [octobot, packages, architecture, monorepo, trading, evaluators, commons]
slug: /developers/packages/overview
sidebar_position: 1
---

# Packages

OctoBot is organized into self-contained packages under `packages/`. Each package encapsulates a specific domain and can contain Python code, Rust code, or both.

## Core Packages

### Trading
The trading engine handling orders, portfolio management, exchange interactions, and position tracking.

### Commons
Shared utilities, data structures, constants, and helper functions used across all packages.

### Evaluators
Framework for technical analysis, social signal evaluation, and strategy composition.

### Async Channel
Multi-task asynchronous communication library enabling real-time data flow between components.

## Infrastructure Packages

### Tentacles Manager
Manages the tentacle plugin lifecycle: discovery, installation, updates, and dependency resolution.

### Backtesting
Strategy backtesting engine for testing trading strategies against historical data.

### Services
External service integrations (notifications, web interface, APIs).

### Trading Backend
Low-level trading backend with optional Rust acceleration via PyO3.

## Utility Packages

### Flow
Data flow orchestration between evaluators, trading modes, and services.

### Node
Node management for distributed OctoBot deployments.

### Agents
Agent functionality for automated bot management.

### Sync
Synchronization utilities for multi-instance coordination.

## Package Structure

Each package follows a consistent structure:

```
packages/<name>/
  <name>/              # Python source code
    __init__.py
    ...
  tests/               # Package tests
  BUILD                # Pants build file
  README.md            # Package documentation
  requirements.txt     # Optional dependencies
```

Packages with Rust components additionally contain a `crates/` directory with PyO3 bridge code.
