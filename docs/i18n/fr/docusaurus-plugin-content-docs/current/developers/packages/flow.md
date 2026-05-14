---
title: Flow
description: Architecture et concepts du package octobot_flow — le runner d'automatisation serverless d'OctoBot.
sidebar_position: 1
---

# Package Flow

`octobot_flow` est un moteur d'exécution d'automatisations sans état. Un objet `AutomationState` est passé en entrée au début de chaque invocation, le job s'exécute, et l'état mis à jour est renvoyé via `AutomationJob.dump()`. Rien n'est conservé en mémoire entre les appels, ce qui signifie que le moteur peut s'exécuter comme une fonction serverless et que plusieurs automatisations sont naturellement isolées les unes des autres.

## Modèle d'exécution

Chaque job exécute un DAG d'actions. Le DAG identifie quelles actions sont prêtes — pas encore terminées, avec toutes les dépendances satisfaites — résout tout placeholder DSL en injectant les résultats amont, et les exécute via `DSLExecutor`. Après l'exécution, l'état de l'exchange est resynchronisé dans l'état d'automatisation.

Les actions prioritaires stockées dans `AutomationState.priority_actions` s'exécutent avant le cycle normal du DAG mais utilisent le DAG principal comme contexte de résolution. C'est le mécanisme d'amorçage : à la toute première invocation, lorsqu'il n'y a pas d'exécution précédente ni de compte d'exchange, seules les actions `apply_configuration` sont traitées pour configurer le compte d'exchange à partir de la configuration avant que le cycle régulier ne s'exécute.

Une réinitialisation du DAG peut être déclenchée en cours d'exécution par un `ReCallingOperatorResult`, que l'opérateur `wait()` renvoie lorsque sa condition n'est pas encore remplie. Une réinitialisation calcule la fermeture transitive des dépendants à partir de l'action cible, sauvegarde leurs résultats courants dans `previous_execution_result`, et efface leurs horodatages d'exécution afin qu'ils se réexécutent à l'invocation suivante. Le résultat précédent sauvegardé permet aux opérateurs réexécutés de reprendre là où ils s'étaient arrêtés plutôt que de repartir à froid.

## Exécution du DSL

`DSLExecutor` enveloppe l'interpréteur de DSL d'`octobot_commons` avec des ensembles d'opérateurs enregistrés par les tentacles. Un interpréteur frais est créé par action pour empêcher toute fuite d'état entre les actions d'une même exécution. Les scripts DSL sont analysés avant que l'exchange ne soit initialisé afin que les symboles et intervalles de temps requis puissent être extraits en amont — seules les données OHLCV que les scripts référencent réellement sont récupérées.

## Modes simulé et live

Lorsqu'aucun identifiant n'est présent, `ExchangeRepositoryFactory` renvoie des implémentations simulées qui lisent depuis des snapshots `FetchedExchangeData` au lieu d'effectuer des appels API en direct. Les données OHLCV sont tout de même récupérées en direct même en mode simulé car elles sont publiques. Un portefeuille peut être forcé sur le gestionnaire d'exchange simulé pour tester des stratégies contre un état de compte spécifique.

Le cache de tickers, doté d'un TTL de cinq minutes et d'un plafond de cinquante entrées, sert de repli lorsque les données OHLCV ne sont pas disponibles à l'initialisation. Les repositories community utilisent intentionnellement des instances d'authentification non singleton par job — aucune session n'est partagée entre les automatisations, ce qui empêche les fuites d'identifiants.

## Cycle de vie de l'exchange

`ExchangeContextMixin` gère le cycle de vie complet de l'exchange pour chaque job : construire la configuration, initialiser `ExchangeManager` avec le stockage désactivé, appliquer tout portefeuille forcé pour les exécutions simulées, puis démanteler une fois le job terminé. La synchronisation du portefeuille est désactivée pendant la création d'ordres car le package flow gère explicitement l'état du portefeuille via des appels de synchronisation post-action plutôt qu'en s'appuyant sur la synchronisation automatique déclenchée par les événements d'ordre.
