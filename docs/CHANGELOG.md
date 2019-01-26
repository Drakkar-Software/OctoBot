*It is strongly advised to perform an update of your tentacles after updating OctoBot.*

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
