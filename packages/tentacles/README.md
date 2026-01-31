# OctoBot-Tentacles
[![OctoBot-Tentacles-CI](https://github.com/Drakkar-Software/OctoBot-Tentacles/workflows/OctoBot-Tentacles-CI/badge.svg)](https://github.com/Drakkar-Software/OctoBot-Tentacles/actions)

This repository contains default evaluators, strategies, utilitary modules, interfaces and trading modes for the [OctoBot](https://github.com/Drakkar-Software/OctoBot) project.

Modules in this tentacles are installed in the **Default** folder of the associated module types

To add custom tentacles to your OctoBot, see the [dedicated docs page](https://www.octobot.cloud/guides/octobot-tentacles-development/customize-your-octobot?utm_source=octobot&utm_medium=dk&utm_campaign=regular_open_source_content&utm_content=octobot_tentacles_readme).

## Contributing to the official OctoBot Tentacles:
1. Create your own fork of this repo
2. Start your branch from the `dev` branch of this repo
3. Commit and push your changes into your fork
4. Create a pull request from your branch on your fork to the `dev` branch of this repo

Tips:

To export changes from your local OctoBot tentacles folder into this repo, run this command from your OctoBot folder:   
`python start.py tentacles -e "../../OctoBot-Tentacles" OctoBot-Default-Tentacles -d "tentacles"`  
Where: 
- `start.py`: start.py script from your OctoBot folder
- `tentacles`: the tentacles command of the script
- `../../OctoBot-Tentacles`: the path to your fork of this repository (relatively to the folder you are running the command from)
- `OctoBot-Default-Tentacles`: filter to only export tentacles tagged as `OctoBot-Default-Tentacles` (in metadata file)
- `-d tentacles`: name of your OctoBot tentacles folder that are to be copied to the repo (relatively to the folder you are running the command from)
