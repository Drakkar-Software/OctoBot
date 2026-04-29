---
title: "Syntaxe des montants d''ordres"
description: "Configurez la taille de vos ordres OctoBot en fonction d'un pourcentage de votre portefeuille, d'une évolution ou même d'un montant fixe."
sidebar_position: 10
---


# La syntaxe des montants d'ordres


Avec OctoBot, vous pouvez dimensionner vos ordres en fonction de différents facteurs tels que la valeur de votre portefeuille, utiliser des montants constants ou qui évoluent en fonction de la croissance de vos gains.

Les montants d'ordres peuvent être configurées dans la configuration du mode de trading, dans les paramètres du profil.

Note : vous pouvez également laisser la configuration du montant de l'ordre vide et les modes de trading utiliseront un pourcentage de votre portefeuille (calculé en fonction de votre niveau de risque) lorsque aucune valeur n'est configurée.

:::info
  Dans la syntaxe des montants d'ordres, `%X` est toujours équivalent à `X%`. Par conséquent, l'utilisation de `%s` ou `s%` est strictement identique. Cela est vrai pour chaque identifiant à 2 caractères.
:::

## Montants constants 
Montants qui restent toujours constants.

### Montant fixes en devise de base
Un montant statique à utiliser dans chaque ordre, en devise de base.

> Utiliser `0.1` pour trader 0.1 BTC à chaque ordre BTC/USD.

### Montant fixes en devise de quotation: q
Un montant statique à utiliser dans chaque ordre, en devise de quotation.

> Utiliser `100q` pour trader l'équivalent de 100 USD de BTC à chaque ordre BTC/USD.

## Montants évolutifs
Des montants qui varient en fonction de la valeur totale du portefeuille. Les montants évolutifs sont utiles pour réinvestir les bénéfices.


### Pourcentage d'actifs du symbole tradé: s%
Un pourcentage de la valeur combinée des actifs associés au symbole tradé.

> Utiliser `12s%` pour trader 12 % de la valeur cumulée des avoirs en BTC et USDT lors du trading en BTC/USDT. 

Note : contrairement à `t%`, `s%` ignore les avoirs d'autres paires de trading.


### Pourcentage total d'actifs tradés: t%
Un pourcentage des avoirs combinés associés à chaque paire de trading configurée.

> Utiliser `12t%` pour trader 12 % de la valeur des avoirs disponibles en BTC, ETH, SOL et USDT lors du trading de BTC/USDT tout en tradant avec ETH et SOL dans d'autres paires de trading. 

`t%` ignore les actifs détenus qui ne sont pas associés aux paires de trading actuellement en cours. 

:::info
  Le pourcentage total d'actifs tradés est particulièrement utile pour maintenir une taille d'ordre évolutif dans le temps indépendamment des autres paires de trading. Cela permet d'ignorer les autres actifs qui peuvent se trouver dans le portefeuille mais qui ne doivent pas être tradés.
:::

## Montants variables
Des montants qui changent après chaque ordre d'achat ou vente. Les montants variables peuvent être utiles pour acheter moins lorsque les fonds disponibles sont réduits par exemple.

### Total des avoirs en actif: %
Un pourcentage du total des avoirs du portefeuille concernant l'actif tradé

> Utiliser `2%` pour trader 2% du total des avoirs portefeuille liés à l'actif tradé. 

Ici, les avoirs totaux du portefeuille désignent votre détention de l'actif à acheter ou à vendre. Il s'agirait d'USDT dans le cas des ordres d'achat BTC/USDT. 

:::info
  Lorsque vous utilisez le total des avoirs en actif, une fois qu'un ordre est exécuté et que le total des avoirs en actif tradé est réduit, le même pourcentage créera des ordres suivants plus petits.
:::

### Avoirs disponibles de l'actif: a%
Un pourcentage des avoirs disponibles de l'actif tradé.

> Utiliser `12a%` pour trader 12% des avoirs disponibles du portefeuille liés à l'actif tradé. 

De manière similaire à `%`, ici les avoirs désignent votre détention de l'actif utilisé pour acheter ou vendre. La différence est que `a%` ne comptera que les fonds disponibles, c'est-à-dire les fonds qui ne sont pas déjà bloqués dans des ordres en cours.

### Pourcentage de position: p%
Un pourcentage de la position courante du symbol donné.

> Utiliser `20p%` pour trader avec 20% de la valeur totale de la position ouverte. 

_Disponible uniquement en trading de futures._
