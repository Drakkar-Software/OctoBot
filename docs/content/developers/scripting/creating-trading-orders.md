---
title: "Creating orders"
description: "Learn how to create market, limit, stop loss and trailing orders with python using OctoBot script."
sidebar_position: 6
---

# Creating trading orders

Orders can be created using the following keywords:
- `market`
- `limit`
- `stop_loss`
- `trailing_market`

## Amount
Each order accept the following optional arguments:
- `amount`: for spot and futures trading
- `target_position`: futures trading only: create the associated order to update to position size to the given value. Uses the same format as the order amount.

To specify the amount per order, use the following syntax:
- `0.1` to trade 0.1 BTC on BTC/USD 
- `2%` to trade 2% of the total portfolio value
- `12%a` to trade 12% of the available holdings

``` python
# create a buy market order using 10% of the total portfolio
await obs.market(ctx, "buy", amount="10%")
```

## Price
Orders set their price using the `offset` argument.

To specify the order price, use the following syntax:
- `10` to set the price 10 USD above the current BTC/USD market price 
- `2%` to set the price 2% USD above the current BTC/USD market price
- `@15555` to set the price at exactly 15555 USD regardless of the current BTC/USD market price

``` python
# create a buy limit order of 0.2 units (BTC when trading BTC/USD) 
# with a price at 1% below the current price
await obs.limit(ctx, "buy", amount="0.2", offset="-1%")
```

Note: market orders do not accept the `offset` argument.

## Automated take profit and stop losses
When creating orders, it is possible to automate the associated 
stop loss and / or take profits. When doing to, the associated take profit/stop loss will have 
the same amount as the initial order.

Their price can be set according to the same rules as the initial order price 
(the `offset` argument) using the following optional argument:
- `stop_loss_offset`: automate a stop loss creation when the initial order is filled and set the stop loss price
- `take_profit_offset`: automate a take profit creation when the initial order is filled and set the take profit price

``` python
# create a buy limit order of 0.2 units (BTC when trading BTC/USD) with: 
# - price at 1% below the current price
# - stop loss at 10% loss
# - take profit at 15% profit
await obs.limit(ctx, "buy", amount="0.2", offset="-1%", stop_loss_offset="-10%", take_profit_offset="15%")
```

> When using both `stop_loss_offset` and `take_profit_offset`, two orders will be created after the initial order fill.
Those two orders will be grouped together, meaning that if one is cancelled or filled, the other will be cancelled.

## Futures trading

### Opening a position
Use regular orders to open a position. When the order is filled, the associated position will be created, updated or closed.

A sell order will open a short position if your balance becomes negative after filling this order.

### Closing a position
Set the position size to 0 to close it. You can do it either by:
- Filling an order with the same amount as the position size and an opposite side
- Or using `target_position=0` as order parameters


### Updating leverage

Use `set_leverage` to update the current leverage value when trading futures.

``` python
await obs.set_leverage(ctx, 5)
```
