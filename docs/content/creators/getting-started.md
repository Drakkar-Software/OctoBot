---
title: Getting Started
description: Create custom trading strategies for OctoBot. Learn about trading modes, evaluators, backtesting, and the tentacle system.
keywords: [octobot, strategies, trading modes, evaluators, backtesting, tentacles, custom]
sidebar_position: 1
---

# Creators Guide

This section is for traders and strategy creators who want to build, customize, and optimize trading strategies in OctoBot.

## What You Can Create

- **Trading Modes**: Define complete trading strategies (when to buy, sell, and how much)
- **Evaluators**: Build custom market analysis tools (technical, social, AI-based)
- **Strategy combinations**: Mix and match evaluators into unique strategies

## How Strategies Work

OctoBot strategies are built from three layers:

1. **Evaluators** analyze the market and produce signals (-1 to +1 scale)
2. **Strategies** combine evaluator signals into a trading decision
3. **Trading Modes** execute trades based on strategy decisions

## Built-in Trading Modes

OctoBot ships with several ready-to-use trading modes:

| Mode | Description |
|------|-------------|
| Grid Trading | Place orders across a price range |
| DCA | Dollar-cost averaging over time |
| Daily Trading | Signal-based daily decisions |
| Dip Analyser | Buy dips, sell on recovery |
| Index Trading | Track cryptocurrency indices |
| AI Trading | AI-powered trading decisions |

Browse all modes in the [Trading Modes](/creators/trading-modes/) section.

## Built-in Evaluators

| Category | Examples |
|----------|----------|
| Technical Analysis | RSI, MACD, Bollinger Bands, SuperTrend, EMA |
| Social | News sentiment, Fear & Greed Index, social scores |
| Real-Time | Instant fluctuation detection |
| AI | GPT-based evaluation |

Browse all evaluators in the [Evaluators](/creators/evaluators/) section.

## Next Steps

- [Trading Modes reference](/creators/trading-modes/) - Detailed docs for each mode
- [Evaluators reference](/creators/evaluators/) - All available evaluators
- [Backtesting](/creators/backtesting/) - Test strategies against historical data
- [Custom Strategies](/creators/custom-strategies/) - Build your own tentacles
