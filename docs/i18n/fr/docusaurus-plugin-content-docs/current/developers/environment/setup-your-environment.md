---
title: "Configurer votre environnement"
description: "Apprenez comment créer votre environnement de développement OctoBot à partir du dépôt Python open source d'OctoBot sur GitHub en utilisant VSCode ou PyCharm."
sidebar_position: 3
---



# Installation pour développeur d'OctoBot

Cet environnement permet d'exécuter un OctoBot en local via le code Python, d'y apporter des modifications, puis de les déboguer et tester.

- [**Install OctoBot requirements**](#install-octobot-requirements)
- [**Cloning OctoBot repositories**](#cloning-octobot-repositories-with-git)
- [**Setting up PyCharm IDE**](#setting-up-pycharm-ide)
- [**Setting up Visual Studio Code IDE**](#setting-up-visual-studio-code-ide)

## Installer les prérequis d'OctoBot

**Télécharger et installer:**

- Langage de programmation: <a href="https://www.python.org/downloads/release/python-3130/" rel="nofollow">Python 3.13</a>
- Gestionnaire de version: <a href="https://git-scm.com/downloads" rel="nofollow">Git</a>
- Système de build: <a href="https://www.pantsbuild.org/" rel="nofollow">Pants</a>
- IDE: <a href="https://www.jetbrains.com/pycharm/" rel="nofollow">PyCharm</a> or <a href="https://code.visualstudio.com/Download" rel="nofollow">Visual Studio Code</a>

Le code d'OctoBot est un monorepo Python : chaque partie d'OctoBot (`commons`, `trading`, `evaluators`, ...) se trouve dans son propre dossier sous `packages` et est construite avec Pants.

Pants n'est pas fourni avec OctoBot, installez le lanceur `scie-pants` une fois et il téléchargera automatiquement la version de Pants requise par le `pants.toml` d'OctoBot lors de sa première exécution. Les instructions d'installation sont sur la <a href="https://www.pantsbuild.org/stable/docs/getting-started/installing-pants" rel="nofollow">page d'installation de Pants</a>.

:::warning
Cette installation basée sur Pants n'est pas encore supportée sur Windows. Pants ne fonctionne sur Windows qu'à travers le <a href="https://learn.microsoft.com/windows/wsl/install" rel="nofollow">sous-système Windows pour Linux (WSL 2)</a>.

Si vous êtes sur Windows, installez WSL 2, clonez le dépôt OctoBot **dans** le système de fichiers Linux de votre distribution WSL et suivez les commandes Linux/macOS de ce guide. Un dépôt conservé du côté Windows et atteint via `/mnt` n'est pas supporté par Pants et provoque des comportements inattendus.

VSCode et PyCharm peuvent tous les deux ouvrir un projet situé dans WSL, dans ce cas votre interpréteur python est `venv/bin/python` et les chemins du `PYTHONPATH` ci-dessous sont séparés par `:`.
:::


## Clonage du dépôt OctoBot

Le dépôt `OctoBot` suffit pour configurer l'environnement de développement OctoBot. Il contient tous les packages du logiciel ainsi que les tentacles.

Ouvrez un terminal dans votre dossier de projet et exécutez la commande suivante pour télécharger le dépôt officiel (version de développement) :


```bash
git clone https://github.com/Drakkar-Software/OctoBot.git --branch dev
```
Remarque :
- Pour contribuer au projet, créez d'abord un fork de ce dépôt et utilisez votre propre copie.
- Les pull requests doivent être soumises vers la branche dev du dépôt.

Chaque partie du logiciel se trouve dans son propre dossier sous `packages`. Plus de détails sur la [page des dépôts GitHub](github-repositories).

## Environnement VSCode pour OctoBot

### Création du projet et installation des dépendances

1. Ouvrez Visual Studio Code dans le dossier `OctoBot` cloné.
2. Ouvez le terminal et créez un environnement virtuel Python 3.13 pour contenir les dépendances d'OctoBot. Commande: `python -m venv venv`
3. Activez l'environnement virtuel : `source venv/bin/activate`
<div style="text-align: center">

![vscode create octobot venv](/images/guides/dev_env/vscode-create-octobot-venv.png)

</div>
4. Installez les dépendances depuis le terminal intégré de VSCode, qui utilise votre environment virtuel. La configuration de build `pants.toml` est à la racine du dépôt, exécutez la commande d'installation de Pants depuis cet emplacement :
```bash
pants install-deps --full ::
```
Cette commande installe toutes les dépendances tierces des packages OctoBot dans l'environnement virtuel actif. `--full` inclut également les dépendances optionnelles listées dans les fichiers `full_requirements.txt`, nécessaires à certaines tentacles, ainsi que les dépendances de test et de développement.
<div style="text-align: center">

![vscode install python requirements](/images/guides/dev_env/vscode-install-python-requirements.png)

</div>


### Configuration de VSCode
1. Créez un dossier `.vscode` à la racine de votre projet.
2. Ajoutez un fichier `settings.json` au dossier `.vscode` avec ce contenu (pour utiliser l'environment virtuel créé)
```json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/venv/bin/python"
}
``` 
3. Dans la dossier `.vscode`, Créez un fichier `launch.json` avec le contenu suivant afin de définit les configurations d'exécutions. Ce fichier simplifie le développement en permettant de : 
- Démarrer OctoBot
- Lancer les tests
- Gérer les Tentacles

Chaque configuration définit une variable d'environnement `PYTHONPATH`. Les packages d'OctoBot ne sont pas installés dans votre environnement virtuel, ils sont utilisés directement depuis leur dossier dans le dépôt, Python a donc besoin de savoir où se trouve chacun d'entre eux. Cette liste reprend les `root_patterns` du `pants.toml` d'OctoBot, mettez-la à jour lorsqu'un nouveau package est ajouté.

```json
{
  "configurations": [
    {
      "type": "debugpy",
      "name": "Start OctoBot",
      "request": "launch",
      "console": "integratedTerminal",
      "program": "${workspaceFolder}/start.py",
      "cwd": "${workspaceFolder}",
      "presentation": {
        "hidden": false,
        "group": "1.Run",
        "order": 1
      },
      "justMyCode": false,
      "args": [],
      "env": {
        "PYTHONPATH": "${workspaceFolder}:${workspaceFolder}/packages/agents:${workspaceFolder}/packages/async_channel:${workspaceFolder}/packages/backtesting:${workspaceFolder}/packages/binary:${workspaceFolder}/packages/commons:${workspaceFolder}/packages/copy:${workspaceFolder}/packages/evaluators:${workspaceFolder}/packages/flow:${workspaceFolder}/packages/node:${workspaceFolder}/packages/protocol:${workspaceFolder}/packages/services:${workspaceFolder}/packages/sync:${workspaceFolder}/packages/tentacles_manager:${workspaceFolder}/packages/trading"
      }
    },
    {
      "type": "debugpy",
      "name": "OctoBot tests",
      "request": "launch",
      "console": "integratedTerminal",
      "cwd": "${workspaceFolder}",
      "presentation": {
        "hidden": false,
        "group": "2.Test",
        "order": 20
      },
      "justMyCode": false,
      "args": [
        "tests",
        "--no-header",
        "--disable-warnings",
        "--show-capture=no",
        "-v",
        "-vv",
        "-k",
        " "
      ],
      "module": "pytest",
      "env": {
        "PYTHONPATH": "${workspaceFolder}:${workspaceFolder}/packages/agents:${workspaceFolder}/packages/async_channel:${workspaceFolder}/packages/backtesting:${workspaceFolder}/packages/binary:${workspaceFolder}/packages/commons:${workspaceFolder}/packages/copy:${workspaceFolder}/packages/evaluators:${workspaceFolder}/packages/flow:${workspaceFolder}/packages/node:${workspaceFolder}/packages/protocol:${workspaceFolder}/packages/services:${workspaceFolder}/packages/sync:${workspaceFolder}/packages/tentacles_manager:${workspaceFolder}/packages/trading"
      }
    },
    {
      "type": "debugpy",
      "name": "Tentacles tests trading modes",
      "request": "launch",
      "console": "integratedTerminal",
      "cwd": "${workspaceFolder}",
      "presentation": {
        "hidden": false,
        "group": "2.Test",
        "order": 21
      },
      "justMyCode": false,
      "args": [
        "tentacles/Trading/Mode",
        "--no-header",
        "--disable-warnings",
        "--show-capture=no",
        "-v",
        "-vv",
        "-s",
        "-k",
        " "
      ],
      "module": "pytest",
      "env": {
        "PYTHONPATH": "${workspaceFolder}:${workspaceFolder}/packages/agents:${workspaceFolder}/packages/async_channel:${workspaceFolder}/packages/backtesting:${workspaceFolder}/packages/binary:${workspaceFolder}/packages/commons:${workspaceFolder}/packages/copy:${workspaceFolder}/packages/evaluators:${workspaceFolder}/packages/flow:${workspaceFolder}/packages/node:${workspaceFolder}/packages/protocol:${workspaceFolder}/packages/services:${workspaceFolder}/packages/sync:${workspaceFolder}/packages/tentacles_manager:${workspaceFolder}/packages/trading"
      }
    },
    {
      "type": "debugpy",
      "name": "OctoBot repair tentacles",
      "request": "launch",
      "console": "integratedTerminal",
      "program": "${workspaceFolder}/start.py",
      "cwd": "${workspaceFolder}",
      "presentation": {
        "hidden": false,
        "group": "3.Tentacles",
        "order": 32
      },
      "justMyCode": false,
      "args": [
        "tentacles",
        "--repair",
        "-d",
        "."
      ],
      "env": {
        "PYTHONPATH": "${workspaceFolder}:${workspaceFolder}/packages/agents:${workspaceFolder}/packages/async_channel:${workspaceFolder}/packages/backtesting:${workspaceFolder}/packages/binary:${workspaceFolder}/packages/commons:${workspaceFolder}/packages/copy:${workspaceFolder}/packages/evaluators:${workspaceFolder}/packages/flow:${workspaceFolder}/packages/node:${workspaceFolder}/packages/protocol:${workspaceFolder}/packages/services:${workspaceFolder}/packages/sync:${workspaceFolder}/packages/tentacles_manager:${workspaceFolder}/packages/trading"
      }
    },
    {
      "type": "debugpy",
      "name": "Export tentacles to zip",
      "request": "launch",
      "console": "integratedTerminal",
      "program": "${workspaceFolder}/start.py",
      "cwd": "${workspaceFolder}",
      "presentation": {
        "hidden": false,
        "group": "3.Tentacles",
        "order": 33
      },
      "justMyCode": false,
      "args": [
        "tentacles",
        "-p",
        "tentacles_default_export.zip",
        "-d",
        "packages/tentacles"
      ],
      "env": {
        "PYTHONPATH": "${workspaceFolder}:${workspaceFolder}/packages/agents:${workspaceFolder}/packages/async_channel:${workspaceFolder}/packages/backtesting:${workspaceFolder}/packages/binary:${workspaceFolder}/packages/commons:${workspaceFolder}/packages/copy:${workspaceFolder}/packages/evaluators:${workspaceFolder}/packages/flow:${workspaceFolder}/packages/node:${workspaceFolder}/packages/protocol:${workspaceFolder}/packages/services:${workspaceFolder}/packages/sync:${workspaceFolder}/packages/tentacles_manager:${workspaceFolder}/packages/trading"
      }
    },
    {
      "type": "debugpy",
      "name": "Install tentacles zip",
      "request": "launch",
      "console": "integratedTerminal",
      "program": "${workspaceFolder}/start.py",
      "cwd": "${workspaceFolder}",
      "presentation": {
        "hidden": false,
        "group": "3.Tentacles",
        "order": 34
      },
      "justMyCode": false,
      "args": [
        "tentacles",
        "-i",
        "--all",
        "--location",
        "output/any_platform.zip"
      ],
      "env": {
        "ALLOW_UNSIGNED_TENTACLES": "true",
        "PYTHONPATH": "${workspaceFolder}:${workspaceFolder}/packages/agents:${workspaceFolder}/packages/async_channel:${workspaceFolder}/packages/backtesting:${workspaceFolder}/packages/binary:${workspaceFolder}/packages/commons:${workspaceFolder}/packages/copy:${workspaceFolder}/packages/evaluators:${workspaceFolder}/packages/flow:${workspaceFolder}/packages/node:${workspaceFolder}/packages/protocol:${workspaceFolder}/packages/services:${workspaceFolder}/packages/sync:${workspaceFolder}/packages/tentacles_manager:${workspaceFolder}/packages/trading"
      }
    }
  ]
}
```

VSCode devrait maintenant afficher les configurations launch.json dans son interface utilisateur.

<div style="text-align: center">

![vscode run configurations selector](/images/guides/dev_env/vscode-run-configurations-selector.png)

</div>

Note: ces fichiers ont été créés avec VSCode 1.102.1 (juillet 2025). Si certaines valeurs deviennent obsolètes dans des versions ultérieures de VSCode, veuillez nous contacter pour mettre à jour ce guide. 

### Exécution d'OctoBot

#### 1. Installation des tentacles
Maintenant que VSCode est configuré, il est nécessaire d'installer vos premiers tentacles OctoBot.

Le code source des tentacles se trouve dans le dossier `packages/tentacles` du dépôt. OctoBot ne peut utiliser que les tentacles correctement installés dans son dossier `tentacles`, qui est généré à partir de `packages/tentacles`. Ne modifiez jamais directement le dossier généré `tentacles`, il est écrasé à chaque installation.

1. Exécutez la configuration `Export tentacles to zip`

Cette étape est nécessaire pour utiliser le code des tentacles du dépôt. Si vous ne l'effectuez pas, OctoBot téléchargera les tentacles associés à sa dernière version, qui pourraient être incompatibles avec la branche `dev` sur laquelle se trouve votre code OctoBot actuel.

<div style="text-align: center">

![vscode executed export tentacles to zip](/images/guides/dev_env/vscode-executed-export-tentacles-to-zip.png)

</div>

Cette action exporte les tentacles dans une archive zip située dans `output/any_platform.zip`, qui peut être installée sur votre OctoBot ou partagée.

2. Exécutez la configuration `Install tentacles zip`

<div style="text-align: center">

![vscode executed install tentacles from zip](/images/guides/dev_env/vscode-executed-install-tentacles-from-zip.png)

</div>

Cela ajoutera à votre OctoBot les tentacles contenus dans ce zip. Cette configuration peut être utilisée pour installer n'importe quel zip de tentacles.

Ré-exécutez `Export tentacles to zip` et `Install tentacles zip` à chaque modification dans `packages/tentacles`, c'est ce qui applique vos changements à l'OctoBot qui s'exécute.  
Attention : cela écrasera toutes les modifications locales faites dans le dossier généré `tentacles`. Assurez-vous de sauvegarder vos changements au préalable.

#### 2. Lancement d'OctoBot

Cette configuration démarrera votre OctoBot local. Assurez-vous d'avoir d'abord installé vos tentacles (via les configurations `Export tentacles to zip` et `Install tentacles zip`), sinon OctoBot installera ses tentacles par défaut et leur import pourrait échouer.

Exécutez la configuration `Start OctoBot`

<div style="text-align: center">

![vscode executed start octobot](/images/guides/dev_env/vscode-executed-start-octobot.png)

</div>

#### 3. Exécution des tests

Les configurations `OctoBot tests` et `Tentacles tests trading modes` sont des exemples pour exécuter tous les tests OctoBot ou les tests des Trading Modes des tentacles. N'hésitez pas à ajouter d'autres configurations de test.

<div style="text-align: center">

![vscode executed tests](/images/guides/dev_env/vscode-executed-tests.png)

</div>


## Environnement OctoBot dans PyCharm

### Création du projet et installation des dépendances
1. Ouvrez PyCharm et sélectionnez le dossier `OctoBot` cloné.
2. Créez un nouvel environnement virtuel Python 3.13 pour les dépendances d'OctoBot.
<div style="text-align: center">

![create pycharm interpreter](/images/guides/dev_env/create-pycharm-interpreter.png)

</div>
3. Installez les dépendances Python depuis le terminal intégré de PyCharm, qui utilise par défaut votre nouvel environnement virtuel. La configuration de build `pants.toml` est à la racine du dépôt, exécutez la commande d'installation de Pants depuis cet emplacement :
```bash
pants install-deps --full ::
```
Cette commande installe toutes les dépendances tierces des packages OctoBot dans votre environnement virtuel. `--full` inclut également les dépendances optionnelles listées dans les fichiers `full_requirements.txt`, nécessaires à certaines tentacles, ainsi que les dépendances de test et de développement.
<div style="text-align: center">

![install octobot requirements from pycharm](/images/guides/dev_env/install-octobot-requirements-from-pycharm.png)

</div>

### Configuration des exécutions dans PyCharm

Les étapes suivantes pour créer des configurations d'exécution PyCharm utilisant l'environnement virtuel créé (celui contenant les dépendances d'OctoBot) pour chaque type de commande Python :
- Démarrer OctoBot
- Exécuter les tests
- Gérer les tentacles

Chacune de ces configurations nécessite également une variable d'environnement `PYTHONPATH`. Les packages d'OctoBot ne sont pas installés dans votre environnement virtuel, ils sont utilisés directement depuis leur dossier dans le dépôt, Python a donc besoin de savoir où se trouve chacun d'entre eux. Cette liste reprend les `root_patterns` du `pants.toml` d'OctoBot, mettez-la à jour lorsqu'un nouveau package est ajouté.

Dans chaque configuration d'exécution ci-dessous, renseignez le champ **Environment variables** avec la valeur suivante, en remplaçant `path_to_your_octobot_repository` par le chemin absolu de votre dépôt OctoBot :

```bash
PYTHONPATH=path_to_your_octobot_repository:path_to_your_octobot_repository/packages/agents:path_to_your_octobot_repository/packages/async_channel:path_to_your_octobot_repository/packages/backtesting:path_to_your_octobot_repository/packages/binary:path_to_your_octobot_repository/packages/commons:path_to_your_octobot_repository/packages/copy:path_to_your_octobot_repository/packages/evaluators:path_to_your_octobot_repository/packages/flow:path_to_your_octobot_repository/packages/node:path_to_your_octobot_repository/packages/protocol:path_to_your_octobot_repository/packages/services:path_to_your_octobot_repository/packages/sync:path_to_your_octobot_repository/packages/tentacles_manager:path_to_your_octobot_repository/packages/trading
```


#### 1. Installation des tentacles
Le code source des tentacles se trouve dans le dossier `packages/tentacles` du dépôt. OctoBot ne peut utiliser que les tentacles correctement installés dans son dossier `tentacles`, qui est généré à partir de `packages/tentacles`. Ne modifiez jamais directement le dossier généré `tentacles`, il est écrasé à chaque installation.

Cette étape est nécessaire pour utiliser le code des tentacles du dépôt. Si vous ne l'effectuez pas, OctoBot téléchargera les tentacles de sa dernière version stable, potentiellement incompatible avec la branche `dev` utilisée.

1. Cliquez sur `Edit Configurations`
<div style="text-align: center">

![edit pycharm configurations](/images/guides/dev_env/edit-pycharm-configurations.png)

</div>
2. Créez la configuration `Export tentacles to zip`:
- Script path: `path_to_your_octobot_repository/start.py`
- Working directory: `path_to_your_octobot_repository`
- Script parameters: `tentacles -p tentacles_default_export.zip -d packages/tentacles`
<div style="text-align: center">

![create pycharm export tentacles config](/images/guides/dev_env/create-pycharm-export-tentacles-config.png)

</div>
3. Exécutez cette configuration pour exporter les tentacles dans une archive zip située dans `output/any_platform.zip`, qui pourra alors être installée sur votre OctoBot, ou partagée.
<div style="text-align: center">

![execute pycharm export tentacles](/images/guides/dev_env/execute-pycharm-export-tentacles.png)

</div>
4. Créez la configuration `Install tentacles zip` pour installer ces tentacles zippées sur votre OctoBot:
- Script path: `path_to_your_octobot_repository/start.py`
- Working directory: `path_to_your_octobot_repository`
- Script parameters: `tentacles -i --all --location output/any_platform.zip`
- Ajoutez `ALLOW_UNSIGNED_TENTACLES=true` au champ **Environment variables**, les tentacles construites localement n'ont pas de fichier de signature
<div style="text-align: center">

![create pycharm install tentacles config](/images/guides/dev_env/create-pycharm-install-tentacles-config.png)

</div>
5. Exécutez cette configuration pour installer les tentacles. Cette configuration peut être utilisée pour installer tout zip de tentacles. 
<div style="text-align: center">

![execute pycharm install tentacles](/images/guides/dev_env/execute-pycharm-install-tentacles.png)

</div>

Ré-exécutez `Export tentacles to zip` et `Install tentacles zip` à chaque modification dans `packages/tentacles`, c'est ce qui applique vos changements à l'OctoBot qui s'exécute.  
Attention : cela écrasera toutes les modifications locales faites dans le dossier généré `tentacles`. Assurez-vous de sauvegarder vos changements au préalable.


#### 2. Lancement d'OctoBot
Cette configuration d'exécution démarrera votre OctoBot local. Assurez-vous d'avoir d'abord installé vos tentacles (via les configurations `Export tentacles to zip` et `Install tentacles zip`), sinon OctoBot installera ses tentacles par défaut et leur import pourrait échouer.

1. Cliquez sur `Edit Configurations`
<div style="text-align: center">

![edit pycharm configurations](/images/guides/dev_env/edit-pycharm-configurations.png)

</div>
2. Créez la configuration `Start OctoBot`:
- Script path: `path_to_your_octobot_repository/start.py`
- Working directory: `path_to_your_octobot_repository`
<div style="text-align: center">

![create pycharm start octobot run config](/images/guides/dev_env/create-pycharm-start-octobot-run-config.png)

</div>
3. Exécutez cette configuration pour démarrer votre OctoBot
<div style="text-align: center">

![execute pycharm start octobot](/images/guides/dev_env/execute-pycharm-start-octobot.png)

</div>

Vous pouvez maintenant démarrer votre OctoBot depuis votre environnement de développement, effectuer des modifications locales et exécuter Python en mode debug. 

#### 3. Exécution des tests

Créez des configurations d'exécution `pytest` pour lancer les tests OctoBot. N'hésitez pas à ajouter d'autres configurations de test selon vos besoins.

<div style="text-align: center">

![create pycharm tests config](/images/guides/dev_env/create-pycharm-tests-config.png)

</div>
<div style="text-align: center">

![execute pycharm tests](/images/guides/dev_env/execute-pycharm-tests.png)

</div>
