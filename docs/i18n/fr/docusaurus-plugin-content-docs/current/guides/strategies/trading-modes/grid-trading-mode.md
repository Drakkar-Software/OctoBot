---
title: "Mode de trading Grid"
description: "Place un nombre fixe d'ordres d'achat et de vente à intervalles fixes pour profiter de tout mouvement du marché. Lorsqu'un ordre est exécuté, un ordre miroir est instantanément créé..."
keywords: ["trading modes", "strategies", "octobot", "grid-trading-mode"]
slug: /guides/strategies/trading-modes/grid-trading-mode
format: md
---

Place un nombre fixe d'ordres d'achat et de vente à intervalles fixes pour profiter de tout mouvement du marché. Lorsqu'un ordre est exécuté,
un ordre miroir est instantanément créé et génère du profit une fois complété.

Pour en savoir plus, consultez le
<a target="_blank" rel="noopener" href="https://www.octobot.cloud/en/guides/octobot-trading-modes/grid-trading-mode?utm_source=octobot&utm_medium=dk&utm_campaign=regular_open_source_content&utm_content=GridTradingModeDocs">
guide complet du mode de trading Grid</a>.

#### Configuration par défaut
Lorsqu'elle n'est pas spécifiée pour une paire de trading, la grille est initialisée avec un spread
de 1,5 % du prix actuel, un incrément de 0,5 % et un maximum de 20 ordres d'achat et de vente.

Lorsque suffisamment de fonds sont disponibles, la configuration par défaut donne :
- Jusqu'à 20 ordres d'achat couvrant de 99,25 % à 89,5 % du prix actuel
- Jusqu'à 20 ordres de vente couvrant de 100,75 % à 110,5 % du prix actuel

#### Configuration des paires de trading
Vous pouvez personnaliser la grille pour chaque paire de trading. Pour configurer une paire, saisissez :
- Le nom de la paire
- L'intervalle entre achat et vente (spread)
- L'intervalle entre chaque ordre (incrément)
- Le nombre d'ordres d'achat et de vente initiaux à créer

#### Options de trailing
Une grille ne peut fonctionner qu'à l'intérieur de sa plage de prix. Cependant, lorsque les options de trailing sont activées,
l'ensemble de la grille peut être automatiquement annulé et recréé
lorsque le prix de l'actif tradé sort de la plage de la grille. Dans ce cas, un ordre au marché peut être exécuté afin de
disposer des fonds nécessaires pour créer les ordres d'achat et de vente de la grille.

#### Profits
Les profits sont réalisés grâce aux mouvements de prix au sein de la zone de prix couverte.
Elle ne « vend jamais à perte », mais toujours avec un profit ; OctoBot n'annule donc jamais d'ordres lors de l'utilisation du mode de trading Grid.

Pour appliquer des modifications aux paramètres du mode de trading Grid, vous devrez annuler manuellement les ordres et redémarrer votre OctoBot.
Ce mode de trading place instantanément des ordres du côté opposé lorsqu'un ordre est exécuté.

Ce mode de trading a été rendu possible grâce au soutien de PKBO & Calusari.

_Ce mode de trading prend en charge l'historique de PNL._
