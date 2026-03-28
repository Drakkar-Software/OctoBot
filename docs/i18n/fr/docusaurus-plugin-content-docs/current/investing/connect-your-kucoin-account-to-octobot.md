---
title: "Se connecter à Kucoin"
description: "|"
sidebar_position: 23
---



# Connecter votre compte Kucoin à OctoBot cloud

Pour automatiser les stratégies d'investisements de votre choix sur votre propre compte Kucoin, il est nécessaire d'autoriser OctoBot à accéder à une partie de votre compte.

Cela est possible en utilisant des clés d'API ou `API Keys`. Les API Keys sont un moyen d'authentification standard et sécurisé qui est très souvent utilisé pour connecter les logiciels ensemble.

Si vous vous demandez ce qu'est une `API Key` et pourquoi OctoBot utilise cette méthode, jetez un œil  à notre [présentation des API Keys de plateformes d'échange](what-is-an-exchange-api-key).

## Connecter votre compte Kucoin grâce aux API Keys

Voici les 5 étapes simples pour connecter votre compte Kucoin à OctoBot cloud et automatiser vos stratégies d'investisements.

### 1. Connectez-vous à votre compte Kucoin

Rendez-vous sur <a href="https://www.kucoin.com/ucenter/signup?rcode=rJ2Q2T3" rel="nofollow">kucoin.com</a> et connectez-vous à votre compte (ou créez un compte).

![connection au compte kucoin](/images/guides/kucoin/kucoin-account-login.png)

### 2. Allez sur Gestion des API

Rendez-vous sur le tableau de bord de votre compte et sélectionnez "API Management".
![compte lien gestion des api](/images/guides/kucoin/account-setting-api-management.png)

### 3. Créer une nouvelle API Key

1. Cliquez sur "Create API", sélectionnez "API-Based Trading".

2. Nommez la comme vous voulez et donnez lui une passphrase. Le nom de l'API Key est uniquement visible pour vous et vous permet de vous souvenir de l'objectif de cette clé. La passphrase devra être renseignée avec les détails de l'API Key sur OctoBot cloud.

3. **Pensez à cocher l'API Restriction "Spot Trading"**

![apis liste creer nouvelle api](/images/guides/kucoin/apis-list-create-new-api.png)

![sélection de l'api name passphrase et restrictions](/images/guides/kucoin/select-api-name-passphrase-and-restrictions.png)

4. Sélectionnez l'option `Restrict to Trusted IPs Only`.

5. Cliquez sur le bouton "copier" depuis OctoBot cloud pour copier la liste blanche d'IP et collez la liste dans le champ IP whitelist, puis cliquez sur `Add`.

### 4. Sauvegarder votre clé d'API

Maintenant que votre clé d'API est nommée, a une passphrase et la permission de "Spot Trading", cliquez sur "Next"

Complétez la vérification de sécurité pour créer l'API Key.

<div style="text-align: center">

![creer api verification securite](/images/guides/kucoin/create-api-security-verification.png)

</div>

Votre clé d'API est créée. Ne pas fermer cette fenêtre tant que vous n'avez pas reporté ces informations sur OctoBot cloud.

<div style="text-align: center">

![api key kucoin créée](/images/guides/kucoin/kucoin-api-key-created.png)

</div>

### 5. Ajouter votre API Key à votre compte OctoBot cloud

Votre API key est maintenant prête à être utilisée par OctoBot !

Tout ce qu'il vous reste à faire est de copier/coller les valeurs de `API Key`, `Secret Key` et passphrase dans la configuration de votre compte Kucoin sur OctoBot cloud. Cette étape peut être réalisée au lancement d'une stratégie de trading avec un compte réel ou depuis votre profil sur [octobot.cloud](https://www.octobot.cloud/)

Remarque : Quand vous ajoutez une API Key sur OctoBot cloud, vous avez la possibilité de la nommer. Cette étape, semblable à celle sur Kucoin, permet de choisir un nom facilement identifiable pour votre configuration Kucoin.

<div style="text-align: center">

![api cree key selectionnees](/images/guides/kucoin/api-creation-completed-selected-values.png)

</div>

![ajouter api key a octobot cloud depuis start de strategie](/images/guides/kucoin/add-api-key-to-octobot-cloud-from-strategy-start.png)

<div style="text-align: center">
  <em>Ajouter une API Key au lancement d'une stratégie</em>
</div>

![ajouter api key a octobot cloud depuis profil](/images/guides/kucoin/add-api-key-to-octobot-cloud-from-profile.png)

<div style="text-align: center">
  <em>Ajouter une API Key depuis <a href="https://www.octobot.cloud/fr/account" rel="nofollow">votre profil</a></em>
</div>

Votre compte Kucoin peut maintenant être utilsié sur OctoBot cloud !

:::info
  Veuillez noter que lors du démarrage d'un bot, une partie des fonds disponibles dans le portefeuille lié à votre API Key peuvent être vendus. Cela inclut les stablecoins, les fonds en monnaie fiduciaire (comme les euros) ainsi que les cryptomonnaies échangées par la stratégie que vous avez sélectionnée. Cela fait partie de [l'optimisation de portefeuille](invest-with-your-strategy#1-optimisation-du-portefeuille).
:::

## Résolution de problèmes

### API key erronée: _Incorrect API keys_

Si vous obtenez l'erreur `Incorrect API keys`, cela généralement signifie que:

- Votre API Key, Secret Key ou passphrase n'a pas été copiée correctement depuis Kucoin
- Vous fait une erreur lors de la copie de la liste blanche d'IP
- Vous avez séléctionné le mauvais échange (assurez vous d'avoir sélectionné Kucoin)

### Trading permissions: _Incorrect API restrictions: missing spot trading_

Si vous obtenez l'erreur `Incorrect API restrictions: missing spot trading`, il est nécessaire de modifier les restrictions de votre API Key sur kucoin afin de cocher "Spot Trading", comme expliqué [en étape 3](#3-créer-une-nouvelle-api-key).

### Retraits activés: _Incorrect API restrictions: withdrawals enabled_

Si vous obtenez l'erreur `Incorrect API restrictions: withdrawals enabled`, alors vous devez décocher la permission `Transfer`. Vous pouvez le faire en modifiant les restrictions de votre API Key, comme expliqué [en étape 3](#3-créer-une-nouvelle-api-key).

### Autres questions

Si vous avez d'autres questions ou si quelque chose n'est pas clair, n'hésitez pas à contacter l'équipe de support en utilisant la chatbox en bas à droite de l'écran sur [octobot.cloud](https://www.octobot.cloud/).
