---
title: "Avec Python et Git"
description: "Apprenez comment installer et démarrer votre OctoBot sur votre propre ordinateur ou serveur (Windows, Mac ou Linux) en utilisant le code Python open source directement depuis GitHub."
sidebar_position: 6
---

# Installer OctoBot avec Python et Git

## Prérequis

-   Packages installés : Python3.13.X, Python3.13.X-dev, Python3.13.X-pip, git
-   Système de build: <a href="https://www.pantsbuild.org/" rel="nofollow">Pants</a>

Le code Python d'OctoBot est un monorepo : chaque partie d'OctoBot (`commons`, `trading`, `evaluators`, ...) se trouve dans son propre dossier sous `packages` et est construite avec Pants.

Pants n'est pas fourni avec OctoBot, installez le lanceur `scie-pants` une fois et il téléchargera automatiquement la version de Pants requise par le `pants.toml` d'OctoBot lors de sa première exécution. Les instructions d'installation sont sur la <a href="https://www.pantsbuild.org/stable/docs/getting-started/installing-pants" rel="nofollow">page d'installation de Pants</a>.

:::warning
Cette installation basée sur Pants n'est pas encore supportée sur Windows. Pants ne fonctionne sur Windows qu'à travers le <a href="https://learn.microsoft.com/windows/wsl/install" rel="nofollow">sous-système Windows pour Linux (WSL 2)</a>.

Si vous êtes sur Windows, installez WSL 2, clonez OctoBot **dans** le système de fichiers Linux de votre distribution WSL et suivez les commandes Linux de ce guide depuis votre terminal WSL. Un dépôt conservé du côté Windows et atteint via `/mnt` n'est pas supporté par Pants et provoque des comportements inattendus.
:::

## Installation

**Commencez par vous assurer que python3.13, python3.13-dev et python3.13-pip sont installés sur votre ordinateur.**

### Avec la version stable actuelle (branche master)

**C'est l'installation Python recommandée.**

Clonez le dépôt OctoBot

``` bash
git clone https://github.com/Drakkar-Software/OctoBot
```

Créez un environnement virtuel pour contenir les dépendances d'OctoBot et activez-le :

``` bash
cd OctoBot
python3 -m venv venv
source venv/bin/activate
```

Installez les packages python. Cette commande installe toutes les dépendances tierces des packages OctoBot dans l'environnement virtuel actif :

``` bash
pants install-deps --full ::
```

`--full` inclut également les dépendances optionnelles listées dans les fichiers `full_requirements.txt`, qui sont nécessaires à certaines tentacles.


> Sur certaines configurations comme les architectures ARM 32 bits, une erreur liée à `rust` peut apparaître pendant `pants install-deps --full ::`, lors de l'installation de `cryptography`.
Dans ce cas, installez le `compilateur rust` : `cryptography` est codé en `rust`.
``` bash
sudo apt-get install -y rustc
```
Vous pouvez ensuite relancer `pants install-deps --full ::`.

### Avec la version la plus récente (branche dev)

**Cette installation permet d'utiliser la version la plus à jour d'OctoBot, mais elle peut être instable selon le moment où elle est faite (des mises à jour de modules peuvent être en cours sur cette branche).**

Clonez le dépôt OctoBot en utilisant la branche **dev**

``` bash
git clone https://github.com/Drakkar-Software/OctoBot -b dev
```

*Ou, si vous avez déjà un dépôt OctoBot*

``` bash
git checkout dev
git pull
```

### Configurer PYTHONPATH

Les packages d'OctoBot ne sont pas installés dans votre environnement virtuel, ils sont utilisés directement depuis leur dossier dans le dépôt. Python a donc besoin de savoir où se trouve chacun d'entre eux : c'est le rôle de `PYTHONPATH`.

Depuis le dossier du dépôt OctoBot :

``` bash
ROOT=$PWD
export PYTHONPATH="$ROOT:$ROOT/packages/agents:$ROOT/packages/async_channel:$ROOT/packages/backtesting:$ROOT/packages/binary:$ROOT/packages/commons:$ROOT/packages/copy:$ROOT/packages/evaluators:$ROOT/packages/flow:$ROOT/packages/node:$ROOT/packages/protocol:$ROOT/packages/services:$ROOT/packages/sync:$ROOT/packages/tentacles_manager:$ROOT/packages/trading"
```

Remarques :
- Utilisez des chemins absolus, certains sous-processus d'OctoBot sont démarrés depuis d'autres dossiers et ne pourraient pas résoudre des chemins relatifs.
- Cette liste reprend les `root_patterns` du `pants.toml` d'OctoBot, mettez-la à jour lorsqu'un nouveau package est ajouté.

### Installer les dernières tentacles :
> Attention : utiliser les dernières tentacles peut casser votre OctoBot 

``` bash
cd OctoBot
pants install-deps --full ::
export TENTACLES_URL_TAG="latest"
python3 start.py tentacles --install --all
```

## Utilisation

La commande suivante remplace l'*OctoBot Launcher* :

``` bash
python3 start.py
```

Assurez-vous que votre environnement virtuel est activé et que `PYTHONPATH` est défini dans le terminal qui exécute cette commande. Les deux sont perdus à la fermeture du terminal, ils doivent donc être redéfinis dans chaque nouveau terminal.

## Mise à jour

Exécuter la commande suivante va mettre à jour votre OctoBot Python en utilisant la dernière version de la branche sélectionnée (`master` ou `dev`) et installer les dépendances associées. Activez d'abord votre environnement virtuel, les dépendances y sont installées.
``` bash
cd OctoBot
source venv/bin/activate
git pull
pants install-deps --full ::
```
Le prochain redémarrage mettra automatiquement à jour les tentacles de votre OctoBot.

## Python3

Ici, **python3** fait référence à votre installation de **Python3.13.X**, adaptez simplement les commandes à votre configuration si elle diffère (cela peut être python, python3, python3.13, etc : cela dépend de votre environnement).

## Lancer OctoBot en tâche de fond

> Pour les distributions unix uniquement

Avec la commande Linux screen, vous pouvez envoyer en arrière-plan des applications lancées dans un terminal et les ramener au premier plan quand vous voulez les consulter.

``` bash
sudo apt-get install -y screen
screen python3 start.py
```

Vous avez besoin du numéro au début du nom de la fenêtre pour vous y rattacher. Si vous l'avez oublié, vous pouvez toujours utiliser l'option -ls (list), comme ci-dessous, pour obtenir la liste des fenêtres détachées :

``` bash
screen -ls
screen -r 23167
```

(23167 est un exemple de valeur)

OctoBot, qui tournait en arrière-plan, est ramené dans votre terminal comme s'il ne l'avait jamais quitté.
