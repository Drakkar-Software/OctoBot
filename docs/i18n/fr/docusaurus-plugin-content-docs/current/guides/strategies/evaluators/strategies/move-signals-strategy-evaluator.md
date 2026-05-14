---
title: "Évaluateur de stratégie Move Signals"
description: "MoveSignalsStrategyEvaluator est une stratégie fractale : elle utilise différentes time frames pour équilibrer ses décisions."
keywords: ["strategy evaluators", "combined signals", "octobot", "move-signals-strategy-evaluator"]
slug: /guides/strategies/evaluators/strategies/move-signals-strategy-evaluator
format: md
---

MoveSignalsStrategyEvaluator est une stratégie fractale : elle utilise différentes time frames pour
équilibrer ses décisions.

Cette stratégie utilise le KlingerOscillatorMomentumEvaluator, basé sur l'[oscillateur de Klinger](https://www.investopedia.com/terms/k/klingeroscillator.asp),
pour savoir quand initier un trade, et le BBMomentumEvaluator, basé sur les [bandes de Bollinger](https://www.investopedia.com/terms/b/bollingerbands.asp),
pour déterminer le poids à accorder à ce trade.

Cette stratégie est mise à jour à la fin de chaque bougie sur la time frame surveillée, soit toutes les 30 minutes.

Il est également possible de la faire se déclencher
automatiquement à l'aide d'un évaluateur temps réel. L'utilisation d'un évaluateur temps réel qui signale les changements soudains du marché, comme
InstantFluctuationsEvaluator, fera également réagir MoveSignalsStrategyEvaluator lors de tels événements.

Les time frames utilisées sont 30m, 1h et 4h.

Avertissement : MoveSignalsStrategyEvaluator ne fonctionne que sur les marchés liquides, car l'oscillateur de Klinger nécessite suffisamment
de volume et une continuité des bougies pour être précis.
