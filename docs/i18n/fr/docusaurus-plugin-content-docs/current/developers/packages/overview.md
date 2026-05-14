---
title: Vue d'ensemble des packages
description: Vue d'ensemble de l'architecture en monorepo des packages d'OctoBot. Chaque package encapsule un domaine spécifique du trading bot.
keywords: [octobot, packages, architecture, monorepo, trading, evaluators, commons]
slug: /developers/packages/overview
sidebar_position: 0
---

# Packages

OctoBot est organisé en packages autonomes situés sous `packages/`. Chaque package est responsable d'un domaine spécifique et possède une frontière claire : il expose une API publique au reste du système et gère ses propres dépendances. Les packages comportant des composants Rust incluent un répertoire `crates/` contenant le code du pont PyO3 aux côtés des sources Python, ce qui permet d'exécuter en Rust les chemins critiques en matière de performance tout en restant appelables depuis Python.

## Packages principaux

**Trading** est le cœur du système. Il est responsable des ordres, de la gestion du portefeuille, des interactions avec les exchanges et du suivi des positions — tout ce qui touche aux flux d'argent réels passe par ici. **Commons** fournit les utilitaires et structures de données partagés utilisés par tous les autres packages ; il ne dépend d'aucune autre partie de la stack. **Evaluators** gère l'analyse technique, l'évaluation des signaux sociaux et la composition de stratégies, transformant les données de marché en signaux normalisés sur lesquels les trading modes peuvent agir. **Async Channel** est la colonne vertébrale de la messagerie : une couche de communication asynchrone multi-tâches qui permet un flux de données en temps réel entre les composants sans couplage fort.

## Packages d'infrastructure

**Tentacles Manager** gère le cycle de vie des plugins — découverte, installation, mise à jour et suppression des bundles de tentacles, ainsi que la génération de l'infrastructure d'import Python qui les rend chargeables. **Backtesting** exécute des stratégies sur des données historiques, en utilisant le même code d'évaluateurs et de trading modes que le trading en direct. **Services** intègre les services externes pour les notifications, l'interface web et les API. **Trading Backend** fournit des primitives de trading de bas niveau avec une accélération Rust optionnelle via PyO3.

## Packages de support

**Flow** orchestre le flux de données entre les évaluateurs, les trading modes et les services, en les reliant entre eux à l'exécution. **Node** gère les déploiements distribués d'OctoBot, en fournissant une exécution durable des tâches pour les automatisations réparties sur plusieurs instances. **Agents** est la couche d'orchestration d'IA multi-agents, coordonnant des agents pilotés par LLM pour l'analyse et la prise de décision automatisées. **Sync** gère la coordination multi-instances, permettant à des instances OctoBot distinctes de partager configurations, signaux et données de compte via un serveur de synchronisation authentifié cryptographiquement.
