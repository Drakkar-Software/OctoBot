---
title: "FAQ"
description: "Any question when using OctoBot ? Check out the most common questions from the OctoBot community and find the detailed answers on our FAQ."
sidebar_position: 7
---

# Frequently Asked Questions (FAQ)


## Why is my OctoBot not creating orders ?


Before creating any order (using [trading simulator](/guides/octobot-usage/simulator) or real trading),
OctoBot asks the exchange for its minimal (and maximal) requirements for
any order. When creating an order (following a buy or sell signal),
these order requirements are checked. If the order is not compliant, it
will not be pushed to the exchange.

The most common case of signals without created orders is when there is
**not enough funds** of the required asset to proceed with an order.

Example: not enough **USD** to buy BTC for a BTC/**USD** **buy** signal.

> In [trading simulator](/guides/octobot-usage/simulator) and [backtesting](/guides/octobot-usage/backtesting) modes, OctoBot uses a simulated portfolio called 
`"starting-portfolio"` that is defined in the 
[trading simulator configuration](simulator#starting-portfolio).

## How often will my OctoBot trade ?


It can be once in a week or 5 times a minute, this depends on the
strategy your OctoBot is using.

For example: when using the default settings, the simple mixed strategy
evaluator is using the 1 hour timeframe as the shortest one. Since it's
a technical evaluator based strategy, it will update every hour. In this
setup, your OctoBot will create new trades every hour it sees an
opportunity. There might be hours with no opportunity and no order
creation.

## I updated my OctoBot and now it's not starting anymore.


This is probably due to an issue in your **tentacles** folder. Try
removing it and restarting your OctoBot, it will download the latest
versions of each tentacle and should fix the problem.

## How to follow my OctoBot's trading activity ?


When your OctoBot places an order or has a order that is filled, it will
appear on the web interface. The web interface displays the list of open
orders and the list of filled orders.

You can also receive Telegram and soon Discord notifications on
orders placement and trades.

## What part of my portoflio will be traded by OctoBot ?


OctoBot will consider it can trade 100% of the portfolio you give it.
However how this funds will be used (size of orders, orders frequency,
...) depends on your risk setting and the trading mode you are using.

## How to change the backtesting starting portfolio ?


Each [backtesting](/guides/octobot-usage/backtesting) run is using the [trading simulator configuration](/guides/octobot-usage/simulator.md#starting-portfolio) 
as a base.


## Why is my reference market changing in backtesting ?


The reference market is automatically switched to the base of the traded
pair in [backtesting](/guides/octobot-usage/backtesting) to compute more accurate profitability.

Example: a backtesting on ETH/**BNB** would make **BNB** the temporary
reference market for this backtesting.

## How much of my exchange funds will be traded by OctoBot ?

For now, OctoBot uses all the available funds to trade. Therefore it's
possible that 100% of the exchange funds on an account will be traded.

## Why is backtesting not using all available data ?


[OctoBot backtesting](/guides/octobot-usage/backtesting) is always using the **maximum available data allowing to keep a realistic simulation**.

However exchange are usually not giving all of their data: they give the
last X candles (500 for binance). Therefore a regular backtesting data
file has 500 1hour (1h) candles, 500 1minute (1m) candles etc. These
candles are always the most recent ones. That means that when running a
backtesting on 1h and 1d time frames, the maximum backtesting range is
not 1h and 1d with 500 candles each but the time range where **both** 1h
and 1d have data: there the past 500 hours (500 1h candles and
approximately 20 1d candles).

As an example, in a backtesting with 1m and 1d candles: the common time
range in 1d is `500/(60*24) = 0.35` which means the whole backtesting is
carried out with the data of one day: the last daily candle of the 500
1d candle only while using 100% of the shortest time frame: 1m (which
all happened during this one day).

## "RuntimeError: Event loop is closed" in my OctoBot's logs, is there a problem ?


This error (or something very similar) might appear in your OctoBot's logs:

```
<function _ProactorBasePipeTransport.del at 0x000001064DE8A310>
Traceback (most recent call last):
  File "asyncio\proactor_events.py", line 116, in del
  File "asyncio\proactor_events.py", line 108, in close
  File "asyncio\base_events.py", line 719, in call_soon
  File "asyncio\base_events.py", line 508, in _check_closed
RuntimeError: Event loop is closed
```

This is a minor issue with the current Windows implementation of the asynchronous 
libraries OctoBot is using. It has absolutely no effect and can be completely ignored.
