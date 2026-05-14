---
title: "Mode de trading AIIndex"
description: "Le **mode de trading AI Index** est un mode de trading avancé qui hérite de `IndexTradingMode` et utilise des agents IA externes pour générer dynamiquement..."
keywords: ["trading modes", "strategies", "octobot", "aiindex-trading-mode"]
slug: /guides/strategies/trading-modes/aiindex-trading-mode
format: md
---

# Mode de trading AI Index

## Vue d'ensemble

Le **mode de trading AI Index** est un mode de trading avancé qui hérite de `IndexTradingMode` et utilise des agents IA externes pour générer dynamiquement des répartitions de portefeuille à partir des données d'évaluation des stratégies. Ce mode combine l'infrastructure robuste de rééquilibrage du trading indiciel avec une prise de décision pilotée par l'IA pour une allocation d'actifs optimale, la logique IA étant gérée par des agents distincts plutôt qu'intégrée au mode.

## Caractéristiques principales

- **Allocations pilotées par des agents** : utilise des agents IA externes pour analyser les signaux de stratégie et générer des poids de portefeuille optimaux
- **Intégration des stratégies** : collecte les données des signaux des évaluateurs TA, sociaux et temps réel lors des callbacks de la matrice
- **IA découplée** : le traitement IA s'effectue dans des agents distincts, ce qui permet l'évolutivité et la modularité
- **Instructions détaillées** : les agents fournissent des instructions de rééquilibrage exploitables accompagnées d'explications
- **Hérite de IndexTradingMode** : capacités complètes de rééquilibrage, de gestion des ordres et d'optimisation du portefeuille
- **Paramètres configurables** : sélection du modèle, température, limites de tokens pour les agents

## Configuration

### Paramètres de configuration de l'IA

| Paramètre | Type | Valeur par défaut | Description |
|-----------|------|---------|-------------|
| `model` | string | "gpt-4" | Modèle GPT utilisé par les agents (gpt-3.5-turbo, gpt-4, gpt-4-turbo) |
| `temperature` | float | 0.3 | Créativité de l'IA pour les agents (0.0 = déterministe, 1.0 = très créatif) |
| `max_tokens` | int | 2000 | Nombre maximal de tokens pour les réponses IA des agents |

### Paramètres de trading indiciel (hérités)

| Paramètre | Type | Valeur par défaut | Description |
|-----------|------|---------|-------------|
| `refresh_interval` | int | 1 | Nombre de jours entre les vérifications de rééquilibrage |
| `rebalance_trigger_min_percent` | int | 5 | Écart minimal en % avant un rééquilibrage |

## Fonctionnement

### 1. Collecte des signaux de stratégie
Le mode de trading AI Index surveille les callbacks de la matrice provenant des évaluateurs de stratégie :
- Signaux d'analyse technique (TA)
- Signaux de sentiment social
- Signaux d'évaluation temps réel

### 2. Soumission des données
Lorsque les stratégies se mettent à jour, le mode :
1. Collecte les données d'évaluation de stratégie actuelles
2. Soumet des évaluations neutres avec `{"strategy_data": data}` pour déclencher le traitement par les agents
3. Les agents écoutent ces soumissions et traitent les données

### 3. Traitement par les agents
Les agents IA externes :
1. Reçoivent les données de stratégie issues des soumissions du mode
2. Analysent les signaux à l'aide des modèles GPT configurés
3. Génèrent des instructions de rééquilibrage
4. Renvoient les instructions au mode

### 4. Application des instructions
Le mode reçoit les instructions générées par les agents :
- Applique les changements de répartition via `ai_index_distribution.apply_ai_instructions`
- Valide les instructions pour en vérifier la cohérence
- Exécute le rééquilibrage en s'appuyant sur la logique de IndexTradingMode

## Architecture des agents

### Flux de données
```
Strategy Callbacks → Mode Producer → Submit {"strategy_data": data}
                        ↓
                Agents Process → Generate {"ai_instructions": instructions}
                        ↓
Mode Consumer → Apply Instructions → Rebalance Portfolio
```

### Format des instructions
Les agents fournissent les instructions sous forme de listes d'actions :
```json
[
  {"action": "reduce_exposure", "symbol": "BTC", "amount": 10, "explanation": "Overbought signals"},
  {"action": "increase_exposure", "symbol": "ETH", "amount": 15, "explanation": "Strong momentum"}
]
```

### Responsabilités des agents
- **Analyse des signaux** : traitent les données de stratégie avec des modèles IA
- **Génération d'instructions** : créent des actions de rééquilibrage validées
- **Gestion des erreurs** : gèrent les défaillances de l'API et fournissent des instructions sûres

## Exemples d'utilisation

### Configuration de base
```json
{
  "trading_mode": "AIIndexTradingMode",
  "model": "gpt-4",
  "temperature": 0.3,
  "max_tokens": 2000,
  "refresh_interval": 1,
  "rebalance_trigger_min_percent": 5
}
```

### Configuration conservatrice
```json
{
  "trading_mode": "AIIndexTradingMode",
  "model": "gpt-3.5-turbo",
  "temperature": 0.1,
  "max_tokens": 1500,
  "refresh_interval": 2
}
```

## Tests

Utilisez les outils tentacles-agent pour tester :
```bash
# Test with strategy evaluators
python tentacle_trading_mode_tester.py --mode AIIndexTradingMode --evaluators strategy_evaluators.json --symbol BTC/USDT --duration 120

# Test basic functionality
python tentacle_configuration_tester.py --config ai_index_config.json --validate
```

## Dépendances

- **Agents IA** : requis pour la génération d'instructions
- **Évaluateurs de stratégie** : tout évaluateur fournissant des signaux TA / sociaux / temps réel
- **IndexTradingMode** : fonctionnalité de rééquilibrage héritée

## Dépannage

### Problèmes courants

**Aucun rééquilibrage ne se produit**
- Vérifiez que les évaluateurs de stratégie sont actifs et déclenchent des callbacks
- Vérifiez que les agents sont en cours d'exécution et traitent les soumissions
- Assurez-vous que le solde du portefeuille est suffisant pour le rééquilibrage

**Les agents ne répondent pas**
- Vérifiez la configuration et la connectivité des agents
- Vérifiez la disponibilité du service IA
- Consultez les logs des agents pour repérer les erreurs de traitement

### Logs à vérifier
- Soumissions des données de stratégie : `"Submitting strategy data for AI processing"`
- Application des instructions : `"Applied AI instructions: {...}"`
- Erreurs de validation : `"Invalid AI instructions received"`

## Améliorations futures

- **Marketplace d'agents** : plusieurs agents IA en concurrence
- **Apprentissage historique** : les agents intègrent les résultats de backtesting
- **Adaptation temps réel** : les agents s'ajustent aux conditions de marché en direct
- **Corrélation multi-actifs** : optimisation avancée du portefeuille
- **Développement d'agents personnalisés** : framework pour des agents définis par l'utilisateur
