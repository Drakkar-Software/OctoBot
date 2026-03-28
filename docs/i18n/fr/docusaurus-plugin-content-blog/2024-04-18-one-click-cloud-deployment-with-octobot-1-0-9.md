---
title: "Déploiement cloud en un clic avec OctoBot 1.0.9"
description: "OctoBot 1.0.9 est disponible ! Déployez votre OctoBot depuis le marketplace DigitalOcean et créez votre panier de crypto personnalisé."
slug: "one-click-cloud-deployment-with-octobot-1-0-9"
date: "2024-04-18"
authors: ["paul"]
tags: ["Tradingview", "Hosting", "Release"]
image: "/images/blog/one-click-cloud-deployment-with-octobot-1-0-9/octobot-1.0.9-ditigtalocean-1-click-deployment-custom-crypto-baskets.png"
---



# Déploiement cloud en un clic avec OctoBot 1.0.9

![octobot 1.0.9 ditigtalocean déploiement en 1 clic et paniers de crypto personalisables](/images/blog/one-click-cloud-deployment-with-octobot-1-0-9/octobot-1.0.9-ditigtalocean-1-click-deployment-custom-crypto-baskets.png)

## Déploiement cloud en un clic

Faire fonctionner votre robot de trading OctoBot dans le cloud n'a jamais été aussi **facile et économique** ! OctoBot est désormais disponible en tant que Droplet 1-Click sur la <a href="https://digitalocean.pxf.io/octobot-app" rel="nofollow">marketplace officielle de DigitalOcean</a>.

<div style={{textAlign: "center"}}>
  ![octobot on the digitalocean
  marketplace](/images/blog/one-click-cloud-deployment-with-octobot-1-0-9/octobot-on-the-digitalocean-marketplace.png)
</div>
En utilisant DigitalOcean, vous pouvez désormais exécuter simplement votre
propre bot de trading OctoBot dans le cloud et l'avoir disponible pour
automatiser vos stratégies de trading 100% du temps.

<div style={{textAlign: "center"}}>
  **[Deployer votre OctoBot](/guides/octobot-installation/cloud-install-octobot-on-digitalocean)**
</div>

Avoir votre OctoBot opérationnel sur DigitalOcean se fait en **un seul clic** et commence à seulement **6$ par mois** avec une configuration minimale.

## OctoBot 1.0.9

Nous sommes heureux d'annoncer la sortie d'OctoBot 1.0.9. Cette version ajoute notamment la prise en charge des [déploiements cloud en un clic](/guides/octobot-installation/cloud-install-octobot-on-digitalocean) mentionnés ci-dessus et ajoute également des Paniers Crypto personnalisés dans OctoBot tout en améliorant les modes de trading existants et en corrigeant de nombreux problèmes.

### Paniers de crypto

Tout comme les [paniers de crypto d'OctoBot cloud](https://www.octobot.cloud/features/crypto-basket), vous pouvez maintenant créer votre propre panier de crypto en utilisant Octobot et le nouvel [Index Mode Trading](/guides/octobot-trading-modes/index-trading-mode).

<div style={{textAlign: "center"}}>
  <div>
    ![panier de
    crypto](/images/blog/one-click-cloud-deployment-with-octobot-1-0-9/crypto-basket.png)
  </div>
</div>

Lorsque vous utilisez l'Index Mode Trading, votre Octobot divisera vos fonds en marché de référence entre les différentes crypto de vos paires configurées. Vous pouvez également définir un intervalle et un seuil de rééquilibrage pour personnaliser la manière dont votre Octobot doit réagir lorsque les crypto détenues dans votre panier changent de valeur.

Et bien sûr, vous pouvez utiliser le backtesting pour optimiser le contenu de vos paniers !

### Trading modes améliorés

Les trading modes DCA et TradingView ont tous deux été améliorés dans Octobat 1.0.9.

**DCA Trading Mode**

Le [DCA Trading Mode](/guides/octobot-trading-modes/dca-trading-mode) supporte maintenant un paramètre supplémentaire. En définissant le `Max asset holding` dans vos stratégies DCA, vous pouvez limiter l'exposition à un actif donné. Cela est particulièrement utile pour les configurations de DCA basée sur des évaluateurs car cela empêche votre bot de DCA d'augmenter indéfiniment votre exposition à une crypto en particulier lorsque les conditions d'achat de cette même crypto se répètent.

**TradingView Trading Mode**

<div style={{textAlign: "center"}}>
  <div>
    ![tradingview logo montrant le trading mode tradingview
    octobot](/images/blog/one-click-cloud-deployment-with-octobot-1-0-9/tradingview-logo-showing-octobot-tradingview-trading-mode.png)
  </div>
</div>

Les ordres limites et stop créés par le [Trading Mode TradingView](/guides/octobot-trading-modes/tradingview-trading-mode) sont désormais beaucoup plus flexibles.

Le Trading Mode TradingView prend maintenant en charge les [prix relatifs](/guides/octobot-trading-modes/order-price-syntax) pour les ordres de type limite et stop. Cela signifie que vous pouvez configurer vos alertes TradingView pour déclencher par exemple:

- Un ordre d'achat BTC/USDT à -10% du prix actuel
- Un ordre de vente ETH/BTC au prix actuel + 0,01 BTC
- Un stop loss BTC/USDT au prix de 35000 USDT

### Amélioration du support des échanges

- **Coinbase**: OctoBot prend désormais en charge à la fois l'ancien et le nouveau format de clé d'API Coinbase
- **MEXC**: Le trading sur MEXC est désormais beaucoup plus stable
- **Tous les échanges**: Le flux d'ordres dans OctoBot a été amélioré. Cela résout de nombreux problèmes liés à la synchronisation des ordres ainsi qu'aux erreurs lors de la création des ordres.

<div style={{textAlign: "center"}}>
  **[Mettre à jour OctoBot](/guides/octobot-installation/install-octobot-on-your-computer)**
</div>

### Liste des changements

Retrouvez l'intégralité des modifications d'OctoBot 1.0.9 sur le <a href="https://github.com/Drakkar-Software/OctoBot/blob/master/CHANGELOG.md" rel="nofollow">dépôt GitHub d'Octobot</a>.

## Le mot de la fin

Nous tenons à remercier la communauté OctoBot pour ses excellentes idées d'amélioration et son support support ainsi que pour avoir signalé bon nombre des problèmes qui ont été corrigés dans la version 1.0.9.
