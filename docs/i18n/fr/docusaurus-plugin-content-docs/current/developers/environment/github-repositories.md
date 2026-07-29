---
title: "Le dépôt GitHub"
description: "Apprenez-en plus sur le monorepo OctoBot sur GitHub, comment le code est réparti en packages et quel est leur but respectif."
sidebar_position: 8
---



# Le dépôt GitHub d'OctoBot

Le code d'OctoBot se trouve dans un unique monorepo Python, hébergé sous
l'organisation <a href="https://github.com/Drakkar-Software" rel="nofollow">Drakkar-Software</a> sur
GitHub : <a href="https://github.com/Drakkar-Software/OctoBot" rel="nofollow">github.com/Drakkar-Software/OctoBot</a> (branche dev pour le développement, branche master pour la version stable).

La racine du dépôt contient l'initialisation du programme principal ainsi que la gestion des données de la
communauté. Tout le reste est réparti en packages, chacun dédié à un aspect différent du logiciel, dans son
propre dossier sous `packages`. Les packages sont construits avec <a href="https://www.pantsbuild.org/" rel="nofollow">Pants</a> et
déclarés dans les `root_patterns` du fichier `pants.toml` à la racine du dépôt.

Chacun de ces packages était auparavant un dépôt GitHub distinct. Ces dépôts sont maintenant archivés et en
lecture seule, tout le développement se fait dans le monorepo.

- <a href="https://github.com/Drakkar-Software/OctoBot/tree/master/packages/trading" rel="nofollow">packages/trading</a> pour tout ce qui touche au trading et aux exchanges :
  connexions aux exchanges, récupération et mise à jour de leurs données, gestion des ordres, des trades et
  des portefeuilles.
- <a href="https://github.com/Drakkar-Software/OctoBot/tree/master/packages/evaluators" rel="nofollow">packages/evaluators</a> pour tout ce qui concerne les évaluateurs et les stratégies.
- <a href="https://github.com/Drakkar-Software/OctoBot/tree/master/packages/services" rel="nofollow">packages/services</a> pour tout ce qui concerne les interfaces : graphique (web)
  et texte (telegram), l'envoi des notifications et la gestion des données d'analyse sociale, avec le moteur
  de mise à jour qui traite les nouvelles données d'un flux externe (par exemple reddit) dès qu'elles sont
  disponibles.
- <a href="https://github.com/Drakkar-Software/OctoBot/tree/master/packages/backtesting" rel="nofollow">packages/backtesting</a> pour le [moteur de
  backtesting](/fr/guides/octobot-usage/backtesting) et sa planification, ainsi que pour la collecte des
  données historiques et leur stockage unifié.
- <a href="https://github.com/Drakkar-Software/OctoBot/tree/master/packages/tentacles" rel="nofollow">packages/tentacles</a> les tentacles : évaluateurs, stratégies, modes de
  trading, interfaces, notificateurs, flux de données externes (reddit, telegram, etc.), gestion des formats
  de données de backtesting et comportements spécifiques à chaque exchange. C'est la source des tentacles, le
  dossier `tentacles` utilisé par un OctoBot en cours d'exécution est généré à partir de celle-ci.
- <a href="https://github.com/Drakkar-Software/OctoBot/tree/master/packages/tentacles_manager" rel="nofollow">packages/tentacles_manager</a> pour l'installation, la mise à jour des tentacles
  et les interactions avec elles : obtenir la documentation, la configuration ou les dépendances d'une tentacle.
- <a href="https://github.com/Drakkar-Software/OctoBot/tree/master/packages/commons" rel="nofollow">packages/commons</a> pour les outils et constantes communs utilisés par chacun
  des autres packages.
- <a href="https://github.com/Drakkar-Software/OctoBot/tree/master/packages/async_channel" rel="nofollow">packages/async_channel</a> qui est utilisé par OctoBot comme framework de base
  pour chaque transfert de données au sein du bot. Cela permet une architecture très optimisée et évolutive,
  qui s'adapte à n'importe quel système tout en consommant très peu de CPU et de RAM.
- <a href="https://github.com/Drakkar-Software/OctoBot/tree/master/packages/agents" rel="nofollow">packages/agents</a> pour les agents IA d'OctoBot : les agents individuels, les
  équipes d'agents et leur stockage.
- <a href="https://github.com/Drakkar-Software/OctoBot/tree/master/packages/copy" rel="nofollow">packages/copy</a> pour le copy trading : la réplication des ordres et le
  rééquilibrage du portefeuille afin de suivre un compte copié.
- <a href="https://github.com/Drakkar-Software/OctoBot/tree/master/packages/flow" rel="nofollow">packages/flow</a> pour le moteur d'automatisations d'OctoBot : les jobs, les
  parsers et la logique derrière les automatisations.
- <a href="https://github.com/Drakkar-Software/OctoBot/tree/master/packages/node" rel="nofollow">packages/node</a> pour OctoBot Node, qui permet d'exécuter n'importe quel
  OctoBot n'importe où en tant que service géré à distance.
- <a href="https://github.com/Drakkar-Software/OctoBot/tree/master/packages/protocol" rel="nofollow">packages/protocol</a> pour les structures de données partagées entre les
  environnements d'exécution d'OctoBot (comptes, ordres, trades, automatisations et leurs enums). Elles sont
  générées depuis un document OpenAPI vers des modèles Python, TypeScript et Rust.
- <a href="https://github.com/Drakkar-Software/OctoBot/tree/master/packages/sync" rel="nofollow">packages/sync</a> pour le composant serveur qui permet aux OctoBot Node de
  servir de point de synchronisation personnel, avec son authentification par wallet et ses collections de
  données utilisateur chiffrées.
- <a href="https://github.com/Drakkar-Software/OctoBot/tree/master/packages/binary" rel="nofollow">packages/binary</a> pour créer et publier les binaires Windows, Linux et MacOS
  de chaque version d'OctoBot.
