---
title: Async Channel
description: Bus de messages producteur/consommateur basé sur asyncio, avec filtrage, niveaux de priorité et mode d'exécution synchronisé.
sidebar_position: 1
---

# Async Channel

`async_channel` est la bibliothèque de communication multi-tâches interne d'OctoBot. Elle implémente un bus de messages producteur/consommateur typé et asynchrone bâti par-dessus `asyncio.Queue`. Les composants à travers l'application l'utilisent pour transmettre des données entre des parties faiblement couplées sans détenir de références directes les unes vers les autres.

## Channels, producteurs et consommateurs

Un `Channel` est le hub qui relie un ou plusieurs producteurs à un ou plusieurs consommateurs. On le sous-classe toujours pour définir un flux de données spécifique, en déclarant `PRODUCER_CLASS` et `CONSUMER_CLASS` comme attributs de classe. Le nom du channel correspond par défaut au nom de la classe avec le suffixe `"Channel"` retiré ; surchargez `get_name()` pour le modifier. `ChannelInstances` est un registre global au processus associant les noms de channels (ou les paires `chan_id` et nom) aux instances vivantes. Pour les déploiements où le même type de channel existe sous plusieurs IDs, les helpers de variante `*_at_id` regroupent les channels par `chan_id`.

Un `Producer` pousse des données dans les files des consommateurs en appelant `send()` pour les mettre en file auprès de tous les consommateurs enregistrés. La méthode de plus haut niveau `push()` est le point d'entrée normal et peut transformer ou filtrer les données avant d'appeler `send()`. Chaque producteur démarre sa propre `asyncio.Task` via `run()`, sauf si le channel est en mode synchronisé.

Un `Consumer` possède une `asyncio.Queue` et exécute une tâche en arrière-plan qui retire continuellement de la file et appelle `perform()`, qui invoque le callback enregistré avec les kwargs mis en file. Les consommateurs sont enregistrés avec un callback et des filtres optionnels ; chacun reçoit sa propre file et sa propre tâche en arrière-plan. Arrêter le channel arrête tous les producteurs et consommateurs dans l'ordre.

## Filtrage

Lors de l'enregistrement d'un consommateur, vous fournissez un dictionnaire `consumer_filters`. Lorsqu'un producteur appelle `get_consumer_from_filters()`, seuls les consommateurs dont les filtres stockés correspondent à toutes les clés du dictionnaire fourni sont renvoyés. Une valeur de requête `CHANNEL_WILDCARD` correspond à n'importe quelle valeur stockée pour cette clé, et un consommateur dont la valeur stockée est `CHANNEL_WILDCARD` correspond à n'importe quelle valeur requêtée. Si la valeur stockée du consommateur est une liste, la correspondance réussit si la valeur requêtée y figure ou si un élément de la liste est le wildcard. Un dictionnaire de filtres vide dans la requête renvoie tous les consommateurs.

## Pause et reprise

Les channels démarrent à l'état en pause. Un channel reprend ses producteurs automatiquement lorsqu'au moins un consommateur doté d'un niveau de priorité non `OPTIONAL` est enregistré, et se met de nouveau en pause lorsqu'il ne reste plus de tels consommateurs. Les producteurs qui ne servent que des consommateurs `OPTIONAL` sont considérés comme logiquement inactifs du point de vue du channel — cela évite le traitement inutile lorsque rien d'utile n'écoute.

## Mode synchronisé

En fonctionnement normal, chaque consommateur et producteur exécute sa propre tâche asyncio. Le mode synchronisé désactive entièrement la création de tâches — aucune tâche n'est lancée pour les producteurs ou les consommateurs. À la place, le producteur pilote explicitement l'exécution en appelant `synchronized_perform_consumers_queue()`, qui vide la file de chaque consommateur dans la coroutine courante pour les consommateurs au niveau de priorité demandé ou au-dessus. Cela donne un contrôle déterministe complet sur l'ordre d'exécution et est utilisé en backtesting, où il faut rejouer les événements dans une séquence définie sans le non-déterminisme des tâches concurrentes.

## Niveaux de priorité

Les niveaux de priorité servent deux objectifs. Les consommateurs `HIGH` et `MEDIUM` maintiennent les producteurs en activité ; les consommateurs `OPTIONAL` non. En mode synchronisé, les consommateurs sont vidés par ordre de priorité, de sorte que les abonnés à haute priorité traitent toujours les données avant ceux à priorité plus basse. Cet ordonnancement est important pour la correction du backtesting, où les stratégies doivent traiter la sortie des évaluateurs avant que l'événement de marché suivant ne soit injecté.

## Types de support

`Channel.get_internal_producer()` fournit un producteur créé paresseusement qui vit sur le channel lui-même, permettant à du code non producteur de publier sans gérer une référence de producteur explicite. Il est arrêté automatiquement à l'arrêt du channel.

`SupervisedConsumer` étend `Consumer` avec un événement `idle` qui suit si `perform()` est en cours d'exécution. Cela permet à un producteur d'attendre qu'un consommateur spécifique termine avant de continuer — important lorsque la correction dépend de l'ordre de consommation plutôt que de la simple livraison.

`InternalConsumer` est une sous-classe de consommateur où le callback est déclaré comme `internal_callback` sur la classe elle-même plutôt que passé à la construction, ce qui est utile lorsque la logique du callback est étroitement couplée à l'état propre du consommateur.
