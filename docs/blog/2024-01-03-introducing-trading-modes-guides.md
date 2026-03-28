---
title: "Introducing trading modes guides"
description: "Discover the multiple ways to trade with with OctoBot using trading modes based on DCA, grid trading, AI and TradingView"
slug: "introducing-trading-modes-guides"
date: "2024-01-03"
authors: ["guillaume"]
tags: ["Trading", "Educational"]
image: "/images/blog/introducing-trading-modes-guides/person-looking-at-his-screens-using-many-trading-strategies.jpg"
---

# Introducing trading modes guides

When trading with OctoBot, you use a trading mode. [Trading modes](/guides/octobot-trading-modes/trading-modes) are responsible for how to create, maintain and cancel orders. 

<!--truncate-->

Trading modes are a key component of any trading strategy and are compatible with each [supported exchange](/guides/exchanges).

<div style={{textAlign: "center"}}>
  <div>
    ![Person looking at his screens using many trading strategies](/images/blog/introducing-trading-modes-guides/person-looking-at-his-screens-using-many-trading-strategies.jpg) *A trader using many trading strategies.*
  </div>
</div>

Based on your feedback, we created [guides for each trading modes](/guides/octobot-trading-modes/trading-modes) to make clear what they are made for and how to use them. We are looking forward to getting your feedback on those guides.

## Breakdown of an OctoBot strategy

An OctoBot strategy is usually split in 2 parts:
1. The trading mode: it decides how to create ordres on exchange, how much to put in each order, when to cancel them
2. The evaluators: they are sending signals to the trading mode so activate it when necessary. We could say they "wake up" the trading mode when something happens

Note: Some trading mode, such as grid-based ones or TradingView automations are not using any evaluator, they are "waken up" automatically either when an order is filled or when receiving a notification fron TradingView.

## Types of trading modes

When using the [OctoBot trading bot](https://www.octobot.cloud/trading-bot), you have access to [many types of trading modes](/guides/octobot-trading-modes/trading-modes#built-in-trading-modes). Here are the main trading modes categories:

- **Statistics-based trading modes**: Entries (and possibly exits) are computed using statistics. It might be from technical evaluators, AI, social medias, price events or many other things.
- **Low-risk grid trading modes**: Buy and sell orders are created deterministically according to the trading mode's configuration. There is no probability in those algorithms.
- **Automated TradingView strategies**: Entries and exits are created based on your TradingView signals. In this trading mode, the core of your strategy lies on TradingView and Octobot acts as an automation to synchronize your strategy with any exchange account.
