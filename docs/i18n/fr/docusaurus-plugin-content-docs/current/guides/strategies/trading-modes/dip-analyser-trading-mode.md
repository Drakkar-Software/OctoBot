---
title: "Mode de trading Dip Analyser"
description: "DipAnalyserTradingMode est un mode de trading adapté aux **marchés volatils**."
keywords: ["trading modes", "strategies", "octobot", "dip-analyser-trading-mode"]
slug: /guides/strategies/trading-modes/dip-analyser-trading-mode
format: md
---

DipAnalyserTradingMode est un mode de trading adapté aux **marchés volatils**.

Il recherche les creux locaux du marché, les pondère et achète sur ces creux. Il ne vend jamais, sauf après l'exécution d'un ordre d'achat.

Lorsqu'un **ordre d'achat est exécuté, des ordres de vente sont automatiquement créés à un prix plus élevé**
que celui de l'ordre d'achat exécuté. Le nombre d'ordres de vente créés après chaque achat est configurable.

Une configuration à risque plus élevé génère des ordres d'achat plus importants lorsque la taille des ordres n'est pas configurée.

Pour en savoir plus, consultez le
<a target="_blank" rel="noopener" href="https://www.octobot.cloud/en/guides/octobot-trading-modes/dip-analyser-trading-mode?utm_source=octobot&utm_medium=dk&utm_campaign=regular_open_source_content&utm_content=DipAnalyserTradingModeDocs">
guide complet du mode de trading Dip analyser</a>.

### Bon à savoir

- Assurez-vous que **suffisamment de fonds sont disponibles dans votre portefeuille** pour qu'OctoBot puisse placer les **ordres d'achat initiaux**.
- Les ordres de vente ne sont jamais annulés par cette stratégie, sauf si les stop losses sont activés ; il n'est donc pas conseillé de l'utiliser sur des
tendances baissières prolongées sans stop losses : des fonds pourraient rester bloqués dans des ordres de vente ouverts.
- Les ordres d'achat limites peuvent être automatiquement annulés et remplacés lorsqu'une meilleure opportunité d'achat est identifiée.

_Ce mode de trading prend en charge l'historique de PNL._
