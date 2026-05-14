---
title: "Mode de trading Arbitrage"
description: "ArbitrageTradingMode surveille les prix des paires de trading configurées sur les exchanges disponibles afin de trouver..."
keywords: ["trading modes", "strategies", "octobot", "arbitrage-trading-mode"]
slug: /guides/strategies/trading-modes/arbitrage-trading-mode
format: md
---

ArbitrageTradingMode surveille les prix des paires de trading configurées sur les exchanges disponibles
afin de trouver des opportunités d'[arbitrage](https://www.investopedia.com/terms/a/arbitrage.asp).

ArbitrageTradingMode surveille le prix des paires tradées sur chaque exchange et calcule leur prix moyen.
Si le prix d'une paire s'écarte suffisamment de son prix moyen inter-exchanges, un trade d'arbitrage est initié.

Un trade d'arbitrage consiste en **2 ordres** :
 1. Un ordre limite d'achat ou de vente au prix actuel de l'exchange local
 2. Lorsque ce premier ordre est exécuté :
    - Un ordre limite d'achat ou de vente au prix moyen (moyenne des prix sur les autres exchanges) est créé pour profiter de l'opportunité d'arbitrage
    - Un stop loss du côté opposé est créé pour sécuriser les fonds

Le premier ordre limite est annulé si le prix de l'exchange local atteint le prix moyen des autres exchanges.
**Aucun fonds n'est transféré** d'un exchange à un autre, tout se passe sur le même exchange.

Il est recommandé d'activer le trading d'arbitrage sur **quelques exchanges seulement** pour profiter du **décalage des prix** :
il suffit d'enregistrer ces exchanges dans votre configuration ArbitrageTradingMode.
**Chaque exchange** de votre configuration OctoBot sera utilisé pour calculer le **prix moyen** de chaque paire tradée,
vous pouvez donc ajouter des **exchanges très liquides** à utiliser uniquement comme **références de prix** et repérer rapidement
les opportunités d'arbitrage.

Par défaut, **chaque exchange** de votre configuration OctoBot est utilisé pour le trading d'arbitrage. Il est recommandé de
**réduire cette liste** dans votre configuration ArbitrageTradingMode et de **trader uniquement sur ceux offrant
des opportunités d'arbitrage, et d'utiliser les autres comme indicateurs de prix**.

Les exchanges utilisés **uniquement comme référence de prix ne nécessitent aucune clé API**, car aucun trade n'y est effectué.

<div class="text-center">
    <img src="https://raw.githubusercontent.com/Drakkar-Software/OctoBot/assets/arbitrage.png" width="100%" height="100%">
</div>

_Ce mode de trading prend en charge l'historique de PNL._
