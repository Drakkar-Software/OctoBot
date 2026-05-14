---
title: "Mode de trading Market Making"
description: "Une stratégie de market making qui maintient le carnet d'ordres configuré sur l'exchange ciblé."
keywords: ["trading modes", "strategies", "octobot", "market-making-trading-mode"]
slug: /guides/strategies/trading-modes/market-making-trading-mode
format: md
---

## MarketMakingTradingMode

Une stratégie de market making qui maintient le carnet d'ordres configuré sur l'exchange ciblé.

### Comportement
Au démarrage, la stratégie crée des ordres selon sa configuration. Elle peut annuler des ordres ouverts lorsqu'ils
sont incompatibles.

Dès que le carnet d'ordres maintenu devient obsolète (en raison d'un changement de prix de référence ou d'ordres exécutés/annulés), 
il est adapté pour toujours essayer de refléter la configuration.

Lorsqu'un remplacement complet du carnet d'ordres a lieu, les ordres sont annulés un par un pour éviter de laisser un carnet vide.

La stratégie utilise tous les fonds disponibles, jusqu'à un maximum de ce qui est nécessaire pour couvrir 
2 % du volume de trading quotidien de la paire sur l'exchange ciblé, dans les 3 % premiers de la profondeur du carnet d'ordres.

Note : la stratégie ne crée pas de volume artificiel en forçant des ordres au marché ; elle se concentre sur le maintien d'un 
carnet d'ordres optimisé.

### Configuration
- Les nombres de bids et d'asks définissent combien d'ordres doivent être maintenus dans le carnet
- Le spread minimum est la distance (en % du prix actuel) entre le bid le plus élevé et l'ask le plus bas
- Le spread maximum est la distance (en % du prix actuel) entre le bid le plus bas et l'ask le plus élevé
- L'exchange de référence est l'exchange depuis lequel obtenir le prix actuel de la paire tradée. Il doit s'agir d'un exchange très liquide afin d'éviter les opportunités d'arbitrage.

Une version avancée de cette stratégie de market making est disponible sur [OctoBot Market Making](https://market-making.octobot.cloud?utm_source=octobot_mm&utm_medium=dk&utm_campaign=regular_open_source_content&utm_content=trading_mode_docs).
