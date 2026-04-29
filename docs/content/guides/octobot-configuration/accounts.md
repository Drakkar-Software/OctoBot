---
title: "Accounts"
description: "Learn OctoBot handles your exchange accounts and setup its web and telegram interfaces and notifications."
sidebar_position: 4
---

# Accounts

The accounts configuration page allows global (cross profile) configuration. It contains exchange API keys, interfaces credentials or keys and notification configuration.

## Exchanges

![exchange accounts configuration in octobot](/images/guides/configuration/exchange-accounts-configuration-in-octobot.png)

You can save as many accounts as you want and only trade on those enabled in your profile. 

[Here is the guide helping to setup an exchange for OctoBot](/guides/exchanges)

## Interfaces


![interfaces configuration in octobot](/images/guides/configuration/interfaces-configuration-in-octobot.png)

Interfaces are ways to connect your OctoBot to other services. 

Here are different page explaining interfaces configuration :

-   [Web](/guides/octobot-interfaces/web)
-   [Telegram](/guides/octobot-interfaces/telegram)
-   [Chat GPT](/guides/octobot-interfaces/chatgpt)
-   [TradingView](/guides/octobot-interfaces/tradingview)
-   [Reddit](/guides/octobot-interfaces/reddit)


## Notifications


![notifications configuration in octobot](/images/guides/configuration/notifications-configuration-in-octobot.png)

When notifications are enabled, OctoBot will create notifications on all the given medias. These notifications contain the current evaluations of monitored markets as well as created, filled and cancelled orders.

Different types of notifications are available, it is possible to use any of them, or even all of them.

### Types of notifications

-   **Global-Info**: General notifications like a startup message or a shutdown message.
-   **Price-Alerts**: A price movement is detected and is triggering a new market state.
-   **Trades**: An order is created, filled or cancelled.
-   **Trading-Script-Alerts**: Any notification related to a scripted trading mode.
-   **Other**: Other type of notifications.

Enable notifications types to tell which types of notifications OctoBot should use.

### Telegram notifications

When selected, notifications will be sent to you on Telegram.

Telegram notifications use the Telegram service. [See Telegram configuration guide](/guides/octobot-interfaces/telegram)

### Web notifications

When selected, notifications will be sent to you on the web interface.

Web notifications use the Web service. [See Web interface configuration guide](/guides/octobot-interfaces/web)
