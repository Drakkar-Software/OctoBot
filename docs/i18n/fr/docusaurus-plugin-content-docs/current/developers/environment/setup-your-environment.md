---
title: "Configurer votre environnement"
description: "Apprenez comment créer votre environnement de développement OctoBot à partir des dépôts Python open source d'OctoBot sur GitHub en utilisant VSCode ou PyCharm."
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

- Langage de programmation: <a href="https://www.python.org/downloads/release/python-31011/" rel="nofollow">Python 3.10</a>
- Gestionnaire de version: <a href="https://git-scm.com/downloads" rel="nofollow">Git</a>
- IDE: <a href="https://www.jetbrains.com/pycharm/" rel="nofollow">PyCharm</a> or <a href="https://code.visualstudio.com/Download" rel="nofollow">Visual Studio Code</a>


## Clonage des dépôts OctoBot

Les dépôts `OctoBot` et `OctoBot-Tentacles` sont nécessaires pour configurer l'environnement de développement OctoBot.

Ouvrez un terminal dans votre dossier de projet et exécutez les commandes suivantes pour télécharger les dépôts officiels (version de développement) :


```bash
git clone https://github.com/Drakkar-Software/OctoBot.git --branch dev
git clone https://github.com/Drakkar-Software/OctoBot-Tentacles.git --branch dev
```
Remarque :
- Pour contribuer aux projets, créez d'abord un fork de ces dépôts et utilisez vos propres copies.
- Les pull requests doivent être soumises vers la branche dev de chaque dépôt.

*Pour aller plus loin*  
Vous êtes un développeur avancé qui maîtrise déjà l'architecture globale d'OctoBot et souhaite modifier ses modules principaux ?

Le code d'OctoBot étant réparti sur plusieurs dépôts GitHub (chaque dépôt couvrant un aspect du logiciel), vous devrez peut-être cloner d'autres dépôts. Plus de détails sur la [page des dépôts GitHub](github-repositories).

## Environnement VSCode pour OctoBot

### Création du projet et installation des dépendances

1. Ouvrez Visual Studio Code dans le dossier contenant les dépôts OctoBot.
2. Ouvez le terminal et créez un environnement virtuel Python 3.10 pour contenir les dépendances d'OctoBot. Commande: `python -m venv venv`
3. Activez l'environnement virtuel (`.\venv\Scripts\Activate.ps1` sur Windows ou `source venv/bin/activate` sur Linux/macOS)
<div style={{textAlign: "center"}}>
![vscode create octobot venv](/images/guides/dev_env/vscode-create-octobot-venv.png)
</div>
4. Installez les dépendances avec `python -m pip install -r OctoBot/requirements.txt -r OctoBot/dev_requirements.txt` depuis le terminal intégré de VSCode terminal, qui utilise votre environment virtuel.
<div style={{textAlign: "center"}}>
![vscode install python requirements](/images/guides/dev_env/vscode-install-python-requirements.png)
</div>


### Configuration de VSCode
1. Créez un dossier `.vscode` à la racine de votre projet.
2. Ajoutez un fichier `settings.json` au dossier `.vscode` avec ce contenu (pour utiliser l'environment virtuel créé). Note: remplacer le chemin vers l'exécutatble python sur Linux/MacOS
```json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/venv/Scripts/python.exe"
}
``` 
3. Dans la dossier `.vscode`, Créez un fichier `launch.json` avec le contenu suivant afin de définit les configurations d'exécutions. Ce fichier simplifie le développement en permettant de : 
- Démarrer OctoBot
- Lancer les tests
- Gérer les Tentacles

```json
{
  "configurations": [
    {
      "type": "debugpy",
      "name": "Start OctoBot",
      "request": "launch",
      "console": "integratedTerminal",
      "program": "${workspaceFolder}/OctoBot/start.py",
      "cwd": "${workspaceFolder}/OctoBot",
      "presentation": {
        "hidden": false,
        "group": "1.Run",
        "order": 1
      },
      "justMyCode": false,
      "args": [],
      "env": {}
    },
    {
      "type": "debugpy",
      "name": "OctoBot tests",
      "request": "launch",
      "console": "integratedTerminal",
      "cwd": "${workspaceFolder}/OctoBot",
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
      "module": "pytest"
    },
    {
      "type": "debugpy",
      "name": "OctoBot-Tentacles tests trading modes",
      "request": "launch",
      "console": "integratedTerminal",
      "cwd": "${workspaceFolder}/OctoBot",
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
      "module": "pytest"
    },
    {
      "type": "debugpy",
      "name": "Export tentacles to repo",
      "request": "launch",
      "console": "integratedTerminal",
      "program": "${workspaceFolder}/OctoBot/start.py",
      "cwd": "${workspaceFolder}/OctoBot",
      "presentation": {
        "hidden": false,
        "group": "OctoBot-Tentacles-Manager",
        "order": 31
      },
      "justMyCode": false,
      "args": [
        "tentacles",
        "-e",
        "../../OctoBot-Tentacles",
        "OctoBot-Default-Tentacles",
        "-d",
        "../OctoBot/tentacles"
      ]
    },
    {
      "type": "debugpy",
      "name": "OctoBot repair tentacles",
      "request": "launch",
      "console": "integratedTerminal",
      "program": "${workspaceFolder}/OctoBot/start.py",
      "cwd": "${workspaceFolder}/OctoBot",
      "presentation": {
        "hidden": false,
        "group": "OctoBot-Tentacles-Manager",
        "order": 32
      },
      "justMyCode": false,
      "args": [
        "tentacles",
        "--repair",
        "-d",
        "."
      ]
    },
    {
      "type": "debugpy",
      "name": "Export OctoBot-Tentacles to zip",
      "request": "launch",
      "console": "integratedTerminal",
      "program": "${workspaceFolder}/OctoBot/start.py",
      "cwd": "${workspaceFolder}/OctoBot",
      "presentation": {
        "hidden": false,
        "group": "OctoBot-Tentacles-Manager",
        "order": 33
      },
      "justMyCode": false,
      "args": [
        "tentacles",
        "-p",
        "../tentacles_default_export.zip",
        "-d",
        "../OctoBot-Tentacles"
      ]
    },
    {
      "type": "debugpy",
      "name": "Install tentacles zip",
      "request": "launch",
      "console": "integratedTerminal",
      "program": "${workspaceFolder}/OctoBot/start.py",
      "cwd": "${workspaceFolder}/OctoBot",
      "presentation": {
        "hidden": false,
        "group": "OctoBot-Tentacles-Manager",
        "order": 34
      },
      "justMyCode": false,
      "args": [
        "tentacles",
        "-i",
        "--all",
        "--location",
        "any_platform.zip"
      ]
    }
  ]
}
```

VSCode devrait maintenant afficher les configurations launch.json dans son interface utilisateur.

<div style={{textAlign: "center"}}>
![vscode run configurations selector](/images/guides/dev_env/vscode-run-configurations-selector.png)
</div>

Note: ces fichiers ont été créés avec VSCode 1.102.1 (juillet 2025). Si certaines valeurs deviennent obsolètes dans des versions ultérieures de VSCode, veuillez nous contacter pour mettre à jour ce guide. 

### Exécution d'OctoBot

#### 1. Installation des tentacles depuis un dépôt de tentacles
Maintenant que VSCode est configuré, il est nécessaire d'installer vos premiers tentacles OctoBot.

1. Exécutez la configuration `Export OctoBot-Tentacles to zip`

Cette configuration installera automatiquement tous les tentacles contenus dans un dossier local dans votre OctoBot, pour qu'il puisse les utiliser. OctoBot ne peut utiliser que les tentacles correctement installés dans son dossier `tentacles`.

Cette étape est nécessaire pour utiliser le code des tentacles cloné depuis `OctoBot-Tentacles`. Si vous ne l'effectuez pas, OctoBot téléchargera les tentacles associés à sa dernière version, qui pourraient être incompatibles avec la branche `dev` sur laquelle se trouve votre code OctoBot actuel.

<div style={{textAlign: "center"}}>
![vscode executed export tentacles to zip](/images/guides/dev_env/vscode-executed-export-tentacles-to-zip.png)
</div>

Cette action exporte les tentacles d'OctoBot-Tentacles dans une archive zip qui peut être installée sur votre OctoBot ou partagée.

2. Exécutez la configuration `Install tentacles zip`

<div style={{textAlign: "center"}}>
![vscode executed install tentacles from zip](/images/guides/dev_env/vscode-executed-install-tentacles-from-zip.png)
</div>

Cela ajoutera à votre OctoBot les tentacles contenus dans ce zip. Cette configuration peut être utilisée pour installer n'importe quel zip de tentacles.

Votre dossier local OctoBot contient maintenant le code des tentacles cloné depuis le dépôt `OctoBot-Tentacles`. Ré-exécutez `Export OctoBot-Tentacles to zip` et `Install tentacles zip` lorsque vous voulez mettre à jour vos tentacles locaux depuis le dépôt git `OctoBot-Tentacles`.  
Attention : cela écrasera toutes les modifications locales des tentacles réinstallés. Assurez-vous de sauvegarder vos changements au préalable.

#### 2. Lancement d'OctoBot

Cette configuration démarrera votre OctoBot local. Assurez-vous d'avoir d'abord installé les tentacles `OctoBot-Tentacles` (via les configurations `Export OctoBot-Tentacles to zip` et `Install tentacles zip`), sinon OctoBot installera ses tentacles par défaut et leur import pourrait échouer.

Exécutez la configuration `Start OctoBot`

<div style={{textAlign: "center"}}>
![vscode executed start octobot](/images/guides/dev_env/vscode-executed-start-octobot.png)
</div>

#### 3. Export des modifications de vos tentacles vers leur dépôt git

Cette configuration exportera les modifications de vos tentacles locaux OctoBot vers le dépôt de tentacles configuré. Elle prendra les fichiers liés à votre package de tentacles sélectionné.

Exécutez la configuration `Export tentacles to repo`


Depuis les paramètres de `launch.json`, vous pouvez modifier :
- `OctoBot-Default-Tentacles` pour sélectionner des tentacles à exporter depuis un package différent
- `OctoBot-Tentacles` pour exporter vers un dépôt git différent

#### 4. Exécution des tests

Les configurations `OctoBot tests` et `OctoBot-Tentacles tests trading modes` sont des exemples pour exécuter tous les tests OctoBot ou les tests des Trading Modes des tentacles. N'hésitez pas à ajouter d'autres configurations de test.

<div style={{textAlign: "center"}}>
![vscode executed tests](/images/guides/dev_env/vscode-executed-tests.png)
</div>


## Environnement OctoBot dans PyCharm

### Création du projet et installation des dépendances
1. Ouvrez PyCharm et sélectionnez le dossier contenant les dépôts OctoBot.
2. Créez un nouvel environnement virtuel Python 3.10 pour les dépendances d'OctoBot.
<div style={{textAlign: "center"}}>
![create pycharm interpreter](/images/guides/dev_env/create-pycharm-interpreter.png)
</div>
3. Installez les dépendances Python depuis le dossier OctoBot en exécutant dans le terminal intégré de PyCharm (qui utilise par défaut votre nouvel environnement virtuel) avec la commande `python -m pip install -r OctoBot/requirements.txt -r OctoBot/dev_requirements.txt`.
<div style={{textAlign: "center"}}>
![install octobot requirements from pycharm](/images/guides/dev_env/install-octobot-requirements-from-pycharm.png)
</div>

### Configuration des exécutions dans PyCharm

Les étapes suivantes pour créer des configurations d'exécution PyCharm utilisant l'environnement virtuel créé (celui contenant les dépendances d'OctoBot) pour chaque type de commande Python :
- Démarrer OctoBot
- Exécuter les tests
- Gérer les tentacles


#### 1. Installation des tentacles depuis un dépôt git
Cette configuration installera automatiquement tous les tentacles d'un dossier local dans votre OctoBot. OctoBot ne peut utiliser que les tentacles correctement installés dans son dossier `tentacles`.

Cette étape est nécessaire pour utiliser le code des tentacles cloné depuis `OctoBot-Tentacles`. Si vous ne l'effectuez pas, OctoBot téléchargera les tentacles de sa dernière version stable, potentiellement incompatible avec la branche `dev` utilisée.

1. Cliquez sur `Edit Configurations`
<div style={{textAlign: "center"}}>
![edit pycharm configurations](/images/guides/dev_env/edit-pycharm-configurations.png)
</div>
2. Créez la configuration `Export OctoBot-Tentacles to zip`:
- Script path: `path_to_your_octobot_repositories/OctoBot/start.py`
- Working directory: `path_to_your_octobot_repositories/OctoBot`
- Script parameters: `tentacles -p ../tentacles_default_export.zip -d ../OctoBot-Tentacles`
<div style={{textAlign: "center"}}>
![create pycharm export tentacles config](/images/guides/dev_env/create-pycharm-export-tentacles-config.png)
</div>
3. Exécutez cette configuration pour exporter les tentacles dans une archive zip qui pourra alors être installée sur votre OctoBot, ou partagée.
<div style={{textAlign: "center"}}>
![execute pycharm export tentacles](/images/guides/dev_env/execute-pycharm-export-tentacles.png)
</div>
4. Créez la configuration `Install tentacles zip` pour installer ces tentacles zippées sur votre OctoBot:
- Script path: `path_to_your_octobot_repositories/OctoBot/start.py`
- Working directory: `path_to_your_octobot_repositories/OctoBot`
- Script parameters: `tentacles -i --all --location any_platform.zip`
<div style={{textAlign: "center"}}>
![create pycharm install tentacles config](/images/guides/dev_env/create-pycharm-install-tentacles-config.png)
</div>
5. Exécutez cette configuration pour installer les tentacles. Cette configuration peut être utilisée pour installer tout zip de tentacles. 
<div style={{textAlign: "center"}}>
![execute pycharm install tentacles](/images/guides/dev_env/execute-pycharm-install-tentacles.png)
</div>

Votre dossier local OctoBot contient maintenant le code des tentacles que vous avez cloné depuis le dépôt `OctoBot-Tentacles`. Ré-exécutez `Export OctoBot-Tentacles to zip` et `Install tentacles zip` lorsque vous souhaitez mettre à jour vos tentacles locaux depuis le dépôt git `OctoBot-Tentacles`.  
Attention : cela écrasera toutes les modifications locales des tentacles réinstallés. Assurez-vous de sauvegarder vos changements au préalable.


#### 2. Lancement d'OctoBot
Cette configuration d'exécution démarrera votre OctoBot local. Assurez-vous d'avoir d'abord installé les tentacles `OctoBot-Tentacles` (via les configurations `Export OctoBot-Tentacles to zip` et `Install tentacles zip`), sinon OctoBot installera ses tentacles par défaut et leur import pourrait échouer.

1. Cliquez sur `Edit Configurations`
<div style={{textAlign: "center"}}>
![edit pycharm configurations](/images/guides/dev_env/edit-pycharm-configurations.png)
</div>
2. Créez la configuration `Start OctoBot`:
- Script path: `path_to_your_octobot_repositories/OctoBot/start.py`
- Working directory: `path_to_your_octobot_repositories/OctoBot`
<div style={{textAlign: "center"}}>
![create pycharm start octobot run config](/images/guides/dev_env/create-pycharm-start-octobot-run-config.png)
</div>
3. Exécutez cette configuration pour démarrer votre OctoBot
<div style={{textAlign: "center"}}>
![execute pycharm start octobot](/images/guides/dev_env/execute-pycharm-start-octobot.png)
</div>

Vous pouvez maintenant démarrer votre OctoBot depuis votre environnement de développement, effectuer des modifications locales et exécuter Python en mode debug. 

#### 3. Export des modifications de vos tentacles vers leur dépôt git
Cette configuration exportera les modifications de vos tentacles OctoBot locaux vers le dépôt de tentacles configuré. Elle sélectionnera les fichiers liés à au package de tentacles sélectionné.

1. Cliquez sur `Edit Configurations`
<div style={{textAlign: "center"}}>
![edit pycharm configurations](/images/guides/dev_env/edit-pycharm-configurations.png)
</div>
2. Créez la configuration `Export tentacles to repo`:
- Script path: `path_to_your_octobot_repositories/OctoBot/start.py`
- Working directory: `path_to_your_octobot_repositories/OctoBot`
- Script parameters: `tentacles -e ../../OctoBot-Tentacles OctoBot-Default-Tentacles -d ../OctoBot/tentacles`
<div style={{textAlign: "center"}}>
![create pycharm export tentacles to repo config](/images/guides/dev_env/create-pycharm-export-tentacles-to-repo-config.png)
</div>
3. Exécutez cette configuration pour appliquer les modifications de votre dossier OctoBot/tentacles vers le dépôt git de ce package de tentacles. 
<div style={{textAlign: "center"}}>
![execute pycharm export tentacles to repo](/images/guides/dev_env/execute-pycharm-export-tentacles-to-repo.png)
</div>

Dans les paramètres du script, vous pouvez modifier:
- `OctoBot-Default-Tentacles` pour sélectionner des tentacles à exporter selon un package différent. Les packages sont définis dans le `metadata.json` de chaque tentacle, sous la clé `origin_package`.
- `OctoBot-Tentacles` pour exporter les tentacles vers un dépôt git différent.


#### 4. Exécution des tests

Créez des configurations d'exécution `pytest` pour lancer les tests OctoBot. N'hésitez pas à ajouter d'autres configurations de test selon vos besoins.

<div style={{textAlign: "center"}}>
![create pycharm tests config](/images/guides/dev_env/create-pycharm-tests-config.png)
</div>
<div style={{textAlign: "center"}}>
![execute pycharm tests](/images/guides/dev_env/execute-pycharm-tests.png)
</div>
