---
title: "Setup your environment"
description: "Learn how to create your OctoBot developer environment from the open source OctoBot GitHub Python repository using VSCode or PyCharm."
sidebar_position: 3
---



# OctoBot developer installation

This environment allows you to execute a local OctoBot from the python code, make local changes, debug and test them.

## Installing OctoBot requirements

- Programming language: <a href="https://www.python.org/downloads/release/python-3130/" rel="nofollow">Python 3.13</a>
- SCM: <a href="https://git-scm.com/downloads" rel="nofollow">Git</a>
- Build system: <a href="https://www.pantsbuild.org/" rel="nofollow">Pants</a>
- IDE: <a href="https://code.visualstudio.com/Download" rel="nofollow">Visual Studio Code</a> (recommended) or <a href="https://www.jetbrains.com/pycharm/" rel="nofollow">PyCharm</a>

OctoBot's code is a Python monorepo: each part of OctoBot (`commons`, `trading`, `evaluators`, ...) lives in its own folder under `packages` and is built with Pants.

Pants is not bundled with OctoBot, install the `scie-pants` launcher once and it will bootstrap the Pants version required by OctoBot's `pants.toml` on its first run. Installation instructions are on the <a href="https://www.pantsbuild.org/stable/docs/getting-started/installing-pants" rel="nofollow">Pants installation page</a>.

:::warning
This Pants based setup is not supported on Windows yet. Pants only runs on Windows through the <a href="https://learn.microsoft.com/windows/wsl/install" rel="nofollow">Windows Subsystem for Linux (WSL 2)</a>.

If you are on Windows, install WSL 2, clone the OctoBot repository **inside** the Linux file system of your WSL distribution and follow the Linux/macOS commands of this guide. A repository kept on the Windows side and reached through `/mnt` is not supported by Pants and leads to unexpected behaviors.

Both VSCode and PyCharm can open a project located in WSL, in that case your python interpreter is `venv/bin/python` and the `PYTHONPATH` paths below are separated by `:`.
:::


## Cloning the OctoBot repository

The `OctoBot` repository is all you need for the OctoBot developer environment. It contains every package of the software as well as the tentacles.

Open a terminal in your project folder and execute the following command to download the official version of the repository.


```bash
git clone https://github.com/Drakkar-Software/OctoBot.git --branch dev
```
A development environment will prefer using the `dev` branch as all pull requests to the OctoBot repository should be created against its official `dev` branch.

If you wish to contribute to OctoBot, please create your own fork of this repository and use it instead.

Each part of the software lives in its own folder under `packages`. More details on the [GitHub repositories page](github-repositories).

## VSCode OctoBot environment

### Creating the project and installing dependencies

1. Open Visual Studio Code and open the cloned `OctoBot` folder.
2. Open the terminal and create a new Python 3.13 virtual environment to contain OctoBot's dependencies. Command: `python -m venv venv`
3. Activate your virtual environment: `source venv/bin/activate`
<div style="text-align: center">

![vscode create octobot venv](/images/guides/dev_env/vscode-create-octobot-venv.png)

</div>
4. Install python dependencies from the integrated VSCode terminal, which is using your new virtual env. The `pants.toml` build configuration is at the root of the repository, run the Pants install command from there:
```bash
pants install-deps --full ::
```
This installs every third party dependency of the OctoBot packages into the currently activated virtual environment. `--full` also includes the optional dependencies listed in the `full_requirements.txt` files, which are required by some tentacles, as well as the test and development dependencies.
<div style="text-align: center">

![vscode install python requirements](/images/guides/dev_env/vscode-install-python-requirements.png)

</div>


### Configuring VSCode
1. Create a `.vscode` folder at the root of your project.
2. In the `.vscode` folder, create a `settings.json` file with the following content to make VSCode use your Virtual environment.
```json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/venv/bin/python"
}
``` 
3. In the `.vscode` folder, create a `launch.json` file with the following content to create your run configurations. This file will configure the run configurations you need to develop on OctoBot by making it simple to:
- Start OctoBot
- Run tests
- Manage tentacles

Each configuration sets a `PYTHONPATH` environment variable. OctoBot's packages are not installed into your virtual environment, they are used directly from their folder in the repository, therefore Python needs to know where each of them is. This list mirrors the `root_patterns` of OctoBot's `pants.toml`, update it when a new package is added.

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

VSCode should now display the launch.json configurations in its user interface.

<div style="text-align: center">

![vscode run configurations selector](/images/guides/dev_env/vscode-run-configurations-selector.png)

</div>

Note: these files were created using VSCode `1.102.1` (from July 2025). If any value becomes deprecated in newer VSCode versions, please contact us to update this guide. 

### Executing OctoBot

#### 1. Installing tentacles
Now that your VSCode is configured, it is necessary to install your initial OctoBot tentacles.

The tentacles source code is in the `packages/tentacles` folder of the repository. OctoBot can only use tentacles that are properly installed in its `tentacles` folder, which is generated from `packages/tentacles`. Never edit the generated `tentacles` folder directly, it is overriden on each install.

1. Execute the `Export tentacles to zip` run configuration

This step is necessary to use the tentacles code of the repository. Skipping it will make your OctoBot download the tentacles associated to its latest release which might be incompatible with the `dev` branch your OctoBot code is currently set to.

<div style="text-align: center">

![vscode executed export tentacles to zip](/images/guides/dev_env/vscode-executed-export-tentacles-to-zip.png)

</div>

This will export the tentacles into a zip archive at `output/any_platform.zip` that can be installed on your OctoBot, or shared

2. Execute the `Install tentacles zip` run configuration

<div style="text-align: center">

![vscode executed install tentacles from zip](/images/guides/dev_env/vscode-executed-install-tentacles-from-zip.png)

</div>

This added to your OctoBot tentacles the tentacles contained into this zip. This run configuration can be used to install any tentacles zip

Re-execute `Export tentacles to zip` and `Install tentacles zip` every time you change something in `packages/tentacles`, this is what applies your changes to the running OctoBot.  
Warning: this will override any local change made to the generated `tentacles` folder so be sure to save your local changes beforehand.

#### 2. Starting OctoBot

This run configuration will start your local OctoBot. Make sure your tentacles have been installed first (from the `Export tentacles to zip` and `Install tentacles zip` run config executions) or OctoBot will install its default tentacles and their import will might fail. 

Execute the `Start OctoBot` run configuration

<div style="text-align: center">

![vscode executed start octobot](/images/guides/dev_env/vscode-executed-start-octobot.png)

</div>

#### 3. Running tests

The `OctoBot tests` and `Tentacles tests trading modes` are example configurations to execute all OctoBot tests or OctoBot tentacles Trading Modes tests. Feel fee to add any other test run configurations. 

<div style="text-align: center">

![vscode executed tests](/images/guides/dev_env/vscode-executed-tests.png)

</div>


## PyCharm OctoBot environment

### Creating the project and installing dependencies
1. Open Pycharm and open the cloned `OctoBot` folder.
2. Create a new Python 3.13 virtual environment to contain OctoBot's dependencies.
<div style="text-align: center">

![create pycharm interpreter](/images/guides/dev_env/create-pycharm-interpreter.png)

</div>
3. Install python dependencies from the integrated PyCharm terminal, which is using your new virtual env by default. The `pants.toml` build configuration is at the root of the repository, run the Pants install command from there:
```bash
pants install-deps --full ::
```
This installs every third party dependency of the OctoBot packages into your virtual environment. `--full` also includes the optional dependencies listed in the `full_requirements.txt` files, which are required by some tentacles, as well as the test and development dependencies.
<div style="text-align: center">

![install octobot requirements from pycharm](/images/guides/dev_env/install-octobot-requirements-from-pycharm.png)

</div>

### Create PyCharm run configurations

The following steps will create PyCharm run configurations using the previously created virtual env (then one which contains the OctoBot dependencies) for each way you want to start python commands:
- Starting OctoBot
- Running tests
- Managing tentacles

Each of these run configurations also requires a `PYTHONPATH` environment variable. OctoBot's packages are not installed into your virtual environment, they are used directly from their folder in the repository, therefore Python needs to know where each of them is. This list mirrors the `root_patterns` of OctoBot's `pants.toml`, update it when a new package is added.

In every run configuration below, set the **Environment variables** field to the following value, replacing `path_to_your_octobot_repository` by the absolute path to your OctoBot repository:

```bash
PYTHONPATH=path_to_your_octobot_repository:path_to_your_octobot_repository/packages/agents:path_to_your_octobot_repository/packages/async_channel:path_to_your_octobot_repository/packages/backtesting:path_to_your_octobot_repository/packages/binary:path_to_your_octobot_repository/packages/commons:path_to_your_octobot_repository/packages/copy:path_to_your_octobot_repository/packages/evaluators:path_to_your_octobot_repository/packages/flow:path_to_your_octobot_repository/packages/node:path_to_your_octobot_repository/packages/protocol:path_to_your_octobot_repository/packages/services:path_to_your_octobot_repository/packages/sync:path_to_your_octobot_repository/packages/tentacles_manager:path_to_your_octobot_repository/packages/trading
```

#### 1. Installing tentacles
The tentacles source code is in the `packages/tentacles` folder of the repository. OctoBot can only use tentacles that are properly installed in its `tentacles` folder, which is generated from `packages/tentacles`. Never edit the generated `tentacles` folder directly, it is overriden on each install.

This step is necessary to use the tentacles code of the repository. Skipping it will make your OctoBot download the tentacles associated to its latest release which might be incompatible with the `dev` branch your OctoBot code is currently set to.

1. Click on `Edit Configurations`
<div style="text-align: center">

![edit pycharm configurations](/images/guides/dev_env/edit-pycharm-configurations.png)

</div>
2. Create the `Export tentacles to zip` run configuration:
- Script path: `path_to_your_octobot_repository/start.py`
- Working directory: `path_to_your_octobot_repository`
- Script parameters: `tentacles -p tentacles_default_export.zip -d packages/tentacles`
<div style="text-align: center">

![create pycharm export tentacles config](/images/guides/dev_env/create-pycharm-export-tentacles-config.png)

</div>
3. Execute this run configuration. This will export the tentacles into a zip archive at `output/any_platform.zip` that can be installed on your OctoBot, or shared.
<div style="text-align: center">

![execute pycharm export tentacles](/images/guides/dev_env/execute-pycharm-export-tentacles.png)

</div>
4. Create the `Install tentacles zip` run configuration to install these zipped tentacles on your OctoBot:
- Script path: `path_to_your_octobot_repository/start.py`
- Working directory: `path_to_your_octobot_repository`
- Script parameters: `tentacles -i --all --location output/any_platform.zip`
- Add `ALLOW_UNSIGNED_TENTACLES=true` to the **Environment variables** field, locally built tentacles have no signature file
<div style="text-align: center">

![create pycharm install tentacles config](/images/guides/dev_env/create-pycharm-install-tentacles-config.png)

</div>
5. Execute this run configuration. This added to your OctoBot tentacles the tentacles contained into this zip. This run configuration can be used to install any tentacles zip. 
<div style="text-align: center">

![execute pycharm install tentacles](/images/guides/dev_env/execute-pycharm-install-tentacles.png)

</div>

Re-execute `Export tentacles to zip` and `Install tentacles zip` every time you change something in `packages/tentacles`, this is what applies your changes to the running OctoBot. 
Warning: this will override any local change made to the generated `tentacles` folder so be sure to save your local changes beforehand.

#### 2. Starting OctoBot
This run configuration will start your local OctoBot. Make sure your tentacles have been installed first (from the `Export tentacles to zip` and `Install tentacles zip` run config executions) or OctoBot will install its default tentacles and their import will might fail. 

1. Click on `Edit Configurations`
<div style="text-align: center">

![edit pycharm configurations](/images/guides/dev_env/edit-pycharm-configurations.png)

</div>
2. Create the `Start OctoBot` run configuration:
- Script path: `path_to_your_octobot_repository/start.py`
- Working directory: `path_to_your_octobot_repository`
<div style="text-align: center">

![create pycharm start octobot run config](/images/guides/dev_env/create-pycharm-start-octobot-run-config.png)

</div>
3. Execute this the run configuration to start your OctoBot
<div style="text-align: center">

![execute pycharm start octobot](/images/guides/dev_env/execute-pycharm-start-octobot.png)

</div>

You can now start your OctoBot from your development environment, make local changes and run python in debug mode. 

#### 3. Running tests

Create `pytest` run configurations to run OctoBot tests. Feel fee to add any other test run configurations. 

<div style="text-align: center">

![create pycharm tests config](/images/guides/dev_env/create-pycharm-tests-config.png)

</div>
<div style="text-align: center">

![execute pycharm tests](/images/guides/dev_env/execute-pycharm-tests.png)

</div>
