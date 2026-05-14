---
title: Binary
description: Pipeline basé sur PyInstaller qui compile OctoBot en exécutables autonomes pour Windows, Linux et macOS.
sidebar_position: 1
---

# Binary

Le package `binary` contient l'outillage qui empaquette OctoBot dans des exécutables autonomes en un seul fichier à l'aide de [PyInstaller](https://pyinstaller.org/). Les binaires résultants s'exécutent sur Windows, Linux et macOS sans nécessiter l'installation de Python ni d'aucune dépendance sur la machine cible.

## Le problème central

PyInstaller fonctionne en traçant statiquement les imports et en empaquetant tout ce qu'il trouve. L'architecture en plugins d'OctoBot le met en échec : les tentacles sont découverts à l'exécution en parcourant le système de fichiers, et non par des imports statiques, de sorte que PyInstaller ne peut pas les voir. La solution est un pipeline de prétraitement qui s'exécute avant PyInstaller et rend l'invisible visible.

## Pipeline de build

Le pipeline comporte quatre étapes. Premièrement, un script de découverte de modules parcourt tous les site-packages installés et le dépôt local pour trouver chaque module `octobot*` ainsi que la bibliothèque `async_channel`, produisant une liste de chemins d'import en notation pointée qui alimente directement les `hiddenimports` de PyInstaller. Cela couvre le code de plugin découvert à l'exécution.

Deuxièmement, le patch des imports cachés gère un cas spécifique que l'étape de découverte ne peut pas traiter : le driver asynchrone `gevent` pour `python-engineio` est chargé via une recherche par chaîne à l'exécution et n'a aucun import statique nulle part dans le code. Le pipeline ajoute une instruction d'import explicite au point d'entrée de la CLI avant la compilation pour forcer PyInstaller à l'inclure.

Troisièmement, le bundling du corpus NLTK garantit que l'analyse de sentiment fonctionne à l'intérieur du binaire. Le corpus `words` de NLTK ne peut pas être téléchargé à l'exécution à l'intérieur d'un exécutable empaqueté, il est donc téléchargé avant l'empaquetage et inclus comme asset statique.

Quatrièmement, PyInstaller est invoqué contre un fichier spec personnalisé plutôt qu'un point d'entrée brut. Le spec donne un contrôle précis sur les assets de données, les imports cachés et les exclusions. Notamment, les répertoires `tentacles/`, `logs/` et `user/` sont exclus du bundle — ils sont exclusivement d'exécution et doivent vivre en dehors de l'exécutable sur la machine de l'utilisateur.

Une fois le build terminé, la CI valide la sortie en exécutant `OctoBot --version` et renomme l'artefact avec le nom de fichier spécifique à la plateforme.

## Décisions de conception

La liste `hiddenimports` dans le fichier spec est maintenue manuellement plutôt que générée, car une découverte entièrement automatisée inclurait des dépendances de test et des outils de développement qui ne devraient pas être livrés dans un binaire de production. La liste reflète les bibliothèques qui utilisent des schémas d'import dynamiques : bibliothèques de connectivité aux exchanges, transports asynchrones de l'interface web, intégrations de services de notification, connectivité blockchain et analyse de sentiment. Les sous-modules `websockets.legacy.*` sont listés explicitement car PyInstaller ne descend pas automatiquement dans les packages d'espace de noms.

PyInstaller est figé à une version spécifique sur toutes les exécutions de CI afin de garantir des builds reproductibles. Faire flotter la version risquerait d'introduire des changements de comportement silencieux dans la façon dont PyInstaller trace les imports, ce qui peut produire un binaire qui passe `--version` mais omet silencieusement un module qui n'a d'importance qu'à l'exécution.
