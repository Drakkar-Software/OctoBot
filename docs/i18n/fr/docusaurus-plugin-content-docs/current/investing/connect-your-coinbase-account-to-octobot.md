---
title: "Se connecter à Coinbase"
description: "|"
sidebar_position: 24
---



# Connecter votre compte Coinbase à OctoBot cloud

Pour automatiser les stratégies d'investisements de votre choix sur votre propre compte Coinbase, il est nécessaire d'autoriser OctoBot à accéder à une partie de votre compte.

Cela est possible en utilisant des clés d'API ou `API Keys`. Les API Keys sont un moyen d'authentification standard et sécurisé qui est très souvent utilisé pour connecter les logiciels ensemble.

Si vous vous demandez ce qu'est une `API Key` et pourquoi OctoBot utilise cette méthode, jetez un œil  à notre [présentation des API Keys de plateformes d'échange](what-is-an-exchange-api-key).

## Connecter votre compte Coinbase grâce aux API Keys

Voici les 5 étapes simples pour connecter votre compte Coinbase à OctoBot cloud et automatiser vos stratégies d'investisements.

### 1. Connectez-vous à votre compte Coinbase

Rendez-vous sur <a href="https://login.coinbase.com/signin" rel="nofollow">coinbase.com</a> et connectez-vous à votre compte (ou créez un compte).

![connection au compte coinbase](/images/guides/coinbase/coinbase-account-login.png)

### 2. Allez sur Gestion des API

Rendez-vous sur la configuration de votre compte en cliquant sur l'icone de votre compte et sélectionnez "Settings".
![compte lien gestion des api](/images/guides/coinbase/account-setting-api-management.png)

### 3. Créer une nouvelle API Key

Scrollez vers le bas si nécessaire et cliquez sur "API".

![setting du compte cliquer sur api](/images/guides/coinbase/account-setting-api-management-click-api.png)

Cliquez sur "Create API Key with Coinbase Developer Platform (Recommended)".

![apis liste creer nouvelle api](/images/guides/coinbase/apis-list-create-new-api.png)

1. Nommez la comme vous voulez. Le nom de l'API Key est uniquement visible pour vous et vous permet de vous souvenir de l'objectif de cette clé.

2. Sélectionnez le portefeuille que vous souhaitez utiliser avec votre OctoBot. Remarque : le portefeuille « Default » (par défaut) de Coinbase contient généralement vos fonds sur la version standard (non Avancée) de Coinbase. Si vous souhaitez utiliser d’autres fonds, veuillez transférer vos actifs vers un autre portefeuille Coinbase et le sélectionner avec votre API Key.

3. **Pensez à cocher l'API-specific restriction "Trading"**.

![sélection de l'api name restrictions](/images/guides/coinbase/select-api-name-and-restrictions.png)

4. Cliquez sur le bouton "copier" depuis OctoBot cloud pour copier la liste blanche d'IP et collez la liste dans le champ `IP whitelist`.

### 4. Sauvegarder votre clé d'API

Maintenant que votre clé d'API est nommée, a la permission de "Trading" et la liste blanche d'IP est configurée, cliquez sur "Create & download".  
Complétez la vérification de sécurité pour créer l'API Key.

Votre clé d'API est créée. Ne pas fermer cette fenêtre tant que vous n'avez pas reporté ces informations sur OctoBot cloud.

<div style="text-align: center">

![api key coinbase créée](/images/guides/coinbase/coinbase-api-key-created.png)

</div>

Note: Coinbase va vous demander de télécharger un fichier contenant les détails de la clé d'API. Ce téléchargement n'est pas nécessaire, ne téléchargez pas ce fichier ou supprimez le de votre ordinateur si vous l'avez téléchargé.

### 5. Ajouter votre API Key à votre compte OctoBot cloud

Votre API key est maintenant prête à être utilisée par OctoBot !

Tout ce qu'il vous reste à faire est de copier/coller les valeurs de `API Key`, `Secret Key` et passphrase dans la configuration de votre compte Coinbase sur OctoBot cloud. Cette étape peut être réalisée au lancement d'une stratégie de trading avec un compte réel ou depuis votre profil sur [octobot.cloud](https://www.octobot.cloud/)

Remarque : Quand vous ajoutez une API Key sur OctoBot cloud, vous avez la possibilité de la nommer. Cette étape, semblable à celle sur Coinbase, permet de choisir un nom facilement identifiable pour votre configuration Coinbase.

<div style="text-align: center">

![api cree key selectionnees](/images/guides/coinbase/api-creation-completed-selected-values.png)

</div>

![ajouter api key a octobot cloud depuis start de strategie](/images/guides/coinbase/add-api-key-to-octobot-cloud-from-strategy-start.png)

<div style="text-align: center">
  <em>Ajouter une API Key au lancement d'une stratégie</em>
</div>

![ajouter api key a octobot cloud depuis profil](/images/guides/coinbase/add-api-key-to-octobot-cloud-from-profile.png)

<div style="text-align: center">
  <em>Ajouter une API Key depuis <a href="https://www.octobot.cloud/fr/account" rel="nofollow">votre profil</a></em>
</div>

Votre compte Coinbase peut maintenant être utilsié sur OctoBot cloud !

:::info
  Veuillez noter que lors du démarrage d'un bot, une partie des fonds disponibles dans le portefeuille lié à votre API Key peuvent être vendus. Cela inclut les stablecoins, les fonds en monnaie fiduciaire (comme les euros) ainsi que les cryptomonnaies échangées par la stratégie que vous avez sélectionnée. Cela fait partie de [l'optimisation de portefeuille](invest-with-your-strategy#1-optimisation-du-portefeuille).
:::

## Résolution de problèmes

### API key erronée: _Incorrect API keys_

Si vous obtenez l'erreur `Incorrect API keys`, cela généralement signifie que:

- Votre API Key ou Secret Key n'a pas été copiée correctement depuis Coinbase
- Vous fait une erreur lors de la copie de la liste blanche d'IP
- Vous avez séléctionné le mauvais échange (assurez vous d'avoir sélectionné Coinbase)
- Faut-il utiliser une clé ECDSA ou Ed25519 ? Vous pouvez utiliser celle de votre choix. Les deux formats ECDSA et Ed25519 sont supportés.

### Trading permissions: _Incorrect API restrictions: missing spot trading_

Si vous obtenez l'erreur `Incorrect API restrictions: missing spot trading`, il est nécessaire de modifier les restrictions de votre API Key sur coinbase afin de cocher "Trade", comme expliqué [en étape 3](#3-créer-une-nouvelle-api-key).

### Retraits activés: _Incorrect API restrictions: withdrawals enabled_

Si vous obtenez l'erreur `Incorrect API restrictions: withdrawals enabled`, alors vous devez décocher la permission `Transfer`. Vous pouvez le faire en modifiant les restrictions de votre API Key, comme expliqué [en étape 3](#3-créer-une-nouvelle-api-key).

### Autres questions

Si vous avez d'autres questions ou si quelque chose n'est pas clair, n'hésitez pas à contacter l'équipe de support en utilisant la chatbox en bas à droite de l'écran sur [octobot.cloud](https://www.octobot.cloud/).
