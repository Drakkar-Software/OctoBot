---
title: "Trader depuis un indicateur"
description: "Apprenez comment faire en sorte qu'OctoBot trade en fonction des indicateurs TradingView. Envoyez des signaux depuis les indicateurs TradingView Pine Script et faites en sorte qu'OctoBot effectue instantanément des transactions sur votre plateforme d'échange."
sidebar_position: 1
---



# Automatiser le trading d'un indicateur TradingView

:::info
  La traduction française de cette page est en cours.
:::

With OctoBot, you can listen to <a href="https://www.tradingview.com/?aff_id=27595" rel="nofollow">TradingView</a> indicator signals
to automate your trades.

## Créer une alerte d'indicateur

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

## Format de l'alerte

Learn more about how to create your TradingView alerts on [the TradingView alert format guide](/guides/octobot-interfaces/tradingview/alert-format).

## Configuration de TradingView

Wondering how to make your OctoBot listen to TradingView signals? Checkout [our TradingView integration guide](/guides/octobot-interfaces/tradingview).
