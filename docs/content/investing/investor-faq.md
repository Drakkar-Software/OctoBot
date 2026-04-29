---
title: "FAQ"
description: "Any question on OctoBot cloud ? Here are the frequently asked questions and their answers."
sidebar_position: 33
---



# OctoBot cloud frequently asked questions (FAQ)

## How can I test strategies or crypto baskets ?

On OctoBot cloud, we try to keep everything as simple as possible and this includes testing strategies or crypto baskets. Additionnaly to public historical performances, **every strategy and crypto basket can be tested risk free using [paper trading](paper-trading-a-strategy)**.

This means that you can run any trading strategy or basket at anytime using virtual funds before [starting to invest on your real exchange account](invest-with-your-strategy). Paper trading allows you to test the strategies you are interested in as much as you want for free free.

[Learn more about paper trading](paper-trading-a-strategy)

## How are strategies profits computed ?

Each strategy on OctoBot cloud is built, run and tested using OctoBot. This means that each strategy past performance is evaluated on a regular basis using historical data and OctoBot's [backtesting](/guides/octobot-usage/backtesting).

At OctoBot we believe in transparency. This means that sometimes strategies can turn unprofitable as profits depends on so many different factors including market conditions. If a strategy is not making profits during a given period, you will see it before using it.

## How to create my strategy ?

OctoBot cloud enables you to trade using your own strategy by [automating TradingView strategies](tradingview-automated-trading).

## Where are your funds when using OctoBot ?

You funds always remain on the exchange, on your own exchange account.

OctoBot is a software allowing you to apply a trading strategy or a crypto basket on your own exchange account. This means that OctoBot is just sending trading orders to your exchange account to buy and sell assets according to your selected strategy or basket. OctoBot never receives or sends funds form its users.

## Depositing and withdrawing funds

The OctoBot platform never holds your funds. When using OctoBot, **your funds always remain on the exchange account you selected for your OctoBot**. Your selected investment strategy will operate by sending buy and sell orders to your exchange account.

As a result, you can deposit and withdraw from your exchange account just as you would normally do if no OctoBot was connected to it. If an OctoBot sees that funds have been added or withdrawn, it will automatically adapt and keep your select investment strategy operating as long as minimal required funds to run this startegy remain available.

Note: If someone pretends that you need to move your funds to any platform to use OctoBot, then this person is lying and trying to steal your money. The OctoBot team will never ask for such a thing.

## How much can you loose ?

This depends on the strategy you selected. In all cases, you can never loose more than your investment.

When using OctoBot, the same rules as on exchanges apply, this means that you can end up loosing funds, for example if the following events happen:

- Selling an asset at a lower price than you bought it
- Trading fees taken by the exchange when executing orders
- Issues with the invested asset or exchange itself (ex: if the asset valuation collapses)

:::info
  You can test any strategy **risk free**, therefore without any chance to loose
  funds using [paper trading](paper-trading-a-strategy).
:::

## Is OctoBot cloud secure ?

Yes, security is among our top priorities. When using OctoBot cloud, the following security measures apply:

- Your exchange API keys are stored on a secure encrypted vault. This means that even in the unlikely event that exchange API keys would leak from OctoBot servers, they would not be readable.
- Your exchange API  keys are configured to only be usable from the IP addresses of OctoBot cloud. This means that in the very unlikely event that your API keys would leak from OctoBot cloud or from you, they would be refused by the exchange.
- OctoBot API keys with withdrawal rights can't be used. OctoBot cloud refuses to store exchange API keys with withdrawal permissions (when technically possible). This means that your funds technically can't be taken out of your exchange account by OctoBot or the company behind it.
- OctoBot relies on automated strategies instead of human actions. This means that each strategy is reliable and predictible. You don't need to trust a human to properly execute the strategy.

## Can I use the same exchange account on 2 OctoBots ?

Yes, you can use the same exchange account on multiple OctoBots. Each OctoBot will operate on the budget you have defined for it, from your exchange account's portfolio.

## Why are there minimal funds to use trading strategies and crypto baskets ?

There are 2 reasons for minimal funds in trading strategies and crypto baskets:

- **Exchange trading rules**: OctoBot ultimately send orders to exchange. Those exchanges have trading rules that are enforcing a minimal size for each order. On Binance, this amount <a href="https://www.binance.com/en/trade-rule" rel="nofollow">is usually $5 or $10</a>. Strategies usually trade with a portion of your portfolio for each order, this means this part need to be large enough to comply with trading rules. This is especially true for Grid-based trading strategies where your funds are split into a large amount of smaller orders.
- **The investor plan**: in order to keep the Investor Plan of OctoBot cloud completely free, we are are partnering up with exchanges to bring them trading volume. This means that we have to require a minimum amount in each portfolio to pay our bills. We try to keep this minimum as low as possible but have to set a threshold.

## How can I connect my exchange account to OctoBot ?

To help you connect your exchange account to OctoBot, we created detailed step by step guides:

- [Binance connection guide](connect-your-binance-account-to-octobot)
- [Kucoin connection guide](connect-your-kucoin-account-to-octobot)
- [Coinbase connection guide](connect-your-coinbase-account-to-octobot)
