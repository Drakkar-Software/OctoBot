---
title: "Évaluateur de stratégie Simple"
description: "SimpleStrategyEvaluator est la stratégie la plus flexible. Conçue pour être personnalisée, elle utilise tous les évaluateurs techniques, sociaux et temps réel activés, et..."
keywords: ["strategy evaluators", "combined signals", "octobot", "simple-strategy-evaluator"]
slug: /guides/strategies/evaluators/strategies/simple-strategy-evaluator
format: md
---

SimpleStrategyEvaluator est la stratégie la plus flexible. Conçue pour être personnalisée, elle utilise
tous les évaluateurs techniques, sociaux et temps réel activés, et calcule la moyenne de la valeur d'évaluation de
chacun pour produire son évaluation finale.

Cette stratégie peut être utilisée pour générer des signaux de trading à partir d'autant d'évaluateurs que nécessaire.

Les time frames utilisées sont 1h, 4h et 1d par défaut.

Avertissement : cette stratégie ne prend en compte que les évaluateurs dont les valeurs d'évaluation sont comprises entre -1 et 1.
