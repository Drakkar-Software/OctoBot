# OctoBot [0.4.46](https://octobot.click/gh-changelog)
[![PyPI](https://img.shields.io/pypi/v/OctoBot.svg?logo=pypi)](https://octobot.click/gh-pypi)
[![Codacy Badge](https://api.codacy.com/project/badge/Grade/e07fb190156d4efb8e7d07aaa5eff2e1)](https://app.codacy.com/gh/Drakkar-Software/OctoBot?utm_source=github.com&utm_medium=referral&utm_content=Drakkar-Software/OctoBot&utm_campaign=Badge_Grade_Dashboard)
[![Downloads](https://pepy.tech/badge/octobot/month)](https://pepy.tech/project/octobot)
[![Dockerhub](https://img.shields.io/docker/pulls/drakkarsoftware/octobot.svg?logo=docker)](https://octobot.click/gh-dockerhub)
[![OctoBot-CI](https://github.com/Drakkar-Software/OctoBot/workflows/OctoBot-CI/badge.svg)](https://github.com/Drakkar-Software/OctoBot/actions)
[![UptimeRobot](https://img.shields.io/uptimerobot/ratio/30/m786447893-903b482e5158c8b6483760e8)](https://octobot.click/gh-status)

#### Octobot Community
[![Active OctoBot](https://img.shields.io/badge/dynamic/json.svg?&url=https://metrics.octobot.online/metrics/community/count/0/-1/0&query=$.total&color=green&label=OctoBots%20this%20month)]()
[![Telegram Chat](https://img.shields.io/badge/telegram-chat-green.svg?logo=telegram&label=Telegram)](https://octobot.click/gh-telegram)
[![Discord](https://img.shields.io/discord/530629985661222912.svg?logo=discord&label=Discord)](https://octobot.click/gh-discord)
[![Telegram News](https://img.shields.io/badge/telegram-news-blue.svg?logo=telegram&label=Telegram)](https://t.me/OctoBot_Project)
[![Twitter](https://img.shields.io/twitter/follow/DrakkarsOctobot.svg?label=twitter&style=social)](https://octobot.click/gh-twitter)
[![YouTube](https://img.shields.io/youtube/channel/views/UC2YAaBeWY8y_Olqs79b_X8A?label=youtube&style=social)](https://octobot.click/gh-youtube)
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
- RAM : 250 MB
- Disk : 1 GB

## Installation
OctoBot's installation is **very simple**... because it is **very documented** ! See the [installation guides](https://www.octobot.online/guides/#installation) for more info.

#### One click deployment
Deploy your OctoBot on the OctoBot Cloud. No installation is required and your OctoBot will always be online and reachable.

[![Telegram News](https://img.shields.io/static/v1?label=Deploy&message=now&color=007bff&style=for-the-badge)](https://octobot.click/gh-deploy)


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

## Exchanges
[![Binance](../assets/binance-logo.png)](https://octobot.click/gh-binance)
[![Okx](../assets/okex-logo.png)](https://octobot.click/gh-okex)
[![GateIO](../assets/gateio-logo.png)](https://octobot.click/gh-gateio)
[![Huobi](../assets/huobi-logo.png)](https://octobot.click/gh-huobi)
[![Hollaex](../assets/hollaex-logo.png)](https://octobot.click/gh-hollaex)
[![Coinbase](../assets/coinbasepro-logo.png)](https://pro.coinbase.com)
[![Kucoin](../assets/kucoin-logo.png)](https://www.kucoin.com)
[![Bitmex](../assets/bitmex-logo.png)](https://bitmex.com)
[![Ascendex](../assets/ascendex-logo.png)](https://octobot.click/gh-ascendex)

Octobot supports many [exchanges](https://octobot.click/gh-exchanges) thanks to the [ccxt library](https://github.com/ccxt/ccxt). 
To activate trading on an exchange, just configure OctoBot with your API keys as described [on the exchange documentation](https://www.octobot.online/guides/#exchanges).

## Contribute from a browser IDE 
Make changes and contribute to OctoBot in a single click with an **already setup and ready to code developer environment** using Gitpod !

[![Open in Gitpod](https://gitpod.io/button/open-in-gitpod.svg)](https://gitpod.io/#https://github.com/Drakkar-Software/OctoBot)

## Disclaimer
Do not risk money which you are afraid to lose. USE THE SOFTWARE AT YOUR OWN RISK. THE AUTHORS 
AND ALL AFFILIATES ASSUME NO RESPONSIBILITY FOR YOUR TRADING RESULTS. 

Always start by running a trading bot in simulation mode and do not engage money
before you understand how it works and what profit/loss you should expect.

Please feel free to read the source code and understand the mechanism of this bot.

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
</table>
