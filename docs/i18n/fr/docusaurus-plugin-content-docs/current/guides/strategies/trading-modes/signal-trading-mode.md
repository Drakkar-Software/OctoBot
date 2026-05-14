---
title: "Mode de trading Signal"
description: "SignalTradingMode est un mode de trading adapté aux marchés liquides et relativement plats. Il essaie de détecter les retournements et de les trader."
keywords: ["trading modes", "strategies", "octobot", "signal-trading-mode"]
slug: /guides/strategies/trading-modes/signal-trading-mode
format: md
---

SignalTradingMode est un mode de trading adapté aux marchés liquides et relativement plats. 
Il essaie de détecter les retournements et de les trader.  

Ce mode de trading utilise le système d'ordres du mode de trading quotidien (daily trading mode) avec des paramètres adaptés.

Avertissement : SignalTradingMode ne fonctionne que sur les marchés liquides car l'[oscillateur de Klinger](https://www.investopedia.com/terms/k/klingeroscillator.asp) 
de MoveSignalsStrategyEvaluator nécessite suffisamment de volume et une continuité des bougies pour être précis.
