---
title: "Suivre des stratégies avec OctoBot cloud"
description: "You can now follow trading strategies of the community"
slug: "following-strategies-in-octobot-cloud"
date: "2022-11"
authors: ["paul"]
tags: ["Cryptocurrency", "Trading", "Strategy", "Exchange", "OctoBot cloud"]
image: "/images/blog/following-strategies-in-octobot-cloud/cover.png"
---



# Suivre les meilleurs stratégies

:::info
  La traduction française de cette page est en cours.
:::

![cover](/images/blog/following-strategies-in-octobot-cloud/cover.png)

On OctoBot cloud, you can subscribe to trading strategies. Subscribing to a strategy allows you to easily trade using a strategy made by someone else from the OctoBot community.

When subscribed to a strategy, you can use the strategy profile directly from your OctoBot. When you do so, your OctoBot will follow the strategy by coping any trade made by this strategy. Order amounts will be adapted to your current portfolio.

## Comment utiliser une stratégie ?

1. Login on [OctoBot cloud](/fr) and go to the desired strategy page
2. Click `Subscribe`
   ![Following-strategies-pre-sub](/images/blog/following-strategies-in-octobot-cloud/pre-sub.png)
3. Now that you are subscribing to the strategy, click `Copy download url`
4. From your OctoBot, login to your OctoBot cloud account
   ![Following-strategies-community](/images/blog/following-strategies-in-octobot-cloud/community.png)
5. Go to the `Profile` tab and click on the name of the current profile, click `Import a profile`
   ![Following-strategies-import](/images/blog/profile-sharing-in-octobot-cloud/bot-import.jpg)
6. Paste the download url (that was copied from step 3) and click `Import`
   ![Following-strategies-imported](/images/blog/following-strategies-in-octobot-cloud/imported.png)
7. Use the imported profile and restart your OctoBot

## Comment ça fonctionne ?

When following a strategy, a user gets access to the trading signals of the strategy. Trading signals are emitted at each order created or cancelled by the followed strategy. This way followers of a strategy benefit from trades of the desired strategy in real time directly from their OctoBot. Strategies can be applied to any exchange as long as the strategy trading pairs are supported. You can follow a strategy with real or simulated trading.

Trading through strategy signals is achieved by using the RemoteTradingSignalsTradingMode configured to follow the strategy you selected. When importing a strategy profile, you are importing an already configured profile that enables this trading mode with the right strategy identifier and the strategy traded pairs and default exchange.

![Following-strategies-mode-config](/images/blog/following-strategies-in-octobot-cloud/mode-config.png)

As following a strategy is only possible through OctoBot cloud, you need to login to your OctoBot cloud account from your OctoBot to be able to follow a strategy.

## Comment publier une stratégie sur OctoBot cloud ?

Trading strategies are published on [OctoBot cloud](/fr) by the OctoBot community.
When a user wants to share a trading strategy, the only thing to do is to:

1. Create a strategy on [OctoBot cloud](/fr)
2. Setup the desired OctoBot trading mode to emit trading signals to this strategy
   ![Following-strategies-config](/images/blog/following-strategies-in-octobot-cloud/config.png)

Note: the identifier of the strategy to emit signal on can be found on the strategy page, by clicking on this button
![Following-strategies-id-button](/images/blog/following-strategies-in-octobot-cloud/id-button.png)

Please note that configuration and content of a published strategy is not uploaded to OctoBot cloud and followers can't access the code or configuration of the strategy. They will only get trading signals when the OctoBot that is actually running the strategy will create or cancel orders.

## Rejoindre la bêta

Following strategies will first be available on the [beta OctoBot cloud](https://beta.octobot.cloud/).
To join the OctoBot beta program, [have a look at our beta program](/guides/octobot-advanced-usage/beta-program)
