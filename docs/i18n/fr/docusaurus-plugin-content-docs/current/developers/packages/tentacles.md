---
title: Tentacles
description: Vue d'ensemble du package tentacles — le système de plugins d'OctoBot fournissant tous les évaluateurs, stratégies, trading modes, services et composants d'automatisation par défaut.
sidebar_position: 1
---

# Package Tentacles

Le package `tentacles` est le bundle de plugins par défaut d'OctoBot — la couche d'implémentation concrète qui se pose au-dessus des packages abstraits du framework (`octobot_evaluators`, `octobot_trading`, etc.). Chaque évaluateur, trading mode, service, agent IA, règle d'automatisation et connecteur d'exchange est livré sous forme de tentacle.

## Ce qu'est un tentacle

Un tentacle est un répertoire autonome qui vit sous l'arborescence `tentacles/` et suit une disposition fixe : un module Python avec votre implémentation, un descripteur `metadata.json`, et éventuellement un sous-répertoire `config/` contenant des fichiers de configuration par défaut (un JSON par classe) et un schéma JSON pour le moteur de rendu de formulaire.

`metadata.json` est le descripteur faisant autorité pour l'unité. Il déclare la `version` du tentacle, l'`origin_package` auquel il appartient (utilisé par le contrôle de version), la liste des `tentacles` (noms de classes Python) qu'il exporte, et une liste optionnelle `tentacles-requirements` nommant les modules de tentacles voisins qui doivent être présents pour que celui-ci fonctionne correctement.

Les fichiers `__init__.py` de premier niveau présents dans toute l'arborescence sont **générés** par `tentacles_manager`, et non écrits à la main. Chacun est construit autour d'un appel à `check_tentacle_version()` : si la version déclarée dans `metadata.json` est inférieure à la version minimale compatible de son package, l'import est ignoré et une erreur est journalisée — le reste du système continue de fonctionner sans être affecté. Cela rend la frontière des plugins fortement isolée : un mauvais tentacle ne peut pas faire planter OctoBot au démarrage.

## Découverte et chargement

Au démarrage, `octobot_tentacles_manager` parcourt l'arborescence du répertoire `tentacles/` jusqu'à trois niveaux de dossiers en profondeur, à la recherche de tout répertoire contenant des sous-répertoires dotés d'un fichier `metadata.json`. Cette heuristique détermine le chemin de type du tentacle (par exemple `Evaluator/TA`, `Trading/Mode`) sans nécessiter de registre ni d'appel d'enregistrement explicite. Chaque module découvert est analysé en un objet modèle `Tentacle` qui suit le chemin de type, les noms de classes, la version, le package d'origine et un éventuel `tentacle_group`.

Le résultat est mis en cache dans un dictionnaire au niveau du module indexé par nom de classe. Tout ce qui se trouve en aval — vérifications d'activation, résolution de configuration, chargement de documentation et recherches de chemins de ressources — passe par ce cache via l'API `loaders`.

Les tentacles peuvent également être enregistrés par programmation via `register_extra_tentacle_data` pour les cas où une classe de tentacle ne peut pas être découverte sur le disque (par exemple des tentacles générés dynamiquement ou compilés).

## Configuration : référence vs. spécifique au profil

Chaque classe de tentacle possède une **configuration de référence** stockée dans son propre répertoire `config/`. Ce fichier est la valeur par défaut d'usine et n'est jamais modifié à l'exécution.

Lorsqu'un utilisateur (ou un profil) personnalise un tentacle, une **copie spécifique au profil** est écrite dans le dossier `specific_config/` du profil actif. À l'exécution, `get_config()` recherche d'abord un fichier spécifique au profil ; s'il n'en existe pas, il se rabat sur la configuration de référence. Une réinitialisation d'usine se contente de recopier le fichier de référence par-dessus la copie spécifique au profil.

L'état d'activation — quels évaluateurs et trading modes sont effectivement activés — est stocké séparément dans `tentacles_config.json` à la racine du profil. Ce fichier est lui aussi géré par `TentaclesSetupConfiguration`, qui sait que les sous-types évaluateur et trading mode sont désactivés par défaut (les utilisateurs doivent les activer explicitement dans un profil), tandis que les services et les tentacles utilitaires s'activent automatiquement à l'installation. Lorsqu'un nouveau tentacle est installé dans un `tentacle_group`, le manager peut automatiquement basculer l'état d'activation du membre par défaut du groupe afin d'éviter d'exécuter des implémentations en double.

Les profils livrés dans le répertoire `tentacles/profiles/` sont fournis avec leurs propres fichiers `tentacles_config.json` et `specific_config/`, de sorte qu'un profil peut surcharger d'emblée à la fois l'état d'activation et les valeurs de paramètres.

## Relation avec tentacles_manager

Le package `tentacles` (ce dépôt) ne contient que des implémentations. Toutes les opérations de cycle de vie — installation, mise à jour, désinstallation, packaging, génération des fichiers init, contrôle de version, gestion de la configuration — vivent dans le package distinct `octobot_tentacles_manager`. Les deux ne sont couplés que par la convention de disposition des fichiers et le contrat des `__init__.py` générés. Cette séparation signifie que le framework peut fonctionner avec n'importe quel bundle de plugins conforme, pas seulement le bundle par défaut fourni ici.

## Évaluateurs

Les évaluateurs analysent les données de marché et produisent un signal normalisé (`eval_note` dans `[-1, 1]`). Quatre types existent : les évaluateurs **TA** se déclenchent à chaque bougie clôturée et utilisent des indicateurs techniques, les évaluateurs **RealTime** réagissent aux événements de marché en direct, les évaluateurs **Social** consomment des flux de données externes (fear & greed, actualités, etc.), et les évaluateurs **Strategy** agrègent les signaux d'autres évaluateurs en une décision de trading finale.

Les évaluateurs de stratégie adossés à des LLM peuvent utiliser soit un pattern d'agents parallèles rapide, soit un superviseur LangChain pour un raisonnement plus poussé. Les évaluateurs basés sur le DSL permettent aux utilisateurs de définir une logique d'évaluation personnalisée sous forme de scripts.

## Trading Modes

Les trading modes définissent la manière dont OctoBot traduit les signaux en ordres. Chaque mode se divise en un producteur (décide quoi trader et quand) et un consommateur (exécute les opérations d'ordres sur l'exchange).

Le package est livré avec des modes grid/staggered, des modes de rééquilibrage d'index, des modes DCA, des modes quotidiens basés sur des signaux, des modes de copy-trading qui répliquent des signaux ou des profils distants, et des modes DSL où toute la logique de trading est un script écrit par l'utilisateur. Les modes index pilotés par l'IA utilisent des équipes d'agents pour déterminer les allocations cibles du portefeuille au lieu de poids fixes.

Les connecteurs d'exchanges sont majoritairement basés sur CCXT, avec des exceptions notables pour les marchés de prédiction (Polymarket avec règlement on-chain EVM) et les DEX de perpétuels (Hyperliquid). Un connecteur CCXT générique gère n'importe quel exchange dépourvu de tentacle dédié.

## Agents IA

Les équipes d'agents orchestrent plusieurs sous-agents pilotés par LLM pour l'analyse de marché. Une équipe simple exécute les sous-agents en parallèle et résume les résultats pour une faible latence. Une équipe approfondie utilise un superviseur LangChain pour une profondeur de raisonnement supérieure. Pour le trading d'index, un pattern structuré de débat haussier/baissier avec évaluation du risque et décisions d'allocation à mémoire est utilisé.

Les backends LLM prennent en charge OpenAI, Anthropic, Ollama, Gemini, Azure, Bedrock et d'autres fournisseurs. Les agents déclarent une préférence vitesse/qualité afin que le système sélectionne le niveau de modèle approprié.

## Services et automatisation

Les service feeds font le pont entre les sources de données externes et le système d'évaluateurs. Les interfaces fournissent un tableau de bord web, un bot Telegram et une API Node pour la gestion multi-instances. Les notifiers diffusent des messages via Telegram, Twitter/X et WebSocket.

Le système d'automatisation est déclaratif : un événement déclencheur (prix, portefeuille, P&L, volatilité ou seuil temporel) combiné à une condition de garde optionnelle et à une action (notifier, tout vendre, annuler des ordres, arrêter le trading, mettre les stratégies en pause). Les conditions peuvent être des scripts DSL pour une logique complexe. Chaque déclencheur prend en charge des réglages de déclenchement unique et de fréquence minimale de re-déclenchement.

## DSL et scripting

La couche DSL enregistre des opérateurs auprès de l'interpréteur de commons pour les indicateurs techniques, l'accès aux données d'exchange, la gestion des ordres, les wallets blockchain et les règles d'automatisation. Une bibliothèque de scripting de plus haut niveau fournit une API asynchrone pour les trading modes — couvrant la création d'ordres, le dimensionnement des positions, le chaînage et le regroupement d'ordres, les annotations de graphiques et la distribution d'index.

## Entrées utilisateur

Chaque tentacle configurable implémente `init_user_inputs`, qui enregistre des paramètres auprès du framework d'interface. Cela se sérialise en un schéma JSON rendu sous forme de formulaire de configuration dans l'interface web.
