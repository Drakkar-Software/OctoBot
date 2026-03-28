---
title: Architecture Overview
description: OctoBot system architecture - monorepo layout, package dependencies, data flow, and the tentacle plugin system.
keywords: [octobot, architecture, monorepo, packages, tentacles, design]
sidebar_position: 1
---

# Architecture

OctoBot is a Python monorepo organized into self-contained packages under `packages/`. The build system is [Pants](https://www.pantsbuild.org/).

## High-Level Design

```
┌─────────────────────────────────────┐
│            OctoBot CLI              │
├─────────────────────────────────────┤
│          Web Interface              │
├──────────┬──────────┬───────────────┤
│ Trading  │Evaluators│   Services    │
│  Engine  │Framework │ (Notifications│
│          │          │   Web, API)   │
├──────────┴──────────┴───────────────┤
│         Tentacles (Plugins)         │
│  Trading Modes │ Evaluators │ ...   │
├─────────────────────────────────────┤
│       Async Channel (Events)        │
├─────────────────────────────────────┤
│    Commons │ Tentacles Manager      │
└─────────────────────────────────────┘
```

## Key Design Principles

- **Multi-strategy**: Any change specific to a strategy goes in a tentacle, not the core
- **Multi-exchange**: Exchange-specific code lives in exchange tentacles
- **Plugin-first**: The tentacle system enables extending without modifying core code
- **Package isolation**: Each package has its own tests, deps, and build target

## Build System

OctoBot uses Pants for:
- Dependency inference from imports
- Parallel test execution per package
- Wheel building and distribution
- Docker image building
- Rust crate compilation (via maturin)

## Data Flow

1. **Exchange data** arrives via websocket/REST
2. **Async channels** distribute data to evaluators
3. **Evaluators** produce signals
4. **Strategies** combine signals into decisions
5. **Trading modes** execute orders on exchanges
