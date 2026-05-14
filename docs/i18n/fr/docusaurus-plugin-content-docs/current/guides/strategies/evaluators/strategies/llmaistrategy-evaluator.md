---
title: "Évaluateur LLMAIStrategy"
description: "Le LLMAIStrategyEvaluator est un évaluateur de stratégie avancé qui s'appuie sur les grands modèles de langage (LLM) pour analyser et synthétiser les signaux des évaluateurs Technical..."
keywords: ["strategy evaluators", "combined signals", "octobot", "llmaistrategy-evaluator"]
slug: /guides/strategies/evaluators/strategies/llmaistrategy-evaluator
format: md
---

# LLMAIStrategyEvaluator

Le LLMAIStrategyEvaluator est un évaluateur de stratégie avancé qui s'appuie sur les grands modèles de langage (LLM) pour analyser et synthétiser les signaux des évaluateurs d'analyse technique (TA), de sentiment social et temps réel. Il fournit des recommandations de trading intelligentes en combinant les entrées de plusieurs évaluateurs avec un raisonnement piloté par l'IA via un traitement parallèle par sous-agents.

## Fonctionnement

1. **Agrégation des signaux** : collecte les notes et descriptions d'évaluation des évaluateurs TA, sociaux et temps réel configurés
2. **Analyse parallèle par sous-agents** : utilise des StrategyAgents spécialisés pour analyser chaque type d'évaluateur de manière indépendante
3. **Synthèse par IA** : s'appuie sur le raisonnement du grand modèle de langage dans chaque sous-agent pour une analyse spécialisée
4. **Résumé** : combine tous les résultats des sous-agents via un SummarizationAgent pour l'évaluation finale
5. **Génération de la sortie** : produit une eval_note (de -1 à 1) et un raisonnement descriptif

## Structure des fichiers

Le LLMAIStrategyEvaluator est organisé selon une architecture modulaire :

```
ai_strategies_evaluator/
├── ai_strategies.py                 # Main evaluator implementation
├── agents/                          # Agent-based architecture
│   ├── __init__.py                  # Agent module exports
│   ├── base_llm_agent.py           # Abstract base agent class
│   ├── summarization_agent.py      # Final result synthesis
│   ├── technical_analysis_agent.py # TA signal analysis
│   ├── sentiment_analysis_agent.py # Social sentiment analysis
│   └── real_time_analysis_agent.py # Real-time market analysis
│   └── factory.py                  # Agent creation factory
├── config/                         # Configuration files
│   └── LLMAIStrategyEvaluator.json # Evaluator configuration
├── resources/                      # Documentation and metadata
│   ├── LLMAIStrategyEvaluator.md   # This documentation
│   └── metadata.json               # Tentacle metadata
├── tests/                          # Test suite
│   └── test_llm_ai_strategy_evaluator.py # Unit tests
└── __init__.py                     # Package initialization
```

### Paramètres utilisateur
- **Prompt** : prompt personnalisé pour l'analyse LLM (laisser vide pour utiliser les prompts spécialisés par défaut selon le type d'évaluateur)
- **Model** : sélection du modèle GPT (utilise les valeurs par défaut de GPTService si non spécifié)
- **Max Tokens** : longueur maximale de la réponse (utilise les valeurs par défaut de GPTService si non spécifié)
- **Temperature** : caractère aléatoire des réponses du LLM (utilise les valeurs par défaut de GPTService si non spécifié)
- **Evaluator Types** : sélection des évaluateurs TA, sociaux et temps réel à inclure (tous activés par défaut)
- **Output Format** : choisir « standard » ou « with_confidence » (inclut le niveau de confiance moyen)

### Comportement par défaut
- Évalue sur les time frames 1 heure, 4 heures et 1 jour
- Utilise le modèle et les paramètres par défaut de GPTService
- Inclut par défaut les évaluateurs TA, sociaux et temps réel
- Fournit une analyse spécialisée pour chaque type d'évaluateur
- Utilise le traitement parallèle pour de meilleures performances

### Types d'analyse spécialisés

#### Agent d'analyse technique
Se concentre exclusivement sur les indicateurs techniques et les configurations de prix :
- Analyse le RSI, le MACD, les moyennes mobiles, les bandes de Bollinger, l'ADX, etc.
- Évalue la direction de la tendance et la convergence des indicateurs
- Fournit un niveau de confiance basé sur la force et la concordance des signaux

#### Agent de sentiment social
Se concentre exclusivement sur les signaux sociaux et de sentiment :
- Analyse les réseaux sociaux, les actualités, les discussions de la communauté
- Évalue l'humeur et le sentiment général du marché
- Fournit un niveau de confiance basé sur la cohérence et le volume des signaux

#### Agent temps réel
Se concentre sur les mouvements de marché en direct et les fluctuations instantanées :
- Analyse les données du carnet d'ordres et les mouvements de prix en temps réel
- Évalue la pression d'achat/vente actuelle
- Fournit un niveau de confiance basé sur la volatilité et la récence des signaux

## Prérequis
- GPTService doit être configuré et activé
- Au moins un évaluateur TA, social ou temps réel doit être actif pour une analyse pertinente
- Fonctionne à la fois en mode live et en mode backtesting

## Cas d'usage
- Synthèse avancée de signaux provenant de plusieurs types d'évaluateurs
- Analyse de marché parallèle assistée par IA pour de meilleures performances
- Analyse spécialisée combinant les signaux techniques, sociaux et temps réel
- Décisions de trading automatisées avec un raisonnement IA multifacette
- Backtesting de stratégies complexes multi-signaux

## Avantages de l'architecture

### Traitement parallèle
- Chaque type d'évaluateur est analysé par un agent dédié s'exécutant en parallèle
- Performances améliorées et latence réduite par rapport au traitement séquentiel
- Meilleure utilisation des ressources lors des appels à l'API LLM

### Analyse spécialisée
- Chaque sous-agent se concentre sur son domaine d'expertise
- Analyse plus précise grâce à des prompts et un raisonnement spécifiques au domaine
- Méthodologie d'évaluation cohérente entre les différents types de signaux

### Résumé intelligent
- L'évaluation finale prend en compte tous les résultats des sous-agents
- Pondère les signaux en fonction de leur confiance et de leur cohérence
- Fournit un raisonnement complet couvrant tous les domaines d'analyse

## Avertissement
- Les réponses du LLM peuvent varier en fonction des réglages de température
- Nécessite un accès à l'API OpenAI via GPTService
- Le traitement parallèle augmente l'utilisation et les coûts de l'API
- Les performances dépendent de la qualité des signaux des évaluateurs en entrée
