---
title: "Avec Python et Git"
description: "Apprenez comment installer et démarrer votre OctoBot sur votre propre ordinateur ou serveur (Windows, Mac ou Linux) en utilisant le code Python open source directement depuis GitHub."
sidebar_position: 6
---



# Installer OctoBot avec Python and Git

:::info
  La traduction française de cette page est en cours.
:::

## Prérequis

-   Packages installed : Python3.10.X, Python3.10.X-dev, Python3.10.X-pip, git

## Installation

**First, make sure you have python3.10 and python3.10-dev and python3.10-pip installed on your computer.**

### Avec la version stable actuelle (branche master)

**This is the recommended python installation.**

Clone the OctoBot repository

``` bash
git clone https://github.com/Drakkar-Software/OctoBot
```

Install python packages :

``` bash
cd OctoBot
python3 -m pip install -Ur requirements.txt
```


> On some setup like 32-bit ARM architectures, you might get a `rust` related error while running `python3 -m pip install -Ur requirements.txt` when installing `cryptography`.
If this happens, you need to install the `rust compiler`: `cryptography` is coded in `rust`.
``` bash
sudo apt-get install -y rustc
```
You can then restart `python3 -m pip install -Ur requirements.txt`.

### Avec la version la plus récente (branche dev)

**This is installation allows to use the most up-to-date version of OctoBot but might broken depending on the moment it is being done (modules updates might be in progress in this branch).**

Clone the OctoBot repository using the **dev** branch

``` bash
git clone https://github.com/Drakkar-Software/OctoBot -b dev
```

*Or if you already have an OctoBot repository*

``` bash
git checkout dev
git pull
```

### Installer les dernières tentacles :
> Warning: using the latest tentacles might break your OctoBot 

#### Sur Unix
``` bash
cd OctoBot
python3 -m pip install -Ur requirements.txt
export TENTACLES_URL_TAG="latest"
python3 start.py tentacles --install --all
```
#### Sur Windows
``` bash
cd OctoBot
python3 -m pip install -Ur requirements.txt
SET TENTACLES_URL_TAG=latest
python3 start.py tentacles --install --all
```

## Utilisation

The following command replaces *OctoBot Launcher*:

``` bash
python3 start.py
```

## Mise à jour

Exécuter la commande suivante va mettre à jour votre OctoBot Python en utilisant la dernière version de la branche sélectionnée (`master` ou `dev`) et installer les dépendances associées.
``` bash
git pull
cd OctoBot
python3 -m pip install -Ur requirements.txt
```
Le prochain redémarrage mettra automatiquement à jour les tentacles de votre OctoBot.

## Python3

There **python3** is refering to your **Python3.10.X** installation, just adapt the commands to match your setup if any different (might be python, python3, python3.10, etc: it depends on your environment).

## Lancer OctoBot en tâche de fond

> For unix distribution only

With the Linux screen command, you can push running terminal applications to the background and pull them forward when you want to see them.

``` bash
sudo apt-get install -y screen
screen python3 start.py
```

You need the number from the start of the window name to reattach it. If you forget it, you can always use the -ls (list) option, as shown below, to get a list of the detached windows:

``` bash
screen -ls
screen -r 23167
```

(23167 is an example value)

OctoBot has been working away in the background is now brought back to your terminal window as if it had never left.
