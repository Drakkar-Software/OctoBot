---
title: "Évaluateur Death And Golden Cross"
description: "DeathAndGoldenCrossEvaluator repose sur deux [moyennes mobiles](https://www.investopedia.com/terms/m/movingaverage.asp), par défaut l'une de **50** périodes et..."
keywords: ["technical analysis", "evaluators", "indicators", "octobot", "death-and-golden-cross-evaluator"]
slug: /guides/strategies/evaluators/ta/death-and-golden-cross-evaluator
format: md
---

DeathAndGoldenCrossEvaluator repose sur deux [moyennes mobiles](https://www.investopedia.com/terms/m/movingaverage.asp), par défaut l'une de **50** périodes et l'autre de **200**.

Si la moyenne mobile rapide passe au-dessus de la moyenne mobile lente, cela indique un marché haussier (signal : -1). Lorsque cela se produit, on parle de [Golden Cross](https://www.investopedia.com/terms/g/goldencross.asp).
À l'inverse, si c'est la moyenne mobile rapide qui passe au-dessus de la moyenne mobile lente, cela indique un marché baissier (signal : 1). Lorsque cela se produit, on parle de [Death Cross](https://www.investopedia.com/terms/d/deathcross.asp)

Cet évaluateur produira toujours une valeur de `0`, sauf juste après la détection d'un golden cross ou d'un death cross,
auquel cas une valeur de `-1` ou `1` sera produite.
