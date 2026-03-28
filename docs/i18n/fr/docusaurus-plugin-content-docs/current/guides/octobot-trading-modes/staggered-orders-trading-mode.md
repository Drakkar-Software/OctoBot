---
title: "Staggered Orders trading mode"
description: "Profitez des marchés stables avec un ensemble d'ordres d'achat et vente de type grille et une configuration avancée grâce au Staggered Orders Trading Mode."
sidebar_position: 8
---



# Staggered Orders Trading Mode

Le Staggered Orders Trading Mode (ou StaggeredOrdersTradingMode) est conçu pour tirer profit des marchés stables en maintenant un ensemble d'ordres d'achat et de vente semblable à une grille. Réalisez de petits bénéfices réguliers sur chaque petite variation du marché avec des risques minimisés grâce aux ordres en grille.

<div style={{textAlign: "center"}}>
    ![grid trading illustrated by a man stepping up on green stairs grabbing coins](/images/guides/grid-trading-illustrated-by-a-man-stepping-up-on-green-stairs-grabbing-coins.png)
</div>

Le Staggered Orders Trading Mode est une version plus complexe et flexible du [Grid Trading Mode](grid-trading-mode). Dans la plupart des situations, le [Grid Trading Mode](grid-trading-mode) est un meilleur choix.

Alors que le Grid Trading Mode est principalement défini autour du nombre d'ordre que vous souhaitez maintenir, le Staggered Orders Trading Mode se concentre sur la plage de prix que vous souhaitez couvrir. En configurant les bornes supérieure et inférieure, l'écart et l'incrément, le Staggered Orders Trading Mode déterminera combien d'ordre sont nécessaires, utilisera les fonds maximum disponibles et maintiendra les ordres pertinents sur la plateforme d'échange.

## Le Staggered Orders Trading Mode peut

- Être configuré pour chaque paire de trading indépendamment
- Spécifier la manière dont les fonds sont dispatchés dans les ordres d'achat et vente
- Maintenez une grille d'ordres d'achat et vente en utilisant l'écart et l'incrément configurés en %.
- Calculer automatiquement le nombre d'ordres d'achat et de vente nécessaires en fonction des bornes supérieure et inférieure configurées, ainsi que de l'écart et de l'incrément
- Maintenez un nombre limité d'ordres sur la plateforme d'échange (les plateformes imposent généralement une limite sur les ordres ouverts simultanés). Cette limite est définie par le paramètre `Operational depth` parameter. Les autres ordres seront marqués comme "virtuels": ils ne seront créés sur la plateforme d'échange que si néccessaire.
- Inclure un délai dans la 
- Inclure un délai lors de la création d'ordres opposés lorsque qu'un achat ou une vente est exécutée
- Tradez sur les marchés SPOT
- Optimiser automatiquement le portefeuille afin de créer la grille parfaite à l'aide de la commande `Optimize Initial Portfolio`
