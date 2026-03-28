---
title: "Syntaxe des prix d''ordres"
description: "Configurez les prix de vos ordres OctoBot en utilisant un pourcentage du prix actuel, un prix fixe ou une différence par rapport au prix actuel."
sidebar_position: 11
---


# Syntaxe des prix d'ordres

En utilisant OctoBot, vous pouvez fixer le prix vos ordres de différentes manières en utilisant une valeur fixe ou une valeur relative au prix actuel d'une crypto.

Les prix des ordres peuvent être configurés dans la configuration de votre trading mode, dans les paramètres du profil.


## Price constant
Un prix qui reste toujours constant.

> Utilisez `50000` pour définir le prix de votre ordre exactement à "50000" USDT lors du trading BTC/USDT par exemple.

## Delta de prix: d
Une valeur qui augmente ou diminue le cours actuel d'une valeur prédéfinie.

> Utilisez `100d` pour définir le prix de votre ordre à 100 de plus que le cours actuel. Par exemple, si le cours actuel est "50000", alors le prix de l'ordre serait de "50100".

> Utilisez `-400d` pour définir le prix de votre ordre à 400 de moins que le cours actuel. Par exemple, si le cours actuel est "50000", alors le prix de l'ordre serait de "49600".

## Pourcentage de prix: %
Pourcentage d'augmentation ou réduction par rapport au cours actuel.

> Utilisez `10%` pour définir le prix de votre ordre à 10% de plus que le cours actuel. Par exemple, si le cours actuel est "50000", alors le prix de l'ordre serait "55000".

Utilisez `-25%` pour définir le prix de votre ordre à 25% de moins que le cours actuel. Par exemple, si le cours actuel est "50000", alors le prix de l'ordre serait "37500".
