---
title: "With Python and Git"
description: "Learn how to install and start your OctoBot on your own computer or server (Windows, Mac or Linux) using the open source Python code directly from GitHub."
sidebar_position: 6
---

# Install OctoBot on Python and Git

## Requirements

-   Packages installed : Python3.10.X, Python3.10.X-dev, Python3.10.X-pip, git

## Installation

**First, make sure you have python3.10 and python3.10-dev and python3.10-pip installed on your computer.**

### Using the current stable version (master branch)

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

### Using the latest version (dev branch)

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

### Installing latest tentacles :
> Warning: using the latest tentacles might break your OctoBot 

#### On Unix
``` bash
cd OctoBot
python3 -m pip install -Ur requirements.txt
export TENTACLES_URL_TAG="latest"
python3 start.py tentacles --install --all
```
#### On Windows
``` bash
cd OctoBot
python3 -m pip install -Ur requirements.txt
SET TENTACLES_URL_TAG=latest
python3 start.py tentacles --install --all
```

## Usage

The following command replaces *OctoBot Launcher*:

``` bash
python3 start.py
```

## Update

Executing the following command will update your Python OctoBot using the latest version of the selected branch (`master` or `dev`), as well as installing the latest requirements. 
``` bash
git pull
cd OctoBot
python3 -m pip install -Ur requirements.txt
```
The next restart will automatically update your OctoBot tentacles.

## Python3

There **python3** is refering to your **Python3.10.X** installation, just adapt the commands to match your setup if any different (might be python, python3, python3.10, etc: it depends on your environment).

## Start in background

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
