---
title: "DCA trading mode"
description: "Optimisez votre stratégie d'investissement en utilisant le trading mode Dollar Cost Averaging avec des achats programmés ou basés sur des indicateurs"
sidebar_position: 2
---



# Trading mode DCA

Le trading mode DCA (ou DCATradingMode) est conçu pour acheter et vendre selon une stratégie de [Smart Dollar cost averaging](/blog/smart-dca-making-of). 

<div style={{textAlign: "center"}}>
    ![dca trading illustrated by a man watering a plant growing money](/images/guides/dca-trading-illustrated-by-a-man-watering-a-plant-growing-money.png)
</div>

Il vous permet d'optimiser vos prix d'entrée et de sortie en fonction de votre configuration.

## Le trading mode DCA peut
- Acheter régulièrement
- Acheter lorsque les évaluateurs signalent une opportunité d'achat
- Créer plusieurs ordres d'achat à des prix différents
- Créer automatiquement un ou plusieurs ordres de take profit après chaque achat
- Créer automatiquement un ou plusieurs ordres stop loss après chaque achat
- Être utilisé pour trader sur les marchés SPOT et Futures

## DCA basé sur le temps
En utilisant le Trigger mode `Time based`, le trading mode DCA créera des ordres d'entrée (achat) régulièrement en fonction de la `Trigger period` configurée.

## DCA basé sur les évaluateurs
En utilisant le trigger mode `Maximum evaluators signals based`, le trading mode DCA créera des ordres d'entrée (achat) à chaque fois qu'une nouvelle valeur maximale d'évaluateur est reçue. Une valeur maximale d'évaluateur est une valeur de `-1` ou `1`.
Avec ce trigger mode, vous pouvez déclencher des ordres DCA basés sur les signaux des évaluateurs techniques, les signaux provenant de Telegram, ChatGPT ou tout autre indicateur que vous activez. Veuillez noter qu'une valeur d'évaluateur `-1` ou `1` est requise ; toute autre valeur sera ignorée.

## Configurer les ordres
- Le trading mode DCA peut créer des ordres d'entrée (achat) sous forme d'ordres au marché ou à cours limité. Lors de l'utilisation d'ordres à cours limité, le paramètre `Limit entry percent difference` permet de définir la différence de prix en % pour calculer le prix de l'ordre d'achat.
- Des ordres secondaires peuvent également être activés. Il peut y en avoir autant que configurés et ils peuvent avoir un prix et un montant différents des ordres initiaux.
- Des ordres de take profit (vente) peuvent être activés pour créer automatiquement des ordres de vente lorsque les ordres d'entrée sont remplis.
- Des ordres stop loss peuvent être activés pour créer automatiquement des ordres stop loss lorsque les ordres d'entrée sont remplis.
- De la même manière que les ordres secondaires, les vente (take profit et stop loss) peuvent également être séparées en plusieurs ordres utilisant différents prix. Lorsqu'ils sont activés, le montant initial sera réparti uniformément entre les ordres de vente.
- Chaque montant d'ordre d'entrée et de sortie peut être configuré en utilisant la syntaxe des [montants des ordres](order-amount-syntax).
Cycle des ordres d'entrées : lorsque `Cancel open orders on each entry` est activé, un seul ordre d'entrée (et ses ordres secondaires si ils existent) est autorisé pour chaque paire tradée. Cela signifie que la réception d'un nouveau signal lorsqu'il existe déjà des ordres d'entrée non executés annulera d'abord les ordres d'entrée ouverts avant de créer des ordres associées à ce nouveau signal. En revanche, lorsque cette option est désactivée, plusieurs ordres d'entrée provenant de signaux différents peuvent coexister car le trading mode ne les annulera pas automatiquement.
- `Enable initialization entry orders`: Ce paramètre active ou désactive la création systématique d'ordres d'entrées lorsque bot démarre, et ce indépendamment des conditions de marché.
- La part maximum du portefeuille allouée à une crypto en particulier peut etre limitée avec le paramètre `Max asset holding`. Par exemple, un "Max asset holding" de 30% signifie que le trading mode DCA n'achetera plus de BTC si la part de BTC du portefeuille dépasse 30% de sa valeur totale.

:::info
  Pour le moment, lors de l'utilisation du trading de futures, le trading mode DCA ne prend en charge que les positions longues. Il ne créera pas de positions courtes.
:::

## Health check
Activer le Health check dans le trading mode DCA garantira qu'il n'y a pas d'actifs au sein des paires de trading qui restent sans ordres de vente.

Cela est utile pour s'assurer que la stratégie DCA reste cohérente même lors du redémarrage du bot ou si votre OctoBot a été hors ligne pendant un certain temps.

Par exemple, en tradant BTC/USDT et ETH/USDT, si le bot constate que de l'ETH se trouve dans le portefeuille et n'est pas inclus dans un ordre de vente, alors il considérera que cet ETH doit être vendu et le vendra contre des USDT avec un ordre au marché.

## Exemples d'utilisation du trading mode DCA
De nombreuses stratégies OctoBot cloud sont construites en utilisant le trading mode DCA.

- Dans notre [Smart DCA making of](/blog/smart-dca-making-of), nous expliquons le processus de conception de certaines des stratégies OctoBot cloud.

- En [tradant avec ChatGPT](chatgpt-trading), vous pouvez également utiliser le trading mode DCA pour la gestion des ordres.
