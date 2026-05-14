---
title: Tentacles Manager
description: Gestion du cycle de vie des plugins tentacles d'OctoBot — installation, mise à jour, désinstallation, configuration, export et publication.
sidebar_position: 1
---

# Tentacles Manager

`octobot_tentacles_manager` est responsable de l'ensemble du cycle de vie des tentacles d'OctoBot — le système de plugins qui étend OctoBot avec des trading modes, des évaluateurs, des connecteurs d'exchanges, des services et bien plus. Il gère tout, du téléchargement et de l'installation d'un bundle de tentacles jusqu'à la génération de l'infrastructure d'import Python qui rend les tentacles chargeables à l'exécution.

## Ce que fait le manager

L'installation fonctionne en téléchargeant une archive ZIP (depuis une URL ou un chemin local), en l'extrayant, puis en copiant chaque tentacle dans l'arborescence `tentacles/` du bot tout en résolvant les éventuelles dépendances inter-tentacles déclarées dans `metadata.json`. Une passe de mise à jour ignore les tentacles dont la version installée est déjà à jour, ce qui rend sûr le fait de la relancer sur la même source. La désinstallation supprime les répertoires concernés et régénère les fichiers d'import `__init__.py` afin que le reste de l'arborescence reste cohérent.

Les fichiers `__init__.py` générés sont une sortie à part entière de ce package, et non un effet secondaire. Chacun est construit autour d'un appel à `check_tentacle_version()` qui conditionne l'import à la version minimale compatible du package d'origine du tentacle. Si la version déclarée d'un tentacle est trop ancienne, son import est silencieusement ignoré plutôt que de lever une exception, ce qui signifie qu'un seul tentacle obsolète ne peut pas empêcher le démarrage des autres.

Une opération de **réparation** régénère les fichiers `__init__.py` et la structure de dossiers manquants sans toucher aux configurations des tentacles. C'est le chemin de récupération pour une installation cassée où le code est intact mais où la machinerie d'import s'est désynchronisée.

## Gestion de la configuration

Le manager lit et écrit deux types distincts de configuration. Le premier est `tentacles_setup_config.json` à la racine du profil, qui enregistre quels tentacles sont activés dans un profil donné. Les évaluateurs et les trading modes sont désactivés par défaut et doivent être activés explicitement ; les services et les tentacles utilitaires s'activent automatiquement à l'installation. Le second type est constitué des fichiers de configuration JSON par tentacle, chacun stocké dans le propre répertoire `config/` du tentacle en tant que valeur par défaut de référence. Lorsqu'un utilisateur personnalise un tentacle, une copie spécifique au profil est écrite dans le dossier `specific_config/` du profil et prend le pas sur la référence à l'exécution.

## Découverte et chargement

Au démarrage, OctoBot appelle le manager pour parcourir l'arborescence `tentacles/` jusqu'à trois niveaux de dossiers en profondeur, à la recherche de répertoires contenant un `metadata.json`. Chaque module découvert est analysé en un modèle `Tentacle` qui suit le chemin de type, les noms de classes, la version, le package d'origine et un éventuel groupe de tentacles. Le résultat est mis en cache dans un dictionnaire au niveau du module indexé par nom de classe, et tout ce qui se trouve en aval — vérifications d'activation, résolution de configuration, chargement de documentation, recherches de chemins de ressources — lit depuis ce cache.

## Export et distribution

Le manager peut également produire des artefacts redistribuables. Une opération de packaging copie ou compresse un ensemble de tentacles depuis une arborescence installée vers un bundle, avec une compilation Cython optionnelle pour distribuer des packages uniquement compilés. Le chemin d'upload pousse ces artefacts vers des dépôts d'artefacts S3 ou Nexus.

## CLI

Le manager est livré avec une interface en ligne de commande autonome et expose également une fonction `register_tentacles_manager_arguments()` qu'OctoBot utilise pour rattacher des sous-commandes de tentacles à son propre analyseur d'arguments. Cela permet de piloter les mêmes opérations d'installation, de mise à jour, de réparation et de packaging soit depuis la CLI propre au manager, soit depuis `octobot --install`, selon le contexte.
