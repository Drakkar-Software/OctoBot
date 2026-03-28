---
title: "Understanding profitability"
description: "Having a hard time understanding how profitability and Profit and loss (PNL) work in OctoBot or how to reset it ? Check out our guide."
sidebar_position: 6
---

# Profitability in OctoBot

## Historical profitability

Every asset in OctoBot is valued using the **reference market** setting
(available in [Trading settings](/guides/octobot-configuration/profile-configuration#reference-market)).
Profitably follows this principle.

![home](https://raw.githubusercontent.com/Drakkar-Software/OctoBot/assets/wiki_resources/home.jpg)

To compute its profitability, OctoBot evaluates the value of all its
traded assets (the ones available for trading in its configuration) by
getting their value in reference market. Profitability is the difference
between the total value of the traded assets when OctoBot
started and the total value of current holdings at the moment
profitability is displayed.

## Historical PNL

Profit and loss (PNL) history, which is the profit from each historical trade independently from your portfolio assets historical valuation, is displayed on the "Trading" tab.

You can see it as "pure profits or losses from your trading strategy".

![pnl history](/images/guides/pnl.png)

> Please note that PNL history is not available on every trading mode.


## Resetting profitability history

You can reset your OctoBot's profitability history from the **Portfolio** tab.

## Resetting PNL history
Profit and loss history is computed using trades history. You can reset it by clearing the trades history from the **Trading** tab.
