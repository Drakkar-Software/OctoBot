---
title: "FAQ"
description: "Des questions lors de l'utilisation d'OctoBot ? Consultez les questions les plus courantes de la communauté OctoBot et trouvez des réponses détaillées dans notre FAQ."
sidebar_position: 7
---



# Foire aux quesitons (FAQ)

:::info
  La traduction française de cette page est en cours.
:::

## Pourquoi mon OctoBot ne crée-t-il pas d'ordres ?

Avant de créer un ordre (en utilisant le simulateur de trading ou le trading réel), OctoBot demande à la plateforme d'échange quelles sont ses exigences minimales (et maximales) pour tout ordre. 
Lors de la création d'un ordre (suite à un signal d'achat ou de vente) ces exigences sont vérifiées. Si l'ordre ne respecte pas ces exigences, il ne sera pas transmis à la plateforme d'échange.

The most common case of signals without created orders is when there is
**not enough funds** of the required asset to proceed with an order.

Example: not enough **USD** to buy BTC for a BTC/**USD** **buy** signal.

> In [trading simulator](/guides/octobot-usage/simulator) and [backtesting](/guides/octobot-usage/backtesting) modes, OctoBot uses a simulated portfolio called 
`"starting-portfolio"` that is defined in the 
[trading simulator configuration](/guides/octobot-usage/simulator.md#starting-portfolio).

## À quelle fréquence mon OctoBot va-t-il trader ?

Cela peut se produire une fois par semaine ou 5 fois par minute, cela dépend de la stratégie que votre OctoBot utilise.

Par exemple : lorsque vous utilisez les paramètres par défaut, l'évaluateur de stratégie mixte simple utilise un intervalle d'une heure comme le plus court. 
Étant donné qu'il s'agit d'une stratégie basée sur l'évaluation technique, elle se mettra à jour toutes les heures. 
Dans cette configuration, votre OctoBot créera de nouvelles transactions chaque fois qu'il détecte une opportunité, soit toutes les heures. 
Il peut y avoir des heures sans opportunité et sans création d'ordre.

## J'ai mis à jour mon OctoBot et il ne démarre plus.

Cela est probablement dû à un problème dans votre dossier **tentacles** folder. 
Essayez de le supprimer et de redémarrer votre OctoBot, il téléchargera les dernières versions de chaque tentacle et devrait résoudre le problème.

## Comment suivre les activités de trading de mon OctoBot ?

Lorsque votre OctoBot passe un ordre ou a un ordre qui est exécuté, il apparaîtra sur l'interface web. 
L'interface web affiche la liste des ordres en cours et la liste des ordres exécutés.

Vous pouvez également recevoir des notifications Telegram et bientôt Discord concernant la passation des ordres et les transactions.

## Quelle partie de mon portfolio est tradée par OctoBot ?


OctoBot will consider it can trade 100% of the portfolio you give it.
However how this funds will be used (size of orders, orders frequency,
...) depends on your risk setting and the trading mode you are using.

## Comment configurer le portfolio de départ en backtesting ?


Each [backtesting](/guides/octobot-usage/backtesting) run is using the 
[trading simulator configuration](/guides/octobot-usage/simulator.md#starting-portfolio) 
as a base.


## Pourquoi mon marché de référence change-t-il en backtesting ?


The reference market is automatically switched to the base of the traded
pair in [backtesting](/guides/octobot-usage/backtesting) to compute more accurate profitability.

Example: a backtesting on ETH/**BNB** would make **BNB** the temporary
reference market for this backtesting.

## Combien de mes fonds sur plateforme d'échange seront tradés par OctoBot ?

For now, OctoBot uses all the available funds to trade. Therefore it's
possible that 100% of the exchange funds on an account will be traded.

## Pourquoi est-ce que le backtesting n'utilise pas toutes les données disponibles ?

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

## "RuntimeError: Event loop is closed" dans mes logs d'exécution, y a-t-il un problème ?


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
