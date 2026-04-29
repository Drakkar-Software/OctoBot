---
title: "FAQ"
description: "Vous avez des questions sur OctoBot cloud ? Voici les questions fréquemment posées et leurs réponses."
sidebar_position: 33
---



# Foire aux questions d'OctoBot cloud (FAQ)

## Comment puis-je tester une stratégie ou un panier de crypto ?

Sur OctoBot cloud, nous cherchons à simplifier autant que possible, et cela inclut les tests de stratégies et de paniers. En plus des performances historiques publiques, **chaque stratégie ou panier de crypto peut être testé sans risque en utilisant le [trading virtuel](paper-trading-a-strategy)**.

Cela signifie que vous pouvez exécuter n'importe quelle stratégie de trading ou panier de crypto à tout moment en utilisant des fonds virtuels avant de [démarrer l'investissement sur votre compte d'échange réel](invest-with-your-strategy). Le trading virtuel vous permet de tester les stratégies qui vous intéressent autant que vous le souhaitez, et ce, gratuitement.

[En savoir plus sur le trading virtuel](paper-trading-a-strategy)

## Comment sont calculés les profits des stratégies ?

Chaque stratégie sur OctoBot cloud est construite, exécutée et testée à l'aide d'OctoBot. Cela signifie que les performances passées de chaque stratégie sont évaluées régulièrement en utilisant des données historiques et le [backtesting d'OctoBot](/guides/octobot-usage/backtesting).

Chez OctoBot, nous croyons en la transparence. Cela signifie que parfois les stratégies peuvent devenir non rentables, car les profits dépendent de nombreux facteurs différents, y compris les conditions du marché. Si une stratégie ne génère pas de profits pendant une période donnée, vous le verrez avant de l'utiliser.

## Comment créer ma stratégie ?

OctoBot cloud vous permet de trader selon votre propre stratégie grace à [l'automatisation de stratégies TradingView](tradingview-automated-trading).

## Où sont vos fonds lorsque vous utilisez OctoBot ?

Vos fonds restent toujours sur la plateforme d'échange, sur votre propre compte d'échange.

OctoBot est un logiciel vous permettant d'appliquer une stratégie de trading ou un panier de crypto sur votre propre compte d'échange. Cela signifie qu'OctoBot envoie simplement des ordres de trading à votre compte d'échange pour acheter et vendre des actifs selon la stratégie ou le panier que vous avez sélectionné. OctoBot ne reçoit jamais ni n'envoie de fonds de la part de ses utilisateurs.

## Dépôt et retrait de fonds

La plateforme OctoBot ne détient jamais vos fonds. Lorsque vous utilisez OctoBot, vos fonds restent toujours sur le compte d'échange que vous avez sélectionné pour votre OctoBot. La stratégie d'investissement que vous avez sélectionnée fonctionnera en envoyant des ordres d'achat et de vente sur votre compte d'échange.

En conséquence, vous pouvez déposer et retirer des fonds de votre compte d'échange comme vous le feriez normalement si aucun OctoBot n'y était connecté. Si un OctoBot constate que des fonds ont été ajoutés ou retirés, il s'adaptera automatiquement et maintiendra la stratégie d'investissement que vous avez sélectionnée en fonctionnement tant que les fonds minimum requis pour exécuter cette stratégie restent disponibles.

Remarque : Si quelqu'un prétend que vous devez déplacer vos fonds vers une plateforme quelconque pour utiliser OctoBot, alors cette personne ment et tente de voler votre argent. L'équipe d'OctoBot ne vous demandera jamais de faire une telle chose.

## Combien pouvez-vous perdre d'argent au maximum ?

Cela dépend de la stratégie que vous avez sélectionnée. Dans tous les cas, vous ne pouvez jamais perdre plus que votre investissement.

Lors de l'utilisation d'OctoBot, les mêmes règles que sur les plateformes d'échange s'appliquent, ce qui signifie que vous pouvez finir par perdre des fonds, par exemple, si les événements suivants se produisent :

- Vente d'un actif à un prix inférieur à celui auquel vous l'avez acheté
- Frais de trading prélevés par la plateforme d'échange lors de l'exécution des ordres
- Problèmes liés à l'actif investi ou à la plateforme d'échange elle-même (par exemple, si la valorisation de l'actif s'effondre)

:::info
  Vous pouvez tester n'importe quelle stratégie **sans risque**, donc sans
  aucune chance de perdre des fonds, en utilisant [le trading
  virtuel](paper-trading-a-strategy).
:::

## OctoBot cloud est-il sécurisé ?

Oui, la sécurité est l'une de nos principales priorités. Lors de l'utilisation d'OctoBot cloud, les mesures de sécurité suivantes s'appliquent :

- Vos clés d'API d'échange sont stockées dans un coffre-fort crypté sécurisé. Cela signifie que même en cas de fuite des clés d'API d'échange depuis les serveurs d'OctoBot, elles ne seraient pas lisibles.
- Vos clés d'API d'échange sont configurées pour ne pouvoir être utilisées que depuis les adresses IP d'OctoBot cloud. Cela signifie que dans l'improbable cas où vos clés d'API seraient compromises (depuis OctoBot cloud ou de votre part), elles seraient refusées par l'échange.
- Les clés d'API d'OctoBot avec des droits de retrait ne peuvent pas être utilisées. OctoBot cloud refuse de stocker les clés d'API d'échange avec des autorisations de retrait (lorsque cela est techniquement possible). Cela signifie que vos fonds ne peuvent techniquement pas être retirés de votre compte d'échange par OctoBot ou par la société qui le gère.
- OctoBot repose sur des stratégies automatisées plutôt que sur des actions humaines. Cela signifie que chaque stratégie est fiable et prévisible. Vous n'avez pas besoin de faire confiance à un être humain pour exécuter correctement la stratégie.

## Puis-je utiliser le même compte de plateforme d'échange sur plusieurs OctoBots ?

Oui, vous pouvez utiliser le même compte d'échange sur plusieurs OctoBots. Chaque OctoBot opérera sur le budget que vous avez défini pour lui, à partir du portefeuille de votre compte d'échange.

## Pourquoi y a-t-il des fonds minimaux pour utiliser les stratégies de trading et les paniers de crypto ?

Il y a deux raisons pour les fonds minimaux dans les stratégies de trading et les paniers de crypto :

- **Règles de trading de l'échange**: OctoBot envoie des ordres à l'échange. Ces échanges ont des règles de trading qui imposent une taille minimale pour chaque ordre. Sur Binance, ce montant <a href="https://www.binance.com/en/trade-rule" rel="nofollow">est généralement de 5 ou 10 dollars</a>. Les stratégies tradent généralement avec une partie de votre portefeuille pour chaque ordre, cela signifie que cette partie doit être suffisamment grande pour respecter les règles de trading. C'est particulièrement vrai pour les stratégies de trading basées sur la grille, où vos fonds sont répartis en un grand nombre de petits ordres.
- **Le plan investisseur**: afin de maintenir le plan investisseur d'OctoBot cloud complètement gratuit, nous nous associons avec des échanges pour leur apporter du volume de trading. Cela signifie que nous devons exiger un montant minimum dans chaque portefeuille pour payer nos factures. Nous essayons de maintenir ce minimum aussi bas que possible, mais nous devons définir un seuil.

## Comment puis-je connecter mon compte de plateforme d'échange à OctoBot ?

Pour vous aider à connecter votre compte de plateforme d'échange à OctoBot, nous avons créé ces guides étape par étape :

- [Guide de connexion à Binance](connect-your-binance-account-to-octobot)
- [Guide de connexion à Kucoin](connect-your-kucoin-account-to-octobot)
- [Guide de connexion à Coinbase](connect-your-coinbase-account-to-octobot)
