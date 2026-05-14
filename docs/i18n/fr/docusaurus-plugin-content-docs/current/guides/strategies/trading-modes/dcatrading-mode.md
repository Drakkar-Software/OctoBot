---
title: "Mode de trading DCA"
description: "Le dollar cost averaging (DCA) est un mode de trading qui peut vous aider à réduire le montant que vous payez pour vos investissements et à minimiser le risque. Au lieu d'acheter..."
keywords: ["trading modes", "strategies", "octobot", "dcatrading-mode"]
slug: /guides/strategies/trading-modes/dcatrading-mode
format: md
---

Le dollar cost averaging (DCA) est un mode de trading qui peut vous aider à réduire le montant que vous payez pour vos investissements et à
minimiser le risque. Au lieu d'acheter des investissements à un seul niveau de prix, avec le dollar cost averaging vous achetez
de plus petits montants à intervalles réguliers.

<div class="text-center">
    <div>
    <iframe width="560" height="315" src="https://www.youtube.com/embed/519pwSV1uwE?si=MT9e1Gqp9WWw45Z" 
    title="Build your own Smart DCA strategy" frameborder="0" allow="accelerometer; autoplay; 
    clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>
    </div>
</div>

Le DCA d'OctoBot va bien au-delà d'une simple technique de DCA régulière, il vous permet d'automatiser avec précision vos
conditions d'entrée et de sortie d'une manière simple, mais très puissante.

Pour en savoir plus, consultez le
<a target="_blank" rel="noopener" href="https://www.octobot.cloud/en/guides/octobot-trading-modes/dca-trading-mode?utm_source=octobot&utm_medium=dk&utm_campaign=regular_open_source_content&utm_content=DCATradingModeDocs">
guide complet du mode de trading DCA</a>.

### En résumé
- Les entrées peuvent être déclenchées soit :
    - Sur une base purement temporelle, indépendamment du prix.
    - Sur les signaux maximaux des évaluateurs activés (évaluations de 1 ou -1 uniquement). Dans ce cas, la dernière évaluation
        prévaudra lors de l'utilisation d'ordres d'entrée limites : les ordres ouverts des évaluations précédentes seront annulés.
- Les entrées peuvent être des ordres au marché ou des ordres limites.
- Une fois une entrée exécutée, vous pouvez choisir de sortir/vendre les actifs vous-même (manuellement) ou de créer automatiquement
un take profit à votre objectif de prix.
- Vous pouvez activer des stop losses pour protéger vos avoirs une fois une entrée exécutée.
- Il est également possible de répartir les entrées et les sorties en plusieurs ordres à intervalles de prix réguliers pour profiter encore davantage
de l'effet du dollar cost averaging.

Sur le long terme, le dollar cost averaging peut vous aider à réduire vos coûts d'investissement et à améliorer vos rendements en optimisant
les prix d'entrée et de sortie selon vos objectifs.

_Note : avec la configuration par défaut, le mode de trading DCA achètera pour 50 $ (ou unité de la devise de cotation : USDT pour BTC/USDT)
chaque semaine._


_Ce mode de trading prend en charge l'historique de PNL lorsque les ordres de sortie en take profit sont activés._
