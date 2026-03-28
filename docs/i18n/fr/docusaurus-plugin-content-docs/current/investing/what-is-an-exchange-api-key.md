---
title: "Qu'est-ce qu'une API Key ?"
description: "Vous vous demandez ce qu'est une API Key et pourquoi vous devriez l'utiliser avec un logiciel de trading ? Voici les réponses à vous questions."
sidebar_position: 34
---

# Qu'est-ce qu'une API Key de plateforme d'échange ?

Dans le trading de cryptomonnaies, les API Keys sont la façon la plus commune de permettre à des logiciels de trading de créer et annuler des ordres sur un compte de plateforme d'échange de façon sécurisée. Cette solution présente aussi l'avantage de ne pas nécessiter de communiquer votre adresse email ou mot de passe de connexion à Binance. 

## Les API Keys sur OctoBot
Sur OctoBot, vos API Keys sont utilisées pour exécuter une stratégie, c'est à dire:
- consulter le solde de votre portefeuille Binance
- consulter, créer et annuler des ordres de trading sur votre compte

## Les permissions
Les API Keys peuvent être configurées avec certaines permissions. Il s'agit d'un dispositif de sécurité supplémentaire permettant d'empêcher toute action non autorisée via cette API Key. Par exemple, un logiciel utilisant une API Key qui ne dispose pas des permissions de retrait ne peut pas initier de retrait des fonds du compte associé.

Pour cette raison, seules les permissions **Permettre la lecture et Activer le trading Spot et sur marge** sont nécessaires pour qu'OctoBot puisse exécuter une stratégie de trading. 

**Aucune autre permission n'est requise et nous recommandons fortement de ne pas ajouter d'autre permission aux API Keys que vous utilisez avec un logiciel de trading, que ce soit OctoBot ou un autre.**

## Comment créer votre API Key de plateforme d'échange ?
Pour vous aider à connecter votre compte de plateforme d'échange à OctoBot, nous avons créé ces guides pas à pas:
- [Guide de connexion à Binance](connect-your-binance-account-to-octobot)
- [Guide de connexion à Kucoin](connect-your-kucoin-account-to-octobot)
- [Guide de connexion à Coinbase](connect-your-coinbase-account-to-octobot)
