*It is strongly advised to perform an update of your tentacles after updating OctoBot.*

Changelog for 0.1.4-beta
====================
*Released date : June 30 2018*

**Info** :
- New pip package to install "gitpython"

# Concerned issues :
    #263 [TentacleCreator] review tentacle creation
    #273 [Web interface] Implement commands

# New features :
    - Update / Restart / Stop Octobot from Web interface

# Bug fix :
    - Fix tentacle Creator (-c)

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
