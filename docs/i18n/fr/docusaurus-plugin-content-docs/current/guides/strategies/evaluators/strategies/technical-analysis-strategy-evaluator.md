---
title: "Évaluateur de stratégie Technical Analysis"
description: "TechnicalAnalysisStrategyEvaluator est une stratégie d'analyse technique flexible. Conçue pour être personnalisée, elle utilise tous les évaluateurs techniques activés et..."
keywords: ["strategy evaluators", "combined signals", "octobot", "technical-analysis-strategy-evaluator"]
slug: /guides/strategies/evaluators/strategies/technical-analysis-strategy-evaluator
format: md
---

TechnicalAnalysisStrategyEvaluator est une stratégie d'analyse technique flexible. Conçue pour être personnalisée, elle utilise
tous les évaluateurs techniques activés et calcule la moyenne de la valeur d'évaluation de chacun pour produire son évaluation finale.

Cette stratégie permet d'attribuer un poids à n'importe quelle time frame afin de rendre les évaluations techniques associées
plus ou moins déterminantes dans l'évaluation finale de la stratégie. Si aucun poids n'est spécifié pour une time frame, le poids par défaut est 50.

Cette stratégie peut être utilisée pour créer des signaux de trading personnalisés à partir d'autant d'évaluateurs
techniques que souhaité.

TechnicalAnalysisStrategyEvaluator peut également utiliser des évaluateurs temps réel pour déclencher une réévaluation instantanée de ses évaluateurs
techniques et réagir rapidement. La valeur d'évaluation de ces évaluateurs temps réel ne sera pas prise en compte dans l'évaluation finale de la stratégie,
car ils servent uniquement à déclencher une réévaluation d'urgence.

Les time frames utilisées sont 30m, 1h, 2h, 4h et 1d par défaut.

Avertissement : cette stratégie ne prend en compte que les évaluateurs dont les valeurs d'évaluation sont comprises entre -1 et 1.
