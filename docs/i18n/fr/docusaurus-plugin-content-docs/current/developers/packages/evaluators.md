---
title: Evaluators
description: Vue d'ensemble du package octobot_evaluators — le framework de génération de signaux, de composition de stratégies et la matrice d'évaluation.
sidebar_position: 1
---

# Package Evaluators

Le package `octobot_evaluators` est la couche de génération de signaux et de composition de stratégies d'OctoBot. Il définit les classes de base abstraites que tous les évaluateurs et stratégies étendent, la structure de données Matrix qui contient les résultats d'évaluation en direct, et les async channels qui routent ces résultats vers les modes de trading.

## Types d'évaluateurs

Tous les évaluateurs concrets étendent `AbstractEvaluator`, qui lui-même étend `AbstractTentacle` de `octobot_commons`. Trois méthodes de classe wildcard — une pour la cryptomonnaie, une pour le symbole, une pour l'intervalle de temps — renvoient `True` par défaut. La factory les utilise pour décider combien d'instances créer : une par combinaison concrète de dimensions, ou une instance partagée pour chaque dimension wildcard.

`TAEvaluator` se déclenche sur les bougies OHLCV clôturées. Lorsqu'un déclencheur de ré-évaluation arrive sur `EvaluatorsChannel`, il récupère à nouveau la dernière bougie complète et rejoue le callback. En mode live, il attend jusqu'à cinq minutes l'initialisation des prix avant de traiter la première bougie. `RealTimeEvaluator` se déclenche sur les bougies en formation et sélectionne le plus court intervalle de temps disponible qui satisfait l'intervalle demandé à l'enregistrement.

`SocialEvaluator` consomme des flux externes tels que les actualités et les réseaux sociaux via `octobot_services`. Une seule instance est partagée entre tous les symboles. `ScriptedEvaluator` exécute une coroutine asynchrone fournie par l'utilisateur, met en cache les résultats via le cache du `Context` de trading, et prend en charge le rechargement à chaud du module de script via une commande `RELOAD_SCRIPT` — il est toujours lié à des symboles et des intervalles de temps spécifiques, jamais wildcard.

`StrategyEvaluator` agrège les signaux de tous les autres évaluateurs. Avant d'appeler son callback, il applique un garde-fou de cycle : il vérifie que l'horodatage Matrix de l'évaluateur déclencheur a effectivement changé, et que chaque évaluateur TA pour les intervalles de temps pertinents de la stratégie possède une valeur dans le delta de temps autorisé par rapport au temps de l'exchange. Cela évite d'agir sur des signaux obsolètes ou de fraîcheur mixte.

## L'eval note

Chaque évaluateur stocke son résultat dans `self.eval_note`, un flottant dans `[-1.0, 1.0]` où `-1` est le signal de vente le plus fort et `+1` le signal d'achat le plus fort. `START_PENDING_EVAL_NOTE` est la valeur sentinelle signifiant qu'il n'y a pas encore de résultat. Après le calcul, l'évaluateur appelle `evaluation_completed()`, qui écrit dans la Matrix et diffuse sur `MatrixChannel`. Passer `notify=False` met à jour la Matrix silencieusement sans diffusion.

## La Matrix

La Matrix est un arbre paresseux basé sur les chemins où les nœuds sont créés à la première écriture. Le chemin canonique comporte six segments : nom de l'exchange, type d'évaluateur, nom de l'évaluateur, cryptomonnaie, symbole et intervalle de temps. Le type d'évaluateur est toujours l'une des valeurs de chaîne `EvaluatorMatrixTypes`. Les segments sont omis — et non mis à `None` — lorsqu'ils ne s'appliquent pas, de sorte qu'un évaluateur social sans intervalle de temps produit un chemin à quatre segments tandis qu'un évaluateur TA en produit six. Les helpers de parcours traitent un segment manquant comme un wildcard, vous pouvez donc récupérer tous les nœuds d'évaluateurs sous un exchange et un type donnés avec une requête à deux segments.

Chaque nœud porte le flottant `eval_note`, l'horodatage Unix auquel il a été évalué, la chaîne de type d'eval note, et des blobs de description et de métadonnées optionnels. Les écritures passent toujours par `MatrixChannelProducer.send_eval_note`, et l'horodatage stocké est celui passé par l'évaluateur — et non l'horloge murale au moment de l'écriture — de sorte que le backtesting peut injecter des horodatages historiques sans que la vérification de fraîcheur n'échoue à tort.

La lecture utilise `get_evaluations_by_evaluator`, qui parcourt les nœuds de nom d'évaluateur sous un préfixe exchange et type donné et renvoie un dictionnaire nom-vers-nœud. Les nœuds dont la valeur échoue à la vérification de validité de l'eval note sont silencieusement écartés sauf si `allow_missing=False`, auquel cas une exception `UnsetTentacleEvaluation` est levée.

Un nœud est considéré comme frais si l'heure courante se situe dans la durée de l'intervalle de temps plus un delta autorisé de 10 secondes par rapport à l'horodatage d'évaluation. La vérification de fraîcheur requiert un chemin se terminant par une valeur d'intervalle de temps valide — les chemins des évaluateurs non TA sans intervalle de temps seront toujours considérés comme obsolètes par cette vérification, ce qui est intentionnel.

Chaque instance de `Matrix` se voit attribuer un UUID à la construction et est enregistrée dans le singleton global au processus `Matrices`. Des connexions d'exchange distinctes ont donc des matrices distinctes et des instances de channels distinctes indexées par le même ID de matrice.

## Channels et factory

Deux async channels s'exécutent par ID de matrice. `EvaluatorsChannel` transporte les commandes inter-évaluateurs telles que les déclencheurs de ré-évaluation et les réinitialisations ; chaque évaluateur s'y abonne filtré par symbole et intervalle de temps. `MatrixChannel` diffuse à chaque appel d'`evaluation_completed()` et est l'endroit où les évaluateurs de stratégie et les modes de trading s'abonnent.

La factory `create_and_start_all_type_evaluators` est déclenchée par un événement de création d'évaluateur sur `OctoBotChannel`. Elle calcule le produit cartésien des cryptomonnaies, symboles et intervalles de temps par classe d'évaluateur, ignore les instances qui ne passent pas le filtre des évaluateurs pertinents, et démarre les survivants par ordre de priorité décroissant tiré de la configuration de tentacle de chaque évaluateur. Avant que la factory ne s'exécute, un helper de démarrage lit les intervalles de temps requis depuis toutes les classes de stratégie actives et les nombres de bougies requis depuis tous les évaluateurs actifs, écrivant les deux dans la configuration du bot afin que le flux d'exchange mette en buffer la bonne quantité d'historique avant que les évaluateurs ne commencent.
