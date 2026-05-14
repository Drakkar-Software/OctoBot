---
title: Services
description: Architecture et concepts du package octobot_services — services, service feeds, interfaces et système de notification.
sidebar_position: 1
---

# Package Services

`octobot_services` est la couche d'intégration d'OctoBot entre les systèmes externes et le reste du bot. Il définit les contrats abstraits et la machinerie d'exécution pour se connecter à des API tierces, faire entrer des données externes dans le bus de canaux interne, présenter des interfaces destinées aux utilisateurs et délivrer des notifications. Ces quatre concepts partagent un cycle de vie commun géré par des utilitaires de factory et de manager, et reliés entre eux par un unique callback `octobot_channel_consumer`.

## Services

`AbstractService` est la classe de base de chaque connexion externe. Chaque classe de service concrète est un singleton — au plus une instance vivante par type de service existe à l'exécution. La configuration est stockée sous la clé de premier niveau `services`, chaque service lisant et écrivant sa propre sous-clé. `save_service_config` persiste les modifications sur disque. La méthode `say_hello()` émet un message de démarrage et positionne un indicateur de santé interne que la factory vérifie avant de remettre une instance aux appelants.

`ServiceFactory` fournit un `create_or_get_service` idempotent qui renvoie soit une instance existante en bonne santé, soit une nouvelle instance créée en appelant `prepare()` puis `say_hello()`. Il découvre toutes les sous-classes de service concrètes via le système de tentacles.

`AbstractAIService` étend la classe de base pour les backends LLM. Il ajoute une couche d'invocation complète : complétions en un seul appel, une boucle agentique qui pilote les appels d'outils jusqu'à une limite d'itérations configurable, une construction de messages adaptée au fournisseur, et un décorateur de retry pour les échecs de parsing courants. La sélection du modèle est pilotée par des règles — une valeur `AIModelPolicy` telle que `"fast"` ou `"reasoning"` est résolue à l'exécution en un nom de modèle concret via la configuration de modèles du service. Des hooks pour l'intégration de LangGraph sont également fournis. `AbstractWebSearchService` suit le même schéma pour les backends de recherche, en ajoutant des méthodes `search` et `search_news` normalisées.

## Service feeds

`AbstractServiceFeed` fait le pont entre un flux de données externe et un canal asynchrone interne. Chaque feed déclare le `FEED_CHANNEL` qui devient son bus de distribution interne et les `REQUIRED_SERVICES` qui doivent être en bonne santé avant qu'il puisse démarrer. Les sous-classes de simulateur positionnent un indicateur pour une utilisation en backtesting. `ServiceFeeds` est un registre singleton qui associe les paires `(bot_id, feed_name)` à des instances ; `ServiceFeedFactory` instancie les feeds et les y enregistre.

## Interfaces

`AbstractInterface` est la base de toutes les surfaces destinées aux utilisateurs. Deux spécialisations existent : `AbstractBotInterface` pour les interfaces de type conversationnel telles qu'un bot Telegram, qui fournit des helpers interrogeant l'API de trading et formatant les réponses pour l'état du portefeuille, l'historique des trades, les ordres ouverts et les commandes de contrôle ; et `AbstractWebInterface` en tant que sous-classe marqueur pour les interfaces basées sur navigateur. Toutes les interfaces partagent des métadonnées au niveau de la classe — identifiant du bot, nom du projet, version du projet — définies une seule fois au démarrage via `AbstractInterface.initialize_global_project_data`.

## Notifications

Une `Notification` est un simple objet valeur portant un corps en texte brut, un corps en markdown, un titre court, un niveau de sévérité, une catégorie, une indication de son optionnelle et un lien optionnel vers une notification précédente. `NotificationChannel` est un canal asynchrone avec un producteur singleton. `api.notification.send_notification` y pousse des éléments. Si le canal n'est pas encore en cours d'exécution lorsqu'une notification est envoyée, elle est mise en mémoire tampon jusqu'à un plafond de dix et rejouée une fois le canal disponible.

`AbstractNotifier` est l'extrémité de livraison. Chaque notifier déclare la clé de configuration qui l'active, les services dont il dépend, et une implémentation `_handle_notification` qui livre vers son transport. Les notifiers s'abonnent également au `OrderChannel` du trading pour des notifications automatiques du cycle de vie des ordres, en parallèle du `NotificationChannel`.

## Utilitaires de cycle de vie

`AbstractServiceUser` combine `InitializableWithPostAction` avec une résolution automatique des dépendances de services. Les sous-classes déclarent `REQUIRED_SERVICES` sous forme de liste de classes de service, ou `False` lorsqu'aucun service n'est nécessaire. Pendant l'initialisation, chaque service requis est créé ou récupéré via la factory. `InitializableWithPostAction` se prémunit contre une double initialisation et enchaîne sur un hook de post-initialisation. `ReturningStartable` fournit à la fois un mode de démarrage asynchrone et un mode threadé. `ExchangeWatcher` suit les enregistrements d'exchanges et notifie les sous-classes lorsqu'un nouvel exchange devient disponible — utilisé par les interfaces et les notifiers qui doivent réagir aux nouvelles connexions d'exchanges.

## Intégration au canal OctoBot

`octobot_channel_consumer.py` connecte ce package au bus de canaux OctoBot de premier niveau. Il gère les événements de création pour les interfaces, les notifiers et les service feeds ; les mises à jour d'enregistrement d'exchanges pour les interfaces et les notifiers ; et les demandes de démarrage de service feeds nommés. Après la création, une confirmation est renvoyée sur le canal OctoBot pour que l'appelant sache que l'instance est prête.
