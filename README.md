# OctoBot [0.4.5](https://octobot.click/gh-changelog)
[![PyPI](https://img.shields.io/pypi/v/OctoBot.svg)](https://octobot.click/gh-pypi)
[![Codacy Badge](https://api.codacy.com/project/badge/Grade/e07fb190156d4efb8e7d07aaa5eff2e1)](https://app.codacy.com/gh/Drakkar-Software/OctoBot?utm_source=github.com&utm_medium=referral&utm_content=Drakkar-Software/OctoBot&utm_campaign=Badge_Grade_Dashboard)[![Downloads](https://pepy.tech/badge/octobot/month)](https://pepy.tech/project/octobot)
[![Dockerhub](https://img.shields.io/docker/pulls/drakkarsoftware/octobot.svg)](https://octobot.click/gh-dockerhub)
[![Coverage Status](https://coveralls.io/repos/github/Drakkar-Software/OctoBot/badge.svg?branch=dev)](https://coveralls.io/github/Drakkar-Software/OctoBot?branch=dev)
[![OctoBot-CI](https://github.com/Drakkar-Software/OctoBot/workflows/OctoBot-CI/badge.svg)](https://github.com/Drakkar-Software/OctoBot/actions)
[![Build Status](https://cloud.drone.io/api/badges/Drakkar-Software/OctoBot/status.svg)](https://cloud.drone.io/Drakkar-Software/OctoBot)
[![UptimeRobot](https://img.shields.io/uptimerobot/ratio/30/m786447893-903b482e5158c8b6483760e8)](https://octobot.click/gh-status)

#### Octobot Community
[![Active OctoBot](https://img.shields.io/badge/dynamic/json.svg?&url=https://octobotmetrics.herokuapp.com/metrics/community/count/0/-1/0&query=$.total&color=green&label=OctoBots%20online%20this%20month)]()
[![Telegram Chat](https://img.shields.io/badge/telegram-chat-green.svg)](https://octobot.click/gh-telegram)
[![Discord](https://img.shields.io/discord/530629985661222912.svg?logo=discord)](https://octobot.click/gh-discord)
[![Telegram News](https://img.shields.io/badge/telegram-news-blue.svg)](https://t.me/OctoBot_Project)
[![Twitter](https://img.shields.io/twitter/follow/DrakkarsOctobot.svg?label=Follow&style=social)](https://octobot.click/gh-twitter)
<p align="center">
<img src="../assets/OctoBot-icon-only.svg" alt="Octobot Logo" height="400" width="400">
</p>

![Web Interface](../assets/web-interface.gif)
## Description
[Octobot](https://www.octobot.online/) is a powerful, fully modular open-source cryptocurrency trading robot.

See the [Octobot official website](https://www.octobot.online/).

This repository contains all the features of the bot (trading tools, evaluation engines, the backtesting toolkit, ...).
[Octobot's tentacles](https://github.com/Drakkar-Software/OctoBot-tentacles) contains the bot's strategies and user interfaces.

To install OctoBot with its tentacles, just use the [latest release for your system](https://github.com/Drakkar-Software/OctoBot/releases/latest) and your OctoBot is ready ! 

Find the answers to the most common questions in [our FAQ](https://www.octobot.info/usage/frequently-asked-questions-faq).

## Your Octobot
<a href="https://www.octobot.online/guides/#telegram"><img src="../assets/telegram-interface.png" height="414" alt="Telegram interface"></a>
[![Twitter Interface](../assets/twitter-interface.png)](https://www.octobot.info/interfaces/twitter-interface)

OctoBot is highly customizable using its configuration and tentacles system. 
You can build your own bot using the infinite [configuration](https://www.octobot.online/guides/#trading_modes) possibilities such as 
**technical analysis**, **social media processing** or even **external statistics management** like google trends.

OctoBot is **AI ready**: Python being the main language for OctoBot, it's easy to integrate machine-learning libraries such as [Tensorflow](https://github.com/tensorflow/tensorflow) or
any other lib and take advantage of all the available data and create a very powerful trading strategy. 

Octobot's main feature is **evolution** : you can [install](https://www.octobot.info/advanced_usage/tentacle-manager), 
[modify](https://developer.octobot.info/guides/customize-your-octobot) and even [create](https://developer.octobot.info/guides/developer-guide) any tentacle you want to build your ideal cryptocurrency trading robot. You can even share your OctoBot evolutions!

## Hardware requirements
- CPU : 1 Core / 1GHz
- RAM : 250 Mo
- Disk : 1 Go

## Installation
OctoBot's installation is **very simple**... because **very documented** ! See the [installation guides](https://www.octobot.online/guides/#installation) for more info.

#### [With executable](https://www.octobot.info/installation/with-binary)
Follow the [2 steps installation guide](https://www.octobot.online/executable_installation/) 

In short:
- Use the latest release on the [release page](https://github.com/Drakkar-Software/OctoBot/releases/latest)

#### [With Docker](https://www.octobot.info/installation/with-docker)
Follow the [docker installation guide](https://www.octobot.online/docker_installation/) 

In short :
```
docker run -itd --name OctoBot -p 80:5001 -v $(pwd)/user:/octobot/user -v $(pwd)/tentacles:/octobot/tentacles -v $(pwd)/logs:/octobot/logs drakkarsoftware/octobot:stable
```
And then open [http://localhost](http://localhost).

With docker-compose : 
```
docker-compose up -d
```
And then open [https://octobot.localhost](https://octobot.localhost).

#### [With pip](https://octobot.click/gh-pip-install)

In short :
```
pip install OctoBot>=0.4.1
Octobot
```

#### [With python sources](https://octobot.click/gh-python-install)
Follow the [python installation guide](https://www.octobot.online/python_installation/) 

In short :
```
git clone https://github.com/Drakkar-Software/OctoBot.git
cd OctoBot
python3 -m pip install -Ur requirements.txt
python3 start.py
```

#### One click deployment
Follow the [Digital Ocean installation guide](https://octobot.click/gh-do-install) 

In short :

[![Deploy to DO](https://mp-assets1.sfo2.digitaloceanspaces.com/deploy-to-do/do-btn-blue.svg)](https://octobot.click/gh-do-deploy)

- Get 60-day free Digital Ocean hosting by registering with [OctoBot referral link](https://m.do.co/c/40c9737100b1).

[![Develop on Okteto](https://okteto.com/develop-okteto.svg)](https://octobot.click/gh-okteto-deploy)

- Free 24-hour demo repeatable indefinitely on Okteto simply using your Github account

## Exchanges
[![Binance](../assets/binance-logo.png)](https://octobot.click/gh-binance)
[![Binance](../assets/ftx-logo.png)](https://octobot.click/gh-ftx)
[![Binance](../assets/okex-logo.png)](https://octobot.click/gh-okex)
[![Binance](../assets/gateio-logo.png)](https://octobot.click/gh-gateio)
[![Binance](../assets/huobi-logo.png)](https://octobot.click/gh-huobi)
[![Bitmax](../assets/ascendex-logo.png)](https://octobot.click/gh-ascendex)
[![Coinbase](../assets/coinbasepro-logo.png)](https://pro.coinbase.com)
[![Kucoin](../assets/kucoin-logo.png)](https://www.kucoin.com)
[![Bitmex](../assets/bitmex-logo.png)](https://bitmex.com)

Octobot supports many [exchanges](https://octobot.click/gh-exchanges) thanks to the [ccxt library](https://github.com/ccxt/ccxt). 
To activate trading on an exchange, just configure OctoBot with your api keys as described [on the exchange documentation](https://www.octobot.online/guides/#exchanges).

## Disclaimer
Do not risk money which you are afraid to lose. USE THE SOFTWARE AT YOUR OWN RISK. THE AUTHORS 
AND ALL AFFILIATES ASSUME NO RESPONSIBILITY FOR YOUR TRADING RESULTS. 

Always start by running a trading bot in simulation mode and do not engage money
before you understand how it works and what profit/loss you should
expect.

Do not hesitate to read the source code and understand the mechanism of this bot.

## License
GNU General Public License v3.0 or later.

See [LICENSE](https://octobot.click/gh-license) to see the full text.

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
