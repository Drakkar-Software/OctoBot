---
title: "Simulateur"
description: "Vous préférez trader avec de l'argent simulé avant d'utiliser vos fonds réels ? Utilisez le simulateur de trading OctoBot pour exécuter n'importe quelle stratégie en utilisant le trading virtuel."
sidebar_position: 1
---



# Simulateur

:::info
  La traduction française de cette page est en cours.
:::

OctoBot peut être utilisé en mode simulation. Dans ce mode, OctoBot simulera des transactions en utilisant exactement le même processus que dans le mode de trading réel.

![octobot trading settings from profiles](/images/guides/configuration/octobot-trading-settings-from-profiles.png)

La seule différence avec un véritable trader réside dans le portefeuille initial défini dans la configuration du simulateur de trading. 
Chaque profil possède son propre portefeuille simulé. 
Ce portefeuille sera géré par OctoBot, et les ordres simulés utiliseront ces cryptomonnaies disponibles comme base.

Le simulateur de trader utilisera les dernières transactions des plateformes d'échange pour déterminer si les ordres actuels auraient été exécutés ou non. 
S'ils auraient été exécutés, les ordres simulés sont exécutés, et le portefeuille simulé actuel est mis à jour en conséquence.

## Frais d'échanges

Fees in % to be deducted at simulated orders completion in simulated orders and [backtesting](backtesting). Examples:
- A maker fee configured to `0.1` corresponds to a 0.1% trading fee on marker orders.
- A taker fee configured to `1.2` corresponds to a 1.2% trading fee on taker orders.

## Portfolio d'origine

This is the imaginary portfolio given to the trader simulator to create
its orders with. It can contain any amount of any cryptocurrency. If
these cryptocurrencies are in the **crypto-currencies** configuration,
they will be traded as if they were from a real portfolio.

The simulated portfolio is kept between instances of your OctoBot is simulated trading. It will be reset to the value of your profile's Starting portfolio when:
- Clicking `Reset history` on your portfolio view
- Changing the value of your current profile Starting portfolio

The starting portfolio is also **used for backtesting**.

## Mode, marché de référence et risque


These parameters are defined in the **trading** section, which is used by the trader simulator as 
well as the real trader. This **trading** section is described on 
the [trading settings](/guides/octobot-configuration/profile-configuration#trading)

## Trader réel

Additionally to the simulated trading system, a real trader is available in OctoBot.
