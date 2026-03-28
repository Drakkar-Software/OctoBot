---
title: "Simulator"
description: "You prefer trading with simulated money before using your real funds ? Use OctoBot trading simulator to run any strategy using paper trading."
sidebar_position: 1
---

# Simulator


OctoBot can be used in a simulation mode. In this mode, OctoBot will
simulate trades using the exact same process as with the real trading
mode.

![octobot trading settings from profiles](/images/guides/configuration/octobot-trading-settings-from-profiles.png)

The only difference with a real trader is in the starting portfolio that
is set in the Trade Simulator configuration.
Each profile has its own simulated portfolio. This portfolio will be
managed by OctoBot and simulated orders will be using these available
cryptocurrencies as a basis. 

The trader simulator will use the
exchanges' last trades to figure out if the current orders would have
been filled or not. If they would have been filled, simulated orders get
filled and the current simulated portfolio is updated accordingly.

## Fees

Fees in % to be deducted at simulated orders completion in simulated orders and [backtesting](backtesting). Examples:
- A maker fee configured to `0.1` corresponds to a 0.1% trading fee on marker orders.
- A taker fee configured to `1.2` corresponds to a 1.2% trading fee on taker orders.

## Starting portfolio

This is the imaginary portfolio given to the trader simulator to create
its orders with. It can contain any amount of any cryptocurrency. If
these cryptocurrencies are in the **crypto-currencies** configuration,
they will be traded as if they were from a real portfolio.

The simulated portfolio is kept between instances of your OctoBot is simulated trading. It will be reset to the value of your profile's Starting portfolio when:
- Clicking `Reset history` on your portfolio view
- Changing the value of your current profile Starting portfolio

The starting portfolio is also **used for backtesting**.

## Mode, Reference-market and Risk


These parameters are defined in the **trading** section, which is used by the trader simulator as 
well as the real trader. This **trading** section is described on 
the [trading settings](/guides/octobot-configuration/profile-configuration#trading)

## Real trader

Additionally to the simulated trading system, a real trader is available in OctoBot.
