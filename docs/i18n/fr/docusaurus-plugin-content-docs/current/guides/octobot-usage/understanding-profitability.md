---
title: "Comprendre la profitabilité"
description: "Vous avez du mal à comprendre comment fonctionnent la profitabilité ou les profits et pertes (PNL) dans OctoBot, ou comment les réinitialiser ? Consultez notre guide."
sidebar_position: 5
---



# La profitabilité dans OctoBot

:::info
  La traduction française de cette page est en cours.
:::

## Historique de profitabilité

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

## Historique de PNL

Profit and loss (PNL) history, which is the profit from each historical trade independently from your portfolio assets historical valuation, is displayed on the "Trading" tab.

You can see it as "pure profits or losses from your trading strategy".

![pnl history](/images/guides/pnl.png)

> Please note that PNL history is not available on every trading mode.


## Réinitialiser l'historique de profitabilité

You can reset your OctoBot's profitability history from the **Portfolio** tab.

## Réinitialiser l'historique de PNL
Profit and loss history is computed using trades history. You can reset it by clearing the trades history from the **Trading** tab.
