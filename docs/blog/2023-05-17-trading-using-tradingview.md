---
title: "Trading using TradingView"
description: "Automate your trades using any TradingView indicator"
slug: "trading-using-tradingview"
date: "2023-05-17"
authors: ["paul"]
tags: ["Tradingview", "Pine Script", "Webhook", "Strategy", "OctoBot cloud", "Educational"]
image: "/images/blog/trading-using-tradingview/cover.png"
---



# Trading using TradingView

![cover](/images/blog/trading-using-tradingview/cover.png)

## Trading using your favorite TradingView strategies

You love using TradingView indicators and strategies ? With OctoBot, you can take it to the next level and trade using TradingView strategies and indicators directly the exchange you want.

<!--truncate-->

This means that you can use all the OctoBot features according to your TradingView tools, this includes:

- Trading on your favorite exchange(s) using your TradingView strategy
- Test your TradingView strategy in real time with simulated funds
- Get real time notifications when your TradingView strategy sends a buy or sell signal

## TradingView strategies in your OctoBot

When following a TradingView strategy, your OctoBot will listen for TradingView signals and when signals are received, it will react instantly by creating the associated alert and order(s), which can be simulated or real, on any supported exchange.

<div style={{textAlign: "center"}}>
  ![plan-display](/images/blog/trading-using-tradingview/telegram.png)
</div>

You can send details on the order to create directly from the TradingView signal such as the type of order, the take profit and stop loss prices and much more. View the full details of orders signals on [the TradingView signals guide](/guides/octobot-interfaces/tradingview/#alert-format).

## How to bind your TradingView account to your OctoBot

### Using a Cloud OctoBot

When using [OctoBot cloud](/), all you need to do is to [create TradingView alerts](/guides/octobot-interfaces/tradingview#create-an-alert) on any event, directly from Pine Script or from a custom alert.

Cloud OctoBots' webhook configuration is done automatically and does not require any work.

### Using a self hosted OctoBot

When using a self hosted OctoBot, you will have to configure a way to make your OctoBot reachable from a webhook. This is required for TradingView to send signals to your OctoBot and might require an external paid software.

Please have a look at the [webhook manual configuration](/guides/octobot-interfaces/tradingview/using-a-webhook).

Once your webhook setup, you can [create TradingView alerts](/guides/octobot-interfaces/tradingview#create-an-alert) on any event, directly from Pine Script or from a custom alert.
