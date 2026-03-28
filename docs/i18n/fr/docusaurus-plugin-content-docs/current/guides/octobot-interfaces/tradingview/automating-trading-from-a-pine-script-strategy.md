---
title: "Trader depuis une stratégie"
description: "Apprenez comment faire en sorte qu'OctoBot trade en fonction des stratégies TradingView Pine Script. Envoyez des signaux depuis des stratégies TradingView Pine Script et faites en sorte qu'OctoBot effectue instantanément des transactions sur votre plateforme d'échange."
sidebar_position: 2
---



# Automatiser vos stratégies Pine Script de TradingView

:::info
  La traduction française de cette page est en cours.
:::

With OctoBot, you can listen to <a href="https://www.tradingview.com/?aff_id=27595" rel="nofollow">TradingView</a> <a href="https://www.tradingview.com/pine-script-docs/en/v5/index.html#" rel="nofollow">Pine Script</a> strategies signals
to automate your trades.

## Créer une alerte de strategie

To send alerts from a strategy, use the <a href="https://www.tradingview.com/pine-script-docs/en/v5/concepts/Alerts.html?highlight=alert_message#order-fill-events" rel="nofollow">`alert_message`</a> parameter from Pine Script strategy functions which can generate order.

1. Define the content of your alert before any `strategy.entry`, `strategy.exit` or `strategy.close` call:
   - example: `messageBuy = "EXCHANGE=binance;SYMBOL=SOLUSDT;VOLUME=100a%;SIGNAL=BUY"`
     > Note: when defining your alert, remember to add `;` between each parameter.
2. In the strategy section, add `alert_message=messageBuy` to your strategy `entry`, `exit` or `close` calls:
   - example: `strategy.entry("Buy", strategy.long, comment="Buy Signal Triggered", alert_message=messageBuy)`
3. When creating a new alert (_right-click on the strategy / add new alert_) make sure that you: - Select the name of your strategy as the condition - Name the alert (the name can be whatever you want) - Replace **ALL** the message content with exactly `{{strategy.order.alert_message}}`
   ![adding a TradingView strategy alert](/images/guides/adding-a-tradingview-strategy-alert.png)

- _Et voilà !_ This alert will automatically notify your OctoBot each time your strategy executes `entry`, `exit` or `close` calls.

Tips:

- For multi-coin, simply edit the strategy and modify the SYMBOL entry in the messageBuy definition. You can thus vary the parameters according to the assets.
- It can be easier to define multiple messages such as `messageBuy`, `messageBuyWithATakeProfit`, `messageSell`or even `messageCancel` and use the appropriate message later on (with the `alert_message` parameter) when calling `entry`, `exit` or `close`.

_Special thanks to @KidCharlemagne for creating the basis of this guide !_

## Format de l'alerte

Learn more about how to create your TradingView alerts on [the TradingView alert format guide](/guides/octobot-interfaces/tradingview/alert-format).

## Configuration de TradingView

Wondering how to make your OctoBot listen to TradingView signals ? Checkout [our TradingView integration guide](/guides/octobot-interfaces/tradingview).
