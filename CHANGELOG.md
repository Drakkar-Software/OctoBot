# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

*It is strongly advised to perform an update of your tentacles after updating OctoBot. (start.py tentacles --install --all)*

## [1.0.10] - 2024-04-19
### Fixed
- [Tentacles download] Fix a rare issue related to SSL certificates when downloading tentacles
- [DeathAndGoldenCrossEvaluator] Now only trigger right after crosses

## [1.0.9] - 2024-04-18
### Added
- [DigitalOcean] Added in marketplace and handle one click deployment
- [IndexTradingMode] Add the Index Trading Mode enabling to follow custom indexes
- [TradingViewTradingMode] Add quote and offsets from the current price
- [DCATradingMode] Add max holding ratio to cap the maximum exposure to an asset
- [Coinbase] Handle new API key format
### Updated
- [CCXT] Update to CCXT 4.2.95
### Fixed
- [ChainedOrders] Fix chained orders quantity computation when handling fees
- [ChainedOrders] Fix chained orders backtesting fill price to adapt to current candles
- [StopLoss] Now always recreate stop losses when restarting on real trading
- [Orders] Fixes rare order creation issues
- [Coinbase] Fix order fetch issues
- [BinanceUS] Fix permissions checks
- [Kucoin] Fix a rare order creation issue
- [MEXC] Fix order cancel issues
- [WebInterface] Add robots.txt to prevent search engine indexing

## [1.0.8] - 2024-02-14
### Added
- [TradingView] Support standalone stop loss and order tags
### Updated
- [Tentacles] Improved docs
- [WebInterface] Fix exchange credentials check when using futures accounts
- [Exchanges] Increase base maximum candles count and make it customizable via env variable
- [Links] octobot.cloud links
### Fixed
- [Exchanges] Remove log spam on invalid credentials
- [Cloud strategies] Fix cloud strategies download

## [1.0.7] - 2024-01-18
### Added
- [CoinEx] Support CoinEx
### Updated
- [WebInterface] Show profitability even on backtesting error, special thanks to Phodia for this improvement.
### Fixed
- [Exchanges] Websocket reconnection issues
- [DailyTradingMode] Fix sell amount when shorting in Target Profits mode

## [1.0.6] - 2024-01-09
### Added
- [TradingModes] Improved documentation and added links to full guides
- [InstantMAEvaluator] Add trigger threshold to avoid triggering at each price update
### Updated
- [CCXT] update to ccxt 4.2.10
- [ChatGPT] update to openai 1.7.0
- [DailyTradingMode] Enable futures position increase: add warning
### Fixed
- [DailyTradingMode] handle invalid MAX_CURRENCY_RATIO
- [TradingView] Fix SIGNAL=CANCEL docs typo
- [Exchanges] MEXC orders synchronization issues
- [Exchanges] HTX renamed Huobi into HTX
### Removed
- [Exchanges] Bittrex

## [1.0.5] - 2023-12-19
### Added
- [GPTEvaluator] Settings to limit used tokens and disable re-evaluation
### Updated
- [WebInterface] Improve home display on smaller screens
### Fixed
- [Telegram] Fixed multiple telegram commands issues
- [TradingViewSignalsTradingMode] Fixed buy orders quantity issues
- [WebInterface] Fixed logs issues
- [GoogleTrends] Fixed issues with crypto in multiple words
- [Exchanges] Rare candles fetch error

## [1.0.4] - 2023-12-10
### Added
- [Strategies] OctoBot cloud strategies can now be downloaded and used as regular OctoBot profiles 
- [DailyTradingMode] New "Enable futures position increase" parameter to avoid building on existing positions when trading futures
- [DCATradingMode] New "Health check" parameter to ensure that no funds remain unsold when using take profits
- [Exchanges] Bingx spot trading support
### Updated
- [CCXT] to version 4.1.82
- [WebInterface] Improve /profile loading speed
### Fixed
- [WebInterface] Fixed outdated currency list in /profile
- [Ngrok] Fixed configuration issue related to custom domains
- [Exchanges] Fixed stop loss and take profit issues
- [Orders & Trading Modes] Multiple rare errors

## [1.0.3] - 2023-10-30
### Fixed
- [Exchanges] real-time timeframe issue

## [1.0.2] - 2023-10-29
### Added
- [ChatGPT] Backtesting on supported configurations, full list on https://www.octobot.cloud/features/chatgpt-trading 
- [TradingView] Support cancel orders signal
- [GridTrading] Optimise initial portfolio command to split funds in an optimized way before starting the trading mode
- [DCATrading] Option not to cancel previously created orders
- [DCATrading] Option to always create initial orders at startup when in evaluators mode
- [Webhook] Support Ngrok custom domains
### Updated
- [ChatGPT] Default GPT Trading profile now uses the DCA trading mode 
- [TradingView] Revamped docs on https://www.octobot.cloud/en/guides/octobot-interfaces/tradingview
- [DCATrading] Improved error messages
- [WebInterface] Do not select duplicated profiles by default
- [DataCollector] Make errors clearer
- [Links] Migrate to https://www.octobot.cloud/
### Fixed
- [Kucoin] Issue regarding minimal order sizes 
- [Backtesting] Issue on orders that could being filled on the same candle they were created at 
- [DCATrading] Time based trigger issues
- [Grid & Staggered orders] Fix order creation when close to spread

## [1.0.1] - 2023-09-28
### Fixed
- [Community] OctoBot account connection timeout error 

## [1.0.0] - 2023-09-26
### Updated
- [Community] Migrate to the updated octobot.cloud. Full details on https://www.octobot.cloud/en/blog/introducing-the-new-octobot-cloud
- [Logs] Improve debug logs
### Fixed
- [GridTrading] Mirror order rebalance issues 
- [DCA & Dip Analyser] Sell order split issues 

## [0.4.54] - 2023-08-31
### Added
- [Kucoin] API Key permissions checks
- [OKX] API Key permissions checks
### Updated
- [GridTrading] Improve quantity computation using recent trades 
- [Orders] Display permission error when missing trading permissions in API Key 
- [TradingView] Quantity documentation 
- [Logging] Reduce httpx requests logs 
### Fixed
- [TradingView] Webhook error 
### Removed
- [Python] Removed support for 3.9. 3.10 is now the required Python version

## [0.4.53] - 2023-08-22
### Added
- [Smart DCA] Revamp the DCA trading mode to handle evaluators, scaled entries and exits
- [GridTrading] Support funds reallocation
- [TradingModes] s% and t% quantity types to trade % of portfolio traded assets
- [WebInterface] Notification history
- [WebInterface] Advanced tips
- [BingX] Trading simulator
### Updated
- [WebInterface] Now check trading permission when adding exchange keys
### Fixed
- [WebInterface] Orders display issues
- [WebInterface] Currencies import issues
- [Binance] Fix futures API
- [Kucoin] Fix API and websocket
- [Orders] Chained orders restore
- [Backtesting] Fix fees computation on very small trades
- [Storage] Fix corrupted file issues

## [0.4.52] - 2023-07-05
### Added
- [Exchanges] Support Binance futures
- [Exchanges] Crypto.com, Kucoin and MEXC as partner exchanges
- [Orders] Stop loss full support on futures exchanges
### Updated
- [Futures] Improved futures trading related error messages
- [WebInterface] improved configuration tips
### Fixed
- [Futures] Futures trading positions synchronisation issues
- [Orders] Trading signals related issues
- [Evaluators] Configuration related time frames issues

## [0.4.51] - 2023-06-09
### Updated
- [WebInterface] improve market status
- [WebInterface] add configuration tips
### Fixed
- [Orders] orders synchronisation issues
- [Display] tentacles configuration display
- [Display] time frame related display

## [0.4.50] - 2023-05-06
### Added
- [DailyTradingMode] Target profit mode
- [ArbitrageTradingMode] Allow to disable short or long arbitrages 
- [WebInterface] Backtesting trades table
- [WebInterface] Open orders display on charts
- [WebInterface] Time frame selector on charts
- [Python] Support for 3.9 and 3.10. 3.10 is now the recommended version for OctoBot
### Updated
- Removed Cython
- Improved overall speed thanks to python 3.10 optimizations
- [Trading Modes] allow order quantity in quote amount
- [Coinbase] Fix trading simulator issues
- [Bybit] Made time sync errors much less frequent
- [WebInterface] Improved spot and futures symbols selector
- [Websockets] Improved global stability
### Fixed
- [Websockets] KeyError
- [Portfolio] Attribute error

## [0.4.49] - 2023-04-23
### Updated
- [CCXT] Update to ccxt 3.0.74
- [Websockets] Reduce unordered candles warnings
### Fixed
- [Coinbase] Trading simulator mode and data collector 
- [Binance] Order creation issues 
- [Bybit] Order creation issues 
- [Telegram] set risk command
- [TradingView] remove warning on empty line

## [0.4.48] - 2023-04-18
### Added
- [WebInterface] Add filters to PNL tab.
- [TradingViewTradingMode] Handle on position open take profit and stop loss.
- [DCATradingMode] Add price and order type config.
- [Hollaex] Possibility to disable websocket in Hollaex exchanges.
### Updated
- [Telegram] Improve portfolio display. Special thanks to Tim !
- [Websockets] Handle partially supported time frames
- [Trading Modes] Improve impossible error creation messages
- [WebInterface] Mobile charts display.
### Fixed
- [Websockets] logs spam
- [Databases] Handle incorrect db files format
- [PNL] invalid trades PNL related issues
- [WebInterface] Portfolio display on smaller screens.

## [0.4.47] - 2023-04-02
### Added
- [Evaluators] ChatGPT evaluator
- [Exchanges] Restore Coinbase support
- [Profiles] Risk and complexity
### Updated
- [WebInterface] Improve candle charts display. Special thanks to Tim !
- [Services] Telegram, flask, reddit and other connectors versions
### Fixed
- [OKX] create order issues
- [WebInterface] Fix unexpected client disconnections
- [PNL] invalid trades PNL related issues


## [0.4.46] - 2023-03-24
### Updated
- [Telegram] portfolio display
### Fixed
- [Orders] saved orders loading issue 

## [0.4.45] - 2023-03-23
### Added
- [Trades] value in reference market
- [PNL] detailed fees
### Updated
- [Telegram] increased timeout delay
- [Telegram] bot portfolio holdings in reference market (thank you, @Max)
### Fixed
- [Orders] initially fetched orders issues 

## [0.4.44] - 2023-03-20
### Fixed
- [Community] portfolio update issues
- [OrderStorage] typing issues

## [0.4.43] - 2023-03-19
### Fixed
- [Profiles] profiles update error management
- [Portfolio] origin portfolio valuation issues

## [0.4.42] - 2023-03-18
### Added
- Crypto.com spot trading support
- Bybit spot trading support
- Order storage: in real trading, stop loss, tags, groups and chained orders are saved between sessions
### Updated
- Improve portfolio valuation
- Improve PNL display
- Telegram library to async version for better performances
### Fixed
- PNL on real trading
- Price limit computation in order creation

## [0.4.41] - 2023-03-03
### Added
- Trades PNL history for supported trading mode
- Support for OKX futures
- Support for market orders in Dip Analyser
### Updated
- Revamped the trading tab of the web interface
- Reduced required RAM for long-lasting instances
- Optimized disc read/write operations when browsing the web interface
### Fixed
- Orders synchronization and cancel issues
- Future trading positions synchronization issues
- Order creation issues related to order minimum and maximum amounts

## [0.4.40] - 2023-02-17
### Fixed
- Historical portfolio reset 

## [0.4.39] - 2023-02-14
### Fixed
- Historical portfolio and live metadata issues 

## [0.4.38] - 2023-02-12
### Added
- Trades and portfolio history through OctoBot sessions
- Grid trading default configuration for any pair
### Fixed
- Kucoin rate limit issues
- Portfolio synchronization issues
- Daily trading: only place stop loss when reducing the position size 

## [0.4.37] - 2023-02-06
### Added
- Configurations: add limits
### Fixed
- Futures trading: portfolio and cancel order issues

## [0.4.36] - 2023-01-29
### Added
- Automations: initialize automations
- Dip Analayser: add stop loss option
### Fixed
- Websockets: reconnect issues

## [0.4.35] - 2023-01-19
### Added
- WebInterface: OctoBot cloud register form
### Updated
- Websockets: ccxt version
### Fixed
- Websockets: kline error

## [0.4.34] - 2023-01-14
### Added
- Websockets: support for many more feeds and exchanges
### Updated
- Websockets: migrate form cryptofeed to ccxt pro
- Web interface display speed
- Coins logo display
- Mobile display

## [0.4.33] - 2023-01-02
### Added
- Profile selector
- Login session persistence
### Updated
- Tutorials
- Mobile display

## [0.4.32] - 2022-12-29
### Fixed
- MQTT reconnection issues

## [0.4.31] - 2022-12-28
### Fixed
- profile duplicate download
- octobot trading typing issue

## [0.4.30] - 2022-12-27
### Fixed
- profile download error

## [0.4.29] - 2022-12-26
### Fixed
- pip install on Unix
- crash on missing profile tentacles setup configuration

## [0.4.28] - 2022-12-25
### Added
- Keywords tentacles
- OctoBot-Pro requirements
- Clock Synchronizer disable env var: ENABLE_CLOCK_SYNCH=False
### Fixed
- Multi exchange dashboard issues

## [0.4.27] - 2022-12-13
### Fixed
- cancel order issue
- signal reconnect issues

## [0.4.26] - 2022-12-12
### Fixed
- stats graphql request

## [0.4.25] - 2022-12-12
### Fixed
- Initial tentacles installation

## [0.4.24] - 2022-12-10
### Fixed
- System resources watcher on linux
- Order quantity computation when from configuration
- Multiple exchanges issues
### Updated
- CCXT version

## [0.4.23] - 2022-11-24
### Fixed
- System resources watcher on linux

## [0.4.22] - 2022-11-23
### Added
- System resources watcher

## [0.4.21] - 2022-11-23
### Added
- Order quantity in Trading modes config
- Copy trading last signal time
### Updated
- Improved profile page load time
### Fixed
- Errors on clock synchronizer
- Exchange deletion spreading on profiles

## [0.4.20] - 2022-11-13
### Updated
- Exceptions handling
### Fixed
- Crash on stop loss

## [0.4.19] - 2022-11-01
### Updated
- Exchange configuration auth details

## [0.4.18] - 2022-11-01
### Fixed
- Do not use beta env by default

## [0.4.17] - 2022-11-01
### Fixed
- Copy trading order sizing

## [0.4.16] - 2022-10-23
### Updated
- Copy trading configuration
- CCXT configuration via environment variables
### Fixed
- Dip Analyser configuration 
- Bitget & Coinex order handling

## [0.4.15] - 2022-10-23
### Fixed
- Copy trading
- Strategy optimizer stop

## [0.4.14] - 2022-10-21
### Fixed
- Crash on historical portfolio computation
### Added
- Close position from web interface
- Signals on user cancel order

## [0.4.13] - 2022-10-15
### Fixed
- Spot trading fees computation

## [0.4.12] - 2022-10-15
### Fixed
- Copy trading

## [0.4.11] - 2022-10-14
### Added
- User inputs system
- Phemex exchange
- Run storage
### Updated
- Configuration for each tentacle
- Community bot system instead of devices

## [0.4.10] - 2022-09-13
### Updated
- Beta tentacles
### Fixed
- Kucoin rate limit issues
- Futures trading issues
- Tentacles versioning in profile import

## [0.4.9] - 2022-09-07
### Updated
- Beta tentacles
### Fixed
- Profile export

## [0.4.8] - 2022-09-04
### Fixed
- Device creation

## [0.4.7] - 2022-09-03
### Updated
- [Astrolab] Improvements and fixes

## [0.4.6] - 2022-08-23
### Added
- [Trading] Futures trading
- [Exchange] Bitget
- [Trading] Copy trading
- [Beta] Beta environment
### Updated
- [Community] Migrate to updated community website
### Fixed
- [Websockets] Multiple issues related to candles refresh

## [0.4.5] - 2022-06-12
### Fixed
- [Trading modes] Stop loss are not created after instantly filled limit orders
- [Exchanges] Multiple backtesting issues
- [WebInterface] Portfolio value sorting

## [0.4.4] - 2022-06-01
### Added
- [Exchanges] Future trading engine
- [TradingModes] 
  - Scripted trading mode bases
  - Copy trader bases

### Fixed
- [WebInterface] Security issue

## [0.4.3] - 2021-11-23
### Added
- [Trading Modes] Add buy volume parameters

### Fixed
- [Orders] Decimal related typing issues

## [0.4.2] - 2021-11-21
### Added
- [WebInterface]
    - Add filter in evaluation matrix
    - Cache and compression
    - Import / Export currencies list
    - Option to change reference market on configured pairs
    - Info message on DataCollector and Backtesting
    - Sort currencies by marketcap
- [Evaluators] SuperTrend

### Updated
- [Profile][Art's scalp] Update telegram channel name

### Fixed
- [WebInterface]
    - Issue with dropdown select on firefox
    - decimal error on json

## [0.4.1] - 2021-10-15
### Added
- [Interface][Telegram]
    - Restart OctoBot
- [Interface][Web] 
    - DataCollector stop button
    - Backtesting Date selection
- [Evaluator] Death and golden cross
- [Exchanges][Partners] Ascendex

### Updated
- [Websockets] Cryptofeed from < 2.0.0 to 2.0.1

### Fixed
- Websockets multiple issues

### Removed
- [Infra] Nexus

## [0.4.0-beta17] - 2021-09-15
### Fixed
- Portfolio holdings market valuation issues

## [0.4.0-beta16] - 2021-09-13
### Fixed
- Portfolio display issues
- Dip analyzer sell orders issues

## [0.4.0-beta15] - 2021-09-09
### Fixed
- Real time evaluators related backtesting issues
- Multiple decimal.Decimal related issues
- Issues with orders parsing

## [0.4.0-beta14] - 2021-09-09
### Added
- [New tentacle] 
   - Art's IA signal evaluator
- [Web Interface] 
   - Progress in historical data collector
- [Websockets] Huobi & GateIO websockets are now available
### Fixed
- [Trader] 
   - Fixed multiple rounding issues
   - Fixed multiple NegativePortfolio error issues
   - Removed the 2000 limit of orders
- [Websockets] 
   - Optimize feed subscription
- [Evaluators] 
   - Fixed non traded pairs unwanted evaluations when using websockets
- 
## [0.4.0-beta13] - 2021-08-12
### Added
- [Community website] 
   - Create and link your account in OctoBot
   - Let us know that you have made a donation to unlock access to websockets without any exchange requirement
- [New docs websites] 
   - New design for docs.octobot.online
   - Developer.docs.octobot.online
   - Exchanges.docs.octobot.online
- [Data collector] (@valouvaliavlo) : can now collect multiple symbols datafiles 
- [Websockets] FTX & OKEx websockets are now available
### Fixed
- [Backtesting] Multiple backtesting bugs related to real time evaluators
- [TA] Technical evaluators can now use the real time time frame

## [0.4.0-beta12] - 2021-07-12
### Fixed
- [WebInterface] Exchanges & Webhook configuration

## [0.4.0-beta11] - 2021-07-11
### Note
Thanks to @valouvaliavlo for his work in this version !

### Added
- [Backtesting] (@valouvaliavlo) : Collect historical data based on a date range
- [Webhooks] (@valouvaliavlo) : Webhooks can now be setup without Ngrok
- [Exchanges] : Support OctoBot by using Binance without referral
- [Binance websocket] : Rate limit related bans shouldn't happen now (only available for accounts without referral)

### Updated
- [Documentation] Update webhook documentation
- [Configuration] Improved exchanges accounts configuration
- [Future trading] Now close to be supported on real trading

## [0.4.0-beta10] - 2021-06-05
### Fixed
- [Websockets] Properly handle websockets errors
- [Loggers] Properly map default logging arguments

## [0.4.0-beta9] - 2021-04-31
### Added
- [WebInterface] Advanced OctoBot statistics
- [Exchanges] Beta websocket connexions
- [Profiles] Default profiles for each trading mode
- [Profiles] Read-only profiles

### Fixed
- Stop command

## [0.4.0-beta8] - 2021-04-06
### Added
- [WebInterface] Starting tutorial
- [WebInterface] Trader switch button
- [WebInterface] Update OctoBot

### Fixed
- [WebInterface] Multiple fixes and improvements
- [Trading] Fix pair wildcard config
- [Exchanges] Fix hitbtc
- [Trading] Rounding problems during order creation 

## [0.4.0-beta7] - 2021-03-26
### Added
- GridOrders config check

### Fixed
- Symbol wildcard configuration
- Docker raspberry armv7 image (thanks to @gabriel-milan)

## [0.4.0-beta6] - 2021-03-22
### Updated
- websites URLs

## [0.4.0-beta5] - 2021-03-21
### Added
- Grid orders trading modes
- Multiple exchanges support
- Web interface logs export
- User commands to interact with trading modes
### Updated
- Web interface datafile date sorting
### Fixed
- Exchange issues (binance and kraken)

## [0.4.0-beta4] - 2021-02-16
### Updated
- Web interface
### Fixed
- Exchange sync issues

## [0.4.0-beta3] - 2021-02-08
### Added
- Configuration profiles
### Updated
- Web interface
### Fixed
- Multiple exchange related issues

## [0.4.0-beta2] - 2020-12-10
### Updated
- Web interface

## [0.4.0-beta1] - 2020-12-08
### Added
- Exception logs

## [0.4.0-alpha27] - 2020-12-06
### Fixed
- Restart issues 

## [0.4.0-alpha26] - 2020-11-26
### Added
- Docker healthcheck 

## [0.4.0-alpha25] - 2020-11-23
### Added
- Community authenticator
### Updated
- Cleanup configuration file
### Fixed
- Various config related starting issues

## [0.4.0-alpha24] - 2020-10-23
### Updated
- Python 3.8 support

## [0.4.0-alpha23] - 2020-09-02
### Updated
- [Real trading] Update order status management

## [0.4.0-alpha22] - 2020-08-23
### Added
- [Real trading] Fix order handling issue

## [0.4.0-alpha21] - 2020-08-23
### Added
- [Real trading] Fix order synchronization issues

## [0.4.0-alpha20] - 2020-08-03
### Added
- [Real trading] Real trading beta phase

## [0.4.0-alpha19] - 2020-06-15
### Added
- [Trading modes] Arbitrage trading mode
- [Orders] Trailing stop orders
- [Web interface] Web interface login
### Updated
- [Orders] Optimized order update system
- [Web interface] Interface libraries
### Fixed
- [Web Interface] OctoBot startup issues

## [0.4.0-alpha18] - 2020-06-01
### Fixed
- [Backtesting] Backtesting data files lock related error

## [0.4.0-alpha17] - 2020-05-26
### Fixed
- [Trades] Trades displayed with a 0 price

## [0.4.0-alpha16] - 2020-05-22
### Updated
- [OctoBotPackage] Move OctoBot related resources into the octobot folder
- [OctoBot services] Initialization
### Fixed
- [Trading] Various bugs
- [StrategyOptimizer] Various bugs

## [0.4.0-alpha15] - 2020-05-20
### Fixed
- [Services] use services channel init

## [0.4.0-alpha14] - 2020-05-19
### Fixed
- [StrategyOptimizer] typing issue

## [0.4.0-alpha13] - 2020-05-18
### Fixed
- [Exchanges] issues in OctoBot exchange data parsing

## [0.4.0-alpha12] - 2020-05-17
### Fixed
- [Exchanges] issues in OctoBot exchange data parsing and exchange disabling

## [0.4.0-alpha11] - 2020-05-16
### Added
- [Channel] OctoBot channel
- [Backtesting] Multiple backtesting file support

### Fixed
- Multiple issues in OctoBot required packages

## [0.4.0-alpha10] - 2020-05-02
### Added
- [Backtesting] Synchronized channel support

### Updated
- [Tests] strategy and TA framework
- [Tests] trading mode framework migration
- [Interfaces & Notifications] Migration follow up
- [Backtesting] Only one instance is created

### Fixed
- [Tests] Stress test timeout 
- [Startup] Fix api calls 

Changelog for 0.3.9-beta
====================
*Released date : April 24 2020*

# Bug fixes :
    - Fixed web interface crypto-currencies selector
    - Fixed Tentacles-manager dependancy helper message

## [0.4.0-alpha9] - 2020-04-12
### Updated
- [Start] Import ConfigEvaluatorError from OctoBot-Commons

### Fixed
- [Stop] recursion error
-  octobot_api cython headers

## [0.4.0-alpha8] - 2020-04-10
### Added
- Create config when missing user folder
- bot_id generation

### Updated
- Python files organisation refactor
- Metrics to community
- Script helper

## [0.4.0-alpha7] - 2020-04-08
### Removed
- Tentacles cythonization

## [0.4.0-alpha6] - 2020-04-07
### Fixed
- Wildcard imports

## [0.4.0-alpha5] - 2020-04-05
### Updated
**Requirements**
- Commons version to 1.3.5
- Evaluators version to 1.4.3
- Trading version to 1.4.20
- Interfaces version to 1.0.1
- Notifications version to 1.0.1
- cython to 0.29.16

Changelog for 0.3.8-beta
====================
*Released date : December 28 2019*

# Concerned issues / pull request:
    #978 can now call start.py from any directory
    #991 add new exchange order types support

# Bug fixes :
    - Fixed ccxt deprecated methods
    - Fixed binance websocket regression
    
# New features :
    - New order types support

## [0.4.0-alpha4] - 2019-12-22
### Updated
**Requirements**
- Commons version to 1.2.0
- Evaluators version to 1.3.1
- Trading version to 1.4.11
- jsonschema to 3.1.1

## [0.4.0-alpha3] - 2019-11-10
### Fixed
- Appveyor CI
- Travis pypi delivery

### Updated
**Requirements**
- Cython version to 0.29.14
- Commons version to 1.1.49
- Evaluators version to 1.2.6
- Trading version to 1.4.5

## [0.4.0-alpha2] - 2019-10-31
### Fixed
- Commands class imports
- start.py calls

## [0.4.0] - 2019-10-19
### Added
- octobot main package to initialize all OctoBot packages

### Moved
- Evaluator modules related to OctoBot-Evaluators
- Trading modules related to OctoBot-Trading
- Services modules related to OctoBot-Services
- Common modules related to OctoBot-Commons
- Backtesting modules related to OctoBot-Backtesting
- Websocket modules related to OctoBot-Websockets
- Service modules related to OctoBot-Services
- Interface modules related to OctoBot-Interface
- Notification modules related to OctoBot-Notifications

Changelog for 0.3.7-beta
====================
*Released date : August 31 2019*

# Warning: config.json file has been moved to the user folder

# Concerned issues / pull request:
    #948 [Trading] Add 6h timeframe
    #949 [Config] Migrate config file to user folder enhancement
    #952 [Trader] Fix kraken orders
    #953 [Docker] Improve dockerfile
    #955 [Backtesting] Improve recent trades generation
    #960 [Backtesting] Use the last candle for profitability computation
    #962 [Portfolio] Missing stablecoins in traded portfolio
    #964 [Backtesting][DipAnalyser] try to create sell order without enough funds
    #968 [Web interface] Handle errors 
    #969 [Web interface] Add refresh real trader button

# Bug fixes :
    - Fixed errors when creating orders on Kraken exchange
    - Fixed innacuracies in backtesting
    - Now correctly takes every currency into consideration when computing profitability and holdings
    - Fixed backtesting exchange simulator inconsistencies
    
# New features :
    - Added refresh real trader button similar to /refresh_real_trader telegram command in web interface
    - Added error handling pages in web interface 
    - Can now handle 6 hours timeframes
    - Optimized Dockerfile

Changelog for 0.3.6-beta
====================
*Released date : July 15 2019*

# Concerned issues / pull request:
    #922 [Notifications] Uncaught exception when error on notifications publish bug
    #937 [Exchanges] API token fail when api-password is provided but not necessary bug
    #940 [Bug][High] Fix updater candle time synchronization
    #927 [Docker] expose web interface for inter-container communications
    #900 Fix Config checker failed when using wildcard on pairs
    #931 Improved navbar UI
    #944 Added switch design for tentacle config checkboxes

# Bug fixes :
    - Fixed exchange API token error during first installation
    - Fixed timeframes update rate to fit timeframes time
    - Fixed uncaught notification exception
    - Fixed wildcard configuration validation error
    
# New features :
    - Added configuration for Daily and Signal trading modes
    - Improved web interface UI 

Changelog for 0.3.5-beta
====================
*Released date : May 27 2019*

# Concerned issues / pull request:
    #894 [GlobalUpdater] does not update timeframes normally when notified by RT
    #896 [Web interface] display of very small numbers digits
    #899 [Simulator] freeze on staggered orders simulation
    #901 [Bug] Candle lost with websocket
    #904 [asyncio] optimize async handling
    #908 [Time frame updater] desync between symbols update time

# Bug fixes :
    - Fixed digit display in web interface configuration
    - Fixed timeframe refresh timings

Changelog for 0.3.4-beta
====================
*Released date : May 12 2019*

# Concerned issues / pull request:
    #191 [Kucoin] Test OctoBot on different exchanges
    #696 [Tentacles config] add tentacle configuration edition on web interface
    #782 [Notifiers] Removed unused notification systems
    #792 [Web interface][Configuration] force display of parameters that are not in config.json
    #804 [Web interface] Cancel orders according to table filter
    #813 [Docker] Add raspberry docker image
    #810 [WebInterface] add cancel orders progress bar 
    #811 [Telegram interface] Start telegram interface more easily
    #817 [WebInterface] Navbar current selection UX improvement
    #818 [Exchanges] Handle api passwords
    #820 [Exchanges] handle order creation when result order is not complete
    #821 [Exchange traded pairs] no message when unavailable traded pair
    #823 [Coinbase Pro] Test OctoBot on different exchanges
    #824 [RealTrader] impossible to start OctoBot with error in real trader login
    #826 [Web interface] price graph update
    #830 [0.3.4][Exchange][REST] Officialize Kucoin and CoinBasePro support
    #832 [TradingModes] can't start when error in trading mode init 
    #834 [StrategyTestFramework] handle different reference market
    #837 [EvaluatorCreator] crash on evaluator __init__ exception
    #839 [WebInterface] refresh backtesting interface
    #847 [WebInterface] add terms of service
    #854 [TentacleManager] ModuleNotFoundError: No module named 'tentacles_manager'
    #865 [Exchange config] simplify exchange token config
    #869 [Factorize] new "Tentacle" abstract class
    #870 [Traders] do not athorize simulator and real trader during the same execution
    #873 [WebInterface] do not delete symbol config when no exchange
    #875 Email Contact is Invalid
    #876 [TentacleManager]No module named 'evaluator.Util.advanced_manager'
    #887 [Metrics] add exec environment type to metrics (code, binary, etc)
    #889 fixed usdX bug in ws
    

# New features :
    - Added tentacles configuration interface: 
        - Generated using on json schema of tentacle config file
        - Allowing to backtest strategies/evaluators directly from web interface
    - Added Kucoin and CoinbasePro support
    - Improved web interface UI and UX
    - Telegram insterface now automatically started when setup
    - Can now copy/paste exchange tokens in config.json: OctoBot will later encrypt those
    - Can't have simultaneously a real trader and trader simulator in order to avoid side effects
    - RaspberryPie OctoBot docker image
    - Now handle exchanges with API passwords
    - Added disclaimer
    

# Bug fixes :
    - Fixed several bugs related to OctoBot start with config error: now start and display errors in interface logs
    - Fixed crashes on error in Tentacles: now display error message instead
    - Fixed price graph update in web inteface
    - Fixed a profitability bug in strategy tests suite
    - Fixed refresh bugs with backtesting web interface
    - Fixed tentacle manager import error
    - Fixed traded pairs config deletion when no available exchange
    - Fixed email contact
    - Fixed bug with USD stable coins on websocket
    

Changelog for 0.3.3-beta
====================
*Released date : April 18 2019*

# Concerned issues :
    #425 [Telemetry] Create telemetry deamon
    #731 [Trader] Allow to start from the previous execution last move
    #734 [Order] order_type is not consistent
    #740 [RunInAsyncMainLoop] problem with exchange commands
    #741 [WebInterface] add possibility to cancel orders
    #747 [Backtesting] prepare for multiple data formats
    #749 [Backtesting] impossible to display candles on specific timeframe from web interface
    #750 [OrderCreator] error when computing order price
    #751 [Backtesting] problem when saving config from web interface on backtesting
    #752 [WebInterface] candles display bug
    #756 [OrderManager] call_order_update_callback not called when exception in _update_order_status
    #785 [Metrics] community metrics display
    #792 [Web interface][Configuration] force display of parameters that are not in config.json

# New features :
    - Cancel orders from web interface
    - Community metrics though optionnal and anonymous telemetry
    - Added bot trader state save and recovery
    - Added telegram commands
    

# Bug fixes :
    - Fixed several bugs related to traders
    - Fixed an exchange timeout bug
    - Fixed web interface bugs
    - Fixed order creator bugs

Changelog for 0.3.2-beta
====================
*Released date : March 10 2019*

# Concerned issues :
    #635 [Interface Bot] New commands for telegram bot, etc
    #647 [Web interface] can't add more than one currency at once bug
    #655 [Configuration interface] do not display in dev evaluators
    #661 HybridTradingMode.json NOT FOUND
    #663 [Telegram evaluator] add telegram dispatcher architecture
    #664 [SignalEvaluator] create abstract signal evaluator
    #665 [Evaluators] add a method to know the type of evaluation carried by the evaluator
    #667 [Web interface] add option to apply strategy default config when activating a strategy
    #671 [Telegram Interface] Improve readability using message formatting (markdown ?)
    #678 [Logs management] do not log errors twice
    #681 [Web Interface] improve checkboxes design
    #684 [Telegram Interface] telegram.error.BadRequest: Message is too long
    #686 [Real Trader] find a way to handle market order fill prices when using ws
    #687 [Web Interface] Improve candles & trades graph readability
    #691 [OrderManager] KeyError "Error when updating orders"
    #694 [TentacleEvolution] Prepare for staggered orders strategy
    #697 [StopLoss] {"code":-2010,"msg":"Account has insufficient balance for requested action."} when triggering stop loss
    #700 [Web interface] Filter ccxt exchanges: do not display unusable exchanges
    #702 [Portfolio display] Portfolio total value not always updated in web and telegram interface
    #705 [Interfaces] add default messages when no available data
    #711 [Bug] Trade creator: does not systematically respect order rules
    #713 [Telegram Interface] /fees command is not responding
    #715 [Order Manager] problem with stop losses on real trades
    #717 [Real Trader] order fill notification not received (web socket)

# New features :
    - New Strategy: staggered orders
    - Improved web and telegram interfaces user experience
    - Added documentation and default settings for evaluators on web interface
    - Added telegram commands
    - Can now handle telegram signals
    

# Bug fixes :
    - Fixed several bugs related to orders management and synchronization
    - Fixed a rare portfolio synchronization bug
    - The telegram interface now splits long messages
    - Fixed web interface bugs
    - Fixed telegram /fees command

Changelog for 0.3.1-beta
====================
*Released date : January 29 2019*

**Warning** :
- Version 0.3.0 required to reinstall all default tentacles (start.py -p reset_tentacles && start.py -p install all)

# Concerned issues :
    #624 fixed offline announcements
    #629 fixed real trader multiple stop orders
    #631 fixed dusts management round system

# New features :
    - Requirement cleanup    

# Bug fixes :
    - Fix pip delivery
    - Fix real trader stop orders
    - Fix dusts management
    - Minor fixes on portfolio

Changelog for 0.3.0-beta
====================
*Released date : January 27 2019*

**Warning** :
- Now requires Python 3.7 
- Requires to reinstall all default tentacles (start.py -p reset_tentacles && start.py -p install all)
- If you use the telegram interface, you can add your telegram username in telegram config whitelist

# Concerned issues :
    #481 [Exchange] Use async exchange call provided by ccxt
    #495 [Global] refactor multi-threaded architecture into async architecture
    #502 [Setup] Update and improve setup.py
    #505 [Web interface] add full offline support for the whole bot and interfaces services & interfaces
    #506 [Profitability] add no trades hypothetical profitability using initial portfolio
    #509 [Matrix] Migrate to dataclass
    #517 [Bug][Strategy Optimizer] can't change strategy once selected the 1st one in web interface 
    #526 [Docker] Migrate to python:3.7.2-slim-stretch
    #532 [PIP] Create pip OctoBot package
    #533 [Security] Add an optional authentification system for external interfaces 
    #534 [Data collector] migrate standalone datacollector into async arch
    #536 [Installation doc] update raspberry install script
    #538 [Trader] MIN_NOTIONAL error when creating order
    #539 [Web Interface] separate required config and default creation fields in services
    #540 [Web Interface] add help info on configuration fields
    #543 [Async] Appveyor warnings are raised
    #549 launcher_windows.exe virus total
    #550 [Release] Add release checksum
    #553 [Release CI] Create macos binary at release
    #561 [Notifier] Add notifier providers to web interface
    #567 [Notifier] add notifier support for web interface
    #571 [User experience] add documentation and help messages regarding configuration and interfaces
    #572 [Donation] add donation systems
    #576 [Binary] Can't restart bot with binary from interface
    #578 [Bug][Async] Can't stop OctoBot properly
    #585 [RestExchange] reccurent exchange side error handling
    #591 [User feedback] add feedback systems
    #592 start on vps?
    #593 [Web&Bot Interface] Add OctoBot version
    #594 [Tentacles] handle incompatible tentacles
    #595 [GUI] Remove pre-launcher
    #596 [Web interface] handle recurent "can't find matching symbol" warnings
    #600 [Public Messages] add public messages handling
    #603 [Web interface] manage candles from index page when bot just started and data are not available
    #606 [Web interface] fix firefox link button display

# New features :
    - Full asyncio architecture for the core engine of the bot
    - Replaced TK launcher window by web launcher
    - Now check tentacles versions and validity at initialization
    - Added initial portfolio profitability
    - Can now add a user whitelist on telegram interface
    - Improved web interface user experience
    - Added several help systems on web interface
    - Added current OctoBot version on web and telegram interface
    - Can now display global announcements
    - Added donation addresses
    - Added several new notification systems
    - Can now properly stop and restart OctoBot from web interface
    - Can now properly stop OctoBot using CTRL+C
    - Optimized execution using data classes
    - Added offline mode with limited options
    - Tested on MacOS X
    - Octobot available on PIP
    - Reduced Docker image size
    - Added checksum on binary versions
    
# Bug fixes :
    - Can now change selected strategy in optimizer multiple calls
    - Can now change restart OctoBot from the web interface
    - Won't spam can't find matching symbol warning anymore
    - Fixed Firefox display bugs on web interface
    - Now handles errors occuring on rest exchange api side

Changelog for 0.2.4-beta
====================
*Released date : December 30 2018*

# Concerned issues :
    #433 [Style] Fix code errors 
    #446 added real trader resync on InsufficientFunds 
    #448 added refresh_real_trader telegram command  
    #450 fixed services startup config check 
    #456 Implement docker configuration persistence 
    #457 improved data collector and market view select UX
    #461 fixed generic card bug with space containing names 
    #474 Implement exchange market status fixer 
    #475 removed trailing new line 
    #477 added stack trace print on all relevant exceptions
    #483 fixed multiple addition in classes list
    #486 Refactor Trade class 
    
# New features :
    - Docker image ready
    - Forced refresh telegram command
    - Exchange market status fixer
    - Update python version to python 3.7.2
    
# Bug fixes :
    - Fixed trading marge colors 
    - Fixed binance api new version
    - Fixed config load erasing bug
    - Web minor fixes

Changelog for 0.2.3-beta
====================
*Released date : November 17 2018*

# Concerned issues :
    #359 [Web Interface][User experience] Improved time frame selectors ordering
    #421 [Web Interface] Added graphic representation of portfolio holdings
    
# New features :
    - Graphic portfolio holdings
    
# Bug fixes :
    - Fixed errors in profitability computation
    - Fixed dockerfile
    - Do not display interfaces logs when disabled (ex: telegram)
    
Changelog for 0.2.2-beta
====================
*Released date : October 04 2018*

# Concerned issues :
    #359 [Web Interface][Configuration] Improve user interface
    #406 [backtesting] add a startup argument to pause the bot at the end of backtesting in order to analyse results
    #408 [New Trading strategy] implement a new trading strategy using real time evaluators and TA
    #410 [Websocket] error when opening a websocket with translated symbols
    #413 [Web interface] add price visualisation for each symbol 
    #414 [Web interface] Dashboard customization
    #417 [Evaluator configuration] inform user when missing required evaluators
    
# New features :
    - Dashboard customization
    
# Bug fixes :
    - Fix error when opening a websocket with translated symbols

Changelog for 0.2.1-beta
====================
*Released date : September 25 2018*

# Concerned issues :
    #359 [Web Interface][Configuration] Improve user interface
    #399 Error when starting backtesting: 'backtesting'
    #401  [GUI] refactor local gui interface packages
    
# New features :
    - Launcher improvements
    
# Bug fixes :
    - Fix default config backtesting

Changelog for 0.2.0-beta
====================
*Released date : September 5 2018*

**Major version: OctoBot Open beta**


# Concerned issues :
    #288 [Binance Websocket] Handle exchange maintenance and websocket reconnection
    #291 [RestExchange] fill return data with default values if missing values and items
    #344 [Notifications] handle market orders price
    #353 [Exchange Simulator] Add fees 
    #359 [Web Interface][Configuration] Improve user interface
    #376 [Tentacles] Trading_config.json
    #377 [Web interface] Advanced evaluator config (TA, RT, Social)
    #378 [Web interface] Display errors and warning (icons topmenu)
    #379 [Web interface] Trading mode and strategy config page
    #385 [Web Interface] add bot profitabily
    #389 [Web Interface] add market status page
    #393 [Web Interface] add info on trading modes and evaluators

# New features :
    - First version of the full web interface
    - Binary versions of OctoBot and its launcher are now available
    - Fee simulation on simulation mode
    - Web sockets auto reconnexion on exchange maintenance
    - Improved first use default setup

# Bug fixes :
    - Market order without price notification

Changelog for 0.1.7-beta
====================
*Released date : August 15 2018*

**Warning** :
- Trading key changed : [See wiki trading page](https://github.com/Drakkar-Software/OctoBot/wiki/Trading)


# Concerned issues :
    #218 [Bin] Thinking about octobot binary 
    #288 [Binance Websocket] Handle exchange maintenance and websocket reconnection
    #305 [Refactor] refactor overall code 
    #321 [Web Interface] add backtesting section 
    #342 [Web Interface] Handle save and reset features in font end
    #343 [Web Interface] Handle removal of card elements
    #347 [Web Interface] Add strategy optimizer in backtesting
    #355 [Bug] StopLossOrders set negative portfolio when backtesting 
    #356 [Web Interface] Octobot doesn't restart onclick 
    #359 [Web Interface][Configuration] Improve user interface 
    #360 [Web Interface] Add data recording section
    #368 [Experiment][Web interface] without dash 
    #369 [Configuration] Split trading settings into trading section instead of trader
    #373 [Interface] Create launcher 
    #374 [Configuration] Remove websocket from configuration and use if by default when available 

# New features :
    - TK app
    - Installer App
    - Web interface : backtesting & data collector
    - Startegy optimizer improvements
    - Web interface : reset & remove in config
    - Web interface : home with custum dashboard

# Bug fixes :
    - StopLossOrders set negative portfolio when backtesting
    - Fix default config interface problems

Changelog for 0.1.6_1-beta
====================
*Released date : August 1 2018*

# Concerned issues :
    #346 refactored tentacles and packages pages
    #347 initialized strategy optimizer page
    #350 [Web Interface] black theme
    #355 [Bug] StopLossOrders set negative portfolio when backtesting 

# New features :
    - Web Interface : Strategy optimizer

# Bug fixes :
    - Fix mutli symbols backtesting

Changelog for 0.1.6-beta
====================
*Released date : July 30 2018*

**Warning** :
- Notification type changed : [See wiki notification page](https://github.com/Drakkar-Software/OctoBot/wiki/Notifications)

# Concerned issues :
    #310 [Web Interface] Notification configuration
    #335 [Notification] Refactor notification-type system
    #340 [Strategy optimizer] add trading mode and average trades count in final report
    #341 Web Interface] Currencies and services configuration
    #345 [Notification] Add web notification type

# New features :
    - Web Interface : Services, Exchange, Symbols configuration improvements
    - Improve Startegy optimizer

Changelog for 0.1.5_3-beta
====================
*Released date : July 26 2018*

**Warning** :
- All config keys with "_" changed to "-" (for example crypto_currencies -> crypto-currencies)

# Concerned issues :
    #312 [Web Interface] Services configuration
    #311 [Web Interface] Symbols configuration
    #334 [Strategy configuration] create a strategy configuration otpimizer

# New features :
    - Web Interface : Services & Symbols configuration
    - Startegy optimizer
    - Encrypter command

Changelog for 0.1.5_2-beta
====================
*Released date : July 24 2018*

**Warning** :
- You have to encrypt your exchange token : **please run python tools/temp_encrypt_tool.py**
- Notification type key changed from "type" to "notification_type"

# Concerned issues :
    #269 [Tool] Implement ConfigManager
    #307 [Tentacle Installation] Add new key in description
    #309 [Web Interface] Exchange configuration
    #331 [Security] Encrypt user api key

# New features :
    - Api key encryption
    - Web Interface : Exchange configuration
    
Changelog for 0.1.5_1-beta
====================
*Released date : July 17 2018*

# Concerned issues :
    #305 [Refactor] refactor overall code
    #318 [Candles management] adapt candles timestamp to have second timestamp everywhere
    #319 [Web interface] trades are displayed for all symbols, display only for the selected one
    #320 [Backtesting] do not start unecessary services on backtesting mode
    #322 [Web interface] Create portfolio page
    #323 [Web interface] Create orders page
    #324 [Web interface] Create trades page

# New features :
    - Backtesting multi symbol support improved
    - Backtesting report at the end of a backtesting
    - Web Interface : New pages (portfolio, orders, trades)
    
# Improvements:
    - Improved readability of web interface
    
# Bug fixes :
    - Backtesting trades timestamps were wrong on multi symbol backtesting

Changelog for 0.1.5-beta
====================
*Released date : July 15 2018*

# Concerned issues :
    #252 [OrderManager] "Timed Out" raised during _update_orders_status
    #265 [Web Interface] Create web evaluator_config.json edition interface
    #266 [Web Interface] Create web tentacles manager interface
    #270 [Web interface] Create advanced web interface
    #294 [Trader simulator] StopLoss orders triggered when they shouldn't
    #302 [Web Interface] setup architecture
    #304 [Trade Manager] Ensure get_average_market_profitability resilience
    #308 [Backtesting] Improve backtesting accuracy

# New features :
    - New features in web interface : tentacles configuration, trades displayed on Dashboard tob
    - Backtesting now fully operational
    - Optimized String operations

# Bug fixes :
    - Fixed rare exceptions on order notification through Telegram
    - Fixed backtesting randomness
    - Fixed wronly triggered orders in simulator mode
    
# Notes :
    - Deactivated Google stats indicator by default while looking for a request limit solution


Changelog for 0.1.4_4-beta
====================
*Released date : July 9 2018*

**Warning** :
- Re-install your tentacles

# Concerned issues :
    #265 [Web Interface] Create web evaluator_config.json edition interface
    #266 [Web Interface] Create web tentacles manager interface
    #288 [Binance Websocket] Handle exchange maintenance
    #289 [Profitability] Add market average change when displaying profitability
    #290 [TimeFrames] Ensure unsupported time frames by exchanges handling
    #294 [Trader simulator] StopLoss orders triggered when they shouldn't
    #299 [OrderCreator] change min digits handling

# New features :
    - New features in web interface : evaluator config, tentacles display
    - Market profitability calculation

# Bug fix :
    - Fix Binance websocket maintenance handling
    - Fix stop loss in simulator mode
    - Fix digits bugs

Changelog for 0.1.4_3-beta
====================
*Released date : July 3 2018*

**Warning** :
- Update your trading mode tentacles

# Concerned issues :
    #286 [Trading Mode] Refactoring

# New features :
    - Refactoring in trading mode that makes it multi symbol

Changelog for 0.1.4_2-beta
====================
*Released date : July 3 2018*

# Concerned issues :
    #281 [Tentacles] handle in development tentacles
    #283 [Tentacle Strategies & Trading Mode] add constants to config files

# New features :
    - In development tentacles
    - Strategies and Trading Mode config creation with tentacle creator

Changelog for 0.1.4_1-beta
====================
*Released date : July 1 2018*

# Concerned issues :
    #279 [Trading Modes] prepare bot for high frequency treading mode 

Changelog for 0.1.4-beta
====================
*Released date : July 1 2018*

**Info** :
- New pip package to install "gitpython"

# Concerned issues :
    #188 [Exchange data] clean order list (closed and canceled) and other old data after 1 day
    #263 [TentacleCreator] review tentacle creation
    #273 [Web interface] Implement commands
    #274 installation issue
    #276 [Bug] Web interface exception when no exchange specified

# New features :
    - Update / Restart / Stop Octobot from Web interface

# Bug fix :
    - Fix tentacle Creator (-c)
    - Fix config no exchange or no cryptocurrency specified (web)

Changelog for 0.1.3_2-beta
====================
*Released date : June 27 2018*

# Concerned issues :
    #264 [Web Interface] Create web architecture
    #267 [Web interface] Manage octobot status
    #268 [Web Interface] Manage notification from bot
    #269 [Tool] Implement ConfigManager
    #270 [Web interface] Create advanced web interface

# New features :
    - Web interface skeleton
    - Notifications in web interface

# Bug fix :
    - Fix reddit reconnexion

Changelog for 0.1.3_1-beta
====================
*Released date : June 25 2018*

# Concerned issues :
    #251 [Tests] Improve tests coverage

# Bug fix :
    - Fix telegram commands
    - Fix exchange symbol data
    - Fix reddit watcher

Changelog for 0.1.3-beta
====================
*Released date : June 23 2018*

# Concerned issues :
    #251 [Tests] Improve tests coverage
    #254 [Tool] Tentacle creation tool

# New features :
    - Tentacle creation tool
    - High Frequency trading basics [see public tentacle](https://github.com/Drakkar-Software/OctoBot-Tentacles/issues/2)

Changelog for 0.1.2_4-beta
====================
*Released date : June 22 2018*

# Concerned issues :
    #256 Implement multi decider trading mode

# New features :
    - Multi-decider management for trading modes

# Bug fix :
    - Fix linux installer
    - Fix Subportfolio

Changelog for 0.1.2_3-beta
====================
*Released date : June 21 2018*

# Concerned issues :
    #232 [Performances] Add performance tests for evaluators
    #233 [Tentacles tests] add tentacles testing framework
    #234 [TentacleManager] harmonize packages, tentacles and modules naming
    #235 [TentacleManager] add progress info
    #250 [Trade creator] check market price orders in simulator
    #251 [Tests] Improve tests coverage

# New features :
    - Improvements in Tentacle Manager

# Bug fix :
    - Fix market order in simulator mode
    - Fix Rest exchange to support additional exchanges

Changelog for 0.1.2_2-beta
====================
*Released date : June 19 2018*

# Concerned issues :
    #193 [Bittrex] Test OctoBot on different exchanges
    #232 added performance tests for evaluator stress test
    #235 added progress info in tentacles manager
    #243 [Config] Fix Exception description
    #245 [TentacleManager] add confirm before delete files
    #247 [OrderCreator] test get_additional_dusts_to_quantity_if_necessary function

# New features :
    - OrderCreator : Take in account potentiel dust when creating order

# Bug fix :
    - Fix backtesting
    - Fix Rest exchange to support additional exchanges

Changelog for 0.1.2_1-beta
====================
*Released date : June 18 2018*

# Concerned issues :
    #216 Enable start/stop of strategies and their evaluators on demand

# New features :
    - Strategy linked tentacles activation and deactivation

# Bug fix :
    - Update order status deadlock when canceling order

Changelog for 0.1.2-beta
====================
*Released date : June 16 2018*

**Info** :
- New pip package to install "tulipy"
- config.json is now in Octobot's root folder

# Concerned issues :
    #214 [Time frames] Setup timeframes at OctoBot setup according to relevant strategies timeframe requirements
    #220 [Tentacle Manager] Implement updating command
    #224 [TA calulation] Study tulipindicators lib
    #225 [Telegram] add get strategies and modes command
    #226 [Data] Store symbol candles in dedicated class
    #229 [Tentacle Manager] add cleanup and help
    #230 [Architecture] Extract Tentacles and config from code folder
    #231 [Architecture] evaluator_config.json updated by Tentacle Manager

# New features :
    - Tentacle Management : update, versions management
    - Migrate from TA-lib indicators to tulipy
    - Telegram Interface new command
    - Architecture improvements

Changelog for 0.1.1-beta
====================
*Released date : June 8 2018*

# Concerned issues :
    #197 Add evaluator specific config in tentacle installation
    #211 [Order Management] set refresh period in OctoBot startup
    #212 [Tentacles management] add dependancies management
    #213 [Tentacles management] add tentacle removal system
    #215 [Trading mode] Add config management
    #217 [Trading Mode] Implement multiple mini creator (with part of pf)
   
# New features :
    - Tentacle Management : uninstall, requirements, configuration files
    
Changelog for 0.1.0_2-beta
====================
*Released date : June 3 2018*

**Info** : 
- Config : "mode" key added to "trader"

# Concerned issues :
    #198 [Order Creation] Implement new architecture
   
# New features :
    - Trading modes

Changelog for 0.1.0_1-beta
====================
*Released date : June 2 2018*

# Bug fix :
    #201 [Real trading] Fix bug when loading exchange current order

Changelog for 0.1.0-beta
====================
*Released date : June 1 2018*

**Info** : 
- Config : "packages" root key renamed to "tentacles"

# Concerned issues :
    #108 [RoadMap] format RoadMap into an attractive image
    #109 [RoadMap] add RoadMap tracker on ReadMe.md
    #136 [Tests] Improve trading tests coverage
    #139 [Tests] Improve evaluator management tests coverage
    #156 [Documentation] Add documentation for evaluator management classes
    #163 [Exchanges Tests] implement web sockets for binance tests
    #164 [ReadMe] make readme sexy !
    #174 Renaming CryptoBot to Octobot
    #181 [Telegram] Pause and resume trading
    #183 Can't create order when order already on exchange on bot start
    #186 [Twitter Interface] Some notifications are not sent to Twitter website

# New features :
    - Telegram pause / resume trading
    - Beautiful README and logo
    - Create roadmap
    - Improve tests coverage

# Bug fix :
    - Fix negative portfolio in simulation

Changelog for 0.0.12-alpha
====================
*Released date : May 26 2018*

**Info** : 
- Config : "data_collector" root key removed
- Backtesting : "file" root key changed to "files" as array
- Package Manager : need to perform `python3 start.py -p install all` to install evaluators

# Concerned issues :
    #84 [Environment] Create docker
    #86 [CI] Implement third party
    #139 [Tests] Improve evaluator management tests coverage
    #144 [Bug] Investigate version 0.0.11 negative simulated portfolio
    #145 [Datacollector] Implements multiple symbol
    #146 [Backtesting] Implement multi symbols
    #147 [Backtesting] Implement multi exchanges
    #148 [Backtesting] Implement better order manager backtesting features
    #151 [Services] log info message when started
    #152 [Wiki] complete wiki version 1
    #153 [Beta Version] Prepare beta version
    #154 [Exchanges] implement web sockets for binance exchange
    #155 [TA] improve real time evaluator
    #157 [Exchanges] manage websockets availability in exchange manager
    #158 [Order management] implement order callback update for websockets additionnaly to poll updates
    #159 added cyclic log file management
    #160 [Real Trader] taking exchanges symbol and minimum trade requirements into account
    #161 [Evaluators] Allows in run evaluator creation
    #162 [Services] Allows in run service creation
    #163 [Exchanges Tests] implement web sockets for binance tests
    #165 Bump matplotlib from 2.0 to 2.2.2
    #166 [Tests] Features testing
    #171 [Package Manager] Prototype
    #172 [Telegram Interface] No response when ask profitability
    #175 Add tests for order creation
    #176 [Package manager] implement advanced evaluators

# New features :
    - Multi symbols / exchanges data collector
    - Multi symbols backtesting
    - Wiki completed
    - Websocket management
    - Exchange management
    - Binance Websocket
    - Cyclic logging
    - Evaluator & Service restarting management
    - Package Manager
    - Windows installer
    
# Bug fix :
    - Improve code quality
    - Fix exception in order update_status when backtesting
    - Fix order fill bug in simulation
    - Fix telegram no response on /profitability command
    - Taking exchanges symbol and minimum trade requirements into account


Changelog for 0.0.11-alpha
====================
*Released date : May 11 2018*

**Info** : 
- Config : "simulator" root key changed to "trader_simulator"

**Warning** : 
- <span style="color:red">Real trading is in pre-alpha version</span>

# Concerned issues :
    #87  [Interface] Prototype telegram interface
    #132 [Web]: add portfolio view
    #133 [Backtesting] Implement report 
    #134 [Order Creation] Fix negative quantity 
    #135 [Simulation] Fix order and trades manager 
    #136 [Tests] Improve trading tests coverage
    #138 [Trading] Implement real trades
    #139 prepare evaluators tests
    #140 [Trading] Implement real portfolio management
    #141 [Trading] Implement real order management
    #142 [Timeframe manager] Implementation

# New features :
    - Web interface improvements
    - Telegram interface
    - Telegram notifications
    - Pretty Printer tool
    - Eval note expiration management
    - Beginning of real trading implementation
    - Multiple new tests to improve code coverage
    - TimeFrame Manager
    
# Bug fix :
    - Fixed trader simulation order creation
    - [Order Creation] Fix negative quantity 

Changelog for 0.0.10-alpha
====================
*Released date : May 5 2018*

# Concerned issues :
    #63 Calculate evaluator divergence note 
    #86 [CI] Implement third party
    #117 auto adapt symbol configuration for backtesting 
    #119 TA test architecture
    #120 [Backtesting] Test Zipline lib implementation
    #121 added sudden pump data and described bank data 
    #122 added test_reaction_to_over_bought_then_dip to all TA 
    #123 added rise after over-sold test for all TA
    #124 added flat trend tests on all TA 
    #125 [Notification] Double notification when an order linked is cancelled
    #127 Add in price graph and out price graph indicator list plot 
    #126 [Order] Too much canceled orders when RealTime Evaluators are created
    #128 [Notification] No notification of profitability
    #129 [Web] Create web interface prototype 

# New features :
    - Web interface prototype
    - Full TA patterns tests
    - Data Visualiser
    - Performance Analyser
    - Bot starter with options
    - Multiple new tests to improve code coverage
    
# Bug fix :
    - Fix risk logic with market orders
    - Fix notifications : only concerned symbol
    - Fix default config
    - Fix datavisualiser style
    - Fix RedditEvaluator overriden method param names
    - Fix portfolio profitability notification 


Changelog for 0.0.9-alpha
====================
*Released date : Apr 30 2018*

# Concerned issues :
    #20 added reddit service and started reddit dispatcher 
    #22 added webpage news retreiver 
    #47 backtesting 
    #76 data collector
    #92 [Evaluators] Enable / disable with config file
    #102 added advanced evaluator in dispatcher handler
    #103 [Portfolio] Implement pytests last 
    #104 Exchange Manager
    #105 fix cancel notification
    #107 factorized refresher threads into one per symbol
    #113 Fix portfolio bug management

# New features :
    - Backtesting
    - Data Collector
    - Data Collector Parser
    - Exchange Manager
    - New social evaluator (reddit, twitter posted media & websites)
    - Tests implementation and coverage
    
# Bug fix :
    - Fix Portfolio management
    - Fix critical bug on symbol evaluator
    - Fix critical bug in order creation
    - Fix trader join
    - Fix tests
    - Fix real time constants
    - Fix new dependency raspberry install
    - Fix realtime instant fluctuation evaluator pending note
    - Fix notification style end order
    - Fix portfolio concurrency access
    
Changelog for 0.0.8-alpha
====================
*Released date : Apr 24 2018*

# Concerned issues :
    #26 optimized moving average evaluator 
    #90 added can_create_order() method to check if an order is issuable
    #91 refactored dispatchers
    #93 [Profitability] Fix calculation error
    #97 [Order] Fix order cancel when state change
    #99 [Symbol evaluator] Symbol evaluator fail to manage multi exchanges
    #100 [Exchanges] Implement automatic instanciation of exchange when keys are in config.json


# New features :
    - New TA evaluators : DoubleMA, BollingerBand, ADX, MACD
    - Risk trading management (order price, order quantity, final state thresholds)

# Bug fix :
    - Fix constants in order creation
    - Fix order end notification
    - Fix Limit price 10% to 5% max
    - Fix gmail notifications
    - Fix evaluator final & add startup notification
    - Fix portfolio profitability
    - Fix order cancel when state change
    
Changelog for 0.0.7-alpha
====================
*Released date : Apr 21 2018*

# Concerned issues :
    #26 added bollinger momentum and advanced util management
    #48 [Portfolio] Manage availability of currencies
    #51 [Trade / Trade Simulator] Implement profitability
    #68 Create Advanced list manager
    #69 fix availability and create mail notification profitability
    #70 [Trading Simulator] Manage stop loss order / Create limit + stop loss 
    #72 add OrderManager per exchange 
    #73 Write exception into log file
    #76 refactor advanced util classes management 
    #83 Create CONTRIBUTING.md
    #85 issue templates 


# New features :
    - Advanced Manager
    - Order Manager
    - Portfolio currencies availability
    - Portfolio profitability measurement

# Bug fix :
    - Fix twitter notifications
    - Fix gmail notifications
    - Fix candle evaluator when no pattern is detected
    - Fix RealTime Evaluators creation
    
Changelog for 0.0.6-alpha
====================
*Released date : Apr 16 2018*

# Concerned issues :
    #15 fixed bollinger evaluator
    #24 Add twitter followed tweets
    #35 first implementation of current candle evaluator
    #63 divergence analysis
    #66 Manage versions / changelog


# New features :
    - Modular Services
    - Service Dispatcher (producer / client)
    - Sentiment Analyser

# Bug fix :
    - Fix twitter encoding
    - Fix twitter and google news evaluators
    - Fix bollinger analyser


Changelog for 0.0.5-alpha
====================
*Released date : Apr 12 2018*

# Concerned issues :
    #54 initialized loggers with only class names
    #55 [EvaluatorCreator] move evaluator creator's setters/getters to evaluator
    #56 [Portfolio][update_portfolio] add fees in currency part
    #57 documentation fix
    #58 removed permanent thread in final evaluator
    #59 [Strategy] Create TA relevancy by timeframe
    #61 [Evaluators] Init eval note with string to produce an exception

# New features :
    - Added twitter simple webhook
    - Implement twitter notification

# Bug fix :
    - Fix mail notification content
    - Fix twitter notification
    - Fix finalize when notify
