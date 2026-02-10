# OctoBot-Evaluators
[![Codacy Badge](https://api.codacy.com/project/badge/Grade/a0c08eab5d4c440aa6e3fc3061ad0520)](https://app.codacy.com/gh/Drakkar-Software/OctoBot-Evaluators?utm_source=github.com&utm_medium=referral&utm_content=Drakkar-Software/OctoBot-Evaluators&utm_campaign=Badge_Grade_Dashboard)
[![Coverage Status](https://coveralls.io/repos/github/Drakkar-Software/OctoBot-Evaluators/badge.svg)](https://coveralls.io/github/Drakkar-Software/OctoBot-Evaluators)
[![Github-Action-CI](https://github.com/Drakkar-Software/OctoBot-Evaluators/workflows/OctoBot-Evaluators-CI/badge.svg)](https://github.com/Drakkar-Software/OctoBot-Evaluators/actions)
[![Build Status](https://cloud.drone.io/api/badges/Drakkar-Software/OctoBot-Evaluators/status.svg)](https://cloud.drone.io/Drakkar-Software/OctoBot-Evaluators)

# Where are evaluators and strategies ?

Because OctoBot is modular, a wide range of evaluators and strategies are usable.

Default evaluators and strategies are located here: [https://github.com/Drakkar-Software/OctoBot-Tentacles](https://github.com/Drakkar-Software/OctoBot-Tentacles).

To install default evaluators and strategies in your OctoBot, run the following command: 

```bash
python start.py tentacles --install --all
```


It is also possible to specify which module(s) to install by naming it(them). In this case only the modules available in the available packages can be installed.
```
python start.py tentacles --install forum_evaluator john_smith_macd_evaluator advanced_twitter_evaluator
```

**You can find how to create your OctoBot evaluators and strategies [on the OctoBot guides](https://www.octobot.cloud/en/guides/octobot-tentacles-development/customize-your-octobot?utm_source=octobot&utm_medium=dk&utm_campaign=regular_open_source_content&utm_content=octobot_evaluators_readme).**


# [Octobot Module Manager](https://github.com/Drakkar-Software/OctoBot-Tentacles-Manager)
A module manager for your [OctoBot](https://github.com/Drakkar-Software/OctoBot) ! 

- Install OctoBot-Tentacles-Manager from pip : 

``` {.sourceCode .bash}
$ python3 -m pip install OctoBot-Tentacles-Manager
```

# [Customize your Octobot](https://www.octobot.cloud/en/guides/octobot-tentacles-development/customize-your-octobot)