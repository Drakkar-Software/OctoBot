---
title: "Orders price syntax"
description: "Configure your OctoBot orders prices using a percent of the current price, static price or a difference from the current price."
sidebar_position: 11
---


# The order price syntax

Using OctoBot, you can price your orders in different ways using a either a fixed value or a value relative to the current price of an asset.

Order prices can be configured in your trading mode configuration, in profile settings.

## Constant price
A price that always remain constant.

> Use `50000` to set your order price at exactly "50000" USDT when trading BTC/USDT for example.

## Delta amount: d
A value that increases or reduces the current price using a predefined value.

> Use `100d` to set your order price 100 higher that the current price. For example, if the current price is "50000", then the order price would be "50100".

> Use `-400d` to set your order price 400 lower that the current price. For example, if the current price is "50000", then the order price would be "49600".

## Percent amount: %
Percent increase or decrease from the current price.

> Use `10%` to set your order price 10% higher that the current price. For example, if the current price is "50000", then the order price would be "55000".

> Use `-25%` to set your order price 25% lower that the current price. For example, if the current price is "50000", then the order price would be "37500".
