---
title: "Starting your Market Making Bot"
description: "A step-by-step guide on how to start your OctoBot Market Making Bot on the crypto market and exchange of your choice and improve your liquidity."
sidebar_position: 3
---

# Starting your Market Making Bot

To start a market making bot, you will first need to create an OctoBot Market Making account.

Once [authenticated to your account](https://market-making.octobot.cloud), the first step is to select your exchange.

## 1. Configuring your exchange

From the [Settings](https://market-making.octobot.cloud/settings/) page, select the exchange you wish to improve your liquidity on.

![octobot market making bot select exchange](/images/guides/octobot-market-making-bot-select-exchange.png)

## 2. Entering your exchange API Keys

Next step is to enter the API Key details of the exchange account which is holding your market making funds. This is necessary for OctoBot Market Making to be able to trade on your account.

![octobot market making exchange credentials settings](/images/guides/octobot-market-making-exchange-credentials-settings.png)

Please note that `Reading and Trading` permissions are required to use OctoBot Market Making. Never add other permissions such as transfers or withdrawals.

![octobot market making exchange accounts list](/images/guides/octobot-market-making-exchange-accounts-list.png)

Your valid credentials will be available to your market making bots.

## 3. Configure your bot

### A. Create a new bot

Once your exchange credentials are valid, proceed to the [bots dashboard](https://market-making.octobot.cloud/bots/) and start a new bot.

![octobot market making bots dashboard](/images/guides/octobot-market-making-bots-dashboard.png)

:::info
**You can't start a new bot?** This means that your account is not yet active. [Contact the team](mailto:contact@octobot.cloud) or [book a call](https://cal.com/octobot.cloud/market-making-30min) to get your account ready.
:::

### B. Select your exchange

Select the exchange you wish to run your bot on, select your previously entered credentials and confirm.

![octobot market making starting bot select exchange](/images/guides/octobot-market-making-starting-bot-select-exchange.png)

### C. Select your market

Select the trading pair(s) you wish to improve liquidity on and confirm. You can type in the symbol of your coin to quickly find it.

![octobot market making starting bot select pairs](/images/guides/octobot-market-making-starting-bot-select-pairs.png)

### D. Configure the reference price

Configure the reference price of each pair. The reference price configuration is the way OctoBot Market Making will compute the price it will use as a basis to create its order book from.

![octobot market making starting bot select reference price](/images/guides/octobot-market-making-starting-bot-select-reference-price.png)

There are different ways you can configure a [market making reference price](using-formulas-to-configure-your-market-making-reference-price):

- **Using the same exchange as the exchange you wish to improve liquidity on**: In this mode, the market making strategy will use the local exchange current price to create its order book. This option is a good choice if your target exchange is among the best exchanges to find the right price of your trading pair.
- **Using a different exchange**: In this mode, the strategy will create its order book based on another exchange price. This is useful if another exchange usually has a more up-to-date price than your target exchange. When providing liquidity on an exchange for a trading pair that has equivalents on a more liquid exchange, this mode is the best choice.
- **Using multiple exchanges**: This mode enables you to compute a market making target price based on weighted average prices from multiple exchanges. This is especially useful when no exchange has a significantly better liquidity than others and no obvious choice is available.
- **Using dynamic pricing with a formula**: This enables you to use a formula to compute the price dynamically or force a static price. This is useful if you wish to lock your market price at a pre-configured value or use a formula to compute the price from an average value, or enforce support levels or resistance levels.

More details about the different ways to configure a market making reference price can be found in the [Using formulas to configure your market making reference price](using-formulas-to-configure-your-market-making-reference-price) guide.

![octobot market making starting bot selected reference price from binance near usdc](/images/guides/octobot-market-making-starting-bot-selected-reference-price-as-binance-near-usdc.png)

### E. Configure your strategy

OctoBot Market Making enables you to configure your market making strategy over many different parameters.

![octobot market making starting bot quick configuration with order book preview](/images/guides/octobot-market-making-starting-bot-quick-configuration-with-order-book-preview.png)

Base parameters such as min and max spread, and order counts are the top level parameters and should always be considered by every market making strategy.

:::info
Every time a parameter changes, the order book preview of your configuration will automatically be updated to reflect your changes.
:::

Many other parameters can be configured to fine-tune the many aspects of a market making strategy including orders distribution, market making budgets, stop conditions, and more.

![octobot market making starting bot advanced configuration](/images/guides/octobot-market-making-starting-bot-advanced-configuration.png)

It is recommended to take the time to configure [stop conditions](configuring-and-protecting-your-market-making-funds) in order to protect your funds from market manipulations, high volatility and unexpected situations.

Once satisfied with your configuration, click `Save and continue` to start your bot.

### F. Name your bot

You can now give a name to your bot while it starts.

![octobot market making starting bot and rename launch](/images/guides/octobot-market-making-starting-bot-and-rename.png)

Once started, your bot will be displayed on your [bots dashboard](https://market-making.octobot.cloud/bots/).

![octobot market making bots view with a running bot](/images/guides/octobot-market-making-bots-view-with-a-running-bot.png)

You can now edit its configuration at any time or stop it at will. In case a [stop condition](configuring-and-protecting-your-market-making-funds) is triggered, your bot will automatically stop itself, cancel its open orders and send you a notification detailing why it stopped and which condition was met.
