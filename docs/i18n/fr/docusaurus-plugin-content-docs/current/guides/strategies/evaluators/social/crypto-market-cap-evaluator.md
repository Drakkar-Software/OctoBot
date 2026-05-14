---
title: "Évaluateur de capitalisation boursière crypto"
description: "Analyse les tendances du marché des cryptomonnaies à partir des données de capitalisation boursière de CoinGecko pour chaque cryptomonnaie."
keywords: ["social evaluators", "sentiment", "news", "octobot", "crypto-market-cap-evaluator"]
slug: /guides/strategies/evaluators/social/crypto-market-cap-evaluator
format: md
---

Analyse les tendances du marché des cryptomonnaies à partir des données de capitalisation boursière de CoinGecko pour chaque cryptomonnaie.

Cet évaluateur interprète les signaux de capitalisation boursière des 100 principales cryptomonnaies (classées par capitalisation boursière) afin de produire un score normalisé indiquant des tendances haussières ou baissières en fonction de :
- La position/le rang de la cryptomonnaie dans le top 100 (un rang plus élevé = plus établie)
- Le pourcentage de variation de la capitalisation boursière sur 24 heures
- Le pourcentage de variation du prix sur 24 heures
- Le volume d'échanges relatif aux autres principales cryptomonnaies

L'évaluateur génère des notes d'évaluation en combinant ces facteurs avec une pondération basée sur la position, où les cryptomonnaies les mieux classées (par exemple, rang 1-10) reçoivent des multiplicateurs de confiance plus élevés que les cryptomonnaies moins bien classées.

Source des données : ([API CoinGecko](https://www.coingecko.com/en/api))
