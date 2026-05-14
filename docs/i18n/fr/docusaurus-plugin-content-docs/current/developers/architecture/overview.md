---
title: Vue d'ensemble de l'architecture
description: Architecture du système OctoBot — couches de packages, système de plugins tentacles, dorsale async channel, pipeline d'évaluation, configuration et modes de déploiement.
keywords: [octobot, architecture, monorepo, packages, tentacles, async-channel, trading, evaluators]
sidebar_position: 1
---

# Vue d'ensemble de l'architecture

OctoBot est un trading bot crypto modulaire et asynchrone. Le code est un monorepo Python situé sous `packages/`, construit avec [Pants](https://www.pantsbuild.org/). Chaque stratégie, évaluateur, connecteur d'exchange et mode de trading existe sous forme de **tentacle** — un plugin qui se greffe sur le framework sans le modifier. Cette séparation est la décision de conception centrale : les packages du cœur définissent les contrats ; les tentacles les remplissent.

## Couches de packages

La stack comporte six couches. Chaque package ne dépend que des packages situés dans les couches inférieures.

**commons** et **async_channel** constituent la fondation — aucun des deux n'a de dépendance interne. Commons fournit la configuration, les bases de données, l'interpréteur de DSL et les utilitaires partagés. Async_channel est le bus de messages typé : les channels relient les producteurs aux consommateurs via des files asynchrones. Le mode synchronisé supprime les tâches asynchrones et pilote l'exécution de manière déterministe, ce qui rend le backtesting possible.

**tentacles_manager**, **backtesting** et **trading_backend** forment la couche suivante. Tentacles_manager gère la découverte, l'installation et la configuration des plugins. Backtesting fournit le moteur de simulation piloté par le temps. Trading_backend gère l'injection des identifiants de broker spécifiques aux exchanges et la validation des permissions des clés API.

**trading** et **evaluators** sont le cœur du framework. Trading possède les gestionnaires d'exchanges, le cycle de vie des ordres, la comptabilité du portefeuille et l'abstraction de mode de trading. Evaluators possède la Matrix (l'arbre de signaux en mémoire) et la factory qui instancie les classes d'évaluateurs à travers les combinaisons symbole/intervalle de temps.

**services** se situe au-dessus de trading et backtesting. Il intègre les interfaces externes — dashboard web, Telegram, dispatch de notifications, backends de modèles d'IA.

**agents**, **flow** et **sync** sont des packages de plus haut niveau. Agents orchestre des équipes pilotées par LLM à travers services. Flow est le runner d'automatisation sans état qui s'appuie sur trading pour les opérations d'exchange. Sync fournit la coordination multi-instances en HTTPS.

**node** dépend de flow et l'enveloppe dans un ordonnanceur durable doté d'une reprise après crash.

**tentacles** se situe au sommet, aux côtés de la CLI. Il ne contient aucun code de framework — uniquement des implémentations concrètes qui dérivent de ce que le framework définit.

## Le système de plugins tentacles

Un tentacle est un répertoire dans l'arborescence `tentacles/` comprenant un module Python, un descripteur `metadata.json` et un sous-répertoire `config/` optionnel. Le descripteur nomme les classes Python qu'il exporte et déclare une version minimale compatible. `tentacles_manager` découvre ces répertoires au démarrage en cherchant les fichiers `metadata.json` jusqu'à trois niveaux de profondeur — aucun registre, aucun appel d'enregistrement explicite.

Les fichiers `__init__.py` répartis dans l'arborescence `tentacles/` sont générés par `tentacles_manager`, et non écrits à la main. Chacun appelle `check_tentacle_version()` à l'import : si la version déclarée du tentacle est inférieure au minimum, l'import est silencieusement ignoré. Un tentacle défectueux ne peut pas faire planter OctoBot au démarrage.

Cette frontière est importante car elle maintient le code de stratégie hors du cœur. Un nouveau mode de trading, évaluateur ou connecteur d'exchange est un nouveau répertoire dans `tentacles/`, et non un patch sur `octobot_trading` ou `octobot_evaluators`. Les packages du framework restent stables à travers des stratégies de trading très différentes.

La configuration suit la même séparation. Chaque classe de tentacle possède une **configuration de référence** dans son propre répertoire `config/` — la valeur par défaut d'usine, jamais modifiée à l'exécution — et une **copie spécifique au profil** optionnelle écrite dans le dossier `specific_config/` du profil actif. À l'exécution, la copie du profil l'emporte si elle est présente ; sinon, la référence est utilisée.

## La dorsale async channel

Tout le flux de données à l'exécution est basé sur les channels. Une sous-classe de `Channel` nomme un type de données et déclare ses classes de producteur et de consommateur. Les producteurs mettent en file ; les consommateurs retirent de la file et appellent un callback enregistré. Les consommateurs peuvent être filtrés — un évaluateur TA s'abonne à `EvaluatorsChannel` filtré sur son symbole et son intervalle de temps spécifiques, de sorte qu'il ne reçoit que les déclenchements pertinents.

Les channels démarrent en pause et reprennent automatiquement lorsqu'un consommateur dont le niveau de priorité n'est pas optionnel s'enregistre. Cela empêche le traitement en amont lorsque rien d'utile n'écoute.

`MatrixChannel` est le channel le plus déterminant : chaque fois qu'un évaluateur termine et appelle `evaluation_completed()`, il publie sur `MatrixChannel`. Les évaluateurs de stratégie et les producteurs de mode de trading s'y abonnent tous deux pour être notifiés lorsque de nouvelles données de signal sont disponibles.

## Le pipeline de l'évaluation au trading

```
 ╔══════════════════════════════════════════════════════════════╗
 ║                    Exchange (WebSocket / REST)               ║
 ╚════════════════════════════╤═════════════════════════════════╝
                              │
                   ┌──────────▼──────────┐
                   │   ExchangeManager   │
                   │  candles · tickers  │
                   │  order book · fees  │
                   └──────────┬──────────┘
                              │ EvaluatorsChannel
          ┌───────────────────┼───────────────────┐
          ▼                   ▼                   ▼
    ┌───────────┐     ┌─────────────┐     ┌───────────┐
    │ TA        │     │ RealTime    │     │ Social    │
    │ Evaluator │     │ Evaluator   │     │ Evaluator │
    └─────┬─────┘     └──────┬──────┘     └─────┬─────┘
          │  eval_note       │  eval_note       │  eval_note
          └───────────────┐  │  ┌───────────────┘
                          ▼  ▼  ▼
                   ┌──────────────────┐
                   │      Matrix      │
                   │  (signal tree)   │
                   └────────┬─────────┘
                            │ MatrixChannel
                   ┌────────▼─────────┐
                   │    Strategy      │
                   │   Evaluator      │
                   └────────┬─────────┘
                            │ TradingModeChannel
                ┌───────────┴───────────┐
                ▼                       ▼
        ┌──────────────┐      ┌──────────────┐
        │   Producer   │      │   Consumer   │
        │  what/when   │─────►│  how/execute │
        │  to trade    │      │  on exchange │
        └──────────────┘      └──────┬───────┘
                                     │
                              ┌──────▼───────┐
                              │    Orders    │
                              │  Portfolio   │
                              └──────────────┘
```

Les données d'exchange arrivent par polling REST ou WebSocket et alimentent des buffers circulaires par intervalle de temps (trois mille bougies chacun). À chaque bougie clôturée, `EvaluatorsChannel` déclenche les évaluateurs TA concernés. Chaque évaluateur écrit son `eval_note` (un flottant dans `[-1, 1]`) dans la Matrix et le diffuse sur `MatrixChannel`. Un `StrategyEvaluator` s'abonne à `MatrixChannel` et agrège les signaux de tous les évaluateurs pour ses intervalles de temps configurés — mais seulement après avoir vérifié que l'horodatage Matrix de chaque évaluateur TA contributeur est suffisamment récent par rapport au temps de l'exchange. La stratégie publie sa propre note, que les producteurs de mode de trading récupèrent pour décider quels ordres créer.

La séparation producteur/consommateur au sein d'un mode de trading est délibérée : le producteur décide *quoi* trader sur la base des signaux ; le consommateur décide *comment* l'exécuter sur l'exchange. Plusieurs modes de trading peuvent partager un même exchange et opérer sur des sous-portefeuilles isolés.

## Configuration et profils

La configuration comporte deux couches fusionnées à l'exécution :

- `config/config.json` — identifiants d'exchange et paramètres propres à l'installation. Ne voyage jamais avec un profil.
- `user/profiles/<name>/profile.json` — tout ce qui définit une stratégie : tentacles actifs, paramètres d'évaluateurs, configuration du mode de trading. Peut être partagé ou commité en toute sécurité.

Le profil actif contient également `tentacles_config.json` (quelles classes de tentacles sont actives) et `specific_config/` (surcharges de paramètres par classe). Les profils peuvent être marqués `auto_update` pour interroger une URL d'origine à un intervalle configurable, ce qui est la manière dont les mises à jour de stratégie gérées sont distribuées. Une mise à jour de profil déclenche un redémarrage en douceur du bot.

`update_config_fields` applique des mises à jour par chemin pointé en place sans recharger depuis le disque, de sorte que l'interface web puisse enregistrer de petites modifications sans agitation inutile.

## Modes de déploiement

**Bot autonome** — le mode par défaut. `octobot/octobot.py` démarre quatre producteurs (`ExchangeProducer`, `EvaluatorProducer`, `ServiceFeedProducer`, `InterfaceProducer`) sur une seule boucle asyncio. Tout ce qui est décrit dans la section pipeline s'exécute ici.

**Node (master/consumer)** — `octobot_node` est un service FastAPI autonome adossé à [DBOS](https://docs.dbos.dev/), un moteur de workflow qui persiste chaque étape vers SQLite ou PostgreSQL. Un node accepte des tâches d'automatisation via son API REST/WebSocket et les transmet à `octobot_flow` pour exécution. Une instance peut agir en tant que master (ordonnance les tâches), consumer (les exécute), ou les deux. Les déploiements multi-nodes partagent une base de données PostgreSQL ; SQLite est limité à un seul node. Les charges utiles des tâches prennent en charge le chiffrement de bout en bout via un schéma hybride RSA/AES-GCM/ECDSA avec séparation directionnelle des clés.

**Flow serverless** — `octobot_flow` est un moteur d'exécution sans état pour les automatisations individuelles. Un objet `AutomationState` est passé en entrée, un DAG d'actions DSL s'exécute, et l'état mis à jour est renvoyé. Aucune mémoire n'est conservée entre les invocations, ce qui rend l'exécution comme fonction serverless sûre. Le moteur flow est ce que le node invoque à chaque itération de tâche.

**Sync** — `octobot_sync` permet à plusieurs instances OctoBot de partager des configurations, des signaux et des données de compte en HTTPS. Chaque requête est authentifiée via une signature de wallet EVM EIP-191. Le contrôle d'accès est piloté par les données via la résolution de propriété on-chain. Les serveurs primaires utilisent un stockage objet compatible S3 ; les serveurs répliques répliquent localement un sous-ensemble.
