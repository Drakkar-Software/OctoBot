---
title: "Dip Analyser trading mode"
description: "Profitez des creux locaux et de multiples prises de profits avec le Dip Analyser Trading Mode sur OctoBot pour trader sur les marchés SPOT ou futures."
sidebar_position: 6
---

# Dip Analyser Trading Mode

Le  Dip Analyser Trading Mode (ou DipAnalyserTradingMode) est conçu pour acheter sur les creux locaux et vendre les actifs achetés avec plusieurs prises de profits. Il peut être comparé à un mode de trading DCA avancé basé sur plusieurs évaluateurs [DCA trading mode](dca-trading-mode).

## Le Dip Analyser Trading Mode peut

- Diviser les take profits en plusieurs ordres de vente pour maximiser les profits
- Utiliser des ordres d'entrée au marché aux limites
- Utiliser des ordres de stop loss
- Personnaliser les prix de take profit en fonction de la force du signal du creux local
- Trader sur les marchés SPOT et futures

## Configurer les ordres
- Le Dip Analyser Trading mode peut diviser les take profits en autant d'ordres que défini dans la configuration.
- Les montants d'entrée utilisent à la fois les montants par défaut ou configurés et le multiplicateur de volume du signal d'entrée.
- Les prix des ordres de take profit sont répartis linéairement entre le prix d'entrée et le multiplicateur de prix du signal d'entrée.
- La définition d'un multiplicateur de prix de stop loss activera la création d'ordres de stop loss aux côtés des ordres de take profit.
- Les montants des ordres d'entrée peuvent être configurés en utilisant la [syntaxe des montants d'ordre](order-amount-syntax).
