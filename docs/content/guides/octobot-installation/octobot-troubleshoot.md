---
title: "Troubleshoot"
description: "Any question when installing OctoBot ? Check out the most common installation issues on our troubleshoot guide."
sidebar_position: 8
---



# OctoBot Troubleshoot

## Keeping the same configuration and history when updating OctoBot

On OctoBot, the `user` folder, located in the directory you are executing OctoBot from, contains:

- Your current configuration
- Your profiles
- Your portfolio history
- Your trades and PNL history

In order to keep the same configuration and history when using another version of OctoBot, you can either:

- Copy the `user` directory of your previous OctoBot into your new OctoBot folder.
- Or execute the new OctoBot in the same directory as the previous one. Warning: the `tentacles` folder will be replaced by its new version.

## Keeping the same backtesting data files when updating OctoBot

When updating your OctoBot, you might want to keep your previous backtesting data files.

For your new OctoBot to access your backtesting data files, just copy the `backtesting` directory (located in the directory you were executing your previous OctoBot from) into your new OctoBot folder.

## Windows

### Time synchronization

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

### OctoBot freeze

When running OctoBot on Windows, clicking into the OctoBot terminal (Powershell or Cmd) can freeze the log output and therefore freeze OctoBot execution (OctoBot will be waiting for the log to be published to continue).

To fix this issue, untick the "QuickEdit Mode" in your terminal properties and restart it.

![Powershell](https://raw.githubusercontent.com/Drakkar-Software/OctoBot/assets/wiki_resources/powerShellEditMode.jpg)

![Cmd](https://raw.githubusercontent.com/Drakkar-Software/OctoBot/assets/wiki_resources/cmdQuickEdit.jpg)

To open the properties menu, right click on the terminal window header and select "properties".

## CentOS

### Install OctoBot on CentOS

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

### Time synchronization

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
