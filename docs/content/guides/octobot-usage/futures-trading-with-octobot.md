---
title: "Futures trading"
description: "OctoBot can be used to trade Futures using configured strategies TradingView on Binance, Bybit, Kucoin and OKX."
sidebar_position: 2
---

# Futures Trading with OctoBot

OctoBot can be used to configure and automate many Futures trading strategies on multiple exchanges exchanges. 

## Supported Trading Modes
The following [Trading Modes](../octobot-trading-modes/trading-modes) can be used to trade using Futures:
- [DCA Trading Mode](../octobot-trading-modes/dca-trading-mode)
- [Dip Analyser Trading Mode](../octobot-trading-modes/dip-analyser-trading-mode)
- [TradingView Trading Mode](../octobot-trading-modes/tradingview-trading-mode)
- [Daily Trading Mode](../octobot-trading-modes/daily-trading-mode)

## Supported exchanges
The following exchanges can be used to trade Futures on OctoBot
- [Binance](exchanges/binance)
- [Bybit](exchanges/bybit)
- [Kucoin](exchanges/kucoin)

## Leverage configuration

The current Futures trading leverage value to use with a profile can be set from the configuration page of your enabled Trading Mode, which is accessible from your [profile configuration](../octobot-configuration/profile-configuration).
![access octobot trading mode config from profiles](/images/guides/configuration/access-octobot-trading-mode-config-from-profiles.png)

Note: futures trading must be enabled on your profile exchange for the leverage setting to appear in your trading mode configuration. 

## Cross and Isolated margin

For now, only Isolated margin is supported by OctoBot. Cross margin should not be used to trade with OctoBot.
