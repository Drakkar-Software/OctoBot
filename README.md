# OctoBot [0.4.0-alpha25](https://github.com/Drakkar-Software/OctoBot/tree/dev/CHANGELOG.md)
[![PyPI](https://img.shields.io/pypi/v/OctoBot.svg)](https://pypi.python.org/pypi/OctoBot/)
[![Codacy Badge](https://api.codacy.com/project/badge/Grade/e07fb190156d4efb8e7d07aaa5eff2e1)](https://app.codacy.com/gh/Drakkar-Software/OctoBot?utm_source=github.com&utm_medium=referral&utm_content=Drakkar-Software/OctoBot&utm_campaign=Badge_Grade_Dashboard)[![Downloads](https://pepy.tech/badge/octobot/month)](https://pepy.tech/project/octobot)
[![Dockerhub](https://img.shields.io/docker/pulls/drakkarsoftware/octobot.svg)](https://hub.docker.com/r/drakkarsoftware/octobot)
[![Coverage Status](https://img.shields.io/coveralls/github/Drakkar-Software/OctoBot.svg)](https://coveralls.io/github/Drakkar-Software/OctoBot?branch=dev) 
[![Build Status](https://cloud.drone.io/api/badges/Drakkar-Software/OctoBot/status.svg)](https://cloud.drone.io/Drakkar-Software/OctoBot)

#### Octobot Community
[![Active OctoBot](https://img.shields.io/badge/dynamic/json.svg?&url=https://octobotmetrics.herokuapp.com/metrics/community/count/0/-1/0&query=$.total&color=green&label=OctoBots%20online%20this%20month)]()
[![Telegram Chat](https://img.shields.io/badge/telegram-chat-green.svg)](https://t.me/joinchat/F9cyfxV97ZOaXQ47H5dRWw)
[![Discord](https://img.shields.io/discord/530629985661222912.svg?logo=discord)](https://discord.gg/vHkcb8W)
[![Telegram News](https://img.shields.io/badge/telegram-news-blue.svg)](https://t.me/OctoBot_Project)
[![Twitter](https://img.shields.io/twitter/follow/DrakkarsOctobot.svg?label=Follow&style=social)](https://twitter.com/DrakkarsOctobot)
<p align="center">
<img src="../assets/octopus.svg" alt="Octobot Logo" height="400" width="400">
</p>

![Web Interface](../assets/web-interface.gif)
## Description
Octobot is a powerful fully modular open-source cryptocurrency trading robot.

This repository contains all the features of the bot (trading tools, interfaces, services, ...) without any modules (Octobot's tentacles).

To install tentacles, you just have to use the [integrated tentacle manager](https://github.com/Drakkar-Software/OctoBot/wiki/Tentacle-Manager) 
and your OctoBot is ready ! 

## Your Octobot
<a href="https://github.com/Drakkar-Software/OctoBot/blob/assets/telegram-interface.png"><img src="../assets/telegram-interface.png" height="414" alt="Telegram interface"></a>
[![Twitter Interface](../assets/twitter-interface.png)](https://twitter.com/HerklosBotCrypt)

OctoBot is highly customizable using its configuration and tentacles system. You can therefore build your own bot using the infinite [configuration](https://github.com/Drakkar-Software/OctoBot/wiki/Configuration) possibilities.

Octobot's main feature is **evolution** : you can [install](https://github.com/Drakkar-Software/OctoBot/wiki/Tentacle-Manager), 
[modify](https://github.com/Drakkar-Software/OctoBot/wiki/Customize-your-OctoBot) and even [create](https://github.com/Drakkar-Software/OctoBot/wiki/Customize-your-OctoBot) any tentacle you want to build your ideal cryptocurrency trading robot. You can even share your OctoBot evolutions !

## Installation
OctoBot's installation is **very simple**... because **very documented** !

#### [With Launcher (only for 64 bits)](https://github.com/Drakkar-Software/OctoBot/wiki/Installation)
- Open the OctoBot-Launcher [release page](https://github.com/Drakkar-Software/OctoBot-Launcher/releases)
- Download launcher (*laucher_windows.exe* or *launcher_linux*)
- Start the launcher
- Click on "Update OctoBot"

#### [With Docker](https://github.com/Drakkar-Software/OctoBot/wiki/With-Docker)
24h demo with a free Okteto account with

[![Develop on Okteto](https://okteto.com/develop-okteto.svg)](https://cloud.okteto.com/deploy?repository=https://github.com/Drakkar-Software/OctoBot&branch=0.4.0)

OR

Self hosting with docker :
```
docker run -itd --name OctoBot -p 80:5001 drakkarsoftware/octobot:0.4.0-stable
```
And then open [http://localhost](http://localhost).

#### [With python sources](https://github.com/Drakkar-Software/OctoBot/wiki/With-Python-only) (unix)
- Install python3.8 (https://www.python.org/downloads/)
```
git clone git@github.com:Drakkar-Software/OctoBot.git -b 0.4.0 && cd OctoBot
pip3 install -r requirements.txt
python3 start.py tentacles --install --all
```

More details in [wiki page](https://github.com/Drakkar-Software/OctoBot/wiki#installation) and it's done !

## Usage
- Just start the launcher
- Click on "Start Octobot"

For more information have a look at the 
[usage wiki page](https://github.com/Drakkar-Software/OctoBot/wiki/Usage) to know all the features of the OctoBot.


## Exchanges
[![Binance](../assets/binance-logo.png)](https://www.binance.com)
[![Bitmex](../assets/bitmex-logo.png)](https://bitmex.com)
[![Bitfinex](../assets/coinbasepro-logo.png)](https://pro.coinbase.com)
[![Bitfinex](../assets/kucoin-logo.png)](https://www.kucoin.com)
[![Bitfinex](../assets/bitfinex-logo.png)](https://www.bitfinex.com)
[![Bittrex](../assets/bittrex-logo.png)](https://bittrex.com)

Octobot supports many [exchanges](https://github.com/Drakkar-Software/OctoBot/wiki/Exchanges#octobot-official-supported-exchanges) thanks to the [ccxt library](https://github.com/ccxt/ccxt). 
To activate trading on an exchange, just configure OctoBot with your api keys as described [on the wiki](https://github.com/Drakkar-Software/OctoBot/wiki/Exchanges).

## Roadmap
[![Roadmap](../assets/roadmap_open_beta.svg)](https://github.com/Drakkar-Software/OctoBot/tree/assets/roadmap_open_beta.png)

## Disclaimer
Do not risk money which you are afraid to lose. USE THE SOFTWARE AT YOUR OWN RISK. THE AUTHORS 
AND ALL AFFILIATES ASSUME NO RESPONSIBILITY FOR YOUR TRADING RESULTS. 

Always start by running a trading bot in simulation mode and do not engage money
before you understand how it works and what profit/loss you should
expect.

Do not hesitate to read the source code and understand the mechanism of this bot.

## Contribute / Sponsors
See the [contribution wiki page](https://github.com/Drakkar-Software/OctoBot/wiki/Contribution)
-   [JetBrains](https://www.jetbrains.com/) with PyCharm Pro.

![](https://resources.jetbrains.com/storage/products/pycharm/img/meta/pycharm_logo_300x300.png)
