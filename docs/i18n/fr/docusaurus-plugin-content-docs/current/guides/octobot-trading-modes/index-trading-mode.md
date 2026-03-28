---
title: "Index trading mode"
description: "Investissez dans plusieurs cryptomonnaies en même temps et créez votre propre indice de crypto en utilisant le mode de trading Index."
sidebar_position: 3
---



# Index Trading Mode

Le Trading Mode Index (ou IndexTradingMode) est conçu pour maintenir votre portefeuille en utilisant une configuration prédéfinie de cryptomonnaies.

<div style={{textAlign: "center"}}>
  <div>
    ![index trading illustraté par un panier de crypto](/images/guides/crypto-basket.png)
  </div>
</div>

Tout comme les [paniers de cryptos d'OctoBot cloud](https://www.octobot.cloud/features/crypto-basket), Le Trading Mode Index vous permet d'investir facilement dans des ensembles de cryptomonnaies.

## L'Index Trading Mode permet de

- Répartir équitablement vos fonds en marché de référence entre les différentes crypto de votre configuration.
- Vérifier et adapter votre portefeuille si une crypto :
  - Prend une plus grande part que prévue dans votre portefeuille
  - Prend une plus petite part que prévue dans votre portefeuille
  - Est absente de votre portefeuille
- Vérifier et si besoin répartir votre portfolio à votre guise à chaque fois que vous démarrez OctoBot ou à intervalle régulier.

## Répartition des fonds
Lorsque vous démarrez un OctoBot avec le trading mode Index, celui-ci va :
1. Évaluer tous les actifs configurés dans les paires échangées de votre profil et calculer leurs ratios dans votre portefeuille
2. Si une crypto des paires échangées est absente ou présente avec un ratio incorrect, un rééquilibrage est déclenché.
3. Si un rééquilibrage est déclenché, alors vos fonds sont convertis sur le marché de référence puis répartis entre les crypto configurées.


## Utiliser les paniers de crypto OctoBot cloud
En utilisant l'[extension premium d'OctoBot](/guides/octobot-configuration/premium-octobot-extension), vous pouvez utiliser chaque panier de cryptos disponible sur OctoBot cloud directement depuis votre OctoBot open source.

<div style={{textAlign: "center"}}>
  <div>
    ![index trading illustraté par un panier de crypto](/images/guides/trading-modes/octobot-open-source-using-crypto-baskets-from-premium-extension.png)
  </div>
</div>

De cette manière, lorsque un panier de cryptos OctoBot cloud est mis à jour, par exemple si le top 20 du marché crypto change ou si une nouvelle crypto rejoint le panier de crypto d'intelligence artificielle, alors votre OctoBot open source se mettra également à jour automatiquement.

## Configurer les rééquilibrages
### Période de rééquilibrage
Votre OctoBot peut vérifier le contenu de votre portefeuille régulièrement pour s'assurer qu'il reste représentatif de l'indice configuré.


La `Trigger period` est le nombre de jours pendant lesquels votre OctoBot attend avant de revérifier le contenu de votre portefeuille par rapport au contenu idéal de l'indice.

### Seuil de rééquilibrage
Lors de la vérification du contenu de votre portefeuille, le contenu idéal de l'indice ne sera jamais rigoureusement conforme. Étant donné que les prix des cryptomonnaies changent constamment, il y aura toujours des petites différences entre vos fonds et la répartition théorique de votre indice.

Le `Rebalance cap` définit une valeur en `%` à partir de laquelle considérer qu'un ratio de fonds est désynchronisé du le ratio cible d'un indice.


**Exemple avec un indice composé de 4 cryptomonnaies : BTC, ETH, SOL et AVAX:**

Idéalement, le portefeuille contiendrait exactement 25% de chaque crypto.  
Cependant, si le prix d'AVAX augmente de 10%, il pourrait alors représenter 28% du portefeuille au lieu des 25% idéaux. Dans ce cas, lors de la prochaine vérification de rééquilibrage du portefeuille, deux résultats sont possibles:
- A. Le `Rebalance cap` est inférieur ou égal à 3% : Le ratio AVAX détenu est supérieur de 3% aux 25% idéal, un rééquilibrage est déclenché afin que les gains d'AVAX soient redistribués entre BTC, ETH et SOL.
- B. Le `Rebalance cap` est supérieur à 3% : Le ratio d'AVAX détenu reste dans la plage idéale plus ou moins la marge autorisée par le `Rebalance cap`: aucun rééquilibrage n'est nécessaire et rien ne se produit.
