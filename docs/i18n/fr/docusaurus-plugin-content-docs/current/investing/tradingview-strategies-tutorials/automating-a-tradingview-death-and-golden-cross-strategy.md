---
title: "Stratégie Golden Cross"
description: "Apprenez à automatiser une stratégie Bitcoin de Death et Golden Cross en utilisant des alertes TradingView et OctoBot avec du trading simulé ou réel."
sidebar_position: 2
---



# Automatiser une stratégie TradingView Death et Golden Cross

Avec ce tutoriel, vous apprendrez à trader avec les Death et Golden Crosses (ou croix d'or et de mort) en utilisant deux <a href="https://www.investopedia.com/terms/e/ema.asp" rel="nofollow">Moyennes mobiles exponentielles</a> (ou EMA).  
Le concept est le suivant :

- Acheter lorsque l'EMA à court terme croise à la hausse l'EMA à long terme. Il s'agit d'une <a href="https://www.investopedia.com/terms/g/goldencross.asp" rel="nofollow">Golden Cross</a> qui est généralement un signe haussier.
- Vendre lorsque l'EMA à court terme croise vers le bas l'EMA à long terme. Il s'agit d'une <a href="https://www.investopedia.com/terms/d/deathcross.asp" rel="nofollow">Death Cross</a> qui est généralement un signe baissier.

## 1. Identifier les Death et Golden Crosses automatiquement

### 1.1 Selectionner votre marché à trader

Tout d'abord, nous voulons visualiser nos Death et Golden Crosses. Allons sur <a href="https://www.tradingview.com/?aff_id=27595" rel="nofollow">TradingView</a> et sélectionnons la paire de trading, plateforme d'échange et time frame sur lesquels nous voulons trader.

<div style={{textAlign: "center"}}>
  ![tradingview selection btcusdt
  marché](/images/guides/trading-view/tradingview-selection-btcusdt-marche.png)
</div>

Pour ce tutoriel, nous allons trader BTC/USDT sur Binance en utilisant un time frames de 5 minutes. Bien sûr, toute autre valeur fonctionnerait également.  
Précision: trader selon des Death et Golden Crosses est généralement plus performant en utilisant des time frames plus long. Le time frame de 5 minutes est uniquement utilisé ici à titre d'exemple.

### 1.2 Ajouter les indicateurs EMA

Ensuite, nous ajoutons 2 fois l'indicateur de Moyenne Mobile Exponentielle :

1. Une fois pour l’EMA à long terme
2. Une fois pour l’EMA à court terme

<div style={{textAlign: "center"}}>
  ![tradingview ajouter ema
  indicateur](/images/guides/trading-view/tradingview-ajouter-ema-indicateur.png)
</div>

### 1.3 Configurer les indicateurs EMA

Cliquez sur les `Configurations` des deux indicateurs EMA et définissez la valeur `Longueur` selon vos souhaits pour configurer vos Death et Golden Crosses.

<div style={{textAlign: "center"}}>
  ![tradingview configurer ema
  indicator](/images/guides/trading-view/tradingview-configurer-ema-indicateur.png)
</div>

Dans cet exemple, nous utiliserons les valeurs suivantes :

1. `21` pour la Longueur de l’EMA à long terme
2. `9` pour la Longueur de l’EMA à court terme

Remarque : vous pouvez également configurer le `Style` ces EMA pour les rendre plus faciles à visualiser sur le graphique.

### 1.4 Visualiser la stratégie

Les Death et Golden crosses se produisent lorsque l'EMA à long term est traversée par celle à court terme. We can now easily see what it would look like.
Les Croisements dorés se produisent lorsque les EMA à longue échance sont traversées par ceux à courte échance . Nous pouvons maintenant facilement voir ce que cela ressemblerait.

<div style={{textAlign: "center"}}>
  ![tradingview visualisation ema indicateur golden et death
  crosses](/images/guides/trading-view/tradingview-visualisation-ema-indicateur-golden-et-death-crosses.png)
</div>

Notre stratégie est prête, la seule étape restante est de créer un OctoBot pour trader lorsque ces croisements se produisent.

## 2. Créer les automatisations OctoBot pour acheter et vendre

### 2.1 Créer un OctoBot TradingView

Ouvrons un nouvel onglet et allons sur <a href="https://www.octobot.cloud/fr/dashboard" rel="nofollow">OctoBot cloud</a> pour démarrer un nouveal OctoBot TradingView.

<div style={{textAlign: "center"}}>
  ![demarrer un nouvel octobot tradingview depuis
  explorer](/images/guides/trading-view/demarrer-un-nouvel-octobot-tradingview-depuis-l-explorer.png)
</div>

**[Démarrer un bot](https://www.octobot.cloud)**

Pour ce tutoriel, nous démarrerons un bot sur Binance. Si vous avez de questions sur comment démarrer un OctoBot TradingView, consultez la section `Créer votre OctoBot TradingView` du [tutorial de trading avec TradingView](../tradingview-trading-tutorial#1-créer-votre-octobot-tradingview).

### 2.2 Créer votre automatisation d'achat

Lorsqu'une Golden Cross se produit, nous voulons que notre OctoBot achète. Pour ce tutoriel, nous achèterons en utilisant 50% des USDT de notre portefeuille.

<div style={{textAlign: "center"}}>
  ![octobot automation creer acheter
  btc](/images/guides/trading-view/octobot-automation-creer-acheter-btc.png)
</div>

### 2.3 Créer votre automatisation de vente

Lorsqu'une death cross se produit, nous voulons que notre OctoBot vende. Pour ce tutoriel, nous vendrons tous les BTC de notre portefeuille.

<div style={{textAlign: "center"}}>
  ![octobot automation creer vendre
  btc](/images/guides/trading-view/octobot-automation-creer-vendre-btc.png)
</div>

Remarque : dans ce tutoriel, nous décrivons un scénario simple en utilisant des ordres au marché, en vendant tout d'un coup et en ayant seulement une seule automatisation d'achat et vente.  
Puisqu'il n'y a pas de limite aux automatisations que vous pouvez créer, vous pouvez personnaliser cette stratégie autant que vous le souhaitez en créant d'autres automatisations d'achat et de vente.

## 3. Connecter les automatisations pour se déclencher sur les Crosses

Remarque : les étapes suivantes supposent que vous avez déjà configuré l'URL du webhook des alertes TradingView. Si ce n'est pas le cas, veuillez suivre le [guide Configurer l'URL du webhook](../tradingview-trading-tutorial#25-configurer-lurl-du-webhook).

### 3.1 Acheter lors des Golden Crosses

Ouvrez le panneau de connexion de votre automation d'achat et copiez son identifiant d'automatisation.

<div style={{textAlign: "center"}}>
  ![octobot automatisations vue connexion interface
  selectionnee](/images/guides/trading-view/octobot-automatisations-vue-connexion-interface-selectionnee.png)
</div>

<div style={{textAlign: "center"}}>
  ![octobot identifiant
  d'automatisation](/images/guides/trading-view/octobot-automatisation-identifiant.png)
</div>

Revenez à votre onglet TradingView et créez une nouvelle alerte.

<div style={{textAlign: "center"}}>
  ![creer une alerte depuis
  tradingview](/images/guides/trading-view/creer-une-alerte-depuis-tradingview.png)
</div>

<div style={{textAlign: "center"}}>
  ![tradingview creer alerte golden
  cross](/images/guides/trading-view/tradingview-creer-golden-cross-alerte.png)
</div>

Dans cette alerte :

- Sélectionnez `Croisement vers le haut` ainsi qu'EMA 9 et 21 comme Condition : c'est notre Golden Cross.
- Sélectionnez `Une fois par barre (sur clôture)` comme Déclenchement pour vérifier les Golden Crosses à chaque clôture de bougie.
- Donnez un nom à votre alerte pour l'identifier facilement plus tard.
- Remplacez la totalité de valeur de Message par l'identifiant de votre automatisation d'achat de votre onglet OctoBot.

Et voila ! Votre stratégie TradingView enverra une alerte déclenchant votre automatisation d'achat par OctoBot lorsqu'une Golden Cross sera identifiée selon vos paramètres d'EMA.

### 3.2 Vendre lors des Death Crosses

De la même manière que pour la configuration de la Golden Cross:

1. Sur votre onglet OctoBot, ouvrez le panneau de connexion de votre automatisation de vente.
2. Sur l'onglet TradingView, créez une deuxième alerte pour identifier les Death Crosses et configurez-la pour déclencher votre automatisation de vente.

<div style={{textAlign: "center"}}>
  ![tradingview creer alerte death
  cross](/images/guides/trading-view/tradingview-creer-death-cross-alerte.png)
</div>

Dans cette alerte, n'oubliez pas de :

- Sélectionner `Croisement vers le base` ainsi qu’EMA 9 et 21 comme Condition : c'est notre Death Cross.
- Sélectionner `Une fois par barre (sur clôture)` comme Déclenchement pour vérifier les Death Crosses à chaque clôture de bougie.
- Donnez un nom à votre alerte pour l'identifier facilement plus tard.
- Remplacez la totalité de valeur de Message par l'identifiant de votre automatisation de vente de votre onglet OctoBot.

## La stratégie est prête

Et c'est prêt !
Nous venons de créer une stratégie EMA de Death et Golden Cross sur TradingView et avons automatisé son trading en utilisant OctoBot. À chaque fois qu'une Death ou Golden Cross se produit sur TradingView, notre OctoBot achètera ou vendra du BTC en conséquence.

![tradingview illustration la de stratégie ema avec 2 achats et 2 ventes](/images/guides/trading-view/tradingview-ema-strategy-illustration-with-2-buy-and-2-sell.png)

![octobot tradingview illustration coté trading de la stratégie ema with avec 2 achats et 2 ventes](/images/guides/trading-view/octobot-tradingview-trading-side-of-ema-strategy-illustration-with-2-buy-and-2-sell.png)

Bien sûr, vous pouvez utiliser cette configuration pour trader toute paire crypto sur n'importe quelle plateforme d'échange en utilisant vos fonds réels ou sans risque avec des [fonds simulés](../paper-trading-a-strategy).

**[Démarrer un bot TradingView](https://www.octobot.cloud)**

Nous espérons que ce tutoriel était suffisamment clair. N'hésitez pas à nous faire savoir s'il y a quelque chose que nous devrions améliorer.

:::info
  Attention : La stratégie présentée dans ce tutoriel est uniquement destinée à
  des fins éducatives et ne constitue pas un conseil financier.
:::
