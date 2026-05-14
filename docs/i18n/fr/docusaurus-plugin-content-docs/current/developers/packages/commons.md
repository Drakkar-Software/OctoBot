---
title: Commons
description: Fondations partagées par tous les packages OctoBot — enums, constantes, configuration, bases de données, logging, signaux, DSL et bien plus.
sidebar_position: 1
---

# OctoBot Commons

Le package `octobot_commons` est la bibliothèque fondatrice partagée par tous les autres packages OctoBot. Il prend en charge les préoccupations transversales — configuration, bases de données, utilitaires asynchrones, un interpréteur de DSL, et bien plus — de sorte qu'aucun autre package n'a besoin de les réimplémenter.

## Configuration et profils

La configuration est organisée en deux couches fusionnées à l'exécution. La configuration globale (`config/config.json`) contient les identifiants d'exchange et les paramètres propres à l'installation. Le profil (`user/profiles/<profile>/profile.json`) contient tout ce qui définit une stratégie de trading et peut être librement partagé ou commité dans un système de contrôle de version, car les identifiants d'API sont toujours conservés dans la configuration globale et jamais écrits dans un profil. Lorsqu'un profil spécifie des paramètres d'exchange, seuls les champs non secrets voyagent avec lui.

`update_config_fields` applique des mises à jour par chemin pointé en place sans recharger depuis le disque, ce qui est la manière dont l'interface web enregistre de petites modifications sans agitation inutile. Les indicateurs de métadonnées de profil portent une signification à l'exécution au-delà du simple affichage : `read_only` empêche la suppression des profils non importés, `hidden` exclut un profil de la liste principale à des fins internes et de modèles, et `auto_update` fait que le bot interroge une URL d'origine à un intervalle configurable.

## Bases de données

La couche base de données est organisée en trois niveaux. Les adaptateurs définissent le contrat CRUD asynchrone. `DBWriter` et `DBReader` se situent au-dessus d'eux — le writer met en attente les écritures via un cache en mémoire ou un buffering de lignes pour le débit du backtesting, tandis que le reader enveloppe l'accès dans un cache de lecture chronologique. `MetaDatabase` est le point d'entrée unique pour le moteur de trading, regroupant toutes les bases de données d'une exécution sous un seul gestionnaire de contexte asynchrone.

`RunDatabasesIdentifier` génère tous les chemins de fichiers d'une exécution en encodant la classe de mode de trading, la campagne et le type d'exécution dans le chemin. Les identifiants d'exécution sont attribués en cherchant le prochain entier disponible, de sorte que les exécutions ne sont jamais écrasées. `RunDatabasesProvider` est un singleton global au processus qui partage une connexion `MetaDatabase` par exécution, ce qui empêche des handles de fichiers concurrents provenant de packages différents.

Le backend TinyDB nettoie automatiquement les fichiers corrompus sur des erreurs connues plutôt que d'échouer brutalement. Le backend SQLite utilise un pool de curseurs asynchrones pour éviter de bloquer la boucle d'événements. `CacheWrapper` stocke les valeurs d'indicateurs calculées indexées par horodatage et respecte les sentinelles `DO_NOT_CACHE` et `DO_NOT_OVERRIDE_CACHE` afin que les évaluateurs puissent ignorer le stockage sans cas particulier au niveau de l'appel. Une table de métadonnées suit la configuration et la version pour la détection de cache obsolète. `GlobalSharedMemoryStorage` est un dictionnaire singleton en cours de processus plus simple, destiné à un état transitoire inter-composants qui n'a pas besoin de survivre à un redémarrage.

## Interpréteur de DSL

L'interpréteur de DSL accepte des chaînes en syntaxe Python, les analyse avec `ast.parse` et convertit l'AST résultant en un arbre d'instances d'`Operator`. Les littéraux restent de simples valeurs Python ; tout le reste devient une sous-classe d'opérateur. La conception est bâtie autour d'un contrat en deux phases : `pre_compute()` parcourt l'arbre de bas en haut pour gérer tout travail asynchrone — I/O, recherches en cache — avant que `compute()` ne s'exécute de haut en bas de manière synchrone. Les opérateurs qui ont besoin de données asynchrones héritent de `PreComputingCallOperator`, qui stocke la valeur récupérée pendant `pre_compute()` et la renvoie depuis `compute()`. Appeler `compute()` avant `pre_compute()` sur un tel opérateur lève immédiatement une exception.

L'enregistrement des opérateurs est indexé par nom : chaque sous-classe expose une méthode statique `get_name()` renvoyant le token tel qu'il apparaît dans le code source du DSL. L'interpréteur résout les appels de fonction, les opérateurs binaires et unaires, les comparaisons, les opérateurs booléens, les subscripts, et même les instructions `raise` par rapport à ce dictionnaire. De nouveaux opérateurs peuvent être injectés dans une instance d'interpréteur existante via `extend()`, ce qui est la manière dont les packages de plus haut niveau enrichissent un ensemble de base sans sous-classer l'interpréteur. `Operator.get_parameters()` renvoie une liste de paramètres typée qui pilote à la fois la validation à l'exécution et la génération de documentation destinée aux utilisateurs via `get_docs()`.

Quelques comportements méritent d'être connus avant de travailler avec le DSL. Les comparaisons chaînées comme `a < b < c` sont décomposées en opérateurs `Compare` par paires reliés par l'opérateur `And` enregistré — si `And` est absent, les comparaisons chaînées échouent à l'analyse même lorsque les comparaisons individuelles réussiraient. Les expressions non valides en mode `eval` sont retentées en mode instruction `single`. `interpreter.prepare(expr)` construit l'arbre d'opérateurs une seule fois afin que les évaluations ultérieures réexécutent pre-compute et compute contre le même arbre, rendant l'évaluation répétée contre des données changeantes peu coûteuse. `ReCallableOperatorMixin` permet des opérateurs avec état en reportant un `last_execution_result` sérialisé dans l'appel suivant, permettant aux opérateurs d'implémenter des périodes d'attente ou un état incrémental à travers les évaluations sans stockage externe.
