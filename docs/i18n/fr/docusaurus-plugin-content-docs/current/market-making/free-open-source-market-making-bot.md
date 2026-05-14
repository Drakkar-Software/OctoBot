---
title: "Bot de market making open source et gratuit"
description: "Améliorez gratuitement la liquidité de votre token sur les exchanges grâce à l'OctoBot de market making open source. Installez-le, configurez-le et exécutez-le sur votre ordinateur."
sidebar_position: 2
---

# Bot de market making open source et gratuit

L'[OctoBot Market Making](https://github.com/Drakkar-Software/OctoBot-Market-Making) open source et gratuit est une distribution du robot de trading de cryptomonnaies open source [OctoBot](https://github.com/Drakkar-Software/OctoBot). Ce logiciel d'automatisation peut être installé et utilisé gratuitement pour automatiser des stratégies de market making simples et constitue la colonne vertébrale de toutes les stratégies de cette plateforme.

![free open source octobot market making dashboard with buy and sell orders](/images/guides/free-open-source-octobot-market-making-dashboard-with-buy-and-sell-orders.png)

La version cloud d'OctoBot Market Making, disponible sur [market-making.octobot.cloud](https://market-making.octobot.cloud), est une version avancée de la distribution OctoBot Market Making, qui ajoute de nombreuses fonctionnalités telles que :

- Des stratégies de market making avancées
- Des configurations sur mesure
- Le suivi de la liquidité

## Installer l'OctoBot Market Making gratuit

### Avec Docker

```shell
docker pull drakkarsoftware/octobot:marketmaking-stable
```

### Avec Python

```shell
git clone https://github.com/Drakkar-Software/OctoBot-Market-Making
cd OctoBot-Market-Making
python -m pip install -Ur requirements.txt
python start.py
```

## Configurer la distribution OctoBot Market Making

La distribution OctoBot Market Making prend en charge plus de 15 exchanges et sa stratégie de market making peut être configurée de la manière suivante.

![free open source octobot market making strategy configuration](/images/guides/free-open-source-octobot-market-making-strategy-configuration.png)

- **Configuration de la liquidité sur l'exchange** : définissez le nombre d'ordres d'achat et de vente à inclure dans votre stratégie ainsi que la plage de prix que vos ordres doivent couvrir.
- **Maintenance du carnet d'ordres** : le bot remplace automatiquement les ordres exécutés et adapte le carnet d'ordres en fonction du prix à jour de votre paire tradée.
- **Protection contre l'arbitrage** : OctoBot Market Making protège vos fonds de l'arbitrage en utilisant les prix de l'exchange le plus liquide.

## Tester une stratégie de market making avec des fonds virtuels

![free open source octobot market making paper-trading configuration](/images/guides/free-open-source-octobot-market-making-paper-trading-configuration.png)

OctoBot Market Making est livré avec un simulateur de trading intégré pour tester les stratégies avec des fonds virtuels.

Configurez votre stratégie de market making et testez-la sans risque avec de l'argent virtuel avant de connecter votre bot à un véritable compte d'exchange.
