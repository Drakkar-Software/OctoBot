---
title: "Se connecter à Binance"
description: "|"
sidebar_position: 22
---



# Connecter votre compte Binance à OctoBot cloud

Pour automatiser les stratégies d'investissement de votre choix sur votre propre compte Binance, il est nécessaire d'autoriser OctoBot à accéder à une partie de votre compte.

Cela est possible en utilisant des clés d'API ou `API Keys`. Les API Keys sont un moyen d'authentification standard et sécurisé qui est très souvent utilisé pour connecter les logiciels ensemble.

Si vous vous demandez ce qu'est une `API Key` et pourquoi OctoBot utilise cette méthode, jetez un œil  à notre [présentation des API Keys de plateformes d'échange](what-is-an-exchange-api-key).

## Connecter votre compte Binance grâce aux API Keys

Voici les 7 étapes simples pour connecter votre compte Binance à OctoBot cloud et automatiser vos stratégies d'investissement.

### 1. Connectez-vous à votre compte Binance

Rendez-vous sur <a href="https://accounts.binance.com/en/register?ref=528112221" rel="nofollow">binance.com</a> et connectez-vous à votre compte (ou créez un compte).

![connection au compte binance](/images/guides/binance/binance-account-authentification.png)

### 2. Allez sur Gestion des API

Sélectionnez "Compte" et "Gestion des API" depuis votre Tableau de bord ou "Gestion des API" depuis le menu déroulant supérieur droit de votre icône de profil.
![compte lien gestion des api](/images/guides/binance/compte-lien-gestion-des-api.png)

![compte lien gestion des api depuis navbar](/images/guides/binance/compte-lien-gestion-des-api-depuis-navbar.png)

### 3. Créer une nouvelle API Key

Cliquez sur "Créer une API", sélectionnez "Générée par le système" et nommez la comme vous voulez. Le nom de l'API Key est uniquement visible pour vous et vous permet de vous souvenir de l'objectif de cette clé.
![apis liste creer nouvelle api](/images/guides/binance/apis-liste-creer-nouvelle-api.png)

![selection api type](/images/guides/binance/selection-api-type.png)

![selection nom de api](/images/guides/binance/selection-nom-api.png)

### 4. Vérification de sécurité

Complétez la vérification de sécurité pour créer l'API Key.
![creer api verification securite](/images/guides/binance/creer-api-verification-securite.png)

### 5. Ajouter la permission de trader et la liste blanche d'IP

Votre API Key est maintenant créée !

La dernière étape sur Binance est l'ajout de la permission de trading afin qu'OctoBot soit en mesure de créer et annuler des ordres sur ce compte en utilisant cette API Key. Pour ce faire :

1. Sélectionnez "Modifier les restrictions"

2. Choisissez "Restreindre l'accès aux adresses IP de confiance uniquement"

3. Cliquez sur le bouton "copier" depuis OctoBot cloud pour copier la liste blanche d'IP

4. Collez la liste dans le champ qui vient d'apparaître

5. Cliquez sur "Confirmer". 

6. Cochez "Activer le trading Spot et sur marge". 

7. Enfin cliquez sur "Sauvegarder".

![api cree modifier restrictions](/images/guides/binance/api-cree-modifier-restrictions.png)

![api cree ajouter trading permission](/images/guides/binance/api-cree-ajouter-trading-permission.png)

![api cree ajouter trading permission sauvegarder](/images/guides/binance/api-cree-ajouter-trading-permission-sauvegarder.png)

![api restreindre aux ips de confiance](/images/guides/binance/api-restreindre-ips-de-confiance.png)

Note: Toutes les permissions en dehors de "Permettre la lecture" et "Activer le trading Spot et sur marge" doivent rester décochée.

### 7. Ajouter votre API Key à votre compte OctoBot cloud

Votre API key est maintenant prête à être utilisée par OctoBot !

Tout ce qu'il vous reste à faire est de copier/coller les valeurs de `API Key` et `Secret Key`
dans la configuration de votre compte Binance sur OctoBot cloud. Cette étape peut être réalisée au lancement d'une stratégie de trading avec un compte réel ou depuis votre profil sur [octobot.cloud](https://www.octobot.cloud/)

Remarque : Quand vous ajoutez une API Key sur OctoBot cloud, vous avez la possibilité de la nommer. Cette étape, semblable à celle sur Binance, permet de choisir un nom facilement identifiable pour votre configuration Binance.
![api cree key selectionnees](/images/guides/binance/api-cree-key-selectionnees.png)

![ajouter api key a octobot cloud depuis start de strategie](/images/guides/binance/ajouter-api-key-a-octobot-cloud-depuis-start-de-strategie.png)

<div style="text-align: center">
  <em>Ajouter une API Key au lancement d'une stratégie</em>
</div>

![ajouter api key a octobot cloud depuis profil](/images/guides/binance/ajouter-api-key-a-octobot-cloud-depuis-profil.png)

<div style="text-align: center">
  <em>Ajouter une API Key depuis <a href="https://www.octobot.cloud/fr/account" rel="nofollow">votre profil</a></em>
</div>

Votre compte Binance peut maintenant être utilsié sur OctoBot cloud !

:::info
  Veuillez noter que lors du démarrage d'un bot, une partie des fonds disponibles dans le portefeuille lié à votre API Key peuvent être vendus. Cela inclut les stablecoins, les fonds en monnaie fiduciaire (comme les euros) ainsi que les cryptomonnaies échangées par la stratégie que vous avez sélectionnée. Cela fait partie de [l'optimisation de portefeuille](invest-with-your-strategy#1-optimisation-du-portefeuille).
:::

## Résolution de problèmes

### API key erronée: _Incorrect API keys_

Si vous obtenez l'erreur `Incorrect API keys`, cela généralement signifie que:

- Votre API Key ou Secret Key n'a pas été copiée correctement depuis Binance
- Vous fait une erreur lors de la copie de la liste blanche d'IP
- Vous avez séléctionné le mauvais échange (assurez vous d'avoir sélectionné Binance)

### Trading permissions: _Incorrect API restrictions: missing spot trading_

Si vous obtenez l'erreur `Incorrect API restrictions: missing spot trading`, il est nécessaire de modifier les restrictions de votre API Key sur binance afin de cocher "Activer le trading Spot et sur marge", comme expliqué [en étape 6](#6-ajouter-la-permission-de-trader).

### Retraits activés: _Incorrect API restrictions: withdrawals enabled_

Si vous obtenez l'erreur `Incorrect API restrictions: withdrawals enabled`, alors vous devez décocher la permission `Activer les retraits`. Vous pouvez le faire en modifiant les restrictions de votre API Key, comme expliqué [en étape 6](#6-ajouter-la-permission-de-trader).

### Autres questions

Si vous avez d'autres questions ou si quelque chose n'est pas clair, n'hésitez pas à contacter l'équipe de support en utilisant la chatbox en bas à droite de l'écran sur [octobot.cloud](https://www.octobot.cloud/).
