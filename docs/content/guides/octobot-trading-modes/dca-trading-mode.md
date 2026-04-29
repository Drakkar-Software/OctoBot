---
title: "DCA trading mode"
description: "Optimize your Dollar cost Averaging strategy (DCA) using the OctoBot DCA Trading Mode. Automate DCA on technical indicators or on a regular basis."
sidebar_position: 2
---


# DCA Trading Mode

The DCA Trading Mode (or DCATradingMode) is designed to buy and sell according to a [Smart Dollar cost averaging strategy](/blog/smart-dca-making-of). 

<div style="text-align: center">

![dca trading illustrated by a man watering a plant growing money](/images/guides/dca-trading-illustrated-by-a-man-watering-a-plant-growing-money.png)

</div>

It allows you to optimize your entry and exit prices according to your configuration.

## The DCA Trading Mode can

- Buy on a regular basis
- Buy when evaluators signal a buy opportunity
- Create multiple buy orders at different prices
- Automatically create one or many take profit orders after each entry
- Automatically create one or many stop loss orders after each entry
- Be used to trade SPOT and Futures markets

## Time based DCA
Using the `Time based` Trigger mode, the DCA Trading Mode will create entry (buy) orders on a regular basis according to your configured `Trigger period`.

## Evaluators based DCA
Using the `Maximum evaluators signals based` Trigger mode, the DCA Trading mode will create entry (buy) orders everytime a new maximum evaluator value is received. A maximum evaluator value is a value of `-1` or `1`. 
Using this trigger mode, you can trigger DCA orders based on technical evaluators signals, signals from telegram, ChatGPT or any indicator you enable. Please note that a `-1` or `1` evaluator value is required, any other value will be ignored.

## Configuring orders
- The DCA Trading mode can create entry (buy) orders as market or limit orders. When using limit orders, the `Limit entry percent difference` allows to set the % price difference to compute the buy order price.
- Secondary entry orders can also be enabled. There can be as many as configured and can have a different price and amount from the initial entry orders.
- Take profit (sell) orders can be enabled to automatically create sell orders when an entry order is filled. 
- Stop loss orders can be enabled to automatically create stop loss orders when an entry order is filled. 
- Similarly to secondary entry orders, exit order (take profit and stop loss) can also be split into multiple exit orders using different prices. When enabled, the entry amount will be evenly distributed between exit orders.
- Each entry and exit order amount can be configured using the [order amounts syntax](order-amount-syntax).
- Entry orders lifecycle: When `Cancel open orders on each entry` is enabled, only one entry (including its secondary orders if any) is allowed for each traded pair. This means that a new entry signal received when existing entry orders are open will first cancel open entry orders before creating orders associated to this new signal. On the order hand, when disabled, multiple entry orders from different signals could exist as the trading mode wont cancel them.
- `Enable initialization entry orders`: This parameter enables or disables the automated creation of entry orders when starting the bot, regardless of trigger conditions.
- The maximum part of your portfolio allocated to a given crypto can be limited using the `Max asset holding` parameter. For example, a "Max asset holding" of 30% means that the DCA Trading mode won't buy more BTC if the % of BTC holdings in your portfolio is higher than 30% of your portfolio total value.
:::info
  For now, when using futures trading, the DCA Trading Mode only supports long positions. It will not create short positions.
:::

## Health check
Enabling Health check on the DCA Trading Mode will ensure that there are no assets within the trading pairs that remain without sell orders.

It is useful to ensure that the DCA strategy remains consistent even when restarting the bot or if your OctoBot has been offline for some time.

For example when trading BTC/USDT and ETH/USDT, if at some point the bot sees that ETH is on the portfolio and is not within a sell order, then it will consider that this ETH should be sold and will sell it for USDT with a market order.

## Example usages of the DCA Trading Mode
Many OctoBot cloud strategies are built using the DCA Trading Mode.

- In our [Smart DCA making of](/blog/smart-dca-making-of), we cover the process of designing some of the OctoBot cloud strategies.

- Trading with [ChatGPT](chatgpt-trading) can also use the DCA trading mode to manage orders
