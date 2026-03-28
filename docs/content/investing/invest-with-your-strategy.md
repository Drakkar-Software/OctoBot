---
title: "Start to invest"
description: "Learn how to quickly and easily start your investment on OctoBot cloud."
sidebar_position: 6
---



# Start your investment

![cloud strategy](/images/guides/cloud-strategy2.png)


Once you found the strategy or the crypto basket you want to use with your real funds, you are ready to really profit from OctoBot cloud. 

## Getting started

1. From the strategy or the crypto basket you want to use, hit **Start trading**.
2. Select **Real trading**.
![trading account type choice real or paper trading](/images/guides/trading-account-type-choice-real-or-paper-trading.png)
3. Select or enter your exchange account [API key](what-is-an-exchange-api-key). Check out the [Binance connection guide](connect-your-binance-account-to-octobot), [Kucoin connection guide](connect-your-kucoin-account-to-octobot) or [Coinbase connection guide](connect-your-coinbase-account-to-octobot) if you have any question.
![cloud strategy select exchange](/images/guides/cloud-strategy-select-exchange.png)
  _Note: OctoBot will make sure that you have enough funds on your exchange account to start the chosen strategy_
![cloud strategy start](/images/guides/cloud-strategy-start.png)
4. Start your OctoBot to automate your investments with this strategy or basket.

## What will happen ?

### 1. Portfolio optimization
Your OctoBot might balance your USD-associated coins (such as USDT, USDC etc), as well as coins traded by your strategy, that available in portfolio in order to create optimal conditions to start your strategy or crypto basket.

Example:

Let's imagine a portfolio with 100 USDC and 100 USDT. Starting a strategy that is using USDT will make OctoBot sell your USDC for USDT in order to be able to trade it with the selected strategy.

:::info
This process only uses the USD-associated coins as well as coins traded by your strategy from your portfolio. If you want the strategy to ignore a part of your funds, just move those funds to a coin that is not USD-associated or traded by your strategy.
:::


### 2. Investment execution
Your OctoBot will now automatically apply the selected strategy or basket to your exchange account by creating buy and sell orders on the traded cryptocurrencies.

As with [paper trading OctoBots](paper-trading-a-strategy), you can [follow your trading bot](follow-your-profits) just as usual.

Please note that your funds always stay on your exchange account. OctoBot is just creating trading orders on your account but never accesses to your funds directly.  
In order to add another security layer, it is recommended to use API keys without withdrawal permission. 

:::info
  Pro tip: You can keep testing other investment strategies or baskets risk free using [paper trading](paper-trading-a-strategy), even when running a strategy or a basket with real funds.
:::
