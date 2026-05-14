---
title: "Évaluateur de signaux Telegram"
description: "Évaluateur très simple conçu comme exemple d'un évaluateur utilisant des signaux Telegram."
keywords: ["social evaluators", "sentiment", "news", "octobot", "telegram-signal-evaluator"]
slug: /guides/strategies/evaluators/social/telegram-signal-evaluator
format: md
---

Évaluateur très simple conçu comme exemple d'un évaluateur utilisant des signaux Telegram.

Se déclenche sur un signal Telegram provenant de n'importe quel groupe ou canal listé dans la configuration de cet évaluateur et dans lequel 
votre bot Telegram a été invité.

Le format de signal pour cette implémentation est : **SYMBOL[evaluation]**. Exemple : **BTC/USDT[-0.45]**.

SYMBOL doit faire partie des symboles actuellement surveillés (dans la configuration) et evaluation doit être comprise entre -1 et 1. 

Souvenez-vous qu'OctoBot ne peut voir que les messages provenant d'une
discussion/d'un groupe où son bot Telegram (dans la configuration d'OctoBot) a été invité. Gardez également à l'esprit que vous
devez désactiver le mode confidentialité de votre bot Telegram pour lui permettre de voir les messages de groupe.

Consultez la [documentation OctoBot sur l'interface Telegram](https://www.octobot.cloud/en/guides/octobot-interfaces/telegram?utm_source=octobot&utm_medium=dk&utm_campaign=regular_open_source_content&utm_content=telegramSignalEvaluator) pour plus d'informations.
