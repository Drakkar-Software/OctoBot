---
title: "TradingView trading mode"
description: "Automatisez facilement vos stratégies et indicateurs de TradingView en passant des ordres sur une plateforme d'échange grâce au mode de TradingView Trading Mode"
sidebar_position: 9
---



# TradingView Trading Mode

Le TradingView Trading Mode (ou TradingViewTradingMode) est conçu pour automatiser la création d'ordres sur les plateformes d'échange en se basant sur les signaux de <a href="https://www.tradingview.com/?aff_id=27595" rel="nofollow">TradingView</a>.

<div style={{textAlign: "center"}}>
  ![tradingview automation illustrated by tradingview
  logo](/images/guides/interfaces/tradingview-automation-illustrated-by-tradingview-logo.png)
</div>

Il vous suffit d'émettre des alertes à partir de vos indicateurs ou stratégies TradingView pour trader sur n'importe quelle plateforme d'échange. Apprenez-en davantage sur la configuration de votre OctoBot pour le trading avec TradingView et la [syntaxe des alertes](/guides/octobot-interfaces/tradingview/alert-format) dans le [guide TradingView](/guides/octobot-interfaces/tradingview).

:::info
  Ces guides concernent l'utilisation de TradingView dans le cadre des [robots
  de trading OctoBot](/fr/trading-bot). Utilisez le [guide d'investisseur
  trading automatisé avec
  TradingView](/fr/investing/tradingview-automated-trading) si vous automatisez
  vos stratégies TradingView avec un [OctoBot
  TradingView](/fr/investing/tradingview-trading-tutorial) depuis
  [www.octobot.cloud](https://www.octobot.cloud/fr).
:::

## Le TradingView Trading Mode peut

- [Automatisez les signaux des indicateurs TradingView](/guides/octobot-interfaces/tradingview/automating-trading-from-an-indicator)
- [Automatisez les signaux des stratégies Pine Script de TradingView](/guides/octobot-interfaces/tradingview/automating-trading-from-a-pine-script-strategy)
- Utilisez des ordres au marché aux limites
- Créez ou annulez simplement des ordres d'achat, de vente ou des stop-loss
- Créez des ordres d'entrée avec un take profit prédéfini
- Créez des ordres d'entrée avec un stop loss prédéfini
- Créez des ordres de stop loss
- Tradez sur les marchés SPOT et Futures

## Configurer les ordres

- Chaque signal provenant de TradingView contient les détails concernant l'ordre à créer.
- La fonctionnalité `Cancel previous orders` peut être activée pour ne maintenir qu'un seul ordre par paire de trading.
- Le montant de chaque ordre peut être configuré en utilisant la [syntaxe des montants d'ordre](order-amount-syntax).
- Le prix de chaque ordre peut être configuré en utilisant la [syntaxe des prix d'ordre](order-price-syntax).
