---
title: "Introduction aux guides des trading modes"
description: "Découvrez les multiples façons de trader en utilisant OctoBot grâce aux trading modes basés sur le DCA, le grid trading, l'IA et TradingView"
slug: "introducing-trading-modes-guides"
date: "2024-01-03"
authors: ["guillaume"]
tags: ["Trading", "Educational"]
image: "/images/blog/introducing-trading-modes-guides/person-looking-at-his-screens-using-many-trading-strategies.jpg"
---



# Introduction aux guides des trading modes

Lorsque vous tradez avec OctoBot, vous utilisez un trading mode. Les [Trading modes](/guides/octobot-trading-modes/trading-modes) sont responsables de la création, du maintien et de l'annulation des ordres.

Les modes de trading sont un élément clé de toute stratégie commerciale et sont compatibles avec chaque [plateforme d'échange prise en charge](/guides/exchanges).


<div style={{textAlign: "center"}}>
  <div>
    ![Une personne regardant ses écrans en utilisant plusieurs stratégies de trading](/images/blog/introducing-trading-modes-guides/person-looking-at-his-screens-using-many-trading-strategies.jpg) *Un trader utilisant plusieurs stratégies de trading.*
  </div>
</div>

Sur la base de vos commentaires, nous avons créé des [guides pour chaque trading mode](/guides/octobot-trading-modes/trading-modes) afin d'expliquer clairement à quoi ils servent et comment les utiliser. Nous sommes impatients d'avoir vos commentaires sur ces guides.

## Décomposition d'une stratégie OctoBot

Une stratégie OctoBot est généralement divisée en 2 parties :

1. Le trading mode : il décide comment créer des ordres sur une plateforme d'échange, combien investir dans chaque ordre, quand les annuler.
2. Les évaluators : ils envoient des signaux au trading mode pour l'activer lorsque cela est nécessaire. On pourrait dire qu'ils "réveillent" le trading mode lorsqu'il se passe quelque chose.

Remarque : Certains trading modes, tels que ceux basés sur une grille ou les automatisations TradingView n'utilisent aucun évaluateur ; ils se "réveillent" automatiquement soit lorsqu'un ordre est exécuté soit lorsqu'ils reçoivent une notification depuis TradingView.


## Types de trading modes

Lorsque vous utilisez OctoBot à partir du [des trading bots OctoBot](https://www.octobot.cloud/trading-bot), vous avez accès à [plusieurs types de trading modes](/guides/octobot-trading-modes/trading-modes#built-in-trading-modes). Voici les principales catégories de trading modes:

- **Trading modes basés sur les statistiques**: Les entrées (et éventuellement les sorties) sont calculées à l'aide des statistiques. Cela peut provenir d'évaluateurs techniques, d'IA, des réseaux sociaux, d'événements de prix ou bien plus encore.
- **Trading modes à faible risque basés sur une grille*: Les ordres d'achat et de vente sont créés de manière déterministe selon la configuration du trading mode. Il n'y a pas de probabilité dans ces algorithmes.
- **Stratégies TradingView automatisées**: Les entrées et sorties sont créées en fonction des signaux provenant de votre compte TradingView. Dans ce mode de trading, le cœur de votre stratégie repose sur TradingView et OctoBot agit en automatisation pour synchroniser votre stratégie avec n'importe quel compte de plateforme d'échange.
