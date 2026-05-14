---
title: "Mode de trading Profile Copy"
description: "Le mode de trading Profile Copy copie automatiquement les positions de trading d'un ou plusieurs profils d'exchange (tels que les profils de traders Polymarket) vers votre propre..."
keywords: ["trading modes", "strategies", "octobot", "profile-copy-trading-mode"]
slug: /guides/strategies/trading-modes/profile-copy-trading-mode
format: md
---

## ProfileCopyTradingMode

Le mode de trading Profile Copy copie automatiquement les positions de trading d'un ou plusieurs profils d'exchange (tels que les profils de traders Polymarket) vers votre propre compte. Il surveille les profils sélectionnés en temps réel et réplique leur distribution de portefeuille, vous permettant de reproduire automatiquement les stratégies de traders performants.

Ce mode de trading est particulièrement utile pour les marchés de prédiction comme Polymarket, où vous pouvez suivre les meilleurs traders et copier automatiquement leurs positions avec votre propre allocation de capital.

### Comment démarrer

1. **Configurez votre exchange** : ajoutez et configurez votre exchange (par exemple Polymarket) dans votre profil OctoBot. Assurez-vous que vos identifiants d'exchange sont correctement configurés.

2. **Trouvez les IDs de profils d'exchange** : vous devez identifier les IDs de profils que vous souhaitez copier. Pour Polymarket, ils se trouvent généralement dans l'URL du profil ou dans le classement (leaderboard). Par exemple, une URL de profil Polymarket peut être `https://polymarket.com/profile/0x1234...`, où `0x1234...` est l'ID du profil.

3. **Configurez l'allocation de portefeuille** : définissez quelle part de votre portefeuille doit être allouée à la copie de chaque profil. Assurez-vous que l'allocation totale ne dépasse pas 100 % de votre portefeuille.

4. **Démarrez le trading** : une fois configuré, OctoBot commencera à surveiller les profils sélectionnés et ajustera automatiquement votre portefeuille pour correspondre à leurs positions.

### Paramètres de configuration

#### Exchange Profile IDs

Une liste d'identifiants de profils d'exchange à copier. Chaque ID de profil doit être un identifiant valide sur l'exchange ciblé.

**Exemple** : pour copier deux profils Polymarket, vous saisiriez :
- `0x1234567890abcdef1234567890abcdef12345678`
- `0xabcdefabcdefabcdefabcdefabcdefabcdefabcd`

Vous pouvez copier plusieurs profils simultanément. L'allocation de portefeuille sera répartie entre tous les profils selon le paramètre *Per Exchange Profile Portfolio Ratio*. Les IDs de profils sont spécifiques à chaque exchange (par exemple, Polymarket utilise des adresses Ethereum).

#### Per Exchange Profile Portfolio Ratio

Le pourcentage de la valeur totale de votre portefeuille à allouer à la copie de chaque profil d'exchange. Cette valeur est appliquée à chaque profil de la liste *Exchange Profile IDs*.

**Exemple** : si vous avez 2 profils et que vous définissez ce paramètre à 30 %, chaque profil reçoit 30 % de votre portefeuille (total : 60 %). Si vous avez 1 profil et que vous définissez ce paramètre à 50 %, ce profil reçoit 50 % de votre portefeuille.

**Important** : l'allocation totale (nombre de profils × ratio par profil) ne doit pas dépasser 100 %. OctoBot le vérifie et empêche les configurations invalides.

**Exemple de validation** :
- 3 profils × 35 % chacun = 105 % → **Invalide** (dépasse 100 %)
- 3 profils × 30 % chacun = 90 % → **Valide**
- 2 profils × 50 % chacun = 100 % → **Valide**

#### Allocation Padding

Le pourcentage de marge (padding) autorisé au-delà de l'allocation de portefeuille configurée par profil. Cela permet au mode de trading d'utiliser une part plus importante de votre portefeuille que ce qui était initialement configuré lorsque le profil copié ouvre des positions supplémentaires.

**Exemple** : si vous définissez *Per Exchange Profile Portfolio Ratio* à 50 % et *Allocation Padding* à 20 %, l'allocation maximale effective pour ce profil peut atteindre jusqu'à 60 % (50 % × 1,2). C'est utile lorsque le profil copié augmente son nombre de positions tradées au fil du temps.

**Cas d'usage** :
- Définir à `0%` pour des limites d'allocation strictes (recommandé pour les stratégies conservatrices)
- Définir à `20-50%` pour autoriser de la flexibilité lorsque le profil copié étend son portefeuille
- Des valeurs plus élevées offrent plus de flexibilité mais augmentent le risque de sur-allocation

**Important** : la marge ne permet qu'une expansion au-delà du ratio configuré.

#### New Position Only

*Non pris en charge sur Polymarket*

Lorsque ce paramètre est activé, seules les positions ouvertes après le démarrage d'OctoBot sont prises en compte pour la copie. Les positions existantes dans les profils suivis sont ignorées.

**Cas d'usage** :
- Définir à `true` pour ne copier que les nouveaux trades effectués par le profil après que vous avez commencé à le suivre
- Définir à `false` pour copier l'intégralité du portefeuille actuel du profil, y compris les positions ouvertes avant que vous ne commenciez à le suivre

#### Unrealized PnL Percent

Filtre les positions selon leur ratio de profit/perte non réalisé par rapport à leur collatéral. Les valeurs sont exprimées sous forme de ratios décimaux (0.1 = 10 %).

**Minimum Unrealized PnL Percent** : ne copier que les positions ayant au moins ce ratio de profit/perte non réalisé. Par exemple, définir à `0.05` pour filtrer les positions perdantes et ne copier que les positions ayant au moins 5 % de profit non réalisé, ou définir à `0.1` pour ne copier que les positions ayant au moins 10 % de profit non réalisé.

**Maximum Unrealized PnL Percent** : ne copier que les positions ayant au plus ce ratio de profit/perte non réalisé. Par exemple, définir à `0.5` pour éviter de copier les positions ayant plus de 50 % de profit non réalisé (potentiellement trop risquées), ou définir à `0.2` pour plafonner à 20 % de profit non réalisé et limiter l'exposition aux positions très profitables.

Définissez l'un ou l'autre paramètre à `0` pour désactiver ce filtre.

#### Mark Price

Filtre les positions selon leur mark price (prix de marché actuel). Utile pour filtrer les positions par fourchette de prix.

**Minimum Mark Price** : ne copier que les positions dont le mark price est supérieur ou égal à cette valeur. Par exemple, définir à `0.5` pour se concentrer sur les marchés à plus forte valeur et ne copier que les positions sur des marchés cotés à 0,50 $ ou plus, ou définir à `0.1` pour filtrer les positions très bon marché.

**Maximum Mark Price** : ne copier que les positions dont le mark price est inférieur ou égal à cette valeur. Par exemple, définir à `0.8` pour se concentrer sur les marchés à plus faible valeur et ne copier que les positions sur des marchés cotés à 0,80 $ ou moins, ou définir à `0.9` pour filtrer les positions proches de la certitude.

Définissez l'un ou l'autre paramètre à `0` pour désactiver ce filtre.

#### Position Size

**Minimum Position Size** : ne copier que les positions dont la taille est supérieure ou égale à cette valeur. Par exemple, définir à `10` pour ne copier que les positions d'une taille de 10 contrats/unités ou plus.

Définir à `0` pour désactiver ce filtre.

### Validation de l'allocation de portefeuille

OctoBot valide automatiquement que votre allocation de portefeuille est réalisable :
- Allocation totale = *Per Exchange Profile Portfolio Ratio* × nombre de profils
- Ce total doit être ≤ 100 %
- En cas d'échec de la validation, OctoBot génère une erreur et empêche le démarrage du mode de trading

**Exemple de validation** :
- 3 profils × 35 % chacun = 105 % → **Invalide** (dépasse 100 %)
- 3 profils × 30 % chacun = 90 % → **Valide**
- 2 profils × 50 % chacun = 100 % → **Valide**

### Dépannage

**Problème** : « Distribution for all exchange profiles are not yet available »
- **Solution** : attendez que l'Exchange Service Feed fournisse les données de tous les profils configurés. C'est normal au démarrage.

**Problème** : « Total portfolio allocation exceeds 100% »
- **Solution** : réduisez *Per Exchange Profile Portfolio Ratio* ou réduisez le nombre de profils dans *Exchange Profile IDs*.

**Problème** : « Impossible to find the Exchange service feed »
- **Solution** : assurez-vous que le tentacle Exchange Service Feed est installé et activé dans votre configuration OctoBot.

**Note** : comme le mode de trading Profile Copy étend le mode de trading Index, il prend également en charge les paramètres du mode de trading Index tels que *Refresh interval* et *Rebalance cap* pour contrôler le comportement de rééquilibrage du portefeuille.

_Ce mode de trading prend en charge le backtesting et est compatible avec l'historique PNL._
