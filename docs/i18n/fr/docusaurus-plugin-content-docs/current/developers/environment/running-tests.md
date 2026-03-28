---
title: "Exécuter les tests"
description: "Découvrez comment les tests automatisés fonctionnent sur les dépôts Python open source d'OctoBot en utilisant pytest et GitHub Actions."
sidebar_position: 4
---



# Tests

Chaque suite de tests des dépôts OctoBot est exécutée avec <a href="https://docs.pytest.org/" rel="nofollow">pytest</a> sur <a href="https://docs.github.com/actions" rel="nofollow">GitHub Action</a> et peut également être lancée localement dans un environnement de développement.

## Prérequis

Pour exécuter les tests d’OctoBot, un environnement de développement OctoBot est nécessaire. La configuration de cet environnement est décrite dans le [guide d’environnement de développement](setup-your-environment)

## Le moteur d'OctoBot

Pour lancer les tests du moteur d’OctoBot, utilisez la commande `pytest` à la racine du dossier OctoBot :

```bash
pytest tests
```

Cette commande exécutera tous les tests présents dans le dossier tests.

## Les Tentacles

Pour lancer les tests des tentacles d’OctoBot, utilisez la commande `pytest tentacles` à la racine du dossier OctoBot :

```bash
pytest tentacles
```

Cette commande exécutera tous les tests du dossier **tentacles**. Le test des tentacles ne fonctionne que si les Tentacles sont installés sur l’OctoBot testé. Consultez le [guide de l'environnement de développement](setup-your-environment)
pour les installer.
