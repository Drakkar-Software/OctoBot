---
title: "Alert format"
description: "Find everything you need to know to format your TradingView alerts and automate trades on your OctoBot. Buy or sell with market or limit orders, set take profits and stop losses."
sidebar_position: 3
---



# TradingView alerts format

:::info
  The following guide describes how to format TradingView alerts to trade using the [open source version of OctoBot](../../octobot).
:::

## Creating orders

### Minimal alert content


The alert format is designed to be easily used from TradingView. Minimal alerts contain the exchange name, the alert symbol (BTCUSDT for BTC/USDT and BTC/USDT:USDT) and the side of the order to create.
Example: 

``` bash
EXCHANGE={{exchange}}
SYMBOL={{ticker}}
SIGNAL=BUY
```

![alert-message](https://raw.githubusercontent.com/Drakkar-Software/OctoBot/assets/wiki_resources/tradingview-alert-message.png)

For a buy signal.


``` bash
EXCHANGE={{exchange}}
SYMBOL={{ticker}}
SIGNAL=SELL
```

For a sell signal.

Parameters can be separated using a new line or a `;` character.

### Additional alert parameters

Additional order details can be added to the alert. These are optional:

``` bash
ORDER_TYPE=LIMIT
VOLUME=0.01
PRICE=42000
STOP_PRICE=38000
TAKE_PROFIT_PRICE=55000
REDUCE_ONLY=true
```

- `ORDER_TYPE` is the type of order, it can be `MARKET`, `LIMIT` or `STOP`
- `VOLUME`  is the volume of the order in base asset (BTC for BTC/USDT) it supports the [orders amount syntax](/guides/octobot-trading-modes/order-amount-syntax)
- `PRICE` is the price of the limit order in quote asset (USDT for BTC/USDT). The [orders price syntax](/guides/octobot-trading-modes/order-price-syntax) is supported
- `STOP_PRICE` is the price of the stop order to create. When increasing the position or buying in spot trading, the stop loss will automatically be created once the initial order is filled. When decreasing the position (or selling in spot) using a LIMIT `ORDER_TYPE`, the stop loss will be created instantly. _Required when `ORDER_TYPE=STOP`_. The [orders price syntax](/guides/octobot-trading-modes/order-price-syntax) is supported
- `TAKE_PROFIT_PRICE` is the price of the take profit order to create. When increasing the position or buying in spot trading, the take profit will automatically be created once the initial order is filled. When decreasing the position (or selling in spot) using a LIMIT `ORDER_TYPE`, the take profit will be created instantly. The [orders price syntax](/guides/octobot-trading-modes/order-price-syntax) is supported. Multiple take profit prices can be used from `TAKE_PROFIT_PRICE_1`, `TAKE_PROFIT_PRICE_2`, ... When using multiple take profits, the initial entry amount will be evenly split between take profits unless a `TAKE_PROFIT_VOLUME_RATIO` is set for each take profit.
- `TAKE_PROFIT_VOLUME_RATIO` is the ratio of the entry order volume to include in this take profit. Used when multiple take profits are set. Specify multiple values using `TAKE_PROFIT_VOLUME_RATIO_1`, `TAKE_PROFIT_VOLUME_RATIO_2`, …. When used, a `TAKE_PROFIT_VOLUME_RATIO` is required for each take profit.  
Exemple: `TAKE_PROFIT_PRICE=1234;TAKE_PROFIT_PRICE_1=1456;TAKE_PROFIT_VOLUME_RATIO_1=1;TAKE_PROFIT_VOLUME_RATIO_2=2` will split 33% of entry amount in TP 1 and 67% in TP 2.
- `REDUCE_ONLY` when true, only reduce the current position (avoid accidental short position opening when reducing a long position). **Only used in futures trading**. Default is false.
- `TAG` is an identifier to associate to the order(s) to create. Any value can be used as tag. Tags can later be used to cancel specific orders.
- `LEVERAGE` the updated leverage value to use. **Only used in futures trading**.

### Examples

#### A limit buy order of 0.01 BTC at 30000 USDT with a take profit
``` bash
EXCHANGE=binance
SYMBOL=BTCUSDT
VOLUME=0.01
PRICE=30000
TAKE_PROFIT_PRICE=35000
SIGNAL=BUY
ORDER_TYPE=LIMIT
```

#### A limit sell order of 0.01 ETH at +10% of its current price in BTC
``` bash
EXCHANGE=binance
SYMBOL=ETHBTC
VOLUME=0.01
PRICE=10%
SIGNAL=SELL
ORDER_TYPE=LIMIT
```

#### A stop loss sell order of 10 ATOM at 3 USDT from the current price wigh an "exit1" tag
``` bash
EXCHANGE=binance
SYMBOL=ATOMUSDT
VOLUME=10
STOP_PRICE=-3d
SIGNAL=SELL
ORDER_TYPE=STOP
TAG=exit1
```


## Canceling orders

Use `SIGNAL=CANCEL` to cancel orders identified buy their `SYMBOL` and `EXCHANGE`

### Canceling every ETH/BTC order on Binance
``` bash
EXCHANGE=binance
SYMBOL=ETHBTC
SIGNAL=CANCEL
```

### Canceling every ATOM/USDT sell order with an "exit1" tag on Binance
``` bash
EXCHANGE=binance
SYMBOL=ATOMUSDT
SIGNAL=CANCEL
PARAM_SIDE=SELL
TAG=exit1
```

Additional cancel parameters are available:
- `PARAM_SIDE` is the side of the orders to cancel, it can be `buy` or `sell` to only cancel buy or sell orders.
- `TAG` is the tag to select orders to cancel with. When provided, only orders created with the given tag and symbols will be canceled.

## Alerts security

You can use a token to add a security layer on your webhook alerts using
an identification token, this token is randomly generated by your
OctoBot and can be found on the configuration interface and in execution
logs.

To add your token on the tradingview.com signal: add the following line
to the alert message:

``` bash
TOKEN=YOUR_TOKEN
```
