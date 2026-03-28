---
title: "Grid trading mode"
description: "Easily profit from sideway markets by maintaining a grid-like set of buy and sell orders using the Grid Trading Mode."
sidebar_position: 7
---

# Grid Trading Mode

The Grid Trading Mode (or GridTradingMode) is designed to profit from sideway markets by maintaining a grid-like set of buy and sell orders. Make small yet regular profits on each small market change with minimized risks using grid trading.

<div style="text-align: center">

![grid trading illustrated by a man stepping up on green stairs grabbing coins](/images/guides/grid-trading-illustrated-by-a-man-stepping-up-on-green-stairs-grabbing-coins.png)

</div>

The Grid Trading Mode is a simplified version of the [Staggered Orders Trading Mode](staggered-orders-trading-mode).

## The Grid Trading Mode can

- Use a default configuration
- Be configured for each trading pair independently
- Maintain a grid of buy and sell orders using a the configured spread and increment configured in flat values
- Trail up and down to follow the market when the traded pair's price moves beyond the grid
- Use a limited amount of funds
- Use configured amount for each order
- Automatically dispatch newly deposited funds
- Include a delay when creating opposite orders when a buy or a sell is filled
- Initialize the grid based on a custom price
- Trade SPOT markets
- Automatically optimize your portfolio holdings to create the perfect grid using the `Optimize Initial Portfolio` command
- Pause orders mirroring using the `Pause Orders Mirroring` command
