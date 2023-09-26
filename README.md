# OctoBot [1.0.0](https://octobot.click/gh-changelog)
[![PyPI](https://img.shields.io/pypi/v/OctoBot.svg?logo=pypi)](https://octobot.click/gh-pypi)
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
  <img src="../assets/illustration.png" alt="Octobot illustration">
</p>

<p align="center">
  <img src="../assets/ReadMeIntro.gif" alt="Intro" />
</p>

## Launch of the new OctoBot cloud
The OctoBot team is proud to announce the launch of the [new octobot.cloud](https://octobot.cloud/?utm_source=github&utm_medium=dk&utm_campaign=regular_open_source_content&utm_content=readme)
where 90% of trading strategies can be automated **in a very easy way** and **for free**.

[![try octobot cloud now](https://img.shields.io/static/v1?label=Try%20the%20new%20OctoBot%20cloud&message=now&color=007bff&style=for-the-badge)](https://octobot.cloud/?utm_source=github&utm_medium=dk&utm_campaign=production_annoucements&utm_content=readme_button)

We are looking forward to receiving your feedback on our new OctoBot based system.

## What is Octobot  ?
<p align="middle">
  <a href="../assets/dashboard.png"><img src="../assets/dashboard.png" height="414" alt="Web interface"></a>  
  &nbsp;&nbsp;&nbsp;&nbsp;    
  <a href="https://www.octobot.info/interfaces/telegram-interface"><img src="../assets/telegram-interface.png" height="414" alt="Telegram interface"></a>  
</p>


[Octobot](https://www.octobot.online/) is a powerful open-source cryptocurrency trading robot.

OctoBot is highly customizable using its configuration and tentacles system.  
You can build your own bot using the infinite [configuration](https://www.octobot.info/configuration/profile-configuration) possibilities such as  **technical analysis**, **social media processing** or even **external statistics management** like google trends.  
  
OctoBot is **AI ready**: Python being the main language for OctoBot, it's easy to integrate machine-learning libraries such as [Tensorflow](https://github.com/tensorflow/tensorflow) or any other libraries and take advantage of all the available data and create a very powerful trading strategy.  
  
Octobot's main feature is **evolution**, you can : 
- Share your configurations with other octobot users.
- [Install](https://www.octobot.info/advanced_usage/tentacle-manager), [modify](https://developer.octobot.info/tentacles/tentacle-development) and even [create](https://developer.octobot.info/tentacles/tentacle-development) new tentacles to build your ideal cryptocurrency trading robot.
- [Contribute](https://developer.octobot.info/installation/developer-installation/octobot-developer-installation) to improve OctoBot core repositories and tentacles.

## Installation  
OctoBot's installation is **very simple**, you can either:
- [Deploy your OctoBot on OctoBot Cloud](https://octobot.cloud/?utm_source=github&utm_medium=dk&utm_campaign=regular_open_source_content&utm_content=readme_deploy_on_cloud). With OctoBot cloud, experience hassle-free installation, updates, and maintenance - leave it all to us! Your robot will also benefit from cloud only features.
- [Download and install](https://www.octobot.info/installation/local-installation) OctoBot on your computer or server and enjoy all features for free.
- Install OctoBot [using docker](https://www.octobot.info/installation/local-installation#option-2-with-docker).

    Docker install in one line summary:
    ```
    docker run -itd --name OctoBot -p 80:5001 -v $(pwd)/user:/octobot/user -v $(pwd)/tentacles:/octobot/tentacles -v $(pwd)/logs:/octobot/logs drakkarsoftware/octobot:stable
    ```
    Your OctoBot will be accessible on [http://localhost](http://localhost).

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
To activate trading on an exchange, just configure OctoBot with your API keys as described [on the exchange documentation](https://www.octobot.info/configuration/exchanges).


### Paper trading
To trade on any exchange, just enable the exchange in your OctoBot. This you to trade with simulated money on this exchange.

No exchange credential is required.

### Real trading
To use your real exchange account with OctoBot, enter your exchange API keys as described [on the exchange documentation](https://octobot.click/gh-exchanges). 

## Testing trading strategies

OctoBot comes with its builtin backtesting engine which enables you to trade with simulated money using historical exchange data.

[![Backtesting report](../assets/backtesting_report.jpg)](https://github.com/Drakkar-Software/OctoBot/blob/assets/backtesting_report.jpg)  

Backtesting will give you accurate insights on the past performance and behavior of strategies using OctoBot.

## Contribute from a browser IDE 
Make changes and contribute to OctoBot in a single click with an **already setup and ready to code developer environment** using Gitpod !

[![Open in Gitpod](https://gitpod.io/button/open-in-gitpod.svg)](https://gitpod.io/#https://github.com/Drakkar-Software/OctoBot)

## Hardware requirements  
- CPU : 1 Core / 1GHz  
- RAM : 250 MB  
- Disk : 1 GB  

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
