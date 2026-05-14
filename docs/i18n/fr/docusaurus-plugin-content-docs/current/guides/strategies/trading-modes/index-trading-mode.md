---
title: "Mode de trading Index"
description: "Le mode de trading Index répartit et maintient votre portefeuille distribué entre les cryptomonnaies tradées. Il permet de maintenir un index crypto basé sur votre..."
keywords: ["trading modes", "strategies", "octobot", "index-trading-mode"]
slug: /guides/strategies/trading-modes/index-trading-mode
format: md
---

Le mode de trading Index répartit et maintient votre portefeuille distribué entre les cryptomonnaies tradées. Il permet 
de maintenir un index crypto basé sur votre sélection de coins.

Pour en savoir plus, consultez le 
<a target="_blank" rel="noopener" href="https://www.octobot.cloud/en/guides/octobot-trading-modes/index-trading-mode?utm_source=octobot&utm_medium=dk&utm_campaign=regular_open_source_content&utm_content=IndexTradingModeDocs">
guide complet du mode de trading Index</a>.

### Contenu de l'Index
L'Index est défini par les paires tradées sélectionnées par rapport à votre marché de référence dans la 
section de configuration du profil.  
Exemple :
- Votre marché de référence est USDT
- Vos paires tradées sont BTC/USDT, ETH/USDT, SOL/USDT, ADA/USDT
Alors votre index sera composé de 25 % BTC, 25 % ETH, 25 % SOL et 25 % ADA. Le pourcentage de détention de chaque coin sera calculé 
par rapport à USDT et vérifié régulièrement. Vous pouvez également spécifier un pourcentage précis pour chaque coin via une distribution personnalisée (Custom 
distribution) en utilisant l'[extension Premium OctoBot](extensions).

Lorsque vous démarrez le mode de trading Index avec une nouvelle configuration, ou si votre portefeuille actuel ne reflète pas
la cible de l'index, votre portefeuille sera automatiquement adapté pour reproduire l'index avec la meilleure
précision possible.

### Rééquilibrage de l'Index
Un rééquilibrage de l'Index est l'événement durant lequel OctoBot envoie des ordres à l'exchange pour adapter le contenu de
votre portefeuille afin de reproduire la configuration de votre Index.  
Une fois votre mode de trading Index démarré, OctoBot maintiendra le contenu de l'index en 
vérifiant automatiquement le contenu de votre portefeuille de manière régulière et déclenchera un rééquilibrage
si nécessaire.

Le contenu de votre portefeuille est vérifié tous les `Trigger period` jours configurés. Des valeurs décimales peuvent être utilisées pour vérifier plusieurs 
fois par jour. Si, lors d'une vérification de l'index, 
votre OctoBot détecte que le contenu de votre portefeuille ne respecte pas votre configuration d'index, il
déclenchera un rééquilibrage.

Si `Trigger period` est défini sur `0`, alors chaque nouveau prix de n'importe quel coin indexé déclenchera une vérification de l'index et un rééquilibrage
si les conditions sont réunies.

### Plafond de rééquilibrage (Rebalance cap)
Lors de la vérification d'un rééquilibrage, le mode de trading Index utilise également votre configuration `Rebalance cap` avant
de considérer que votre portefeuille est désynchronisé de votre configuration d'index.
Le plafond de rééquilibrage est un pourcentage d'allocation autorisé qui évite de déclencher un rééquilibrage tant que la
détention d'un coin reste dans le pourcentage de détention idéal, plus ou moins le plafond de rééquilibrage.  
Exemple :
Un index sur 3 coins avec une cible de 33,33 % par coin et un plafond de rééquilibrage de 5 % déclenchera un rééquilibrage si 
la détention de l'un de ces 3 coins représente plus de 38,33 % ou moins de 28,33 % du portefeuille

Avertissement sur les plafonds de rééquilibrage élevés : lorsque le plafond de rééquilibrage de votre index est supérieur ou égal au pourcentage de détention cible d'un coin, aucun rééquilibrage 
ne sera déclenché si vos détentions de ce coin deviennent très faibles ; les rééquilibrages ne seront déclenchés que lorsque les détentions
deviennent trop élevées. Il s'agit d'un cas particulier qui peut se produire lors de l'utilisation d'un plafond de rééquilibrage important.
Exemple :  
Prenons un index sur 10 coins utilisant une cible de 10 % pour chaque coin. Utiliser un plafond de rééquilibrage de 11 % ne déclenchera un 
rééquilibrage que si l'un de ces 10 coins représente plus de 21 % du portefeuille (10 % + 11 %). De l'autre côté : 10 % - 11 % = -1 % 
est négatif et ne peut donc pas se produire, ce qui signifie que les rééquilibrages ne seront pas déclenchés à partir de détentions plus faibles dans cette
configuration. Utiliser un plafond de rééquilibrage de 9 % déclencherait toutefois un rééquilibrage à 1 % de détention (10 % - 9 %). 

Veuillez noter que si le pourcentage détenu d'un coin est de 0 %, un rééquilibrage se déclenchera toujours, en ignorant le plafond de rééquilibrage.

### Fonds minimum
Pour utiliser le mode de trading Index, les fonds minimum requis sont le double du montant minimum d'ordre de l'exchange pour chaque 
coin tradé. Cela signifie que pour trader 3 coins sur Binance, il faut au moins 3 fois 5 $ x2, soit 30 $.  
Veuillez noter qu'il s'agit du strict minimum ; il est préférable d'avoir au moins le double de ce montant. Si le minimum est atteint, 
le mode de trading Index cessera de mettre à jour son portefeuille selon l'index jusqu'à ce que la valeur du portefeuille 
remonte au-dessus du minimum requis.

### Index OctoBot cloud
L'[extension Premium OctoBot](extensions) permet à votre OctoBot open source d'utiliser et de personnaliser les
<a target="_blank" rel="noopener" href="https://app.octobot.cloud/explore?utm_source=octobot&utm_medium=dk&utm_campaign=regular_open_source_content&utm_content=IndexTradingModeDocs">index automatiquement configurés</a> d'OctoBot cloud. 
