---
title: "Grid trading mode"
description: "Profitez facilement des marchés stables en maintenant un ensemble d'ordres d'achat et de vente selon une grille grâce au mode Grid Trading Mode."
sidebar_position: 7
---



# Grid Trading Mode

Le Grid Trading Mode (ou GridTradingMode) est conçu pour tirer profit des marchés stables en maintenant un ensemble d'ordres d'achat et de vente semblable à une grille. Réalisez des bénéfices réguliers sur chaque petite variation du marché avec des risques minimisés grâce au trading par grille. 

<div style={{textAlign: "center"}}>
    ![grid trading illustrated by a man stepping up on green stairs grabbing coins](/images/guides/grid-trading-illustrated-by-a-man-stepping-up-on-green-stairs-grabbing-coins.png)
</div>

Le Grid Trading Mode est une version simplifiée du [Staggered Orders Trading Mode](staggered-orders-trading-mode).

## Le Grid Trading Mode peut

- Utilisez une configuration par défaut
- Être configuré pour chaque paire de trading indépendamment
- Maintenir une grille d'ordres d'achat et de vente en utilisant l'écart et l'incrément configuré en valeurs statiques
- S'adapter à la hausse ou à la baisse (via trailing) lorsque le prix du marché dépasse les ordres la grille
- Utiliser une quantité limitée de fonds
- Utiliser le montant configuré pour chaque ordre
- Dispatcher automatiquement les nouveaux fonds déposés
- Inclure un délai lors de la création d'ordres opposés lorsque qu'un achat ou une vente est exécutée
- Initialiser la grille en fonction d'un prix personnalisé
- Tradez sur les marchés SPOT
- Optimiser automatiquement le portefeuille afin de créer la grille parfaite à l'aide de la commande `Optimize Initial Portfolio`
- Mettre en pause le maintient des ordres à l'aide dela commande `Pause Orders Mirroring`
