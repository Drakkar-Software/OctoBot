---
title: "Utiliser un webhook"
description: "Configurez vos webhooks OctoBot pour investissez à partir de signaux TradingView. Utilisez OctoBot cloud, Ngrok ou votre configuration personnelle."
sidebar_position: 5
---



# Utiliser un webhook avec OctoBot

:::info
  La traduction française de cette page est en cours.
:::

There are many ways to wake your OctoBot up and make it do something,
one of them is using a webhook. With a webhook, you can automatically
send messages to your OctoBot from any website supporting this system.

<a href="https://www.tradingview.com/?aff_id=27595" rel="nofollow">TradingView</a> is one of them.

In order to be able to receive TradingView webhook's message, you need to make your OctoBot reachable from TradingView. For this, there are 3 options:

- Use the [Premium OctoBot Extension](/guides/octobot-configuration/premium-octobot-extension) and simply connect your OctoBot through the OctoBot cloud secure server.
- Use <a href="https://ngrok.com/" rel="nofollow">Ngrok</a> to act as a secure intermediary between the internet and your OctoBot.
- Or setup your own public IP and port configuration

## Configurer le webhook de votre OctoBot

1.  In your OctoBot configuration, from the `Accounts` tab, in `Interfaces`, add the webhook service.
2.  Set up your webhook configuration using one of the following options:

    - Option 1: Using [Premium OctoBot Extension](/guides/octobot-configuration/premium-octobot-extension): just select the `Enable-Octobot-Webhook`
    - Option 2: Using Ngrok :

      1.  Select `Enable-Ngrok`, uncheck `Enable-Octobot-Webhook`
      2.  Create an account on <a href="https://ngrok.com/" rel="nofollow">ngrok</a>
      3.  Copy your Ngrok token from https://dashboard.ngrok.com/get-started/your-authtoken
      4.  Enter your Ngrok token into your OctoBot's webhook service configuration.

    - Option 3: Manual configration: if you are familiar with webhook setups and your OctoBot is exposed to the Internet, you can disable both `Enable-Ngrok` and `Enable-Octobot-Webhook` and configure the listening port and IP for the webhook yourself.  
      _Note: With this manual configuration, when using docker, you also need to add `-p 9000:9000` after `docker run`_.

3.  Activate a tentacle using a webhook service (like the TradingView signals trading mode).
4.  Restart your OctoBot.
5.  The webhook address will be displayed on your OctoBot configuration, on to the TradingView inteface and printed in your logs.

:::info
  **Your Webhook URL is missing?** For your webhook URL to be displayed, a
  TradingView-related profile has to be active. If you don't see the URL in your
  TradingView configuration, select a TradingView profile in your profile
  configuation and restart your OctoBot.
:::

Follow [this guide](/guides/octobot-interfaces/tradingview) to know more on how to send TradingView signals to your OctoBot.

## Examples de configuration

### Option de configuration 1: Utiliser l'extension premium OctoBot

**TradingView** and **Webhook** configuration in the Accounts tab
![octobot open source premium extension webhook configuration](/images/guides/trading-view/octobot-open-source-premium-extension-webhook-configuration.png)

The Webhook URL is also printed in logs
![octobot open source premium extension webhook log](/images/guides/trading-view/octobot-open-source-premium-extension-webhook-log.png)

### Option de configuration 1: Utiliser Ngrok

TradingView and Webhook configuration in the Accounts tab
![octobot open source ngrok webhook configuration](/images/guides/trading-view/octobot-open-source-ngrok-webhook-configuration.png)

The Webhook URL is also printed in logs
![octobot open source ngrok webhook log](/images/guides/trading-view/octobot-open-source-ngrok-webhook-log.png)

Activate a tentacle using a webhook service (like the TradingView signals trading mode)

## À propos de ngrok.com

You can use Ngrok with a free account, the only drawback of having a
free version is that your webhook address will change at every OctoBot
restart, you will have to update it on your message sender <a href="https://www.tradingview.com/?aff_id=27595" rel="nofollow">TradingView</a>.

To avoid having to re-enter your IP each time, you can either:

- Use the [Premium OctoBot Extension](/guides/octobot-configuration/premium-octobot-extension): in this case you only pay once and always have your OctoBot secure webhook ready to receive your TradingView alerts.
- Pay a Ngrok monthly subscription
