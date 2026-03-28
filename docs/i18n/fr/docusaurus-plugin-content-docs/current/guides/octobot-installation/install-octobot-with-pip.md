---
title: "Avec PIP"
description: "Apprenez comment installer et démarrer votre OctoBot sur votre propre ordinateur ou serveur (Windows, Mac ou Linux) en utilisant la version PIP (Python Index Package) du bot."
sidebar_position: 7
---



# Installer OctoBot avec Python index package (pip)

:::info
  La traduction française de cette page est en cours.
:::

## Prérequis

- Python 3.10 (<a href="https://www.python.org/downloads/" rel="nofollow">download</a>)
- Add python to your PATH (<a href="https://superuser.com/questions/143119/how-do-i-add-python-to-the-windows-path" rel="nofollow">tutorial windows</a>)

## Installation

In a command line (with python in your PATH) type the following command:

```bash
python3.10 -m pip install OctoBot
```

You can change **python3.10** to the name of the python binary you added to your PATH (for example on linux you may use **python3** or even **python** if the **python --version** commands outputs a python 3.10 version)

## Utilisation

```bash
OctoBot
```

## Mise à jour

Exécuter la commande suivante va mettre à jour votre OctoBot Python en utilisant la dernière version et installer les dépendances associées.

```bash
python3.10 -m pip install -U OctoBot
```

Le prochain redémarrage mettra automatiquement à jour les tentacles de votre OctoBot.

## Lancer plusieurs OctoBots

To run a second OctoBot on the same computer :

1.  Create a new directory and enter it
2.  Start OctoBot and stop it after 1-2min to let it create default files
3.  Open user/config.json file
4.  Change web config lines

    FROM

    ```json
    "web": {
        "auto-open-in-web-browser": true
    }
    ```

    TO

    ```json
    "web": {
        "auto-open-in-web-browser": true,
        "port": 8000
    }
    ```

    In this example, the second OctoBot's web interface is accessible at http://127.0.0.1:8000.

    Any port can be used except those already used by another OctoBot or any software on your system.

5.  Start the new OctoBot
