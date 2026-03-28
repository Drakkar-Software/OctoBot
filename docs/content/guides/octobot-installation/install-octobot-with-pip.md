---
title: "With PIP"
description: "Learn how to install and start your OctoBot on your own computer or server (Windows, Mac or Linux) using the PIP (Python index package) version of the bot."
sidebar_position: 7
---



# Install OctoBot on Python index package (pip)

## Requirements

- Python 3.10 (<a href="https://www.python.org/downloads/" rel="nofollow">download</a>)
- Add python to your PATH (<a href="https://superuser.com/questions/143119/how-do-i-add-python-to-the-windows-path" rel="nofollow">tutorial windows</a>)

## Installation

In a command line (with python in your PATH) type the following command:

```bash
python3.10 -m pip install OctoBot
```

You can change **python3.10** to the name of the python binary you added to your PATH (for example on linux you may use **python3** or even **python** if the **python --version** commands outputs a python 3.10 version)

## Usage

```bash
OctoBot
```

## Update

Executing the following command will update your Python OctoBot using the latest version, as well as installing the latest requirements.

```bash
python3.10 -m pip install -U OctoBot
```

The next restart will automatically update your OctoBot tentacles.

## Start multiple OctoBots

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
