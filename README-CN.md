# OctoBot - 免费开源的加密货币交易机器人

> [English](README.md) | 简体中文

[![PyPI](https://img.shields.io/pypi/v/OctoBot.svg?logo=pypi)](https://pypi.org/project/OctoBot)
[![Downloads](https://pepy.tech/badge/octobot/month)](https://pepy.tech/project/octobot)
[![Dockerhub](https://img.shields.io/docker/pulls/drakkarsoftware/octobot.svg?logo=docker)](https://hub.docker.com/r/drakkarsoftware/octobot)
[![OctoBot-CI](https://github.com/Drakkar-Software/OctoBot/workflows/OctoBot-CI/badge.svg)](https://github.com/Drakkar-Software/OctoBot/actions)
[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/Drakkar-Software/OctoBot)

<p align="center">
  <img src="../assets/octobot-free-open-source-trading-bot-web-user-interface-showcase.gif" alt="OctoBot 免费开源交易机器人 Web 用户界面展示" width="630px"/>
</p>

[![OctoBot](https://img.shields.io/badge/dynamic/json.svg?&url=https://octobot.cloud/api/community/stats&query=$.total_bots&color=blue&label=Installed%20OctoBots)](https://www.octobot.cloud/trading-bot?utm_source=github&utm_medium=dk&utm_campaign=regular_open_source_content&utm_content=readme_installed_bots_badge)
[![Telegram Chat](https://img.shields.io/badge/telegram-chat-green.svg?logo=telegram&label=Telegram)](https://t.me/octobot_trading)
[![Discord](https://img.shields.io/discord/530629985661222912.svg?logo=discord&label=Discord)](https://discord.com/invite/vHkcb8W)
[![Telegram News](https://img.shields.io/badge/telegram-news-blue.svg?logo=telegram&label=Telegram)](https://t.me/OctoBot_Project)
[![Twitter](https://img.shields.io/twitter/follow/DrakkarsOctobot.svg?label=twitter&style=social)](https://x.com/DrakkarsOctoBot)
[![YouTube](https://img.shields.io/youtube/channel/views/UC2YAaBeWY8y_Olqs79b_X8A?label=youtube&style=social)](https://www.youtube.com/@octobot1134)

OctoBot 是一款带有**可视化用户界面**的**免费开源加密货币交易机器人**。你可以在 [octobot.cloud](https://www.octobot.cloud/trading-bot?utm_source=github&utm_medium=dk&utm_campaign=regular_open_source_content&utm_content=readme_hero) 上查看指南、功能及云端方案。

## 全新 OctoBot Beta 已上线

最新版本默认以[**节点模式**](https://www.octobot.cloud/en/guides/octobot?utm_source=github&utm_medium=dk&utm_campaign=regular_open_source_content&utm_content=node_mode)运行。你的节点会作为[全新 OctoBot 界面](https://new.mobile.octobot.cloud/home?utm_source=github&utm_medium=dk&utm_campaign=regular_open_source_content&utm_content=readme_new_interface)和移动应用的后端；你可以在统一且安全的仪表盘中管理钱包、自动化任务和多个策略。

通过节点界面，你还可以启动**手动 OctoBot** 实例，用于回测、Telegram、TradingView 以及其他经典 OctoBot 工作流。

阅读[完整的 Beta 公告](https://www.octobot.cloud/en/blog/next-octobot-beta-testing-starts?utm_source=github&utm_medium=dk&utm_campaign=regular_open_source_content&utm_content=full_beta_announcement)，进一步了解 OctoBot 迄今为止规模最大的一次更新。

请注意，全新 OctoBot Beta 仍在开发中，你可能会遇到缺陷或尚未完整的功能。

## 带可视化用户界面的开源加密货币交易机器人

[OctoBot](https://www.octobot.cloud/trading-bot?utm_source=github&utm_medium=dk&utm_campaign=regular_open_source_content&utm_content=readme_what_is_octobot) 是一款开源加密货币交易机器人，专为希望自动化投资策略的加密货币投资者设计。该机器人可通过以下内置能力实现策略自动化：

- 可配置的策略，例如[网格](#grid-trading-bot)、[DCA 策略](#dca-trading-bot)、[加密货币篮子](#crypto-basket-trading-bot)等
- [AI 连接器](#ai-trading-bot)，可使用任意 [OpenAI](https://openai.com/) 或 [Ollama](https://ollama.com/) 模型进行交易，例如 ChatGPT、llama，或运行在 Ollama 服务器上的任意[自定义模型](https://ollama.com/search)
- [TradingView 连接器](#tradingview-trading-bot)，可根据 [TradingView](https://www.tradingview.com/?aff_id=27595) 指标或策略自动执行交易
- 社交指标，用于分析 [Google Trends](https://trends.google.com/trends/explore?date=today%205-y&q=%2Fm%2F05p0rrx&hl=en) 或 [Reddit](https://reddit.com) 等社交数据
- RSI、移动平均线或 MACD 等技术分析指标
- [15 家以上交易所集成](#your-trading-bot-for-binance-coinbase-hyperliquid-and-15-other-exchanges)，包括 Binance、Coinbase、MEXC 和 Hyperliquid

<p align="middle">
  <a href='https://www.youtube.com/watch?v=TJUU62e1jR8'  target="_blank" rel="noopener"><img alt='OctoBot - 来自 OctoBot 官方 YouTube 频道的开源加密货币交易机器人介绍视频' src='../assets/meet_octobot_preview.png' width="630px"/></a>
</p>

该交易机器人使用 Python 编写，自 2018 年起作为免费开源软件持续构建。你可以[将它安装在自己的系统上，或运行在云服务提供商上](#installing-octobot-open-source-crypto-trading-bot)。

### 通过桌面端、移动端、网页或 Telegram 控制 OctoBot

你是否希望能在家中安静的环境中完成机器人配置，并通过手机随时随地查看运行情况？

#### OctoBot Beta：节点模式与全新界面

安装最新版本，并在你的电脑或服务器上运行 OctoBot。你可以通过浏览器中的[全新 OctoBot 界面](https://new.mobile.octobot.cloud/home?utm_source=github&utm_medium=dk&utm_campaign=regular_open_source_content&utm_content=readme_new_interface)连接它，也可以使用移动应用。

在一个节点上运行多个**自动化任务**（DCA、网格、加密货币篮子、TradingView 等），并在同一个仪表盘中监控整个投资组合。

[全新 OctoBot 的理念](https://www.octobot.cloud/en/blog/next-octobot-one-platform-for-all?utm_source=github&utm_medium=dk&utm_campaign=regular_open_source_content&utm_content=new_octobots_philosophy)围绕三大支柱：
1. 多投资组合分析与自动化
2. 自托管：你的密钥永远不会离开你的设备
3. 零知识隐私：所有数据均经过端到端加密，除你之外无人能够读取

#### Web 界面与 Telegram

OctoBot 专为希望以简单方式自动化交易策略的加密货币投资者而设计，它提供图形界面，可用于：

- 配置策略细节及其交易市场和交易所
- 使用[回测](https://www.octobot.cloud/en/guides/octobot-usage/backtesting?utm_source=github&utm_medium=dk&utm_campaign=regular_open_source_content&utm_content=backtesting)测试并优化策略
- 使用模拟资金进行实盘测试
- 在真实交易所账户上执行策略，自动向交易所发送订单

**手动 OctoBot** 实例仍可通过其内置 Web 界面进行配置和跟踪，因此即使运行在云服务器上也能访问。
OctoBot 还可以连接 Telegram 机器人，从而将 OctoBot 变成 [Telegram 交易机器人](https://www.octobot.cloud/en/guides/octobot-interfaces/telegram?utm_source=github&utm_medium=dk&utm_campaign=regular_open_source_content&utm_content=telegram)。


你还可以通过 OctoBot 移动应用查看交易机器人的运行情况；该应用旨在自动化 [octobot.cloud](https://www.octobot.cloud/trading-bot?utm_source=github&utm_medium=dk&utm_campaign=regular_open_source_content&utm_content=octobot_app_section) 策略。该应用也可用于查看你的开源 OctoBot 收益、投资组合、未完成订单和交易记录。

公开（非 Beta）的 OctoBot 移动应用面向 [octobot.cloud](https://www.octobot.cloud/trading-bot?utm_source=github&utm_medium=dk&utm_campaign=regular_open_source_content&utm_content=octobot_app_section) 策略。若要管理 Beta 版开源 OctoBot，请改用全新 OctoBot 界面或移动端 Beta 应用。

<p align="middle">
  <img src="../assets/mobile/octobot-mobile-app-deashboard-with-portfolio-value-and-two-live-bots-with-news.png" height="414" alt="OctoBot 移动应用仪表盘，显示投资组合价值、两个正在运行的机器人及新闻">
  &nbsp;&nbsp;&nbsp;&nbsp;    
  <img src="../assets/mobile/octobot-mobile-app-bot-view-with-portfolio-content-recent-activities-and-historical-profits.png" height="414" alt="OctoBot 移动应用机器人视图，显示投资组合内容、近期活动和历史收益">
</p>

<p align="middle">
    <a href='https://apps.apple.com/us/app/octobot-crypto-investment/id6502774175?utm_source=octobot-github&utm_media=readme&utm_content=mobile-app-img'><img alt='在 Apple App Store 获取' src='../assets/apple_store.png' height="50px"/></a>
    <a href='https://play.google.com/store/apps/details?id=com.drakkarsoftware.octobotapp&utm_source=octobot-github&utm_media=readme&utm_content=mobile-app-img'><img alt='在 Google Play 获取' src='https://play.google.com/intl/en_us/badges/images/generic/en_badge_web_generic.png' height="50px"/></a>
</p>

### 实盘交易与回测交易策略自动化

OctoBot 不仅仅是策略执行引擎，它还可以通过[无风险模拟交易](https://www.octobot.cloud/en/guides/octobot-usage/simulator?utm_source=github&utm_medium=dk&utm_campaign=regular_open_source_content&utm_content=risk-free_paper_trading)模拟投资。

更进一步，该交易机器人内置[回测引擎](https://www.octobot.cloud/en/guides/octobot-usage/backtesting?utm_source=github&utm_medium=dk&utm_campaign=regular_open_source_content&utm_content=backtesting_engine)，可利用模拟投资组合和历史交易所数据，帮助你长期测试并优化策略（仅适用于[手动 OctoBot](https://www.octobot.cloud/en/guides/octobot?utm_source=github&utm_medium=dk&utm_campaign=regular_open_source_content&utm_content=manual_octobots)）。

<p align="middle">
  <img alt='使用网格交易在 ETH/BTC 上获得 8% 收益的回测报告' src='../assets/backtesting_report.jpg' width="630px"/>
</p>

对交易策略和投资组合进行回测，可以让你基于初始投资组合准确了解策略过去的表现和行为。这一分析工具提供所需的全部指标，帮助你在使用真实资金通过交易所账户自动化执行策略之前，打造出最佳版本的策略。

<a id="your-trading-bot-for-binance-coinbase-hyperliquid-and-15-other-exchanges"></a>
### 适用于 Binance、Coinbase、Hyperliquid 及 15 家以上其他交易所的交易机器人

得益于出色的 [CCXT 库](https://github.com/ccxt/ccxt)，OctoBot 支持绝大多数加密货币交易所。

<p align="middle">
  <img alt='OctoBot 支持的交易所列表，包括 Binance、Coinbase、Hyperliquid、MEXC 等' src='../assets/list-of-octobot-supported-exchanges-including-binance-coinbase-hyperliquid-mexc-and-more.png' width="630px"/>
</p>

如此广泛的交易所支持，使你可以轻松为任何加密货币创建投资策略，从 Bitcoin、Ethereum 或 Solana，到山寨币森林最深处的各类山寨币。

支持的交易所主要包括：

- [Binance](https://accounts.binance.com/en/register?ref=528112221)：使用 REST 和 WebSocket API 进行现货及期货交易
- [Coinbase](https://www.coinbase.com/)：使用 REST 和 WebSocket API 进行现货交易
- [Bybit](https://www.bybit.com/en-US/invite?ref=QW6O5)：使用 REST 和 WebSocket API 进行现货及期货交易。注意：由于近期更新，Bybit API 很快将重新在 OctoBot 上提供
- [Hyperliquid](https://app.hyperliquid.xyz/)：使用 API 密钥及 REST 和 WebSocket API 进行现货交易
- [MEXC](https://www.mexc.com/register?inviteCode=1fqGu)：使用 REST 和 WebSocket API 进行现货交易
- [Kucoin](https://www.kucoin.com/ucenter/signup?rcode=rJ2Q2T3)：使用 REST 和 WebSocket API 进行现货及期货交易
- 所有[由 HollaEx 驱动](https://www.octobot.cloud/en/guides/octobot-partner-exchanges/hollaex/account-setup)的交易所。进一步了解[开源白标交易所 HollaEx](https://hollaex.com/)
- 其他众多交易所，例如 OKX、Binance US、Crypto.com、HTX、Bitget、BingX、CoinEx、BitMart、Phemex、Gate.io、Ascendex 等，详见[支持的交易所完整列表](https://www.octobot.cloud/en/guides/exchanges?utm_source=github&utm_medium=dk&utm_campaign=regular_open_source_content&utm_content=exchanges_full_list)。

## 自动化你的交易策略

OctoBot 被设计为加密货币交易策略的一站式解决方案。只要你设想的策略不依赖极其复杂的自定义机制，它很可能都可以通过 OctoBot 实现自动化。

<a id="ai-trading-bot"></a>
### AI 交易机器人

OctoBot 可以利用 [OpenAI](https://openai.com/) 的 ChatGPT 等模型成为 AI 交易机器人。[ChatGPT 交易模式](https://www.octobot.cloud/en/guides/octobot-trading-modes/chatgpt-trading?utm_source=github&utm_medium=dk&utm_campaign=regular_open_source_content&utm_content=ai-trading-bot)是 OctoBot 的专用配置，用于向 LLM 模型提供市场背景、征求其意见并据此交易。

该机器人还可以使用本地 LLM 模型，例如 [Ollama](https://ollama.com/) 的 llama，或运行在你自己的 Ollama 服务器上的任意[自定义模型](https://ollama.com/search)，从而实现更深入的定制和成本管理。

<a id="grid-trading-bot"></a>
### 网格交易机器人

网格交易是一种从波动中获利的策略。与大多数策略不同，它依赖纯数学而非统计学。它会“简单地”按固定间隔创建并维护大量买入和卖出订单，并在每当买入和卖出订单均成交时产生收益。[OctoBot 网格交易机器人](https://www.octobot.cloud/en/guides/octobot-trading-modes/grid-trading-mode?utm_source=github&utm_medium=dk&utm_campaign=regular_open_source_content&utm_content=grid-trading-bot)可以进行深度定制和优化，以完美适配你的市场和交易所。

<a id="dca-trading-bot"></a>
### DCA 交易机器人

定投（Dollar Cost Averaging，DCA）是一种广为人知的投资策略，通过定期买入来从局部价格下跌中获利。它可以帮助投资者降低整体买入成本。作为 [DCA 交易机器人](https://www.octobot.cloud/en/guides/octobot-trading-modes/dca-trading-mode?utm_source=github&utm_medium=dk&utm_campaign=regular_open_source_content&utm_content=dca-trading-bot)，OctoBot 可通过高度定制和回测能力，针对短期或长期收益优化你的投资策略。

<a id="tradingview-trading-bot"></a>
### TradingView 交易机器人

只需从 TradingView 指标或策略中发出警报，即可将 OctoBot 用作你的 [TradingView 交易机器人](https://www.octobot.cloud/en/guides/octobot-trading-modes/tradingview-trading-mode?utm_source=github&utm_medium=dk&utm_campaign=regular_open_source_content&utm_content=tradingview-trading-bot)。使用这些警报，你可以在任何交易所交易任何加密货币市场，并直接沿用 TradingView 原生策略。
无论使用可视化 TradingView 指标，还是经过深度优化的 Pine Script 策略，你的交易都可以实现自动化。

<a id="crypto-basket-trading-bot"></a>
### 加密货币篮子交易机器人

加密货币篮子类似于股票指数或 ETF，可以让你以简单的方式同时投资多种加密货币。加密货币篮子既可以用于一次性投资整个加密货币市场，也可以用于跟踪 AI 或 RWA 代币等币种类别。
OctoBot 可用作[加密货币篮子交易机器人](https://www.octobot.cloud/en/guides/octobot-trading-modes/index-trading-mode?utm_source=github&utm_medium=dk&utm_campaign=regular_open_source_content&utm_content=crypto-basket-trading-bot)，让你轻松投资自定义加密货币指数，或跟踪 [OctoBot 云端丰富的加密货币篮子](https://www.octobot.cloud/features/crypto-basket?utm_source=github&utm_medium=dk&utm_campaign=regular_open_source_content&utm_content=crypto-basket-trading-bot)。

### 做市交易机器人

OctoBot 还可以[自动化做市策略](https://github.com/Drakkar-Software/OctoBot-market-making)，帮助代币发行方为其市场提供流动性。

<p align="middle">
  <img alt='OctoBot 做市仪表盘，显示买入和卖出订单' src='https://raw.githubusercontent.com/Drakkar-Software/OctoBot-Market-Making/master/docs/octobot-market-making-dashboard-with-buy-and-sell-orders.png' width="630px"/>
</p>

高级做市策略可在 [market-making.octobot.cloud](https://market-making.octobot.cloud?utm_source=github&utm_medium=dk&utm_campaign=regular_open_source_content&utm_content=market-making) 上实现自动化，这是一个基于 OctoBot 的自助式做市平台。如有任何疑问，欢迎与我们联系。

### 机构定制策略

如果你代表机构，并希望获得商业许可证或定制开发服务以满足特定需求或策略，请通过 [contact@drakkar.software](mailto:contact@drakkar.software) 联系我们。

<a id="installing-octobot-open-source-crypto-trading-bot"></a>
## 安装 OctoBot 开源加密货币交易机器人

<p align="center">
  <img src="../assets/a-man-relaxing-in-his-couch-while-octobot-the-free-open-source-crypto-trading-bot-is-making-money-by-automating-cryptocurrency-strategies.png" alt="一个人惬意地躺在沙发上，而免费开源的加密货币交易机器人 OctoBot 正通过自动化加密货币策略赚钱" width="630px">
</p>

启动[最新版本](https://github.com/Drakkar-Software/OctoBot/releases/latest)会以**节点模式**运行 OctoBot。请参阅[入门指南](https://www.octobot.cloud/en/guides/octobot-beta-getting-started?utm_source=github&utm_medium=dk&utm_campaign=regular_open_source_content&utm_content=readme_install_beta)，将全新 OctoBot 界面连接到你的节点。

OctoBot 可部署在云端，也可免费运行在你的电脑、服务器或 [Raspberry Pi](https://www.raspberrypi.com/) 上。

Linux、macOS、WSL 2 或 Windows 用户如需使用 uv 从源码安装 OctoBot，请参阅 [OctoBot 源码安装与使用指南](GUIDE-CN.md)。

### 在 DigitalOcean 上一键部署 OctoBot

你可以通过 [DigitalOcean Marketplace](https://marketplace.digitalocean.com/apps/octobot) 轻松在云端启动 OctoBot。

[![Deploy on DigitalOcean](https://mp-assets1.sfo2.digitaloceanspaces.com/deploy-to-do/do-btn-blue.svg)](https://marketplace.digitalocean.com/apps/octobot)

### 使用 OctoBot 可执行文件

这是在你的电脑或服务器上下载并安装 OctoBot 最简单的方式。这里是[可执行文件安装指南](https://www.octobot.cloud/en/guides/octobot-installation/install-octobot-on-your-computer?utm_source=github&utm_medium=dk&utm_campaign=regular_open_source_content&utm_content=readme_local_installation)。
注意：适用于 Windows、MacOS、Linux 和 Raspberry Pi 的最新版本可执行文件会自动构建并推送至 [releases](https://github.com/Drakkar-Software/OctoBot/releases) 页面。

### 使用 OctoBot Docker 镜像

你还可以使用 [OctoBot Docker 镜像](https://hub.docker.com/r/drakkarsoftware/octobot)安装 OctoBot。这里是我们的 [Docker 安装指南](https://www.octobot.cloud/en/guides/octobot-installation/install-octobot-with-docker-video?utm_source=github&utm_medium=dk&utm_campaign=regular_open_source_content&utm_content=readme_docker_installation)。

使用一行命令通过 Docker 安装：

```sh
docker run -itd --name OctoBot -p 80:5001 -v $(pwd)/user:/octobot/user -v $(pwd)/tentacles:/octobot/tentacles -v $(pwd)/logs:/octobot/logs drakkarsoftware/octobot:stable
```

### 使用 Python 安装 OctoBot

如果你想通过 Python 安装 OctoBot，例如为了修改代码或参与贡献，请参阅 [Python 安装指南](https://www.octobot.cloud/en/guides/octobot-installation/install-octobot-with-python-and-git?utm_source=github&utm_medium=dk&utm_campaign=regular_open_source_content&utm_content=readme_python_installation)。

你可能还想查看我们的[贡献指南](CONTRIBUTING.md)，快速了解 OctoBot 的架构。

### 最低硬件要求

- CPU：1 核 / 1GHz
- 内存：250 MB
- 磁盘：1 GB

## 如何为 OctoBot 做贡献

你想为 OctoBot 添加或改进功能吗？我们欢迎你提交 pull request！
请查看我们的[贡献指南](CONTRIBUTING.md)，了解相关准则。

### 通过本地 IDE 为 OctoBot 做贡献

我们推荐使用基于 [VSCode](https://code.visualstudio.com/) 的 IDE 为 OctoBot 做贡献，不过也可以使用 [PyCharm](https://www.jetbrains.com/pycharm/)。
由于 OctoBot 代码分布在不同的仓库中，我们编写了[开发者安装指南](https://www.octobot.cloud/en/guides/octobot-developers-environment/setup-your-environment?utm_source=github&utm_medium=dk&utm_campaign=regular_open_source_content&utm_content=setup_your_environment)，帮助你搭建 VSCode 或 PyCharm 环境。

### 通过 Ona（原 Gitpod）为 OctoBot 做贡献

使用 Ona，只需一键即可在**已经配置好、可以直接编写代码的开发环境**中修改代码并为 OctoBot 做贡献。

[![Contribute from Ona](https://gitpod.io/button/open-in-gitpod.svg)](https://gitpod.io/#https://github.com/Drakkar-Software/OctoBot)

## 免责声明

不要投入你无法承受损失的资金。使用本软件的风险由你自行承担。作者及所有关联方不对你的交易结果承担任何责任。

请始终先在模拟模式下运行交易机器人，并在了解其运作方式以及预期盈亏之前，不要投入真实资金。

欢迎阅读源代码，了解这个机器人的运作机制。

## 赞助商
<table>
<tr>
<td>特别感谢 <a href="https://www.chatwoot.com/" target="_blank">Chatwoot</a> 帮助我们为 OctoBot 用户提供支持。</td>
<td><a href="https://github.com/chatwoot/chatwoot" target="_blank"><p align="center"><img src="https://raw.githubusercontent.com/chatwoot/chatwoot/develop/public/brand-assets/logo.svg" width="500px"></p></a></td>
</tr>
<tr>
<td>衷心感谢 <a href="https://www.scaleway.com" target="_blank">Scaleway</a> 托管 OctoBot 的云服务。</td>
<td><a href="https://www.scaleway.com" target="_blank"><p align="center"><img src="https://raw.githubusercontent.com/Drakkar-Software/OctoBot/assets/scaleway.svg" width="500px"></p></a></td>
</tr>
<tr>
<td>非常感谢 <a href="https://sentry.io/welcome/" target="_blank">Sentry</a> 帮助我们识别并理解 OctoBot 中的错误，从而让它变得更好。</td>
<td><a href="https://sentry.io/welcome/" target="_blank"><p align="center"><img src="https://raw.githubusercontent.com/Drakkar-Software/OctoBot/assets/sentry.png" width="500px"></p></a></td>
</tr>
</table>

## 许可证

GNU 通用公共许可证第 3 版或更高版本。

查看 [GPL-3.0 LICENSE](https://github.com/Drakkar-Software/OctoBot/blob/master/LICENSE) 以了解完整文本。

## 为 OctoBot 助力

你喜欢我们正在用 OctoBot 构建的东西吗？请考虑给我们一个星标 ⭐，帮助提升项目的可见度！

并欢迎加入 OctoBot 的各个频道。

[![Telegram Chat](https://img.shields.io/badge/telegram-chat-green.svg?logo=telegram&label=Telegram)](https://t.me/octobot_trading)
[![Discord](https://img.shields.io/discord/530629985661222912.svg?logo=discord&label=Discord)](https://discord.com/invite/vHkcb8W)
[![Telegram News](https://img.shields.io/badge/telegram-news-blue.svg?logo=telegram&label=Telegram)](https://t.me/OctoBot_Project)
[![Twitter](https://img.shields.io/twitter/follow/DrakkarsOctobot.svg?label=twitter&style=social)](https://x.com/DrakkarsOctoBot)
[![YouTube](https://img.shields.io/youtube/channel/views/UC2YAaBeWY8y_Olqs79b_X8A?label=youtube&style=social)](https://www.youtube.com/@octobot1134)
