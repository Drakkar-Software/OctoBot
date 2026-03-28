---
title: "Setup your environment"
description: "Learn how to create your OctoBot developer environment from the open source OctoBot GitHub Python repositories using VSCode or PyCharm."
sidebar_position: 3
---



# OctoBot developer installation

This environment allows you to execute a local OctoBot from the python code, make local changes, debug and test them.

## Installing OctoBot requirements

- Programming language: <a href="https://www.python.org/downloads/release/python-31011/" rel="nofollow">Python 3.10</a>
- SCM: <a href="https://git-scm.com/downloads" rel="nofollow">Git</a>
- IDE: <a href="https://code.visualstudio.com/Download" rel="nofollow">Visual Studio Code</a> (recommended) or <a href="https://www.jetbrains.com/pycharm/" rel="nofollow">PyCharm</a>


## Cloning OctoBot repositories

The `OctoBot` and `OctoBot-Tentacles` repositories are required for the OctoBot developer environment.

Open a terminal in your project folder and execute the following commands to download the repos to use the official version of the repositories. 


```bash
git clone https://github.com/Drakkar-Software/OctoBot.git --branch dev
git clone https://github.com/Drakkar-Software/OctoBot-Tentacles.git --branch dev
```
A development environment will prefer using the `dev` branches as all pull requests to those OctoBot repositories should be created against the official `dev` branch of each repository.

If you wish to contribute to those repositories, please create your own fork of these repositories and use them instead.

*Going further*  
Are you an advanced developer who already understand how OctoBot works as a whole and you would like to add changes to the core modules of OctoBot?

As the OctoBot code is split into different repositories, each dedicated to a different aspect of the software, cloning repositories might be necessary. More details on the [GitHub repositories page](github-repositories).

## VSCode OctoBot environment

### Creating the project and installing dependencies

1. Open Visual Studio Code and open the folder where the OctoBot repositories are.
2. Open the terminal and create a new Python 3.10 virtual environment to contain OctoBot's dependencies. Command: `python -m venv venv`
3. Activate your virtual environment (`.\venv\Scripts\Activate.ps1` on Windows or `source venv/bin/activate` on Linux/macOS)
<div style="text-align: center">

![vscode create octobot venv](/images/guides/dev_env/vscode-create-octobot-venv.png)

</div>
4. Install python dependencies using `python -m pip install -r OctoBot/requirements.txt -r OctoBot/dev_requirements.txt` from the integrated VSCode terminal, which is using your new virtual env.
<div style="text-align: center">

![vscode install python requirements](/images/guides/dev_env/vscode-install-python-requirements.png)

</div>


### Configuring VSCode
1. Create a `.vscode` folder at the root of your project.
2. In the `.vscode` folder, create a `settings.json` file with the following content to make VSCode use your Virtual environment.  Note: replace the path to the python executable on Linux/MacOS.
```json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/venv/Scripts/python.exe"
}
``` 
3. In the `.vscode` folder, create a `launch.json` file with the following content to create your run configurations. This file will configure the run configurations you need to develop on OctoBot by making it simple to:
- Start OctoBot
- Run tests
- Manage tentacles

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

VSCode should now display the launch.json configurations in its user interface.

<div style="text-align: center">

![vscode run configurations selector](/images/guides/dev_env/vscode-run-configurations-selector.png)

</div>

Note: these files were created using VSCode `1.102.1` (from July 2025). If any value becomes deprecated in newer VSCode versions, please contact us to update this guide. 

### Executing OctoBot

#### 1. Installing tentacles from a tentacles repository
Now that your VSCode is configured, it is necessary to install your initial OctoBot tentacles.

1. Execute the `Export OctoBot-Tentacles to zip` run configuration

This run configuration will automatically install all tentacles contained in a local folder into your OctoBot, so that it can use them. OctoBot can only use tentacles that are properly installed in its `tentacles` folder.

This step is necessary to use the previously clonned `OctoBot-Tentacles` tentacles code. Skipping it will make your OctoBot download the tentacles associated to its latest release which might be incompatible with the `dev` branch your OctoBot code is currently set to.

<div style="text-align: center">

![vscode executed export tentacles to zip](/images/guides/dev_env/vscode-executed-export-tentacles-to-zip.png)

</div>

This will export the OctoBot-Tentacles tentacles into a zip archive that can be installed on your OctoBot, or shared

2. Execute the `Install tentacles zip` run configuration

<div style="text-align: center">

![vscode executed install tentacles from zip](/images/guides/dev_env/vscode-executed-install-tentacles-from-zip.png)

</div>

This added to your OctoBot tentacles the tentacles contained into this zip. This run configuration can be used to install any tentacles zip


Your OctoBot local folder now contains the tentacles code you clonned from the `OctoBot-Tentacles` repository. Re-execute `Export OctoBot-Tentacles to zip` and `Install tentacles zip` when you want to update your local tentacles from the `OctoBot-Tentacles` git repository.  
Warning: this will override any local change to the re-installed tentacles so be sure to save your local changes beforehand.

#### 2. Starting OctoBot

This run configuration will start your local OctoBot. Make sure your `OctoBot-Tentacles` tentacles have been installed first (from the `Export OctoBot-Tentacles to zip` and `Install tentacles zip` run config executions) or OctoBot will install its default tentacles and their import will might fail. 

Execute the `Start OctoBot` run configuration

<div style="text-align: center">

![vscode executed start octobot](/images/guides/dev_env/vscode-executed-start-octobot.png)

</div>

#### 3. Exporting your tentacle changes into their git repository

This run configuration will export changes of your local OctoBot tentacles into the configured tentacles repository. It will take the files linked to your selected tentacle package.

Execute the `Export tentacles to repo` run configuration


This will apply your the changes from your OctoBot/tentacles folder into the git repository of this tentacles package. 
<div style="text-align: center">

![vscode executed export tentacles to repo](/images/guides/dev_env/vscode-executed-export-tentacles-to-repo.png)

</div>

From the `launch.json` parameters, you can change:
- `OctoBot-Default-Tentacles` to select tentacles to export from a different package. Packages are defined in the `metadata.json` of each tentacle, under the `origin_package` key.
- `OctoBot-Tentacles` to export tentacles to a different git reposition.


#### 4. Running tests

The `OctoBot tests` and `OctoBot-Tentacles tests trading modes` are example configurations to execute all OctoBot tests or OctoBot tentacles Trading Modes tests. Feel fee to add any other test run configurations. 

<div style="text-align: center">

![vscode executed tests](/images/guides/dev_env/vscode-executed-tests.png)

</div>


## PyCharm OctoBot environment

### Creating the project and installing dependencies
1. Open Pycharm and open the folder where the OctoBot repositories are.
2. Create a new Python 3.10 virtual environment to contain OctoBot's dependencies.
<div style="text-align: center">

![create pycharm interpreter](/images/guides/dev_env/create-pycharm-interpreter.png)

</div>
3. Install python dependencies from the OctoBot repo folder using `python -m pip install -r OctoBot/requirements.txt -r OctoBot/dev_requirements.txt` from the integrated PyCharm terminal, which is using your new virtual env by default.
<div style="text-align: center">

![install octobot requirements from pycharm](/images/guides/dev_env/install-octobot-requirements-from-pycharm.png)

</div>

### Create PyCharm run configurations

The following steps will create PyCharm run configurations using the previously created virtual env (then one which contains the OctoBot dependencies) for each way you want to start python commands:
- Starting OctoBot
- Running tests
- Managing tentacles

#### 1. Installing tentacles from a git repository
This run configuration will automatically install all tentacles contained in a local folder into your OctoBot, so that it can use them. OctoBot can only use tentacles that are properly installed in its `tentacles` folder.

This step is necessary to use the previously clonned `OctoBot-Tentacles` tentacles code. Skipping it will make your OctoBot download the tentacles associated to its latest release which might be incompatible with the `dev` branch your OctoBot code is currently set to.

1. Click on `Edit Configurations`
<div style="text-align: center">

![edit pycharm configurations](/images/guides/dev_env/edit-pycharm-configurations.png)

</div>
2. Create the `Export OctoBot-Tentacles to zip` run configuration:
- Script path: `path_to_your_octobot_repositories/OctoBot/start.py`
- Working directory: `path_to_your_octobot_repositories/OctoBot`
- Script parameters: `tentacles -p ../tentacles_default_export.zip -d ../OctoBot-Tentacles`
<div style="text-align: center">

![create pycharm export tentacles config](/images/guides/dev_env/create-pycharm-export-tentacles-config.png)

</div>
3. Execute this run configuration. This will export the OctoBot-Tentacles tentacles into a zip archive that can be installed on your OctoBot, or shared.
<div style="text-align: center">

![execute pycharm export tentacles](/images/guides/dev_env/execute-pycharm-export-tentacles.png)

</div>
4. Create the `Install tentacles zip` run configuration to install these zipped tentacles on your OctoBot:
- Script path: `path_to_your_octobot_repositories/OctoBot/start.py`
- Working directory: `path_to_your_octobot_repositories/OctoBot`
- Script parameters: `tentacles -i --all --location any_platform.zip`
<div style="text-align: center">

![create pycharm install tentacles config](/images/guides/dev_env/create-pycharm-install-tentacles-config.png)

</div>
5. Execute this run configuration. This added to your OctoBot tentacles the tentacles contained into this zip. This run configuration can be used to install any tentacles zip. 
<div style="text-align: center">

![execute pycharm install tentacles](/images/guides/dev_env/execute-pycharm-install-tentacles.png)

</div>

Your OctoBot local folder now contains the tentacles code you clonned from the `OctoBot-Tentacles` repository. Re-execute `Export OctoBot-Tentacles to zip` and `Install tentacles zip` when you want to update your local tentacles from the `OctoBot-Tentacles` git repository. 
Warning: this will override any local change to the re-installed tentacles so be sure to save your local changes beforehand.

#### 2. Starting OctoBot
This run configuration will start your local OctoBot. Make sure your `OctoBot-Tentacles` tentacles have been installed first (from the `Export OctoBot-Tentacles to zip` and `Install tentacles zip` run config executions) or OctoBot will install its default tentacles and their import will might fail. 

1. Click on `Edit Configurations`
<div style="text-align: center">

![edit pycharm configurations](/images/guides/dev_env/edit-pycharm-configurations.png)

</div>
2. Create the `Start OctoBot` run configuration:
- Script path: `path_to_your_octobot_repositories/OctoBot/start.py`
- Working directory: `path_to_your_octobot_repositories/OctoBot`
<div style="text-align: center">

![create pycharm start octobot run config](/images/guides/dev_env/create-pycharm-start-octobot-run-config.png)

</div>
3. Execute this the run configuration to start your OctoBot
<div style="text-align: center">

![execute pycharm start octobot](/images/guides/dev_env/execute-pycharm-start-octobot.png)

</div>

You can now start your OctoBot from your development environment, make local changes and run python in debug mode. 

#### 3. Exporting your tentacle changes into their git repository
This run configuration will export changes of your local OctoBot tentacles into the configured tentacles repository. It will take the files linked to your selected tentacle package.

1. Click on `Edit Configurations`
<div style="text-align: center">

![edit pycharm configurations](/images/guides/dev_env/edit-pycharm-configurations.png)

</div>
2. Create the `Export tentacles to repo` run configuration:
- Script path: `path_to_your_octobot_repositories/OctoBot/start.py`
- Working directory: `path_to_your_octobot_repositories/OctoBot`
- Script parameters: `tentacles -e ../../OctoBot-Tentacles OctoBot-Default-Tentacles -d ../OctoBot/tentacles`
<div style="text-align: center">

![create pycharm export tentacles to repo config](/images/guides/dev_env/create-pycharm-export-tentacles-to-repo-config.png)

</div>
3. Execute this the run configuration to apply your the changes from your OctoBot/tentacles folder into the git repository of this tentacles package. 
<div style="text-align: center">

![execute pycharm export tentacles to repo](/images/guides/dev_env/execute-pycharm-export-tentacles-to-repo.png)

</div>

From the script parameters, you can change:
- `OctoBot-Default-Tentacles` to select tentacles to export from a different package. Packages are defined in the `metadata.json` of each tentacle, under the `origin_package` key.
- `OctoBot-Tentacles` to export tentacles to a different git reposition.


#### 4. Running tests

Create `pytest` run configurations to run OctoBot tests. Feel fee to add any other test run configurations. 

<div style="text-align: center">

![create pycharm tests config](/images/guides/dev_env/create-pycharm-tests-config.png)

</div>
<div style="text-align: center">

![execute pycharm tests](/images/guides/dev_env/execute-pycharm-tests.png)

</div>
