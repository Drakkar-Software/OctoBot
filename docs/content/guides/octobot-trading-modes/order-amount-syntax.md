---
title: "Orders amount syntax"
description: "Configure your OctoBot orders sizes using the many available options. Size your orders based your a percent of your portfolio, a scaling or even a static amount."
sidebar_position: 10
---


# The order amounts syntax

Using OctoBot, you can size your orders based on many different factor such as your portfolio holdings, use amounts that remain constant or that scale up or down according to your portfolio growth.

Order sizes can be configured in your trading mode configuration, in profile settings.

Note: you can also leave the order amount configuration empty and trading modes will use a percent of your portfolio (computed based on your risk level) when no value is configured.


:::info
  In the order amounts syntax, `%X` is always equivalent to `X%`. Therefore, using `%s` or `s%` is strictly identical. This is true for every 2-characters identifier.
:::


## Constant amounts 
Amounts that always remain constant.

### Flat base amount
A static amount to use in each order, in base currency.

> Use `0.1` to trade 0.1 BTC on each BTC/USD order.

### Flat quote amount: q
A static amount to use in each order, in quote currency.

> Use `100q` to trade 100 USD worth of BTC on each BTC/USD order.

## Scaling amounts
Amounts that scale with the total portfolio value. Scaling amounts are useful to reinvest profits.

### Traded symbol assets percent: s%
A percent of combined holdings value associated to the traded symbol assets.

> Use `12s%` to trade 12% of cumulated BTC & USDT holdings value when trading BTC/USDT. 

Note: unlike `t%`, `s%` ignores other traded pairs assets holdings.

### Total traded assets percent: t%
A percent of combined holdings associated to each configured trading pairs assets.

> Use `12t%` to trade 12% of available BTC & ETH & SOL & USDT holdings value when trading BTC/USDT while also trading ETH and SOL in other trading pairs. 

`t%` ignores assets in your holdings that are not associated to any currently traded pairs. 

:::info
  Total traded assets percent is especially useful to maintain scaling order sizes through time regardless of other trading pairs. This ignores other assets that might be in portfolio but are not to be traded.
:::

## Variable amounts
Amounts that change after each buy or sell order. Variable amounts can be useful to buy less and less when available funds are reduced for example.

### Total asset holdings: %
A percent of the total portfolio holdings of the traded asset.

> Use `2%` to trade 2% of the total portfolio holdings of the traded asset. 

Here total portfolio holdings means your holding of the asset to buy or sell with. It would be USDT in BTC/USDT buy orders. 

:::info
  When using total asset holdings, once an order is filled, if the total portfolio holdings of the traded asset is reduced, the same % amount will create smaller subsequent orders. Similarly, it will also create bigger ones if more of this asset becomes available, after a sell for example.
:::

### Available asset holdings: a%
A percent of the available holdings of the traded asset.

> Use `12a%` to trade 12% of the available portfolio holdings of the traded asset. 

Similarly to `%`, here holdings means your holding of the asset to buy or sell with. The difference is that `a%` will only count available funds, which means funds that are not already locked in open orders.

### Position percent: p%
A percent of the given symbol current position.

> Use `20p%` to trade using 20% of the open position total value. 

_Only available when trading futures._
