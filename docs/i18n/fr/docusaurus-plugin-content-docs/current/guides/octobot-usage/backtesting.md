---
title: "Backtesting"
description: "Utilisez le backtesting pour tester et optimiser sans risque vos stratégies de trading OctoBot. Evaluez leurs performances sur plusieurs jours, semaines ou mois"
sidebar_position: 3
---



# Backtesting

Le backtesting est le processus permettant de mesurer les performances d'un système sur des données historiques. Il utilise des données enregistrées des marchés de cryptomonnaies ou d'actions. Apprenez-en davantage sur le backtesting sur <a href="https://www.investopedia.com/terms/b/backtesting.asp" rel="nofollow">investopedia</a>.

![résumé des résultats de backtesting octobot](/images/guides/backtesting/octobot-backtesting-result-summary.png)

Dans OctoBot, le backtesting est un outil essentiel qui vous permet de tester et d'optimiser rapidement vos stratégies dans un environnement sans risque, en exécutant votre stratégie sur des scénarios passés pour identifier les meilleurs paramètres pour vos marchés tradés.

## Backtester une stratégie de trading dans OctoBot

OctoBot comprend un moteur de backtesting qui peut rapidement exécuter les stratégies de trading OctoBot sur des données historiques. Pour effectuer un backtest d'une stratégie, il vous suffit de :

1. Sélectionner le profil à tester dans le sélecteur de profils.
2. Utiliser le collecteur de données pour télécharger des données historiques
3. Démarrer un backtesting
4. Analyser les résultats

### Sélection du profil à exécuter lors du backtesting

Accédez au sélecteur de profils sur votre OctoBot et sélectionnez le profil que vous souhaitez tester.

![sélecteur de profil pour backtesting octobot](/images/guides/backtesting/octobot-backtesting-profile-selector.png)

#### Trading modes, stratégies et évaluateurs

Lors du backtesting, OctoBot utilise la version la plus récente du trading mode sélectionné, des stratégies et évaluateurs choisis, ainsi que leur plus récente configuration.

Cela signifie que vous pouvez sélectionner différents trading modes & évaluateurs et relancer des backtestings sans avoir à redémarrer OctoBot : votre prochain backtesting prendra en compte vos dernières modifications.
Ceci est utile pour rapidement essayer différentes valeurs d'un indicateur ou de tout autre paramètre de configuration.

Remarque : lors du backtesting d'une stratégie, il est préférable de sélectionner un profil utilisant le `trading simulé` (utiliser le [Simulateur](simulator)), ainsi toute modification que vous apporterez au profile n'affectera pas vos profiles de trading réel.

#### Portfolio initial

De la même manière que pour le trading simulé, votre portefeuille initial de backtesting est constitué en utilisant la configuration `Starting-Portfolio` de votre profil.

Lorsque vous lancez un backtest, assurez-vous d'avoir configuré votre portefeuille de départ avec suffisamment de fonds pour que votre stratégie puisse effectuer des transactions. N'oubliez pas d'ajouter du BTC lorsque vous tradez contre le BTC, par exemple.

#### Paramètres des actifs tradés lors du backtesting

- **Coins**: Les coins et les paires sélectionnées sont ignorés car le fichier de données que vous allez sélectionner pour exécuter vos backtests fournira les paires tradées
- **Reference market**: Le marché de référence sélectionné sera modifié pour correspondre à la devise commune des paires tradées dans votre fichier de données s'il y a une devise commune. Par exemple, un fichier de données contenant BTC/USDT et ETH/USDT forcera son marché de référence à USDT afin de calculer les profits en USDT

### Téléchargement des données historiques

À l'aide du collecteur de données disponible dans l'onglet Backtesting, vous pouvez télécharger des données historiques à partir de la plupart des plateformes d'échanges de cryptomonnaies.

![collecteurde donnée de backtesting octobot](/images/guides/backtesting/octobot-backtesting-data-collector.png)

Vous pouvez télécharger des données sur plusieurs paires d'échange et time frames simultanément. En utilisant de tels fichiers, le backtestings appliquera votre stratégie sur chaque paire disponible et utilisera les time frames [requis dans sa configuration](../octobot-trading-modes/trading-modes#evaluators-responsabilities).

#### Échanges avec historique complet

Lors de la sélection des données historiques à télécharger, les échanges sont répartis en 2 catégories : `Full History` (historique complet) et `Other` (autres). Voici les différences.

**Full history**: ces échanges permettent de télécharger des données historiques sur une plage de temps sélectionnée. Lorsque vous effectuez cette opération, chaque bougie pour chaque time frame sur chaque paire tradée sera téléchargée sur l'intervalle de tmeps sélectionné. Cela signifie que lorsqu'un intervalle de temps est sélectionné:

- L'historique téléchargé est complet pour chaque bougie sur intervalle de temps sélectionné
- Le processus de téléchargement peut être lent si vous avez sélectionné un grand nombre total de bougies
- Les fichiers de données d'historique complet sont marqués comme `Full` dans le sélecteur de fichiers de données.
  **Avertissement**: ne pas sélectionner une plage horaire dans les échanges avec historique complet entraînera le téléchargement des dernières bougies uniquement, tout comme pour les échanges **Other**.

Les échanges **Other** sont des échanges qui n'autorisent pas (actuellement) le téléchargement des données historiques. Cela signifie que:

- Seules les bougies les plus récentes seront téléchargées (généralement les 500 dernières bougies)
- Sélectionner des time frames courts et longues en même temps donnera lieu à des backtesting courts car ils ne s'exécuteront que sur les bougies disponibles. Par exemple, un fichier de données de backtesting contenant les 500 dernières bougies d'une minute et les 500 dernières bougies quotidiennes ne s'exécutera que sur les 500 dernières bougies, soit moins d'une journée
- Les fichiers de ce type affichent leur nombre total de bougies dans le sélecteur de fichiers.

Dans l'ensemble, il est préférable d'utiliser des exchanges avec historique **Full** et de sélectionner l'intervalle de temps sur lequel pour effectuer vos backtests.

### Démarrage d'un backtesting

Une fois votre fichier de données téléchargé, sélectionnez-le et lancez votre backtesting.
![sélection du fichier de données pour le backtesting octobot](/images/guides/backtesting/octobot-backtesting-data-selector-starting-a-backtesting.png)

Les backtestings durent généralement quelques secondes et s'exécutent en arrière-plan. Si vous le souhaitez, vous pouvez faire autre chose avec votre OctoBot pendant qu'un backtesting est en cours.

Vous êtes notifié une fois que votre backtesting est terminé.

### Analyser les résultats

Vous pouvez accéder aux résultats de votre backtest depuis l'onglet Backtesting. Votre rapport de backtesting se trouve sous le sélecteur de données.
Dans ce rapport, vous trouverez un résumé des performances de votre backtesting, des graphiques avec les prix historiques, les trades et les ordres ouverts, ainsi qu'un explorateur de trades.

#### Profitabilité

![résumé des résultats d'un backtesting octobot](/images/guides/backtesting/octobot-backtesting-result-summary.png)

Ce résumé montre la rentabilité de votre stratégie sur l'intervalle de temps sélectionné.

- **Bot profitability** correspond aux bénéfices en % du marché de référence réalisés par votre stratégie.
- **Market average profitability** est la rentabilité moyenne des marchés tradés. Elle est donnée à titre de comparaison des bénéfices que vous auriez réalisés si vous aviez une exposition permanente à 100% de ces actifs, ce qui est extrêmement risqué. Cela correspond à diviser vos fonds initiaux entre ces actifs et les détenir pendant toute la durée du backtesting.
- **Symbol profitability** correspond à la rentabilité de chaque paire tradée pendant le backtesting.
- **End portfolio** représente le contenu de votre portefeuille à la fin du backtest.
- **Starting portfolio** représente le contenu de votre portefeuille au début du backtest.
- **Reference market** est le marché de référence utilisé pour calculer la profitabilité

#### Graphiques historiques

![graphique de résultats d'un backtesting octobot](/images/guides/backtesting/octobot-backtesting-result-graph.png)
Pour chaque paire échangée, un graphique historique sera affiché. Ces graphiques sont interactifs et vous pouvez sélectionner le time frame à utiliser. Pour les backtesting de grande envergure, il peut être plus facile de lire un graphique sur un time frmae plus grand. Chaque graphique affiche:

- Les bougies historiques et leur volume
- Les trades effectués lors du backtesting
- Les ordres encore ouverts à la fin du backtesting

#### Trades historiques

![trades résultant d'un backtesting octobot](/images/guides/backtesting/octobot-backtesting-result-trades.png)
Tout trade exécuté lors d'un backtesting est disponible dans l'explorateur de trade où vous pouvez facilement filtrer et trier les trades pour comprendre le comportement de votre stratégie.

## Approfondir avec le Strategy Designer

Le backtesting tel que présenté sur cette page est la version basique, mais déjà très complète du [Strategy Designer](strategy-designer) disponible sur les plans cloud d'OctoBot.

![résultats strategy designer octobot sur doge btc shib](/images/guides/strategy-designer/octobot-strategy-designer-results-on-doge-btc-shib.png)

Le Strategy Designer vous permet de faire tout ce que fait le backtesting traditionnel et ajoute :

- L'accès à **l'historique de vos résultats** de backtesting
- Des graphiques pour analyser plus efficacement vos exécutions en backtesting avec la **valeur historique du portefeuille**, le PNL et plus encore
- La possibilité de **comparer les résultats de vos backtestings** entre eux.
- Des profils spécifiques au backtesting pour tester sans affecter votre profil actuel de trading live
- Et bien plus encore...

Si vous effectuez déjà des tests sur vos stratégies et souhaitez utiliser un outil plus puissant, nous vous recommandons vivement de jeter un coup d'œil au [Strategy Designer](strategy-designer).

## Fonctionnement du Backtesting dans OctoBot

### Backtesting vs live trading

Lorsqu'il s'exécute en mode backtesting, OctoBot utilise le même code pour exécuter une stratégie de trading que lorsqu'il s'exécute en mode réel. Cela signifie que les résultats obtenus lors d'une exécution en backtesting et en réel sont identiques tant que les données d'entrée sont également identiques.

Comme le backtesting utilise des bougies complètes, il peut y avoir une différence avec le trading live car ce dernier peut utiliser des bougies incomplètes pour exécuter ses indicateurs (c'est le cas par exemple avec les évaluateurs en temps réel). Par conséquent, lors du backtesting, **les évaluateurs en temps réel ne fonctionnent pas de la même manière qu'en trading live** car les bougies en cours de construction ne sont pas disponible.

Pour la même raison, car seules les données des bougies sont disponibles, il est actuellement impossible de faire des backtests sur des stratégies qui utilisent d'autres données que les données des bougies (par exemple en suivant les tendances Google).

La seule exception concerne les **signaux historiques de ChatGPT qui sont mis à disposition gratuitement** grâce à OctoBot cloud lorsqu'un backtesting est effectué en utilisant le ChatGPTEvaluator sur les paires de trading et les time frames utilisés par <a href="https://www.octobot.cloud/explore" rel="nofollow">les stratégies du cloud OctoBot</a> qui utilisent également le ChatGPTEvaluator.

### Gestion du temps

Le backtesting fonctionne en appliquant une stratégie à l'aide de données du passé. Lorsque vous appliquez une stratégie, le moteur de backtesting simule le passage du temps à partir du début des données de backtesting, et ce jusqu'à la fin de la période sélectionnée.
Le backtesting itère sur les bougies et chaque itération effectue les opérations suivantes :

1. Mettre à jour de la bougie actuelle pour chaque paires de trading et chaque time frame
2. Vérifier si les ordres ouverts doivent être exécutés en fonction des nouvelles données de prix
3. Déclanchement d'un cycle d'évaluation pour chaque paires de trading:
   1. Envoie des nouvelles nouvelles bougies aux évaluateurs
   2. Activation des stratégies pour résumer les analyses des évaluateurs
   3. Activation des trading modes pour créer ou annuler des ordres
4. Vérifier si des ordres doivent être exécutés instantanément (par exemple, les ordres au marché)

### Plusieurs paires de trading

Lorsque vous sélectionnez un fichier contenant plusieurs paires de trading, à chaque nouveau tick temporel, les bougies associées (si il y en a de nouvelles) seront envoyées aux évaluateurs. Cet envoi se fait séquentiellement, une paire après l'autre.

### Exécution des ordres

Lors d'un backtest, OctoBot n'a accès qu'aux bougies historiques. Cela signifie que pour déterminer si un ordre doit être exécuté, il examinera la bougie la plus récente.

:::info
  Vous pouvez améliorer la précision des exécutions d'ordres lors du backtesting
  en sélectionnant un time frame court dans votre fichier de données. Cela
  rendra votre backtesting plus lent mais cela peut être utile si l'exécution
  des ordres doit être précise dans le temps.
:::
