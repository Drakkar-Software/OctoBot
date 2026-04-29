---
title: "TradingView"
description: "Learn how to make OctoBot trade based on TradingView alerts. Send signals from TradingView webhooks and have your OctoBot trade on your exchange."
sidebar_position: 4
---



# Automating trading from TradingView

<div style="text-align: center">

![tradingview trading automation illustrated by tradingview logo](/images/guides/interfaces/tradingview-automation-illustrated-by-tradingview-logo.png)

</div>

With OctoBot, you can listen to <a href="https://www.tradingview.com/?aff_id=27595" rel="nofollow">TradingView</a> alerts
and automate trades based on your TradingView indicators or strategies.

This way, when a TradingView alert is fired, you can instantly create orders on the exchange of your choice.  
This works with any kind of alert, whether it is from:

- A price threshold you defined yourself
- A threshold value from an indicator
- A trading strategy you are using on TradingView

:::info
  The following guides cover using TradingView with [OctoBot trading
  bots](https://www.octobot.cloud/trading-bot). Please use the [TradingView automated trading investor
  guide](/en/investing/tradingview-automated-trading) if you are automating
  TradingView strategies using a [TradingView
  OctoBot](/en/investing/tradingview-trading-tutorial) from
  [www.octobot.cloud](https://www.octobot.cloud/).
:::

Learn more on TradingView trading in OctoBot on the [TradingView Trading Mode guide](/guides/octobot-trading-modes/tradingview-trading-mode)

## Indicator based alerts

You can make your OctoBot trade based on TradingView indicators or price events. Follow the [indicator alert guide](tradingview/automating-trading-from-an-indicator) to learn more.

## Strategy based alerts

You can also make your OctoBot trade based on TradingView Pine Script strategies. Follow the [strategy alert guide](tradingview/automating-trading-from-a-pine-script-strategy) to synchronize your OctoBot with your TradingView strategies.

## OctoBot configuration

Simply add the `Trading-view` interface to your OctoBot's "Accounts" configuration and configure the [webhook service](tradingview/using-a-webhook).

## TradingView account

First, create a <a href="https://www.tradingview.com/?aff_id=27595" rel="nofollow">TradingView</a> account if you don't already have one.  
Then, to be able to automate your TradingView strategy, you will either need to use [webhooks](tradingview/using-a-webhook), which requires a TradingView pro account. If you don't have one, you can use the 30 days free trial.

<div style="text-align: center">

<a href="https://www.tradingview.com/?aff_id=27595" rel="nofollow">![tradingview go pro trial button](https://raw.githubusercontent.com/Drakkar-Software/OctoBot/assets/wiki_resources/tradingview-go-pro-trial-button.png)</a>

</div>

<div style="text-align: center">

![tradingview start trial button](https://raw.githubusercontent.com/Drakkar-Software/OctoBot/assets/wiki_resources/tradingview-start-trial-button.png)

</div>

Your account is now ready to be used with OctoBot!

## Alert format

You can send commands to your OctoBot using TradingView alerts including creating market or limit orders, take profits, canceling orders and much more.

Check out the [alert format guide](tradingview/alert-format) to learn more.
