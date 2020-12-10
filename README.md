# OctoBot [0.4.0-beta2](https://github.com/Drakkar-Software/OctoBot/tree/dev/CHANGELOG.md)
[![PyPI](https://img.shields.io/pypi/v/OctoBot.svg)](https://pypi.python.org/pypi/OctoBot/)
[![Codacy Badge](https://api.codacy.com/project/badge/Grade/e07fb190156d4efb8e7d07aaa5eff2e1)](https://app.codacy.com/gh/Drakkar-Software/OctoBot?utm_source=github.com&utm_medium=referral&utm_content=Drakkar-Software/OctoBot&utm_campaign=Badge_Grade_Dashboard)[![Downloads](https://pepy.tech/badge/octobot/month)](https://pepy.tech/project/octobot)
[![Dockerhub](https://img.shields.io/docker/pulls/drakkarsoftware/octobot.svg)](https://hub.docker.com/r/drakkarsoftware/octobot)
[![Coverage Status](https://coveralls.io/repos/github/Drakkar-Software/OctoBot/badge.svg?branch=dev)](https://coveralls.io/github/Drakkar-Software/OctoBot?branch=dev)
[![OctoBot-CI](https://github.com/Drakkar-Software/OctoBot/workflows/OctoBot-CI/badge.svg)](https://github.com/Drakkar-Software/OctoBot/actions)
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

This repository contains all the features of the bot (trading tools, user interfaces, services, ...).
[Octobot's tentacles](https://github.com/Drakkar-Software/OctoBot-tentacles) contains the bot's strategies.

To install OctoBot with its tentacles, just use the [launcher](https://github.com/Drakkar-Software/OctoBot/wiki/Installation#octobot-launcher) and your OctoBot is ready ! 

## Your Octobot
<a href="https://github.com/Drakkar-Software/OctoBot/blob/assets/telegram-interface.png"><img src="../assets/telegram-interface.png" height="414" alt="Telegram interface"></a>
[![Twitter Interface](../assets/twitter-interface.png)](https://twitter.com/HerklosBotCrypt)

OctoBot is highly customizable using its configuration and tentacles system. 
You can build your own bot using the infinite [configuration](https://github.com/Drakkar-Software/OctoBot/wiki/Configuration) possibilities such as 
**technical analysis**, **social media processing** or even **external statistics management** like google trends.

OctoBot is **AI ready**: Python being the main language for OctoBot, it's easy to integrate machine-learning libraries such as [Tensorflow](https://github.com/tensorflow/tensorflow) or
any other lib and take advantage of all the available data and create a very powerful trading strategy. 

Octobot's main feature is **evolution** : you can [install](https://github.com/Drakkar-Software/OctoBot/wiki/Tentacle-Manager), 
[modify](https://github.com/Drakkar-Software/OctoBot/wiki/Customize-your-OctoBot) and even [create](https://github.com/Drakkar-Software/OctoBot/wiki/Customize-your-OctoBot) any tentacle you want to build your ideal cryptocurrency trading robot. You can even share your OctoBot evolutions !

## Installation
OctoBot's installation is **very simple**... because **very documented** ! See the [OctoBot Wiki](https://github.com/Drakkar-Software/OctoBot/wiki) for more info.

#### [With executable](https://github.com/Drakkar-Software/OctoBot/wiki/Installation)
- Open the OctoBot-Binary [release page](https://github.com/Drakkar-Software/OctoBot-Binary/releases)
- Open the latest release **Assets** panel
- Download the OctoBot executable for your platform
- Start OctoBot

#### [With Docker](https://github.com/Drakkar-Software/OctoBot/wiki/With-Docker)
Self hosting with docker :
```
docker run -itd --name OctoBot -p 80:5001 drakkarsoftware/octobot:0.4.0-stable
```
And then open [http://localhost](http://localhost).

#### [With python sources](https://github.com/Drakkar-Software/OctoBot/wiki/With-Python-only) (unix)
- Install python3.8 (https://www.python.org/downloads/)
```
git clone git@github.com:Drakkar-Software/OctoBot.git && cd OctoBot
pip3 install -r requirements.txt
python3 start.py
```

#### One click deployment
[![Deploy to DO](https://mp-assets1.sfo2.digitaloceanspaces.com/deploy-to-do/do-btn-blue.svg)](https://cloud.digitalocean.com/apps/new?repo=https://github.com/Drakkar-Software/OctoBot/tree/master&refcode=40c9737100b1)

Get 60-day free hosting by registering with [OctoBot referral link](https://m.do.co/c/40c9737100b1).

## Exchanges
[![Binance](../assets/binance-logo.png)](https://www.binance.com)
[![Bitmex](../assets/bitmex-logo.png)](https://bitmex.com)
[![Bitmax](../assets/bitmax-logo.png)](https://bitmax.io)
[![Coinbase](../assets/coinbasepro-logo.png)](https://pro.coinbase.com)
[![Kucoin](../assets/kucoin-logo.png)](https://www.kucoin.com)
[![Bitfinex](../assets/bitfinex-logo.png)](https://www.bitfinex.com)
[![Bittrex](../assets/bittrex-logo.png)](https://bittrex.com)

Octobot supports many [exchanges](https://github.com/Drakkar-Software/OctoBot/wiki/Exchanges#octobot-official-supported-exchanges) thanks to the [ccxt library](https://github.com/ccxt/ccxt). 
To activate trading on an exchange, just configure OctoBot with your api keys as described [on the wiki](https://github.com/Drakkar-Software/OctoBot/wiki/Exchanges).

## Disclaimer
Do not risk money which you are afraid to lose. USE THE SOFTWARE AT YOUR OWN RISK. THE AUTHORS 
AND ALL AFFILIATES ASSUME NO RESPONSIBILITY FOR YOUR TRADING RESULTS. 

Always start by running a trading bot in simulation mode and do not engage money
before you understand how it works and what profit/loss you should
expect.

Do not hesitate to read the source code and understand the mechanism of this bot.

## Sponsors
<table>
<tr>
<td><a href="https://www.jetbrains.com" target="_blank">JetBrains</a> with PyCharm Pro.</td>
<td><a href="https://www.jetbrains.com" target="_blank"><p align="center"><img src="https://resources.jetbrains.com/storage/products/pycharm/img/meta/pycharm_logo_300x300.png" width="100px"></p></a></td>
</tr>
<tr>
<td>Special thanks to <a href="https://m.do.co/c/40c9737100b1" target="_blank">DigitalOcean</a> for hosting OctoBot's open source tentacles and community websites.</td>
<td><a href="https://m.do.co/c/40c9737100b1" target="_blank"><p align="center"><img src="https://opensource.nyc3.cdn.digitaloceanspaces.com/attribution/assets/PNG/DO_Logo_Horizontal_Blue.png?utm_medium=opensource&utm_source=OctoBot"></p></a></td>
</tr>
</table>
