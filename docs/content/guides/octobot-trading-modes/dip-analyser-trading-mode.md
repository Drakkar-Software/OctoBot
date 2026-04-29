---
title: "Dip Analyser trading mode"
description: "Profit from local bottoms and multiple take profits using the Dip Analyser Trading Mode on OctoBot to trade SPOT or futures markets."
sidebar_position: 6
---

# Dip Analyser Trading Mode

The Dip Analyser Trading Mode (or DipAnalyserTradingMode) is designed to buy on local bottoms and sell the bought assets using multiple take profits. It can be compared to an advanced pre-defined evaluator-based [DCA trading mode](dca-trading-mode).

## The Dip Analyser Trading Mode can

- Split take profits into mutliple sell orders to maximize profits
- Use limit or market entry orders
- Use stop losses
- Customize take profit prices based on the local bottom signal strength
- Trade SPOT and Futures markets

## Configuring orders
- The Dip Analyser Trading mode can spit take profits into as many orders as defined in configuration.
- Entry amounts are using both default or configured amounts and the entry signal's Volume multiplier.
- Take profit order prices are linearly spread between the entry price and the entry signal's Price multiplier.
- Entering a Stop loss price multiplier will enable the creation of stop loss orders alongside take profit orders.
- Entry order amounts can be configured using the [order amounts syntax](order-amount-syntax).
