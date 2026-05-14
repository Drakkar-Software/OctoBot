---
title: Backtesting
description: Architecture et concepts clés du package octobot_backtesting — le moteur qui exécute les stratégies de trading sur des données historiques ou sociales.
sidebar_position: 1
---

# Package Backtesting

`octobot_backtesting` fournit une boucle de simulation pilotée par le temps qui rejoue des données de marché historiques ou sociales à travers la même infrastructure de channels que celle utilisée par le trading en direct. Comme le moteur de backtesting alimente les données via les producteurs `async_channel` de la même manière qu'un connecteur d'exchange en direct, les modes de trading et les évaluateurs ne nécessitent aucune modification pour s'exécuter dans l'un ou l'autre contexte.

## Boucle de simulation

La boucle est pilotée par `TimeUpdater`, qui fait avancer une horloge gérée par `TimeManager` et pousse chaque horodatage à travers un `TimeChannel`. À chaque tick, le gestionnaire de channels vide les producteurs par ordre de priorité croissant, drainant entièrement un niveau de priorité avant de passer au suivant. Cet ordonnancement reproduit le séquencement causal en direct : les données de prix brutes se terminent avant que les évaluateurs ne calculent les signaux, ce qui se termine avant que les stratégies n'émettent des ordres. Une fois tous les producteurs vidés, la boucle rend la main à la boucle d'événements asyncio avant de faire avancer l'horloge, garantissant que toute coroutine déclenchée s'exécute au moment simulé correct.

Après la première itération réussie, la boucle élague les producteurs dont les channels n'ont aucun consommateur et reconstruit la carte des niveaux de priorité. Cela retire le travail non pertinent de chaque tick ultérieur plutôt que de le revérifier à chaque fois.

Lorsque plusieurs backtests s'exécutent dans le même processus — comme c'est le cas lors d'exécutions d'optimisation — chaque instance de `Backtesting` enregistre son `TimeChannel` sous une clé avec espace de noms afin que leurs horloges n'interfèrent pas.

## Contrôle de l'horloge et des horodatages

`TimeManager` détient les horodatages de début et de fin, la position courante, et un intervalle de temps configurable qui vaut 50 secondes par défaut. Faire avancer l'horloge consiste normalement simplement à ajouter l'intervalle, mais un mode whitelist est disponible pour les cas où seuls des horodatages spécifiques importent — les flux de données sociales clairsemés, par exemple. Lorsqu'une whitelist est active, `next_timestamp()` saute tout horodatage absent du deque trié de la whitelist. Le deque retire les entrées obsolètes à mesure qu'il avance, ce qui maintient le parcours peu coûteux. Un callback peut contourner la whitelist pour un tick spécifique si nécessaire.

## Fichiers de données

Les données historiques résident dans des fichiers `.data`, qui sont des bases de données SQLite. Une table `description` enregistre la version du fichier, son type (exchange ou social), le nom de l'exchange, les symboles, les intervalles de temps et la plage temporelle couverte. Pendant la collecte, la base de données est écrite vers un chemin `.part` puis renommée atomiquement en `.data` à l'achèvement, de sorte que les importateurs ne rencontrent jamais de fichier partiel.

Le nom du fichier encode la classe de collecteur qui l'a produit. Lorsqu'un importateur est créé à partir d'un nom de fichier, le package résout la classe de collecteur par son nom et lit son attribut `IMPORTER` pour instancier le bon importateur. Si aucune correspondance n'est trouvée, il se rabat sur l'importateur d'historique d'exchange par défaut, qui gère gracieusement les fichiers renommés.

Le schéma de description a évolué à travers les versions de format. La version 2.0 sépare les types de données exchange et social et ajoute `start_timestamp` ; les versions antérieures sont exclusivement exchange et ne disposent pas de ce champ. Les importateurs détectent la version à l'initialisation et l'analysent en conséquence.

## Importateurs exchange et social

`ExchangeDataImporter` sonde chaque table au démarrage et n'enregistre que celles qui ne sont pas vides, de sorte que les requêtes par plage temporelle ne touchent que les tables qui contiennent effectivement des données. `SocialDataImporter` stocke les événements avec un nom de service, un channel, un symbole et une charge utile JSON ; sa description encode une liste de services plutôt qu'un nom d'exchange.

Les deux importateurs maintiennent un cache de lecture chronologique indexé par symbole, intervalle de temps et type de données. La première requête récupère toutes les lignes à partir de l'horodatage demandé et alimente le cache ; les requêtes ultérieures découpent la liste déjà chargée. Ce contrat à sens unique signifie que les recherches en arrière renvoient des résultats obsolètes à moins que le cache ne soit explicitement réinitialisé — ce qui est le comportement correct pour un rejeu séquentiel et efficace pour le cas d'optimisation où le même fichier est rejoué de nombreuses fois.

## Collecteurs

`DataCollector` est la classe de base pour tout ce qui écrit un fichier `.data`. Elle gère la création des chemins, construit la base de données au chemin `.part`, détient une session HTTP, et fournit un helper de requête capable de retry ainsi qu'un helper de pagination récursif pour les API qui renvoient des URLs de continuation. Les branches exchange et social l'étendent avec des helpers de sauvegarde typés. L'implémentation concrète de collecteur pour un contexte donné est résolue via la découverte de tentacles, de sorte que les packages de tentacles peuvent surcharger le comportement de collecte sans toucher au code du cœur.

## Partage multi-exécutions et progression

`BacktestData` pré-initialise les importateurs une seule fois et les partage entre plusieurs instances de `Backtesting`. Il gère également des tableaux de bougies préchauffés indexés par exchange, symbole, intervalle de temps et plage temporelle. Entre des exécutions séquentielles, réinitialiser les index de cache de l'importateur rembobine la position de lecture sans rouvrir les connexions SQLite.

La progression est exposée sous forme de flottant entre 0.0 et 1.0 basé sur les itérations restantes par rapport au total. L'achèvement est signalé via un `asyncio.Event` que les appelants peuvent attendre ; nul besoin de faire du polling. Un timeout de drainage par niveau de priorité de 15 secondes protège contre les consommateurs bloqués — un timeout est journalisé mais n'interrompt pas l'exécution.
