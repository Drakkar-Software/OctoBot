---
title: "Design Philosophy"
description: "Learn about the OctoBot design philosophy and technical architecture based with speed and scalability in mind using Python and asynchronous programming with asyncio."
sidebar_position: 2
---



# Design Philosophy

## Philosophy

The goal behind OctoBot is to have a **very fast and scalable** trading robot.

To achieve this, OctoBot is entirely built around the

<a href="https://docs.python.org/3/library/asyncio.html" rel="nofollow">asyncio</a> producer-consumer
<a href="https://github.com/Drakkar-Software/Async-Channel" rel="nofollow">Async-Channel</a> framework which allows to very quickly and efficiently
transmit data to different elements within the bot. The idea is to all the time
maintain **fully up-to-date data** without having to use update loops. Update
loops require sleeping time, which is inefficient. This architecture enables to
**notify the evaluation chain as quickly as possible** when an update is
available without having to wait for any update cycle of any update loop.

Additionally, in order to save CPU time, as little threads as possible are used
by OctoBot (usually less than 10 with a standard setup).

## Overview

The OctoBot code is split into [several repositories](github-repositories).
Each module is handled as an independent python module and is available on the

<a href="https://pypi.org/" rel="nofollow">official python package repository</a> (used in `pip` commands).

## OctoBot

![OctoBot architecture](https://raw.githubusercontent.com/Drakkar-Software/OctoBot/assets/wiki_resources/octobot_arch.svg)

Simplified view of the OctoBot core components.

Inside the OctoBot part, each arrow is an async channel.

## OctoBot tentacles

Tentacles are OctoBot's extensions, they are meant to be easily customizable, can
be activated or not and do any specific action within OctoBot.

### Evaluation chain tentacles

They are tools to analyze market data as well as any other type of data (Teddit, Telegram, etc).
They implement abstract evaluators, strategies and trading modes.

### Utility tentacles

These are OctoBot's interfaces (web, telegram), notification systems, social news feeds
and [backtesting](/guides/octobot-usage/backtesting) data collectors. They implement abstract interfaces, services, service
feeds, notifiers and data collectors

## Evaluators, strategies and trading modes:

### Evaluators

Simple python classes that will automatically be wake up when new data is available.
Their goal is to set `self.eval_note` and call `await self.evaluation_completed`
that will then be made available to the Strategy(ies). They should be dedicated to
a single simple task such as (for example) evaluate the RSI on the current data or
looks for a divergence in a trend.

### Strategies

Strategies are more complex elements, they can read all the evaluators evaluations
on every time frame and are considering these evaluations to set their `self.eval_note`
and call `await self.strategy_completed`. As a comparison if evaluators are human
senses, strategies are the brain that will take these senses' signals and decide to
do something or not. Strategies can be generic like SimpleStrategyEvaluator that
will take any standard evaluator and time frame into account or using specific
evaluators only like MoveSignalsStrategyEvaluator.

### Trading modes

[Trading modes](../octobot-trading-modes/trading-modes) use the strategy(ies) evaluations to create, update or cancel orders.
Using the strategies signals, they are responsible for the way to translate a signal
into an order by looking at the available funds, open orders, considering stop loss
or not and other trading related responsibilities.

### Triggers

Evaluators, strategies and trading modes are automatically triggered when their channel
has a new data. Trigger sources are:

For evaluators

- Technical evaluators: any new candle or refresh request (with updated candles data) from a strategy
- Real time evaluators: any new candle and any market price change
- Social evaluators: associated signal (ex: a post for a Reddit social evaluator)

For strategies

- After a technical evaluator cycle: when all TA have updated their evaluation and called `await self.evaluation_completed`
- After any real time evaluator evaluation and call of `await self.evaluation_completed`
- After any social evaluator evaluation and call of `await self.evaluation_completed`

For trading mode

- After any strategy evaluation and call of `await self.strategy_completed`

_Thanks for reading this guide and if you have any idea on how to improve it, please reach out to us !_
