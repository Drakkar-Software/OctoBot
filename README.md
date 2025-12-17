# OctoBot - Free Open Source Crypto Trading Bot
[![PyPI](https://img.shields.io/pypi/v/OctoBot.svg?logo=pypi)](https://pypi.org/project/OctoBot)
[![Downloads](https://pepy.tech/badge/octobot/month)](https://pepy.tech/project/octobot)
[![Dockerhub](https://img.shields.io/docker/pulls/drakkarsoftware/octobot.svg?logo=docker)](https://hub.docker.com/r/drakkarsoftware/octobot)
[![OctoBot-CI](https://github.com/Drakkar-Software/OctoBot/workflows/OctoBot-CI/badge.svg)](https://github.com/Drakkar-Software/OctoBot/actions)
[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/Drakkar-Software/OctoBot)

<p align="center">
  <img src="../assets/octobot-free-open-source-trading-bot-web-user-interface-showcase.gif" alt="OctoBot free open source trading bot web user interface showcase" width="630px"/>
</p>

[![OctoBot](https://img.shields.io/badge/dynamic/json.svg?&url=https://octobot.cloud/api/community/stats&query=$.total_bots&color=blue&label=Installed%20OctoBots)]()
[![Telegram Chat](https://img.shields.io/badge/telegram-chat-green.svg?logo=telegram&label=Telegram)](https://t.me/octobot_trading)
[![Discord](https://img.shields.io/discord/530629985661222912.svg?logo=discord&label=Discord)](https://discord.com/invite/vHkcb8W)
[![Telegram News](https://img.shields.io/badge/telegram-news-blue.svg?logo=telegram&label=Telegram)](https://t.me/OctoBot_Project)
[![Twitter](https://img.shields.io/twitter/follow/DrakkarsOctobot.svg?label=twitter&style=social)](https://x.com/DrakkarsOctoBot)
[![YouTube](https://img.shields.io/youtube/channel/views/UC2YAaBeWY8y_Olqs79b_X8A?label=youtube&style=social)](https://www.youtube.com/@octobot1134)

## Open source crypto trading bot with a visual user interface

[OctoBot](https://www.octobot.cloud/trading-bot?utm_source=github&utm_medium=dk&utm_campaign=regular_open_source_content&utm_content=readme_what_is_octobot) is an open source cryptocurrency trading robot designed for crypto investors who want to automate their investment strategies. The bot can automate strategies using built-in:
- Strategies such as [grids](#grid-trading-bot), [DCA strategies](#dca-trading-bot), [crypto baskets](#crypto-basket-trading-bot) and much more, which can all be configured
- [AI connectors](#ai-trading-bot) to trade using any [OpenAI](https://openai.com/) or [Ollama](https://ollama.com/) model such as ChatGPT, llama or any [custom model](https://ollama.com/search) running on an Ollama server 
- [TradingView connectors](#tradingview-trading-bot) to automate trades from [TradingView](https://www.tradingview.com/?aff_id=27595) indicators or strategies
- Social indicators to analyze social data such as [Google trends](https://trends.google.com/trends/explore?date=today%205-y&q=%2Fm%2F05p0rrx&hl=en) or [Reddit](https://reddit.com)
- Technical analysis indicators such as RSI, Moving Averages or MACD
- [15+ exchange integrations](#your-trading-bot-for-binance-coinbase-hyperliquid-and-15-other-exchanges) including Binance, Coinbase, MEXC and Hyperliquid


<p align="middle">
  <a href='https://www.youtube.com/watch?v=TJUU62e1jR8'  target="_blank" rel="noopener"><img alt='OctoBot - Open Source Crypto Trading Bot Introduction Video from the official OctoBot YouTube Channel' src='../assets/meet_octobot_preview.png' width="630px"/></a>
</p>

The trading bot is written in Python being built and improved as a free open source software since 2018. It can be [installed on your system or executed on a cloud provider](#installing-octobot-open-source-crypto-trading-bot).

### An easy to use trading bot with a Mobile App, Web and Telegram user interfaces
Are you looking for a bot you can setup from the peaceful environment of your home computer and that you can follow from anywhere using your phone?

OctoBot is designed for crypto investors who want to automate their trading strategies in a simple way, using a graphic interface to:
- Configure the details of their strategy and its traded markets and exchange(s)
- Test and optimize the strategy using [backtesting](https://www.octobot.cloud/en/guides/octobot-usage/backtesting?utm_source=github&utm_medium=dk&utm_campaign=regular_open_source_content&utm_content=backtesting)
- Live test it with paper money
- Execute it on a real exchange account, by automatically sending orders to the exchange

Once started, an OctoBot can be followed using its web interface, making it reachable when running on a cloud server.  
OctoBot can also be connected to a Telegram bot, therefore turning OctoBot into a [Telegram trading bot](https://www.octobot.cloud/en/guides/octobot-interfaces/telegram?utm_source=github&utm_medium=dk&utm_campaign=regular_open_source_content&utm_content=telegram).

You can also follow your trading bot from the OctoBot mobile app, which is designed to automate [octobot.cloud](https://www.octobot.cloud/trading-bot?utm_source=github&utm_medium=dk&utm_campaign=regular_open_source_content&utm_content=octobot_app_section) strategies, the app can also be used to follow your open source OctoBot's profits, portfolio, open orders and trades.

<p align="middle">
  <img src="../assets/mobile/octobot-mobile-app-deashboard-with-portfolio-value-and-two-live-bots-with-news.png" height="414" alt="octobot mobile app dashboard with portfolio value and two live bots with news">
  &nbsp;&nbsp;&nbsp;&nbsp;    
  <img src="../assets/mobile/octobot-mobile-app-bot-view-with-portfolio-content-recent-activities-and-historical-profits.png" height="414" alt="octobot mobile app bot view with portfolio content recent activities and historical profits">
</p>

<p align="middle">
    <a href='https://apps.apple.com/us/app/octobot-crypto-investment/id6502774175?utm_source=octobot-github&utm_media=readme&utm_content=mobile-app-img'><img alt='Get it on the Apple Play Store' src='../assets/apple_store.png' height="50px"/></a>
    <a href='https://play.google.com/store/apps/details?id=com.drakkarsoftware.octobotapp&utm_source=octobot-github&utm_media=readme&utm_content=mobile-app-img'><img alt='Get it on Google Play' src='https://play.google.com/intl/en_us/badges/images/generic/en_badge_web_generic.png' height="50px"/></a>
</p>

### Live and backtesting trading strategies automation
OctoBot is more than just a strategy execution engine, it can also simulate investments using [risk-free paper trading](https://www.octobot.cloud/en/guides/octobot-usage/simulator?utm_source=github&utm_medium=dk&utm_campaign=regular_open_source_content&utm_content=risk-free_paper_trading).


Even better, the trading robot comes with its [built-in backtesting engine](https://www.octobot.cloud/en/guides/octobot-usage/backtesting?utm_source=github&utm_medium=dk&utm_campaign=regular_open_source_content&utm_content=backtesting_engine) to help you test and optimize your strategy over a long period of time with a simulated portfolio and historical exchange data.

<p align="middle">
  <img alt='Backtesting report using grid trading on eth btc with 8 percent profit' src='../assets/backtesting_report.jpg' width="630px"/>
</p>

Backtesting your trading strategy and portfolio will give you accurate insights on the past performance and behavior of your trading strategy starting from its initial portfolio. This analysis tool gives you all the metrics to create the best version of your strategy before automating it with your real funds, on your exchange account.

### Your trading bot for Binance, Coinbase, Hyperliquid and 15+ other exchanges   
OctoBot supports the vast majority of crypto exchanges thanks to the great [CCXT library](https://github.com/ccxt/ccxt).

<p align="middle">
  <img alt='list of octobot supported exchanges including binance coinbase hyperliquid mexc and more' src='../assets/list-of-octobot-supported-exchanges-including-binance-coinbase-hyperliquid-mexc-and-more.png' width="630px"/>
</p>


This wide range of supported exchanges makes it easy to create investment strategies on any crypto, from Bitcoin, Ethereum or Solana to altcoins from the darkest depths of the altcoin forest.


Supported exchanges notably include:
- [Binance](https://accounts.binance.com/en/register?ref=528112221) spot and futures trading using the REST and websocket APIs
- [Coinbase](https://www.coinbase.com/) spot trading using the REST and websocket APIs
- [Bybit](https://www.bybit.com/en-US/invite?ref=QW6O5) spot and futures trading using the REST and websocket APIs Note: due to a recent update, the Bybit API will soon be available again on OctoBot 
- [Hyperliquid](https://app.hyperliquid.xyz/) spot trading (with API Keys) using the REST and websocket APIs
- [MEXC](https://www.mexc.com/register?inviteCode=1fqGu) spot trading using the REST and websocket APIs
- [Kucoin](https://www.kucoin.com/ucenter/signup?rcode=rJ2Q2T3) spot and futures trading using the REST and websocket APIs
- All [HollaEx-Powered](https://www.octobot.cloud/en/guides/octobot-partner-exchanges/hollaex/account-setup) exchanges. Learn more on [HollaEx, the open source white label exchange](https://hollaex.com/)
- Many other such as OKX, Binance US, Crypto.com, HTX, Bitget, BingX, CoinEx, BitMart, Phemex, Gate.io, Ascendex and more on the [full list of supported exchanges](https://www.octobot.cloud/en/guides/exchanges?utm_source=github&utm_medium=dk&utm_campaign=regular_open_source_content&utm_content=exchanges_full_list).

## Automate your trading strategies
OctoBot is designed as a one-stop-shop for crypto trading strategies. If you think of a crypto trading strategy, it can most likely be automated by OctoBot, unless it requires very complex custom mechanisms.

### AI trading bot
OctoBot can be an AI trading bot using [OpenAI](https://openai.com/) model such as ChatGPT. The [ChatGPT trading mode](https://www.octobot.cloud/en/guides/octobot-trading-modes/chatgpt-trading?utm_source=github&utm_medium=dk&utm_campaign=regular_open_source_content&utm_content=ai-trading-bot) is the dedicated OctoBot configuration to give market context to a LLM model, ask for its opinion and trade accordingly.

Local LLM models, such as [Ollama](https://ollama.com/) llama or any [custom model](https://ollama.com/search) running on your Ollama server can also be used by the bot for deeper customization and cost management.

### Grid trading bot
Grid trading is a strategy that extracts value from volatility. Unlike most strategies, it relies on pure math and no statistics. It will "simply" create and maintain many buy and sell orders at regular intervals and generate profits every time both buy and sell orders are executed. [The OctoBot grid trading bot](https://www.octobot.cloud/en/guides/octobot-trading-modes/grid-trading-mode?utm_source=github&utm_medium=dk&utm_campaign=regular_open_source_content&utm_content=grid-trading-bot) can be heavily customized and optimized to be perfectly adapted to your market and exchange.

### DCA trading bot
Dollar Cost Averaging (DCA) is a well known investment strategy where you buy on a regular basis in order to profit from local price drops. It allows investors to reduce their overall buying costs. As a [DCA trading bot](https://www.octobot.cloud/en/guides/octobot-trading-modes/dca-trading-mode?utm_source=github&utm_medium=dk&utm_campaign=regular_open_source_content&utm_content=dca-trading-bot), OctoBot can optimize your investment strategies for short or long term gains with heavy customization and backtesting capabilities.

### TradingView trading bot
Use OctoBot as your [TradingView trading bot](https://www.octobot.cloud/en/guides/octobot-trading-modes/tradingview-trading-mode?utm_source=github&utm_medium=dk&utm_campaign=regular_open_source_content&utm_content=tradingview-trading-bot) and simply emit alerts from your TradingView indicators or strategies. Use these alerts to trade any crypto market, on any exchange from your TradingView native strategy.  
Whether it's from a visual TradingView indicator or a heavily optimized Pine Script strategy, your trades can be automated.

### Crypto basket trading bot
Crypto baskets are similar to stock indexes or ETFs. They enable you to invest into many cryptocurrencies, all at once, in a simple way. A crypto basket is a simple way to invest in the whole crypto market at once, or follow coin categories, such as AI or RWA coins.  
OctoBot can be used as a [crypto basket trading bot](https://www.octobot.cloud/en/guides/octobot-trading-modes/index-trading-mode?utm_source=github&utm_medium=dk&utm_campaign=regular_open_source_content&utm_content=crypto-basket-trading-bot) and make it simple to invest in customized crypto indexes or follow baskets from the wide range of [OctoBot cloud's crypto baskets](https://www.octobot.cloud/features/crypto-basket?utm_source=github&utm_medium=dk&utm_campaign=regular_open_source_content&utm_content=crypto-basket-trading-bot).

### Market Making trading bot
OctoBot can also [automate market making strategies](https://github.com/Drakkar-Software/OctoBot-market-making) to help token creators provide liquidity to their markets.

<p align="middle">
  <img alt='octobot market making dashboard with buy and sell orders' src='https://raw.githubusercontent.com/Drakkar-Software/OctoBot-Market-Making/master/docs/octobot-market-making-dashboard-with-buy-and-sell-orders.png' width="630px"/>
</p>

Advanced market making strategies can be automated on [market-making.octobot.cloud](https://market-making.octobot.cloud?utm_source=github&utm_medium=dk&utm_campaign=regular_open_source_content&utm_content=market-making), the self-service market making platform based on OctoBot. Feel free to contact us if you have any questions about it.

### Institutional custom strategies
If you represent an institution that is interested in a commercial license or custom development to suit your specific needs or strategy please contact us at <a href="mailto:contact@drakkar.software">contact@drakkar.software</a>. 

## Installing OctoBot, open source crypto trading bot

<p align="center">
  <img src="../assets/a-man-relaxing-in-his-couch-while-octobot-the-free-open-source-crypto-trading-bot-is-making-money-by-automating-cryptocurrency-strategies.png" alt="A man relaxing in his couch while octobot the free open source crypto trading bot is making money by automating cryptocurrency strategies" width="630px">
</p>

OctoBot can be deployed on the cloud or for free on your computer, server or [Raspberry Pi](https://www.raspberrypi.com/).

### Deploying OctoBot with one click on DigitalOcean
OctoBot can be easily launched in the cloud from the [DigitalOcean Marketplace](https://digitalocean.pxf.io/octobot-app).

[![Deploy on DigitalOcean](https://mp-assets1.sfo2.digitaloceanspaces.com/deploy-to-do/do-btn-blue.svg)](https://digitalocean.pxf.io/start-octobot)

### Using the OctoBot Executable
This is the easiest way to download and install OctoBot on your computer or server. Here is [our executable installation guide](https://www.octobot.cloud/en/guides/octobot-installation/install-octobot-on-your-computer?utm_source=github&utm_medium=dk&utm_campaign=regular_open_source_content&utm_content=readme_local_installation).  
Note: The latest release executables for Windows, MacOS, Linux and Raspberry Pi are automatically built and pushed to the [releases](https://github.com/Drakkar-Software/OctoBot/releases) page.

### Using the OctoBot Docker image
You can also install OctoBot using the [OctoBot Docker image](https://hub.docker.com/r/drakkarsoftware/octobot). Here is our [using Docker installation guide](https://www.octobot.cloud/en/guides/octobot-installation/install-octobot-with-docker-video?utm_source=github&utm_medium=dk&utm_campaign=regular_open_source_content&utm_content=readme_docker_installation).

Docker install in one liner:
```sh
docker run -itd --name OctoBot -p 80:5001 -v $(pwd)/user:/octobot/user -v $(pwd)/tentacles:/octobot/tentacles -v $(pwd)/logs:/octobot/logs drakkarsoftware/octobot:stable
```

### Installing OctoBot using Python
If you want to install OctoBot from Python, for example in order to edit the code or contribute, [here is our python installation guide](https://www.octobot.cloud/en/guides/octobot-installation/install-octobot-with-python-and-git?utm_source=github&utm_medium=dk&utm_campaign=regular_open_source_content&utm_content=readme_python_installation).

You might also want to look at our [contributing guide](CONTRIBUTING.md) to quickly understand how OctoBot is architected.

### Minimum hardware requirements  
- CPU : 1 Core / 1GHz  
- RAM : 250 MB
- Disk : 1 GB

## How to contribute to OctoBot

Would you like to add or improve something in OctoBot? We welcome your pull requests!  
Please have a look at our [contributing guide](CONTRIBUTING.md) to read our guidelines.

### Contribute to OctoBot from a local IDE
We recommend using a [VSCode](https://code.visualstudio.com/)-based IDE to contribute to OctoBot however [PyCharm](https://www.jetbrains.com/pycharm/) can also be used.  
As the OctoBot code is split into different repositories, we created a [developer installation guide](https://www.octobot.cloud/en/guides/octobot-developers-environment/setup-your-environment?utm_source=github&utm_medium=dk&utm_campaign=regular_open_source_content&utm_content=setup_your_environment) to help setting up a VSCode or PyCharm environment.

### Contribute to OctoBot from Ona (formerly Gitpod)
Make changes and contribute to OctoBot in a single click with an **already setup and ready to code developer environment** using Ona.

[![Contribute from Ona](https://gitpod.io/button/open-in-gitpod.svg)](https://gitpod.io/#https://github.com/Drakkar-Software/OctoBot)

## Disclaimer
Do not risk money which you are afraid to lose. USE THE SOFTWARE AT YOUR OWN RISK. THE AUTHORS AND ALL AFFILIATES ASSUME NO RESPONSIBILITY FOR YOUR TRADING RESULTS. 

Always start by running a trading bot in simulation mode and do not engage money
before you understand how it works and what profit/loss you should expect.

Please feel free to read the source code and understand the mechanism of this bot.

## Sponsors
<table>
<tr>
<td>Special thanks to <a href="https://www.chatwoot.com/" target="_blank">Chatwoot</a> for helping us assist the users of OctoBot.</td>
<td><a href="https://github.com/chatwoot/chatwoot" target="_blank"><p align="center"><img src="https://raw.githubusercontent.com/chatwoot/chatwoot/develop/public/brand-assets/logo.svg" width="500px"></p></a></td>
</tr>
<tr>
<td>Huge thank you to <a href="https://www.scaleway.com" target="_blank">Scaleway</a> for hosting OctoBot's cloud services.</td>
<td><a href="https://www.scaleway.com" target="_blank"><p align="center"><img src="https://raw.githubusercontent.com/Drakkar-Software/OctoBot/assets/scaleway.svg" width="500px"></p></a></td>
</tr>
<tr>
<td>A big thank you to <a href="https://sentry.io/welcome/" target="_blank">Sentry</a> for helping us identify and understand errors in OctoBot to make it better.</td>
<td><a href="https://sentry.io/welcome/" target="_blank"><p align="center"><img src="https://raw.githubusercontent.com/Drakkar-Software/OctoBot/assets/sentry.png" width="500px"></p></a></td>
</tr>
</table>

## License
GNU General Public License v3.0 or later.

See [GPL-3.0 LICENSE](https://github.com/Drakkar-Software/OctoBot/blob/master/LICENSE) to see the full text.


## Give a boost to OctoBot
Do you like what we are building with OctoBot? Consider giving us a star ⭐ to boost the project's visibility! 

And join us on the OctoBot channels 

[![Telegram Chat](https://img.shields.io/badge/telegram-chat-green.svg?logo=telegram&label=Telegram)](https://t.me/octobot_trading)
[![Discord](https://img.shields.io/discord/530629985661222912.svg?logo=discord&label=Discord)](https://discord.com/invite/vHkcb8W)
[![Telegram News](https://img.shields.io/badge/telegram-news-blue.svg?logo=telegram&label=Telegram)](https://t.me/OctoBot_Project)
[![Twitter](https://img.shields.io/twitter/follow/DrakkarsOctobot.svg?label=twitter&style=social)](https://x.com/DrakkarsOctoBot)
[![YouTube](https://img.shields.io/youtube/channel/views/UC2YAaBeWY8y_Olqs79b_X8A?label=youtube&style=social)](https://www.youtube.com/@octobot1134)
