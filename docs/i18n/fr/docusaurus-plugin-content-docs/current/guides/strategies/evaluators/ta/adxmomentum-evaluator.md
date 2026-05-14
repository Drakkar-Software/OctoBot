---
title: "Évaluateur ADXMomentum"
description: "Utilise l'[Average Directional Index](https://www.investopedia.com/terms/a/adx.asp) pour détecter les retournements. L'implémentation par défaut suit..."
keywords: ["technical analysis", "evaluators", "indicators", "octobot", "adxmomentum-evaluator"]
slug: /guides/strategies/evaluators/ta/adxmomentum-evaluator
format: md
---

Utilise l'[Average Directional Index](https://www.investopedia.com/terms/a/adx.asp)  
pour détecter les retournements. L'implémentation par défaut suit
[l'article d'Investopedia ADX: The Trend Strength Indicator](https://www.investopedia.com/articles/technical/02/041002.asp).

Évalue une valeur de -1 à 1 en fonction du prix actuel à l'aide de la
[moyenne mobile exponentielle](https://www.investopedia.com/terms/e/ema.asp) d'une longueur de 20, couplée à
l'[ADX](https://www.investopedia.com/terms/a/adx.asp).
