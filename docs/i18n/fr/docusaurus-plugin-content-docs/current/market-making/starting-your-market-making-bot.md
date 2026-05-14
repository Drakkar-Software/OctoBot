---
title: "Démarrer votre bot de market making"
description: "Un guide pas à pas pour démarrer votre bot OctoBot Market Making sur le marché crypto et l'exchange de votre choix et améliorer votre liquidité."
sidebar_position: 3
---

# Démarrer votre bot de market making

Pour démarrer un bot de market making, vous devrez d'abord créer un compte OctoBot Market Making.

Une fois [authentifié sur votre compte](https://market-making.octobot.cloud), la première étape consiste à sélectionner votre exchange.

## 1. Configurer votre exchange

Depuis la page [Paramètres](https://market-making.octobot.cloud/settings/), sélectionnez l'exchange sur lequel vous souhaitez améliorer votre liquidité.

![octobot market making bot select exchange](/images/guides/octobot-market-making-bot-select-exchange.png)

## 2. Saisir vos clés API d'exchange

L'étape suivante consiste à saisir les informations de la clé API du compte d'exchange qui détient vos fonds de market making. Cela est nécessaire pour qu'OctoBot Market Making puisse trader sur votre compte.

![octobot market making exchange credentials settings](/images/guides/octobot-market-making-exchange-credentials-settings.png)

Veuillez noter que les permissions `Reading and Trading` sont requises pour utiliser OctoBot Market Making. N'ajoutez jamais d'autres permissions telles que les transferts ou les retraits.

![octobot market making exchange accounts list](/images/guides/octobot-market-making-exchange-accounts-list.png)

Vos identifiants valides seront disponibles pour vos bots de market making.

## 3. Configurer votre bot

### A. Créer un nouveau bot

Une fois vos identifiants d'exchange validés, rendez-vous sur le [tableau de bord des bots](https://market-making.octobot.cloud/bots/) et démarrez un nouveau bot.

![octobot market making bots dashboard](/images/guides/octobot-market-making-bots-dashboard.png)

:::info
**Vous ne pouvez pas démarrer un nouveau bot ?** Cela signifie que votre compte n'est pas encore actif. [Contactez l'équipe](mailto:contact@octobot.cloud) ou [réservez un appel](https://cal.com/octobot.cloud/market-making-30min) pour activer votre compte.
:::

### B. Sélectionner votre exchange

Sélectionnez l'exchange sur lequel vous souhaitez exécuter votre bot, choisissez les identifiants que vous avez précédemment saisis et confirmez.

![octobot market making starting bot select exchange](/images/guides/octobot-market-making-starting-bot-select-exchange.png)

### C. Sélectionner votre marché

Sélectionnez la ou les paires de trading sur lesquelles vous souhaitez améliorer la liquidité et confirmez. Vous pouvez saisir le symbole de votre cryptomonnaie pour la trouver rapidement.

![octobot market making starting bot select pairs](/images/guides/octobot-market-making-starting-bot-select-pairs.png)

### D. Configurer le prix de référence

Configurez le prix de référence de chaque paire. La configuration du prix de référence définit la manière dont OctoBot Market Making calculera le prix qu'il utilisera comme base pour créer son carnet d'ordres.

![octobot market making starting bot select reference price](/images/guides/octobot-market-making-starting-bot-select-reference-price.png)

Il existe différentes façons de configurer un [prix de référence de market making](using-formulas-to-configure-your-market-making-reference-price) :

- **Utiliser le même exchange que celui sur lequel vous souhaitez améliorer la liquidité** : dans ce mode, la stratégie de market making utilise le prix actuel de l'exchange local pour créer son carnet d'ordres. Cette option est un bon choix si votre exchange ciblé fait partie des meilleurs exchanges pour trouver le juste prix de votre paire de trading.
- **Utiliser un exchange différent** : dans ce mode, la stratégie crée son carnet d'ordres en se basant sur le prix d'un autre exchange. C'est utile lorsqu'un autre exchange affiche généralement un prix plus à jour que votre exchange ciblé. Lorsque vous fournissez de la liquidité sur un exchange pour une paire de trading ayant un équivalent sur un exchange plus liquide, ce mode est le meilleur choix.
- **Utiliser plusieurs exchanges** : ce mode vous permet de calculer un prix cible de market making basé sur les moyennes pondérées des prix de plusieurs exchanges. C'est particulièrement utile lorsqu'aucun exchange n'a une liquidité nettement supérieure aux autres et qu'aucun choix évident ne s'impose.
- **Utiliser une tarification dynamique avec une formule** : cela vous permet d'utiliser une formule pour calculer le prix dynamiquement ou d'imposer un prix statique. C'est utile si vous souhaitez verrouiller le prix de votre marché à une valeur préconfigurée ou utiliser une formule pour calculer le prix à partir d'une valeur moyenne, ou pour imposer des niveaux de support ou de résistance.

Plus de détails sur les différentes façons de configurer un prix de référence de market making sont disponibles dans le guide [Utiliser des formules pour configurer votre prix de référence de market making](using-formulas-to-configure-your-market-making-reference-price).

![octobot market making starting bot selected reference price from binance near usdc](/images/guides/octobot-market-making-starting-bot-selected-reference-price-as-binance-near-usdc.png)

### E. Configurer votre stratégie

OctoBot Market Making vous permet de configurer votre stratégie de market making selon de nombreux paramètres.

![octobot market making starting bot quick configuration with order book preview](/images/guides/octobot-market-making-starting-bot-quick-configuration-with-order-book-preview.png)

Les paramètres de base, tels que le spread minimum et maximum et le nombre d'ordres, sont les paramètres de premier niveau et doivent toujours être pris en compte par toute stratégie de market making.

:::info
Chaque fois qu'un paramètre change, l'aperçu du carnet d'ordres de votre configuration est automatiquement mis à jour pour refléter vos modifications.
:::

De nombreux autres paramètres peuvent être configurés pour affiner les différents aspects d'une stratégie de market making, notamment la répartition des ordres, les budgets de market making, les conditions d'arrêt, et plus encore.

![octobot market making starting bot advanced configuration](/images/guides/octobot-market-making-starting-bot-advanced-configuration.png)

Il est recommandé de prendre le temps de configurer les [conditions d'arrêt](configuring-and-protecting-your-market-making-funds) afin de protéger vos fonds contre les manipulations de marché, la forte volatilité et les situations imprévues.

Une fois satisfait de votre configuration, cliquez sur `Save and continue` pour démarrer votre bot.

### F. Nommer votre bot

Vous pouvez maintenant donner un nom à votre bot pendant son démarrage.

![octobot market making starting bot and rename launch](/images/guides/octobot-market-making-starting-bot-and-rename.png)

Une fois démarré, votre bot s'affiche sur votre [tableau de bord des bots](https://market-making.octobot.cloud/bots/).

![octobot market making bots view with a running bot](/images/guides/octobot-market-making-bots-view-with-a-running-bot.png)

Vous pouvez désormais modifier sa configuration à tout moment ou l'arrêter à votre guise. Si une [condition d'arrêt](configuring-and-protecting-your-market-making-funds) est déclenchée, votre bot s'arrêtera automatiquement, annulera ses ordres ouverts et vous enverra une notification détaillant la raison de l'arrêt et la condition remplie.
