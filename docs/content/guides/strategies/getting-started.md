---
title: Getting Started
description: Create custom trading strategies for OctoBot using profiles, trading modes, and evaluators.
keywords: [octobot, strategies, trading modes, evaluators, profiles, custom]
sidebar_position: 1
---

# Strategy Creator Guide

This section is for creators who want to build, customize, and publish trading strategies in OctoBot.

## What You Can Create

A strategy in OctoBot is a **profile** — a self-contained folder that bundles everything needed to define how the bot trades: which trading mode to use, which evaluators analyze the market, which pairs to trade, on which exchanges, and with what risk settings. Creating a new strategy means creating and configuring a profile.

Beyond profiles, you can also build custom **trading modes** (the logic that decides when and how to trade), custom **evaluators** (market analysis tools — technical, social, or AI-based), and combine existing evaluators into new **strategy compositions** without writing any code.

## How Strategies Work

OctoBot strategies are built from three layers:

1. **Evaluators** analyze the market and produce signals on a -1 to +1 scale
2. **Strategies** combine evaluator signals into a single trading decision
3. **Trading Modes** execute trades based on that decision

The profile ties these layers together by declaring which trading mode is active, which evaluators feed into it, and how they are configured.

## Profiles

A profile lives as a folder under `user/profiles/` and contains three things:

- **`profile.json`** — the profile's identity and trading configuration: which exchanges are enabled, which cryptocurrency pairs to trade, the reference market, risk level, and whether to run in live or simulated mode.
- **`tentacles_config.json`** — which tentacles are active. Only one trading mode can be active per profile. Evaluators are additive — a strategy evaluator aggregates signals from multiple TA, social, or real-time evaluators.
- **`specific_config/`** — per-tentacle JSON configuration files. This is where timeframes live (in the strategy evaluator's config, not in `profile.json`), along with order sizing, stop-loss behavior, DSL scripts, and any other tentacle-specific settings.

### Creating a strategy

Creating a new strategy means assembling a profile:

1. **Pick a trading mode** — grid trading, DCA, daily signal-based, index rebalancing, AI-powered, or a custom scripted mode. Only one is active per profile.
2. **Pick evaluators** — choose which TA indicators (RSI, MACD, Bollinger, etc.), social feeds (Fear & Greed, news), or AI evaluators contribute signals. Enable them in `tentacles_config.json`.
3. **Configure timeframes** — set them in the strategy evaluator's specific config (e.g., `SimpleStrategyEvaluator.json` has a `required_time_frames` field).
4. **Set trading pairs and exchanges** — define which pairs to trade and on which exchanges in `profile.json`. Exchange credentials stay in the global `config.json` and are never included in the profile.
5. **Tune risk and sizing** — adjust the `risk` parameter (0.0–1.0) and trading mode-specific settings like order size, stop-loss percentage, or grid spread.

The easiest way to start is to duplicate an existing profile — OctoBot assigns a fresh ID and clears the read-only flag so you can modify it freely.

### Profile configuration

The `profile.json` file separates metadata from trading config.

**Metadata** includes the profile's unique `id` (used internally to select it — not the folder name), a human-readable `name`, `description`, `complexity` and `risk` ratings, and several behavioral flags:

- **`read_only`** — prevents editing and deletion. Built-in profiles ship with this set to `true`.
- **`hidden`** — hides the profile from the UI. Used for profiles that should only appear under specific conditions.
- **`auto_update`** — when enabled, the profile periodically polls OctoBot Cloud using its `slug` and re-downloads if the published strategy has changed. This is how managed strategy updates are distributed to users. The profile's `specific_config/` and `tentacles_config.json` are refreshed, but the user's exchange credentials and `profile.json` metadata are never overwritten.
- **`imported`** — set automatically when a profile is installed from a zip or the cloud.

**Trading config** defines what and how to trade:

- **`crypto-currencies`** — which pairs are enabled (e.g., `"Bitcoin": {"enabled": true, "pairs": ["BTC/USDT"]}`).
- **`exchanges`** — which exchanges to use and their type (spot, margin, futures). The profile only controls `enabled` and `exchange-type`; credentials live in the global config and are never exported with a profile.
- **`trader` / `trader-simulator`** — toggle between live and simulated trading. The simulator section includes starting portfolio and fee settings.
- **`trading`** — the reference market (e.g., `"USDT"`), risk level, and pause state.

### Sharing and publishing

Profiles are designed to be portable. When exported, disabled exchanges are stripped and credentials are never included, so a profile can be shared safely. Profiles bundled inside the `tentacles/profiles/` directory ship with their own `tentacles_config.json` and `specific_config/`, making them immediately usable out of the box.

