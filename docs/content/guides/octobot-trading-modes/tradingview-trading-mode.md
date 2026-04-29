---
title: "TradingView trading mode"
description: "Easily automate your TradingView strategies and indicators trades on exchange using the TradingView Trading Mode."
sidebar_position: 9
---



# TradingView Trading Mode

The TradingView Trading Mode (or TradingViewTradingMode) is designed to automate orders creation on exchanges based on <a href="https://www.tradingview.com/?aff_id=27595" rel="nofollow">TradingView</a> signals.

<div style="text-align: center">

![tradingview automation illustrated by tradingview logo](/images/guides/interfaces/tradingview-automation-illustrated-by-tradingview-logo.png)

</div>

Simply emit alerts from your TradingView indicators or strategies to trade on any exchange. Learn more on how to configure your OctoBot to trade using TradingView and the [alert on syntax](/guides/octobot-interfaces/tradingview/alert-format) on the [Automating trading from TradingView guide](/guides/octobot-interfaces/tradingview).

:::info
  The TradingView Trading Mode guides cover using TradingView with [OctoBot
  trading bots](https://www.octobot.cloud/trading-bot). Please use the [TradingView automated trading
  investor guide](/en/investing/tradingview-automated-trading) if you are
  automating TradingView strategies using a [TradingView
  OctoBot](/en/investing/tradingview-trading-tutorial) from
  [www.octobot.cloud](https://www.octobot.cloud/).
:::

## The TradingView Trading Mode can

- [Automate TradingView indicator signals](/guides/octobot-interfaces/tradingview/automating-trading-from-an-indicator)
- [Automate TradingView Pine Script strategies signals](/guides/octobot-interfaces/tradingview/automating-trading-from-a-pine-script-strategy)
- Create and cancel market, limit and stop orders
- Create simple entry or exit orders
- Create entry orders with a pre-defined take profit
- Create entry orders with a pre-defined stop loss
- Create stop loss orders
- Trade SPOT and Futures markets

## Configuring orders

- Each TradingView signal contains the details of the order to be created.
- `Cancel previous orders` can be enabled to only maintain one order per trading pair.
- Each order amount can be configured using the [order amounts syntax](order-amount-syntax).
- Each order price can be configured using the [order price syntax](order-price-syntax).
