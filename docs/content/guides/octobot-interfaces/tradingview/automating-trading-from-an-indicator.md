---
title: "Trading from indicators"
description: "Learn how to make OctoBot trade based on TradingView indicators. Send signals from TradingView Pine Script indicator and have your OctoBot instantly trade on your exchange."
sidebar_position: 1
---



# Automating trading from a TradingView indicator

With OctoBot, you can listen to <a href="https://www.tradingview.com/?aff_id=27595" rel="nofollow">TradingView</a> indicator signals
to automate your trades.

## Create an indicator alert

- Go to the right menu and click on the alert button

  ![alert-menu-button](https://raw.githubusercontent.com/Drakkar-Software/OctoBot/assets/wiki_resources/tradingview-alert-menu.png)

- Create a new alert with ![create-alert-button](https://raw.githubusercontent.com/Drakkar-Software/OctoBot/assets/wiki_resources/tradingview-add-alert-button.png)
- Choose the condition : an indicator cross, a price drop, whatever
  you want
- Add your OctoBot [webhook](using-a-webhook) as the following screenshot.

  ![set-webhook-url](https://raw.githubusercontent.com/Drakkar-Software/OctoBot/assets/wiki_resources/tradingview-alert-webhook-url.png)

  You will find OctoBot's alert webhook URL on your OctoBot's configuration
  page or in OctoBot's starting logs. It should be an url like `https://webhook.octobot.cloud/tradingview/xxxx` or `http://XXXXXXXX.ngrok.io/webhook/trading_view`.

  WARNING: To improve performances, webhooks are started only when
  required, this means that **you need to activate a webhook related
  tentacle to get the webhook url** (a tentacle such as the **trading
  view signals trading mode**)

  ![octobot open source configured tradingview alert and webhook config](/images/guides/trading-view/octobot-open-source-configured-tradingview-alert-and-webhook-config.png)

  ![webhook log](https://raw.githubusercontent.com/Drakkar-Software/OctoBot/assets/wiki_resources/webhook_log.jpg)

- Set the alert message

## Alert format

Learn more about how to create your TradingView alerts on [the TradingView alert format guide](alert-format).

## TradingView setup

Wondering how to make your OctoBot listen to TradingView signals? Check out [our TradingView integration guide](/guides/octobot-interfaces/tradingview).
