---
title: "Mode de trading Staggered Orders"
description: "StaggeredOrdersTrading est une version avancée du GridTradingMode. Il place une grande quantité d'ordres d'achat et de vente à intervalles fixes, couvrant le carnet d'ordres..."
keywords: ["trading modes", "strategies", "octobot", "staggered-orders-trading-mode"]
slug: /guides/strategies/trading-modes/staggered-orders-trading-mode
format: md
---

StaggeredOrdersTrading est une version avancée du GridTradingMode. 
Il place une grande quantité d'ordres d'achat et de vente à intervalles fixes, couvrant le carnet d'ordres depuis
des prix très bas jusqu'à des prix très élevés, à la manière d'une grille.  
La fourchette (définie par des bornes inférieure et supérieure) est censée couvrir tous les prix concevables aussi
longtemps que l'utilisateur prévoit d'exécuter la stratégie, et ce pour chaque paire tradée.
Cela pourrait aller de -100x à +100x (-99 % à +10000 %).  
Note : plus la fourchette couverte est large, plus la stratégie nécessite d'ordres et de fonds pour s'exécuter. 

Les profits seront réalisés à partir des mouvements de prix au sein de la zone de prix couverte.  
Elle ne « vend jamais à perte », mais toujours avec un profit ; OctoBot n'annule donc jamais d'ordres lors de l'utilisation du mode de trading Staggered Orders.

Pour en savoir plus, consultez le 
<a target="_blank" rel="noopener" href="https://www.octobot.cloud/en/guides/octobot-trading-modes/staggered-orders-trading-mode?utm_source=octobot&utm_medium=dk&utm_campaign=regular_open_source_content&utm_content=StaggeredOrdersTradingModeDocs">
guide complet du mode de trading Staggered Orders</a>.

#### Modifier la configuration

Pour appliquer des modifications aux paramètres du mode de trading Staggered Orders, vous devrez annuler manuellement les ordres et redémarrer votre OctoBot.  
Ce mode de trading place instantanément des ordres du côté opposé lorsqu'un ordre est exécuté.  
OctoBot effectue également une vérification tous les 3 jours pour s'assurer du bon état de la grille et créer les ordres de grille manquants le cas échéant.

#### Paires tradées
Fonctionne uniquement avec des bases et des quotes indépendantes : ETH/USDT et ADA/BTC peuvent être activées ensemble, mais ETH/USDT
et BTC/USDT ne peuvent pas être activées ensemble sur la même instance OctoBot puisqu'elles partagent le même symbole 
(ici USDT).

#### Allocation des fonds
Les modes staggered peuvent être utilisés pour spécifier la manière d'allouer les fonds : les modes sont neutral, mountain, valley, sell slope et buy slope.

_Ce mode de trading prend en charge l'historique PNL._
