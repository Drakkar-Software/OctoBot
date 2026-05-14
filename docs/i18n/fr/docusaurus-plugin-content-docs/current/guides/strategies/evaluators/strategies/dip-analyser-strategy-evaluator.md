---
title: "Évaluateur de stratégie Dip Analyser"
description: "DipAnalyserStrategyEvaluator est une stratégie qui analyse les creux du marché à l'aide des moyennes du [RSI](https://www.investopedia.com/terms/r/rsi.asp). Selon le niveau..."
keywords: ["strategy evaluators", "combined signals", "octobot", "dip-analyser-strategy-evaluator"]
slug: /guides/strategies/evaluators/strategies/dip-analyser-strategy-evaluator
format: md
---

DipAnalyserStrategyEvaluator est une stratégie qui analyse les creux du marché à l'aide des moyennes du [RSI](https://www.investopedia.com/terms/r/rsi.asp).
Selon le niveau du RSI, un signal d'achat peut être généré. Ce signal possède un poids qui correspond à
une intensité plus ou moins forte de l'évaluation du RSI.

Cette stratégie utilise également l'[oscillateur de Klinger](https://www.investopedia.com/terms/k/klingeroscillator.asp) pour identifier
les retournements et créer des signaux d'achat.

Un signal d'achat est généré lorsque la composante RSI signale une opportunité et que la partie Klinger confirme
une situation de retournement.

Cette stratégie est mise à jour à la fin de chaque bougie sur la time frame surveillée.

Il est également possible de la faire se déclencher
automatiquement à l'aide d'un évaluateur temps réel. L'utilisation d'un évaluateur temps réel qui signale les changements soudains du marché, comme
InstantFluctuationsEvaluator, fera également réagir DipAnalyserStrategyEvaluator lors de tels événements.

DipAnalyserStrategyEvaluator se concentre sur une seule time frame et fonctionne mieux sur les time frames longues telles que 4h et plus.
