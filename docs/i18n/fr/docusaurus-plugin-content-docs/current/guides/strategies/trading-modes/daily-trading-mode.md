---
title: "Mode de trading Daily"
description: "Le DailyTradingMode prend en compte chaque stratégie et évaluateur compatible et calcule la moyenne de leurs évaluations pour produire chaque mise à jour."
keywords: ["trading modes", "strategies", "octobot", "daily-trading-mode"]
slug: /guides/strategies/trading-modes/daily-trading-mode
format: md
---

Le DailyTradingMode prend en compte chaque stratégie et évaluateur compatible et calcule la moyenne de leurs évaluations pour produire
chaque mise à jour.

Il crée des ordres lorsque son état change vers
un état différent du précédent et qui n'est pas NEUTRAL.

Un état LONG déclenche un ordre d'achat. Un état SHORT déclenche un ordre de vente.

<div class="text-center">
    <iframe width="560" height="315" src="https://www.youtube.com/embed/e-GqmTfrchY?showinfo=0&amp;rel=0" 
    title="YouTube video player" frameborder="0" allow="accelerometer; autoplay; 
    clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>
</div>

Pour en savoir plus, consultez le
<a target="_blank" rel="noopener" href="https://www.octobot.cloud/en/guides/octobot-trading-modes/daily-trading-mode?utm_source=octobot&utm_medium=dk&utm_campaign=regular_open_source_content&utm_content=DailyTradingModeDocs">
guide complet du mode de trading Daily</a>.

### Mode Default
En mode Default, le DailyTradingMode annule les ordres ouverts précédemment créés
et en crée de nouveaux en fonction de son nouvel état.
Dans ce mode, les ordres d'achat comme de vente sont exclusivement créés sur signaux de stratégie et d'évaluateur.

### Mode Target profits
En mode Target profits, le DailyTradingMode n'écoute que les signaux LONG lors du trading spot
et les signaux d'augmentation de position lors du trading futures, c'est-à-dire SHORT et LONG. Lorsqu'un tel signal est reçu, il crée un ordre d'entrée
qui sera suivi d'un take profit (et éventuellement d'un stop-loss) une fois exécuté. Dans ce mode, seuls les signaux d'entrée sont
définis par la configuration de votre stratégie et de vos évaluateurs, car les cibles de take profit et de stop loss sont définies dans
la configuration du mode Target profits.
*L'utilisation du DailyTradingMode en mode Target profits est compatible avec l'historique de PNL.*

### À propos du trading futures
Le mode **Target profits** est plus adapté au trading futures, car il crée des take profits et des stop losses (lorsqu'ils sont activés)
pour clôturer les positions créées.
