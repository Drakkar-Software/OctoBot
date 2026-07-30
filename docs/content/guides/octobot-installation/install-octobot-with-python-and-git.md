---
title: "With Python and Git"
description: "Learn how to install and start your OctoBot on your own computer or server (Windows, Mac or Linux) using the open source Python code directly from GitHub."
sidebar_position: 6
---

# Install OctoBot on Python and Git

## Requirements

-   Packages installed : Python3.13.X, Python3.13.X-dev, Python3.13.X-pip, git
-   Build system: <a href="https://www.pantsbuild.org/" rel="nofollow">Pants</a>

OctoBot's Python code is a monorepo: each part of OctoBot (`commons`, `trading`, `evaluators`, ...) lives in its own folder under `packages` and is built with Pants.

Pants is not bundled with OctoBot, install the `scie-pants` launcher once and it will bootstrap the Pants version required by OctoBot's `pants.toml` on its first run. Installation instructions are on the <a href="https://www.pantsbuild.org/stable/docs/getting-started/installing-pants" rel="nofollow">Pants installation page</a>.

:::warning
This Pants based setup is not supported on Windows yet. Pants only runs on Windows through the <a href="https://learn.microsoft.com/windows/wsl/install" rel="nofollow">Windows Subsystem for Linux (WSL 2)</a>.

If you are on Windows, install WSL 2, clone OctoBot **inside** the Linux file system of your WSL distribution and follow the Linux commands of this guide from your WSL shell. A repository kept on the Windows side and reached through `/mnt` is not supported by Pants and leads to unexpected behaviors.
:::

## Installation

**First, make sure you have python3.13 and python3.13-dev and python3.13-pip installed on your computer.**

### Using the current stable version (master branch)

**This is the recommended python installation.**

Clone the OctoBot repository

``` bash
git clone https://github.com/Drakkar-Software/OctoBot
```

Create a virtual environment to contain OctoBot's dependencies and activate it :

``` bash
cd OctoBot
python3 -m venv venv
source venv/bin/activate
```

Install python packages. This command installs every third party dependency of the OctoBot packages into the currently activated virtual environment :

``` bash
pants install-deps --full ::
```

`--full` also includes the optional dependencies listed in the `full_requirements.txt` files, which are required by some tentacles.


> On some setup like 32-bit ARM architectures, you might get a `rust` related error while running `pants install-deps --full ::` when installing `cryptography`.
If this happens, you need to install the `rust compiler`: `cryptography` is coded in `rust`.
``` bash
sudo apt-get install -y rustc
```
You can then restart `pants install-deps --full ::`.

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

### Setting PYTHONPATH

OctoBot's packages are not installed into your virtual environment, they are used directly from their folder in the repository. Python therefore needs to know where each of them is: this is what `PYTHONPATH` is for.

From the OctoBot repository folder :

``` bash
ROOT=$PWD
export PYTHONPATH="$ROOT:$ROOT/packages/agents:$ROOT/packages/async_channel:$ROOT/packages/backtesting:$ROOT/packages/binary:$ROOT/packages/commons:$ROOT/packages/copy:$ROOT/packages/evaluators:$ROOT/packages/flow:$ROOT/packages/node:$ROOT/packages/protocol:$ROOT/packages/services:$ROOT/packages/sync:$ROOT/packages/tentacles_manager:$ROOT/packages/trading"
```

Notes:
- Use absolute paths, some OctoBot subprocesses are started from other folders and would not be able to resolve relative ones.
- This list mirrors the `root_patterns` of OctoBot's `pants.toml`, update it when a new package is added.

### Installing latest tentacles :
> Warning: using the latest tentacles might break your OctoBot 

``` bash
cd OctoBot
pants install-deps --full ::
export TENTACLES_URL_TAG="latest"
python3 start.py tentacles --install --all
```

## Usage

The following command replaces *OctoBot Launcher*:

``` bash
python3 start.py
```

Make sure your virtual environment is activated and `PYTHONPATH` is set in the terminal running this command. Both are lost when you close your terminal, so they have to be set again in every new one.

## Update

Executing the following command will update your Python OctoBot using the latest version of the selected branch (`master` or `dev`), as well as installing the latest requirements. Activate your virtual environment first, the dependencies are installed into it.
``` bash
cd OctoBot
source venv/bin/activate
git pull
pants install-deps --full ::
```
The next restart will automatically update your OctoBot tentacles.

## Python3

There **python3** is refering to your **Python3.13.X** installation, just adapt the commands to match your setup if any different (might be python, python3, python3.13, etc: it depends on your environment).

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
