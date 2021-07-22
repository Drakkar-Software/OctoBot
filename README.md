# OctoBot [0.4.0-beta12](https://github.com/Drakkar-Software/OctoBot/tree/dev/CHANGELOG.md)
[![PyPI](https://img.shields.io/pypi/v/OctoBot.svg)](https://pypi.python.org/pypi/OctoBot/)
[![Codacy Badge](https://api.codacy.com/project/badge/Grade/e07fb190156d4efb8e7d07aaa5eff2e1)](https://app.codacy.com/gh/Drakkar-Software/OctoBot?utm_source=github.com&utm_medium=referral&utm_content=Drakkar-Software/OctoBot&utm_campaign=Badge_Grade_Dashboard)[![Downloads](https://pepy.tech/badge/octobot/month)](https://pepy.tech/project/octobot)
[![Dockerhub](https://img.shields.io/docker/pulls/drakkarsoftware/octobot.svg)](https://hub.docker.com/r/drakkarsoftware/octobot)
[![Coverage Status](https://coveralls.io/repos/github/Drakkar-Software/OctoBot/badge.svg?branch=dev)](https://coveralls.io/github/Drakkar-Software/OctoBot?branch=dev)
[![OctoBot-CI](https://github.com/Drakkar-Software/OctoBot/workflows/OctoBot-CI/badge.svg)](https://github.com/Drakkar-Software/OctoBot/actions)
[![Build Status](https://cloud.drone.io/api/badges/Drakkar-Software/OctoBot/status.svg)](https://cloud.drone.io/Drakkar-Software/OctoBot)
[![UptimeRobot](https://img.shields.io/uptimerobot/ratio/30/m786447893-903b482e5158c8b6483760e8)](https://status.octobot.online/)

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
[Octobot](https://www.octobot.online/) is a powerful fully modular open-source cryptocurrency trading robot.

See the [Octobot official website](https://www.octobot.online/).

This repository contains all the features of the bot (trading tools, evaluation engines, the backtesting toolkit, ...).
[Octobot's tentacles](https://github.com/Drakkar-Software/OctoBot-tentacles) contains the bot's strategies and user interfaces.

To install OctoBot with its tentacles, just use the [latest release for your system](https://github.com/Drakkar-Software/OctoBot/releases/latest) and your OctoBot is ready ! 

## Your Octobot
<a href="https://www.octobot.online/guides/#telegram"><img src="../assets/telegram-interface.png" height="414" alt="Telegram interface"></a>
[![Twitter Interface](../assets/twitter-interface.png)](https://docs.octobot.online/pages/Twitter-interface.html)

OctoBot is highly customizable using its configuration and tentacles system. 
You can build your own bot using the infinite [configuration](https://www.octobot.online/guides/#trading_modes) possibilities such as 
**technical analysis**, **social media processing** or even **external statistics management** like google trends.

OctoBot is **AI ready**: Python being the main language for OctoBot, it's easy to integrate machine-learning libraries such as [Tensorflow](https://github.com/tensorflow/tensorflow) or
any other lib and take advantage of all the available data and create a very powerful trading strategy. 

Octobot's main feature is **evolution** : you can [install](https://docs.octobot.online/pages/Tentacle-Manager.html), 
[modify](https://docs.octobot.online/pages/Customize-your-OctoBot.html) and even [create](https://docs.octobot.online/pages/Customize-your-OctoBot.html#tentacle-customization-octobot-v0-3) any tentacle you want to build your ideal cryptocurrency trading robot. You can even share your OctoBot evolutions !

## Installation
OctoBot's installation is **very simple**... because **very documented** ! See the [installation guides](https://www.octobot.online/guides/#installation) for more info.

#### With executable
Follow the [2 steps installation guide](https://www.octobot.online/executable_installation/) 

In short:
- Use the latest release on the [release page](https://github.com/Drakkar-Software/OctoBot/releases/latest)

#### [With Docker](https://docs.octobot.online/pages/With-Docker.html)
Follow the [docker installation guide](https://www.octobot.online/docker_installation/) 

In short :
```
docker run -itd --name OctoBot -p 80:5001 -v $(pwd)/user:/octobot/user -v $(pwd)/tentacles:/octobot/tentacles -v $(pwd)/logs:/octobot/logs drakkarsoftware/octobot:stable
```
And then open [http://localhost](http://localhost).

#### [With python sources](https://docs.octobot.online/pages/With-Python-only.html)
Follow the [python installation guide](https://www.octobot.online/python_installation/) 

In short :
```
git clone https://github.com/Drakkar-Software/OctoBot.git
cd OctoBot
python3 -m pip install -Ur requirements.txt
python3 start.py
```

#### One click deployment
Follow the [Digital Ocean installation guide](https://www.octobot.online/digital_ocean_installation/) 

In short :

[![Deploy to DO](https://mp-assets1.sfo2.digitaloceanspaces.com/deploy-to-do/do-btn-blue.svg)](https://cloud.digitalocean.com/apps/new?repo=https://github.com/Drakkar-Software/OctoBot/tree/master&refcode=40c9737100b1)

- Get 60-day free Digital Ocean hosting by registering with [OctoBot referral link](https://m.do.co/c/40c9737100b1).

[![Develop on Okteto](https://okteto.com/develop-okteto.svg)](https://cloud.okteto.com/deploy?repository=https://github.com/Drakkar-Software/OctoBot&branch=master)

- Free 24-hour demo repeatable indefinitely on Okteto simply using your Github account

## Exchanges
[![Binance](../assets/binance-logo.png)](https://www.binance.com)
[![Bitmex](../assets/bitmex-logo.png)](https://bitmex.com)
[![Bitmax](../assets/bitmax-logo.png)](https://bitmax.io)
[![Coinbase](../assets/coinbasepro-logo.png)](https://pro.coinbase.com)
[![Kucoin](../assets/kucoin-logo.png)](https://www.kucoin.com)
[![Bitfinex](../assets/bitfinex-logo.png)](https://www.bitfinex.com)
[![Bittrex](../assets/bittrex-logo.png)](https://bittrex.com)

Octobot supports many [exchanges](https://docs.octobot.online/pages/Exchanges.html#octobot-officially-supported-exchanges) thanks to the [ccxt library](https://github.com/ccxt/ccxt). 
To activate trading on an exchange, just configure OctoBot with your api keys as described [on the exchange documentation](https://www.octobot.online/guides/#exchanges).

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
<tr>
<td>Thanks to <a href="https://okteto.com/" target="_blank">Okteto</a> for allowing OctoBot developers to test their changes online with a simple button.</td>
<td><a href="https://okteto.com/" target="_blank"><p align="center"><img src="https://github.com/Drakkar-Software/OctoBot/blob/assets/okteto.png?raw=true"></p></a></td>
</tr>
</table>
