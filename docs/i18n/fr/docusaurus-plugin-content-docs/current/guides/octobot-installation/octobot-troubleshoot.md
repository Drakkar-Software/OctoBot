---
title: "Résoudre les problèmes"
description: "Des questions lors de l'installation d'OctoBot ? Consultez les problèmes d'installation les plus courants dans notre guide de dépannage."
sidebar_position: 8
---



# Résoudre les problèmes d'OctoBot

:::info
  La traduction française de cette page est en cours.
:::

## Conserver votre configuration et historique après une mise à jour

Sur OctoBot, le dossier `user`, localisé dans le dossier dans lequel vous exécutez OctoBot contient :

- Votre configuration actuelle
- Vos profils
- Votre historique de portefeuille
- Votre historique de trades et PNL

Afin de conserver la même configuration et le même historique après une mise à jour, vous pouvez soit :

- Copier le dossier `user` de votre OctoBot précédent dans le dossier de votre nouvel OctoBot
- Ou exécuter votre nouvel OctoBot dans le même dossier que votre précédent bot. Attention : le dossier `tentacles` sera remplacé par sa nouvelle version.

## Conserver vos fichiers de backtesting après une mise à jour

Lors de la mise à jour, vous pouvez vouloir conserver vos fichiers de backtesting précédents.

Pour que votre nouvel OctoBot ai accès à vos précédents fichiers de backtesting, copiez le dossier `backtesting` (localisé dans le dossier dans lequel vous exécutiez votre OctoBot précédent) dans le dossier de votre nouvel OctoBot.

## Windows

### Synchronization temporelle

This issue happens when error messages such as `'recvWindow' must be less than ...` appear.

Open an administrator terminal (`Win + X` then `A`) and type:

```bash
net stop w32time
net start w32time
w32tm /resync
w32tm /query /status
```

Code from <a href="https://serverfault.com/questions/294787/how-do-i-force-sync-the-time-on-windows-workstation-or-server" rel="nofollow">serverfault.com</a>

Another solution found by @alpi on discord channel: [timesynctool.com](http://www.timesynctool.com)

### OctoBot est bloqué

When running OctoBot on Windows, clicking into the OctoBot terminal (Powershell or Cmd) can freeze the log output and therefore freeze OctoBot execution (OctoBot will be waiting for the log to be published to continue).

To fix this issue, untick the "QuickEdit Mode" in your terminal properties and restart it.

![Powershell](https://raw.githubusercontent.com/Drakkar-Software/OctoBot/assets/wiki_resources/powerShellEditMode.jpg)

![Cmd](https://raw.githubusercontent.com/Drakkar-Software/OctoBot/assets/wiki_resources/cmdQuickEdit.jpg)
To open the properties menu, right click on the terminal window header and select "properties".

## CentOS

### Installer OctoBot sur CentOS

Requirements

```bash
yum -y update
yum install -y git wget sqlite-devel screen
yum -y groupinstall "Development Tools"
yum -y install openssl-devel bzip2-devel libffi-devel
yum install -y screen
cd /root
wget https://www.python.org/ftp/python/3.10.11/Python-3.10.11.tgz
tar xvf Python-3.10.11.tgz
cd Python-3.10*/
./configure --enable-loadable-sqlite-extensions && make && sudo make install
```

OctoBot

```bash
git clone https://github.com/Drakkar-Software/OctoBot.git
cd OctoBot/
python3.10 -m pip install virtualenv
virtualenv venv
source venv/bin/activate
pip install -Ur requirements.txt
python start.py
```

## Linux

### Synchronization temporelle

This issue happens when error messages such as `'recvWindow' must be less than ...` appear.

On Debian or Ubuntu, open a terminal and type:

```bash
sudo service ntp stop
sudo ntpd -gq
sudo service ntp start
```

Requires `ntp` package installation `sudo apt-get install ntp`.

Code from

<a href="https://askubuntu.com/questions/254826/how-to-force-a-clock-update-using-ntp#256004" rel="nofollow">askubuntu.com</a>
.

### Installation

During pip install if you have SSL problems, open a terminal and type

```bash
pip3 install service_identity --force --upgrade
```
