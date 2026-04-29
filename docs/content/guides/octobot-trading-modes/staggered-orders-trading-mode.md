---
title: "Staggered Orders trading mode"
description: "Profit from sideway markets by maintaining a grid-like set of buy and sell orders with advanced configuration using the Staggered Orders Trading Mode."
sidebar_position: 8
---

# Staggered Orders Trading Mode

The Staggered Orders Trading Mode (or StaggeredOrdersTradingMode) is designed to profit from sideway markets by maintaining a grid-like set of buy and sell orders. Make small yet regular profits on each small market change with minimized risks grid order.

<div style="text-align: center">

![grid trading illustrated by a man stepping up on green stairs grabbing coins](/images/guides/grid-trading-illustrated-by-a-man-stepping-up-on-green-stairs-grabbing-coins.png)

</div>

The Staggered Orders is a more complex and flexible version of the [Grid Trading Mode](grid-trading-mode). In most situations, the [Grid Trading Mode](grid-trading-mode) is a better choice.

Where the Grid Trading Mode is mainly defined around the number of orders you want to maintain, the Staggered Orders Trading Mode focuses on the price range you want to cover. By configuring upper and lower bounds, spread and increment, the Staggered Orders Trading Mode will determine how many orders are required, use the maximum available funds and maintain the relevant orders on exchange.

## The Staggered Orders Trading Mode can

- Be configured for each trading pair independently
- Specify the way funds are dispatched within buy and sell orders
- Maintain a grid of buy and sell orders using a the configured spread and increment configured in %
- Automatically compute the required number of sell and buy orders according to the configured upper and lower bounds as well a spread and increment
- Maintain a limited amount of orders on exchange (exchanges usually enforce a limit on simultaneous open orders). This limit is set by the `Operational depth` parameter. Other orders will be tagged as "virtual": they will only be created when necessary.
- Include a delay when creating opposite orders when a buy or a sell is filled
- Trade SPOT markets
- Automatically optimize your portfolio holdings to create the perfect staggered orders grid using the `Optimize Initial Portfolio` command
