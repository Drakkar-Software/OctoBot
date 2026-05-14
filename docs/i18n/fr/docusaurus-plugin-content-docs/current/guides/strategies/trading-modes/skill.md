---
title: "SKILL"
description: "Ce skill fournit des recommandations complètes pour analyser les signaux de marché à partir des données de prix, de volume, de flux d'ordres et d'actualités afin d'identifier des opportunités de trading potentielles..."
keywords: ["trading modes", "strategies", "octobot", "skill"]
slug: /guides/strategies/trading-modes/skill
format: md
---

# signal-analysis

## Vue d'ensemble

Ce skill fournit des recommandations complètes pour analyser les signaux de marché à partir des données de prix, de volume, de flux d'ordres et d'actualités afin d'identifier des opportunités de trading potentielles. À utiliser lors du traitement de données de marché brutes pour générer des signaux exploitables.

## Instructions

### 1. Analyse du Price Action

**Identification de tendance**
- Tendance haussière : série de sommets plus hauts et de creux plus hauts
- Tendance baissière : série de sommets plus bas et de creux plus bas
- Range : prix oscillant entre support et résistance

**Évaluation du momentum**
- Momentum fort : grandes bougies avec suivi (follow-through)
- Momentum faiblissant : bougies plus petites, mèches, indécision
- Divergence : désaccord entre le prix et les indicateurs de momentum

### 2. Analyse du volume

**Schémas de volume**
- Pic de volume sur cassure : confirme la force
- Volume en baisse : tendance faiblissante
- Volume au support/résistance : points de décision clés
- Pics de volume inhabituels : investiguer la cause

**Indicateurs de flux d'ordres**
- Déséquilibre de pression acheteuse/vendeuse
- Ratio des gros ordres par rapport aux petits ordres
- Flux d'ordres au marché par rapport aux ordres à cours limité

### 3. Structure de marché

**Niveaux clés**
- Support : creux précédents où l'achat a émergé
- Résistance : sommets précédents où la vente a émergé
- Niveaux de cassure (breakout/breakdown)
- Nombres ronds psychologiques

**Reconnaissance de schémas**
- Consolidation avant les mouvements
- Fausses cassures (pièges)
- Gaps d'épuisement
- Schémas de climax

### 4. Évaluation de la qualité du signal

**Signaux de haute qualité**
- Confirmation sur plusieurs unités de temps
- Le volume confirme le price action
- Configuration risque/rendement claire
- Des schémas similaires récents ont fonctionné

**Signaux de faible qualité**
- Unités de temps contradictoires
- Faible volume, price action erratique
- Mauvais ratio risque/rendement
- Bruit élevé, faible conviction

### 5. Impact des actualités et événements

**Événements à fort impact**
- Annonces réglementaires majeures
- Listings/delistings d'exchanges
- Annonces de partenariats
- Incidents de sécurité

**Intégration des signaux**
- Actualité positive + technique haussière = signal d'achat fort
- Actualité négative + technique baissière = signal de vente fort
- Actualité en conflit avec la technique = attendre confirmation

## Format de sortie

```json
{
  "signals": [
    {
      "symbol": "BTC/USDT",
      "signal_type": "bullish" | "bearish" | "neutral",
      "strength": 0.8,
      "confidence": 0.75,
      "key_factors": [
        "Breakout above resistance with high volume",
        "Multiple timeframe alignment",
        "Positive news catalyst"
      ],
      "description": "Strong bullish breakout signal with volume confirmation",
      "entry_zone": {"min": 45000, "max": 46000},
      "targets": [48000, 50000, 52000],
      "stop_loss": 43500
    }
  ],
  "market_overview": "General market showing strength with Bitcoin leading, altcoins following"
}
```

## Bonnes pratiques

1. **Toujours considérer le contexte de l'unité de temps** - Aligner les signaux avec la tendance de l'unité de temps supérieure
2. **Le volume est essentiel** - Ne faites pas confiance aux mouvements sans volume
3. **Attendre la confirmation** - Ne vous précipitez pas sur les signaux faibles
4. **Suivre la performance des signaux** - Apprenez quels schémas fonctionnent le mieux
5. **Soyez patient** - La qualité prime sur la quantité
6. **Documenter les schémas** - Sauvegardez les schémas réussis dans /memories/signals/
