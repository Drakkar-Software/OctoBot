---
title: Agents
description: Framework d'orchestration multi-agents IA bâti sur les async channels, prenant en charge les équipes, la mémoire, l'auto-amélioration, les phases de débat et l'intégration LangChain Deep Agents.
sidebar_position: 1
---

# Package Agents

`octobot_agents` fournit l'infrastructure pour composer et exécuter des workflows IA multi-agents au sein d'OctoBot. Il définit une couche abstraite par-dessus `async_channel` qui permet de construire des agents individuels adossés à des LLM, de les assembler en équipes, d'orchestrer l'ordre d'exécution, de noter les résultats avec un critique, et d'améliorer les performances au fil du temps grâce à un sous-système de mémoire persistante.

## Abstractions principales

Un **Agent** est une unité unique adossée à un LLM qui s'exécute sur des données d'entrée et produit un résultat. Chaque type d'agent possède sa propre classe de channel qui route les résultats d'un producteur vers un ou plusieurs consommateurs, suivant le modèle `async_channel` utilisé partout dans OctoBot.

Une **Team** (équipe) est un DAG d'agents géré par un seul agent manager. L'équipe contrôle l'ordre d'exécution, transmet les sorties entre agents et exécute optionnellement des cycles de débat et d'auto-amélioration par-dessus la passe d'exécution principale.

Le **Manager** décide de ce qui s'exécute et dans quel ordre. Il peut fonctionner selon deux modes : piloté par plan, où il produit un `ExecutionPlan` ordonné avant que le moindre agent ne se déclenche, ou piloté par les outils, où il appelle directement les agents comme des outils et renvoie un `ManagerResult`. Le bon mode dépend de la question de savoir si la tâche est suffisamment structurée pour être planifiée à l'avance.

Le **Critic** (critique) s'exécute après l'exécution de l'équipe et produit une analyse structurée des problèmes, incohérences et notes d'amélioration par agent. Sa sortie alimente directement le sous-système de mémoire.

Le **Judge** (juge) arbitre les phases de débat : à partir de l'historique de débat accumulé, il renvoie soit continuer, soit sortir, avec un résumé de synthèse optionnel. Le maximum par défaut est de trois tours.

## Modes d'exécution

Trois stratégies d'exécution d'équipe sont disponibles. **Sync** est séquentiel en une passe — le manager produit un plan ou un résultat, les agents s'exécutent dans l'ordre du DAG, et l'appel se termine une fois tous les résultats collectés. **Live** est asynchrone à exécution longue — les channels sont câblés, les agents se déclenchent à mesure que les résultats amont arrivent, et l'achèvement est signalé une fois que tous les agents terminaux ont terminé. **Deep Agents** délègue à un superviseur LangChain doté de `SubAgentMiddleware`, qui orchestre les workers comme des sous-agents et prend en charge à la fois `ainvoke` et le streaming. Le chemin Deep Agents est optionnel ; le package reste entièrement importable sans que les dépendances LangChain soient installées.

## Boucle d'auto-amélioration

Lorsqu'une équipe est configurée avec `self_improving=True`, l'exécution déclenche une passe supplémentaire en arrière-plan. Le `CriticAgent` reçoit toutes les sorties des agents et produit une analyse, puis le `MemoryAgent` écrit de nouvelles mémoires dans le `JSONMemoryStorage` de chaque agent. À l'exécution suivante, les agents récupèrent ces mémoires via des appels d'outils LLM et ajustent leur comportement en conséquence. Les deux étapes s'exécutent comme une `asyncio.Task` en arrière-plan afin de ne pas bloquer l'appelant en attente des résultats.

Les fichiers de mémoire sont stockés par classe d'agent et élagués lorsqu'ils dépassent le maximum configuré, en privilégiant les entrées à forte importance et à forte utilisation. L'effet est que les mémoires fréquemment utiles survivent à la compression tandis que les obsolètes sont écartées.

## Skills

Les skills sont des fichiers markdown avec un frontmatter YAML qui décrivent des capacités ou des connaissances de domaine qu'un agent doit connaître. Ils résident dans un répertoire `skills/` aux côtés du code de l'agent et sont découverts automatiquement au moment du build, puis transmis dans le contexte de l'agent pendant l'inférence. Des agents individuels peuvent également recevoir des skills injectés au moment de l'instanciation, indépendamment des valeurs par défaut au niveau du répertoire.

## Deep Agents et human-in-the-loop

L'intégration Deep Agents prend en charge les interruptions au niveau des outils. Une configuration d'interruption identifie quels outils nécessitent une approbation humaine avant de continuer — par exemple, les outils à haut risque comme le placement d'ordres. Lorsque l'exécution atteint l'un de ces outils, le workflow se met en pause et fait remonter un `__interrupt__` dans son résultat. L'appelant peut alors reprendre en approuvant toutes les interruptions, en les rejetant, ou en fournissant des décisions explicites par outil.

## Utilitaires

Le package inclut des helpers d'extraction JSON résilients pour analyser la sortie des LLM, qui arrive rarement sous forme de JSON propre. L'extracteur essaie plusieurs stratégies en séquence : appariement d'accolades à partir de texte mixte, extraction depuis des blocs de code délimités, extraction depuis des balises de style XML, et prétraitement pour retirer les délimiteurs et les séquences d'échappement. Un décorateur de retry asynchrone enveloppe en interne les appels LLM du manager piloté par les outils.
